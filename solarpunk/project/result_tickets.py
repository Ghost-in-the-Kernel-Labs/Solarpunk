"""A ticket from a failed test result (7.9, SP-046), split from orchestrator.py: a ticket opens on one failed result (its
asset, test and run), not on the asset, and one ticket holds a streak of them. Two results are consecutive when they are
the same test on the same asset with no other result of that test between their run instants; a failure continues the
streak only when the result before it failed, a pass or no data ending it. A failure whose previous result is a
failure in a ticket joins that ticket as the run records it (join_streak); opening on a result already in a ticket
shows that ticket. The ticket is the corrective work order on the fault telemetry raised for the result."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from solarpunk.faults import ledger
from solarpunk.leaf.codes import GENERIC_TEST_FAILURE, AssetKind, lookup
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.tickets import priority_of
from solarpunk.project.engineers import check_engineer
from solarpunk.project.orchestrator import known
from solarpunk.project.runs import verdict_of
from solarpunk.remote import results as result_table
from solarpunk.remote.registry import discover
from solarpunk.remote.results import Recorded
from solarpunk.workorders import ledger as work_ledger
from solarpunk.workorders import ticket_results
from solarpunk.workorders.ledger import WorkOrderError
from solarpunk.workorders import tickets as ticket_ledger
from solarpunk.workorders.tickets import Ticket

OPENED = "open"
WORD_NOTE = "entered on the word of {engineer}"


class ResultTicketError(WorkOrderError):
    """Raised for a result a ticket cannot open on: ResultTicketError("result 9 is not stored"), a result that passed or
    had no data, or one with no fault raised for it; each writes nothing."""


@dataclass(frozen=True)
class ResultTicket:
    """What opening a ticket on a result gave: the ticket and whether this call opened it (False: it was already there
    and is shown), and the failed results it holds, oldest first."""

    ticket: Ticket
    opened: bool
    results: tuple[Recorded, ...]


def fault_code(kind: AssetKind, test_name: str) -> str:
    """The code a failing test raises on an asset kind: the test's Fault reaction's, else the catalogue's generic SIT-004
    (7.7, 13.4): fault_code(AssetKind.SENSOR, "reachable") is "SEN-001"; a test the folder lacks gives SIT-004."""
    # Decision: SP-046 (a failing remote test raises its fault by its Fault reaction's code or the generic one)
    test = discover().get(test_name)
    return GENERIC_TEST_FAILURE if test is None else test.fault_code(kind)


def fault_of(conn: sqlite3.Connection, found: Recorded) -> Fault | None:
    """The fault telemetry raised for a failed result: the fault of its code on its asset whose [opened, closed) covers
    the run instant, or None for a result stored before 7.7."""
    code = fault_code(known(conn, found.asset_id).kind, found.test_name)
    return next((fault for fault in ledger.by_asset(conn, found.asset_id) if fault.code == code and fault.opened <= found.run_at
                 and (fault.closed is None or found.run_at < fault.closed)), None)


def open_ticket_of(conn: sqlite3.Connection, result_id: int) -> int | None:
    """The ticket a result is in while that ticket is still open, or None: a closed ticket ends its streak, so a failure
    after it is a recurrence that starts a new one (J-123)."""
    wo_id = ticket_results.ticket_of(conn, result_id)
    return wo_id if wo_id is not None and work_ledger.get(conn, wo_id).closed is None else None


def join_streak(conn: sqlite3.Connection, found: Recorded) -> None:
    """Joins a failure just recorded to its streak's ticket: when the result before it is a failure linked to a ticket,
    the new result is linked to that ticket too; otherwise, and for a result already linked, nothing."""
    # Decision: SP-046 (a failure in the run right after a failure of the same test on the same asset joins its ticket)
    previous = result_table.previous_of(conn, found)
    if previous is None or not previous.failed or ticket_results.ticket_of(conn, found.result_id) is not None:
        return
    wo_id = open_ticket_of(conn, previous.result_id)
    if wo_id is not None:
        ticket_results.link(conn, wo_id, found.result_id)


def results_of_ticket(conn: sqlite3.Connection, wo_id: int) -> tuple[Recorded, ...]:
    """The failed results a ticket holds, oldest first: the ticket opened on the demo's failed reachable holds it; a
    ticket opened from a fault has ()."""
    held = (result_table.get(conn, result_id) for result_id in ticket_results.results_of(conn, wo_id))
    return tuple(sorted((found for found in held if found is not None), key=lambda result: (result.run_at, result.result_id)))


def ticket_of_result(conn: sqlite3.Connection, result_id: int) -> Ticket | None:
    """The ticket a result is in, or None: a failure that joined a streak gives the streak's ticket."""
    wo_id = ticket_results.ticket_of(conn, result_id)
    return None if wo_id is None else ticket_ledger.ticket(conn, wo_id)


def streak_of(conn: sqlite3.Connection, found: Recorded) -> tuple[list[Recorded], int | None]:
    """A failed result with the unlinked failures just before it in its streak (newest first), and the ticket the streak
    is already in, or None: the first failure of a run of three, none linked, gives ([it], None); the third, with the
    first in ticket 1, gives ([third, second], 1). A result already linked is its own ticket's."""
    chain, joined = [found], ticket_results.ticket_of(conn, found.result_id)
    while joined is None:
        previous = result_table.previous_of(conn, chain[-1])
        if previous is None or not previous.failed:
            break
        if ticket_results.ticket_of(conn, previous.result_id) is not None and open_ticket_of(conn, previous.result_id) is None:
            break  # a closed ticket ends the streak
        joined = open_ticket_of(conn, previous.result_id)
        if joined is None:
            chain.append(previous)
    return chain, joined


def open_ticket_from_result(conn: sqlite3.Connection, result_id: int, opened: datetime, assigned_by: str,
                            recorded_by: str | None = None) -> ResultTicket:
    """Opens the ticket for a failed result, or shows the one it is already in: on a failure not yet in a ticket it
    opens a corrective work order on the fault telemetry raised for it, priority from that code's severity, and links
    the result and the unlinked failures just before it in its streak; a streak reaching a failure that is in a ticket
    joins that ticket, opening none, and so does a fault that already has an open ticket; a closed ticket ends a
    streak. assigned_by is an engineer check_engineer passes, recorded_by the operator whose
    entry it is: the opening is logged as the engineer's, with a comment by the operator naming them. A result that is
    not stored, passed, had no data or has no fault raised for it raises ResultTicketError, writing nothing."""
    # Decision: SP-046 (a ticket opens from a failed test result; one ticket holds a streak of them)
    found = result_table.get(conn, result_id)
    if found is None:
        raise ResultTicketError(f"result {result_id} is not stored")
    if not found.failed:
        raise ResultTicketError(f"result {result_id} is a {verdict_of(found)}: a ticket opens on a failed result")
    check_engineer(conn, assigned_by, found.asset_id)
    chain, joined = streak_of(conn, found)
    fault = fault_of(conn, found) if joined is None else None
    if fault is not None and (on_fault := work_ledger.open_for_fault(conn, fault.fault_id)) is not None:
        joined = on_fault.wo_id  # the fault's open ticket is shown, never a second (J-123)
    if joined is not None:
        for member in chain:
            if ticket_results.ticket_of(conn, member.result_id) is None:
                ticket_results.link(conn, joined, member.result_id)
        return ResultTicket(ticket_ledger.ticket(conn, joined), False, results_of_ticket(conn, joined))
    if fault is None:
        raise ResultTicketError(f"result {result_id} has no fault raised for it: it was stored before faults came from tests")
    meaning = lookup(fault.code)
    note = f"{meaning.meaning} ({found.test_name} failed: {found.reason})"
    order = work_ledger.open_corrective(conn, found.asset_id, fault.fault_id, opened, note, priority_of(meaning.severity))
    for member in chain:
        ticket_results.link(conn, order.wo_id, member.result_id)
    work_ledger.record_move(conn, order.wo_id, OPENED, opened.isoformat(), assigned_by)
    conn.commit()
    if recorded_by:  # the operator's own comment
        ticket_ledger.comment(conn, order.wo_id, recorded_by, opened, WORD_NOTE.format(engineer=assigned_by))
    return ResultTicket(ticket_ledger.ticket(conn, order.wo_id), True,
                        results_of_ticket(conn, order.wo_id))
