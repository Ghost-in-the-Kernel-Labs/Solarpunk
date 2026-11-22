"""The closed trail read back (13.17, SP-053): one call, ticket_trail, returns everything a ticket holds, read through
the ledgers and never kept apart from them: its fault (code, who assigned it), each root cause written with its author
and instant (the newest stands), its comments, its moves with their actors, its closeout words, and each failed result
it holds with that test's clauses and the next result of the same test on the same asset. A link the store lacks
(no result for an engineer's fault, no fault for a preventive order) is an empty part, never a guess. trail_text
words it in plain lines, the one text `solarpunk ticket show` prints and the Tickets window shows (SP-010)."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from solarpunk.faults import ledger as fault_ledger
from solarpunk.faults.ledger import FaultCause
from solarpunk.leaf.codes import lookup
from solarpunk.project.result_tickets import results_of_ticket
from solarpunk.project.runs import verdict_of
from solarpunk.remote import results as result_table
from solarpunk.remote.registry import discover
from solarpunk.remote.results import Recorded
from solarpunk.workorders import ledger as work_ledger
from solarpunk.workorders import tickets as ticket_ledger
from solarpunk.workorders.tickets import Comment, Move, Ticket

NOBODY = "nobody signed in"
NONE = "  none"
FAULT_LINE = "  fault {fault_id}  {code}  {meaning}  opened {opened}  closed {closed}"
STILL_OPEN = "open"
ASSIGNED = "  assigned by {who}"
ENTERED = "  entered by {who}"
CAUSE_LINE = "  {at}  {who}  {cause}{standing}"
STANDS = "  (stands)"
COMMENT_LINE = "  {at}  {who}  {body}"
MOVE_LINE = "  {at}  {status}  {who}"
CLOSEOUT_LINE = "  closed {at}  {words}"
NOT_CLOSED = "  not closed"
RESULT_LINE = "  result {result_id}  {test}  {at}  {reason}"
CLAUSES_LINE = "    clauses {clauses}"
NEXT_LINE = "    next result {result_id}  {at}  {verdict}  {reason}"
NO_NEXT = "    next result none"
HEADINGS = ("Fault", "Causes", "Comments", "Moves", "Closeout", "Results")


@dataclass(frozen=True)
class TrailFault:
    """The fault a ticket was opened on: TrailFault(1, "INV-001", "Inverter offline", "test:reachable", None, 11:30,
    14:00); assigned_by is "test:NAME" or "device" for telemetry, an engineer's email for a called-in fault, whose
    operator is recorded_by; closed None while open."""

    fault_id: int
    code: str
    meaning: str
    assigned_by: str
    recorded_by: str | None
    opened: datetime
    closed: datetime | None


@dataclass(frozen=True)
class TrailCause:
    """One writing of a fault's root cause and whether it stands (the newest does): with two writings the second is
    TrailCause(cause, True) and the first TrailCause(cause, False)."""

    cause: FaultCause
    stands: bool


@dataclass(frozen=True)
class TrailResult:
    """A failed result the ticket holds, its test's clauses (from the registry; () for a test whose module is gone) and
    the next stored result of that test on that asset, or None: reachable failed at 11:00, passing at 12:00, gives
    TrailResult(failed, ("55000-9.1",), passed)."""

    result: Recorded
    clauses: tuple[str, ...]
    next_result: Recorded | None


@dataclass(frozen=True)
class TicketTrail:
    """A ticket's whole trail (13.17): the ticket; its fault (None for a preventive order); the causes, oldest first;
    the comments and moves, oldest first; the closeout words (the evidence of the resolving move, None while it is
    not resolved); the failed results, oldest first, () for a ticket opened from an engineer's fault."""

    ticket: Ticket
    fault: TrailFault | None
    causes: tuple[TrailCause, ...]
    comments: tuple[Comment, ...]
    moves: tuple[Move, ...]
    closeout: str | None
    results: tuple[TrailResult, ...]


def trail_fault(conn: sqlite3.Connection, fault_id: int | None) -> TrailFault | None:
    """The fault of a work order's fault id, in the trail's terms; None for no fault id."""
    if fault_id is None:
        return None
    found = fault_ledger.get(conn, fault_id)
    return TrailFault(found.fault_id, found.code, lookup(found.code).meaning, found.assigned_by, found.recorded_by,
                      found.opened, found.closed)


def trail_causes(conn: sqlite3.Connection, fault_id: int | None) -> tuple[TrailCause, ...]:
    """Every root-cause writing of the fault, oldest first, the newest marked as the one that stands; () with none."""
    written = () if fault_id is None else fault_ledger.causes_of(conn, fault_id)
    return tuple(TrailCause(cause, index == len(written) - 1) for index, cause in enumerate(written))


def trail_results(conn: sqlite3.Connection, wo_id: int) -> tuple[TrailResult, ...]:
    """The failed results the ticket holds, each with its test's clauses and next result."""
    found = discover()
    return tuple(TrailResult(held, found[held.test_name].clauses if held.test_name in found else (),
                             result_table.next_after(conn, held))
                 for held in results_of_ticket(conn, wo_id))


def ticket_trail(conn: sqlite3.Connection, wo_id: int) -> TicketTrail:
    """A ticket's trail, closed or open: for the ticket opened on the demo's failed reachable, resolved and closed, it
    holds the fault, both causes, the comment, the moves, the closeout words, the failed result with its clauses and the
    passing result after it. An unknown work order raises WorkOrderError; nothing is written."""
    # Decision: SP-053 (a closed ticket reads back whole: its fault, cause, comments, closeout and results)
    found = ticket_ledger.ticket(conn, wo_id)
    fault_id = work_ledger.get(conn, wo_id).fault_id
    return TicketTrail(found, trail_fault(conn, fault_id), trail_causes(conn, fault_id),
                       ticket_ledger.comments(conn, wo_id), ticket_ledger.moves(conn, wo_id), found.evidence,
                       trail_results(conn, wo_id))


def fault_lines(found: TrailFault | None) -> list[str]:
    """The Fault part: "  fault 1  SIT-004  …  opened 2026-06-01T11:30:00+00:00  closed open", then who assigned it."""
    if found is None:
        return [NONE]
    closed = STILL_OPEN if found.closed is None else found.closed.isoformat()
    lines = [FAULT_LINE.format(fault_id=found.fault_id, code=found.code, meaning=found.meaning,
                               opened=found.opened.isoformat(), closed=closed), ASSIGNED.format(who=found.assigned_by)]
    return lines + ([ENTERED.format(who=found.recorded_by)] if found.recorded_by else [])


def result_lines(held: TrailResult) -> list[str]:
    """One failed result, its clauses and its next result: "  result 1  reachable  <at>  <reason>", "    clauses
    55000-9.1", "    next result 3  <at>  pass  <reason>" or "    next result none"."""
    found, after = held.result, held.next_result
    lines = [RESULT_LINE.format(result_id=found.result_id, test=found.test_name, at=found.run_at.isoformat(),
                                reason=found.reason), CLAUSES_LINE.format(clauses=", ".join(held.clauses) or "none")]
    if after is None:
        return lines + [NO_NEXT]
    return lines + [NEXT_LINE.format(result_id=after.result_id, at=after.run_at.isoformat(), verdict=verdict_of(after),
                                     reason=after.reason)]


def trail_lines(trail: TicketTrail) -> list[str]:
    """The trail as plain lines under the headings Fault, Causes, Comments, Moves, Closeout and Results; an empty part
    says "  none" (a ticket from an engineer's fault has no results)."""
    closeout = trail.ticket.closed
    parts = [
        fault_lines(trail.fault),
        [CAUSE_LINE.format(at=held.cause.written_at.isoformat(), who=held.cause.written_by, cause=held.cause.cause,
                           standing=STANDS if held.stands else "") for held in trail.causes],
        [COMMENT_LINE.format(at=held.moment.isoformat(), who=held.author, body=held.body) for held in trail.comments],
        [MOVE_LINE.format(at=held.moment.isoformat(), status=held.status.value, who=held.actor or NOBODY)
         for held in trail.moves],
        [NOT_CLOSED] if closeout is None else [CLOSEOUT_LINE.format(at=closeout.isoformat(), words=trail.closeout)],
        [line for held in trail.results for line in result_lines(held)],
    ]
    return [line for heading, part in zip(HEADINGS, parts) for line in (heading, *(part or [NONE]))]


def trail_text(trail: TicketTrail) -> str:
    """The trail's lines joined, the text `ticket show` prints and the Tickets window shows."""
    return "\n".join(trail_lines(trail))
