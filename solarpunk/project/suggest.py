"""Suggestions joined to the fleet and the ledger (7.4, SP-015): the scheduled run's failures raise the suggestions their
tests' rules name, a code an asset pushes is one from the device, and an engineer accepts one into a fault, through
assign_fault (the one door that requires an engineer), or dismisses it with a reason; either decision is an engineer's
as check_engineer has it (SP-035) and records the operator who entered it on the engineer's word. A suggestion
counts in status alone: yellow, never red, and no KPI reads it (the KPIs read the ledger)."""
import sqlite3
from datetime import datetime

from solarpunk.faults import ledger
from solarpunk.leaf.faults import Fault
from solarpunk.project.engineers import check_engineer
from solarpunk.project.orchestrator import assign_fault, check_fault, known
from solarpunk.remote import results as result_table
from solarpunk.remote import suggestions as suggestion_table
from solarpunk.remote.registry import discover
from solarpunk.remote.suggestions import DEVICE, Suggestion

PUSHED = "pushed by the asset"


def open_codes(conn: sqlite3.Connection, asset_id: str) -> set[str]:
    """The codes the asset carries open faults of, which no suggestion repeats: {"INV-001"} for an open INV-001."""
    return {fault.code for fault in ledger.by_asset(conn, asset_id) if fault.closed is None}


def suggest_from_run(conn: sqlite3.Connection, asset_ids: tuple[str, ...], run_at: datetime) -> tuple[Suggestion, ...]:
    """For each asset's latest results at run_at, every failure whose test's rule names a code raises that suggestion
    (or keeps the open one; no data suggests nothing, SP-039), unless the asset already carries an open fault of the code: the demo's run, OAHE-SEN-001's
    reachable failing, gives an open SEN-001 on it; OAHE-INV-002's INV-001 is already an open fault, so none."""
    # Decision: SP-015 (the tests' rules suggest; an engineer assigns)
    tests = discover()
    raised = []
    for asset_id in asset_ids:
        kind = known(conn, asset_id).kind
        for found in result_table.latest_for(conn, asset_id):
            test = tests.get(found.test_name)
            code = None if not found.failed or found.run_at != run_at or test is None else test.suggestion(kind)
            if code is not None and code not in open_codes(conn, asset_id):
                raised.append(suggestion_table.raise_suggestion(conn, asset_id, code, found.test_name, found.reason,
                                                                run_at))
    return tuple(raised)


def suggest_pushed(conn: sqlite3.Connection, asset_id: str, code: str, now: datetime) -> Suggestion:
    """A code an asset pushed, as a suggestion from the device (SP-015): suggest_pushed(conn, "OAHE-INV-001", "INV-001",
    10:10 UTC).source is "device"; an asset the fleet lacks raises UnknownAsset and a code the catalogue lacks
    UnknownFaultCode, as assign_fault would."""
    # Decision: SP-015 (a pushed code is a suggestion, superseding SP-008 in part)
    check_fault(conn, asset_id, code)
    return suggestion_table.raise_suggestion(conn, asset_id, code, DEVICE, PUSHED, now)


def accept_suggestion(conn: sqlite3.Connection, suggestion_id: int, engineer: str, recorded_by: str | None = None,
                      opened: datetime | None = None, read_at: int | None = None) -> Fault:
    """Opens the suggested fault as the engineer, entered by the operator when it was called in, opened at the
    suggestion's instant unless another is given, and marks the suggestion accepted with the fault's id and the
    operator: the demo's SEN-001 suggestion accepted by site@oahe.example gives an open SEN-001 fault assigned by
    site@oahe.example. A refusal (an engineer check_engineer refuses, a second open fault of the code) changes nothing; one no longer open raises
    SuggestionError, one read at an older version StaleWrite before any fault is opened (12.2)."""
    # Decision: SP-015 (only an engineer assigns; the suggestion keeps the link to the fault it became)
    found = suggestion_table.check_read(conn, suggestion_id, read_at)
    if found.state != suggestion_table.OPEN:
        raise suggestion_table.SuggestionError(f"suggestion {suggestion_id} is already {found.state}")
    fault = assign_fault(conn, found.asset_id, found.code, opened or found.raised_at, engineer, recorded_by)
    suggestion_table.mark_accepted(conn, suggestion_id, engineer, fault.fault_id, read_at, fault.recorded_by)
    return fault


def dismiss_suggestion(conn: sqlite3.Connection, suggestion_id: int, engineer: str, reason: str,
                       read_at: int | None = None, recorded_by: str | None = None) -> Suggestion:
    """Dismisses the suggestion as the engineer, with why, entered by the operator recorded_by names when it was called
    in: dismiss_suggestion(conn, 1, "site@oahe.example", "sensor cleaned").state is "dismissed"; an engineer
    check_engineer refuses raises UnknownEngineer, a suggestion the table lacks or a blank reason SuggestionError, one
    read at an older version StaleWrite (12.2), each changing nothing."""
    # Decision: SP-015 (a dismissal is an engineer's decision, recorded with who and why); SP-035 (and the operator)
    check_engineer(conn, engineer, suggestion_table.get(conn, suggestion_id).asset_id)
    entered = recorded_by.strip() if recorded_by is not None else None
    return suggestion_table.mark_dismissed(conn, suggestion_id, engineer, reason, read_at, entered or None)


def open_suggestions(conn: sqlite3.Connection, asset_id: str | None = None) -> tuple[Suggestion, ...]:
    """The open suggestions, of one asset (a device's first, then the newest) or of all: () before any run."""
    return suggestion_table.open_suggestions(conn, asset_id)
