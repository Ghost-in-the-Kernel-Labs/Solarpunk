"""Faults from telemetry (7.7, SP-046, which supersedes SP-015 in part): a failing remote test raises its fault itself,
by its rule table's code or the catalogue's generic one, and a code an asset pushes is a fault from the device. Nobody
accepts or dismisses anything and no code changes a fault in place: a later fact is a new row. A fault carries the test
(assigned_by "test:reachable") or "device" that raised it, and is opened at the run's instant. The suggestions table
stays readable for a store made before 7.7 (open_suggestions); nothing writes to it."""
import sqlite3
from datetime import datetime

from solarpunk.faults import ledger
from solarpunk.leaf.codes import GENERIC_TEST_FAILURE
from solarpunk.leaf.faults import DEVICE_ASSIGNER, TEST_ASSIGNER, Fault
from solarpunk.project.orchestrator import check_fault, known
from solarpunk.remote import results as result_table
from solarpunk.remote import suggestions as suggestion_table
from solarpunk.remote.registry import discover
from solarpunk.remote.suggestions import Suggestion


def raise_fault(conn: sqlite3.Connection, asset_id: str, code: str, assigned_by: str, opened: datetime) -> Fault | None:
    """Opens the fault telemetry names, assigned by the test or device, at the instant; None when the asset already
    carries an open fault of the code, which the failure then joins (the ledger holds one open fault of a code on an
    asset): raise_fault(conn, "OAHE-SEN-001", "SEN-001", "test:reachable", 13:00 UTC).assigned_by is "test:reachable"."""
    # Decision: SP-046 (telemetry assigns the fault; a failure joins the open fault of its code, a later fact is a new row)
    if any(fault.code == code and fault.closed is None for fault in ledger.by_asset(conn, asset_id)):
        return None
    return ledger.assign(conn, asset_id, code, opened, assigned_by)


def faults_from_run(conn: sqlite3.Connection, asset_ids: tuple[str, ...], run_at: datetime) -> tuple[Fault, ...]:
    """For each asset's latest results at run_at, every failure raises a fault of its test's rule code, or the generic
    SIT-004 where the table names none; a pass and no data raise none (SP-039). The demo's run, OAHE-SEN-001's reachable
    failing, gives an open SEN-001 assigned by test:reachable; OAHE-INV-002's INV-001 is already open, so none."""
    # Decision: SP-046 (a failing remote test raises its fault itself; no data raises none)
    tests = discover()
    raised = []
    for asset_id in asset_ids:
        kind = known(conn, asset_id).kind
        for found in result_table.latest_for(conn, asset_id):
            if not found.failed or found.run_at != run_at:
                continue
            test = tests.get(found.test_name)
            code = (None if test is None else test.suggestion(kind)) or GENERIC_TEST_FAILURE
            fault = raise_fault(conn, asset_id, code, TEST_ASSIGNER.format(name=found.test_name), run_at)
            if fault is not None:
                raised.append(fault)
    return tuple(raised)


def fault_from_device(conn: sqlite3.Connection, asset_id: str, code: str, now: datetime) -> Fault:
    """A code an asset pushed, as a fault assigned by "device" (SP-046): fault_from_device(conn, "OAHE-INV-001",
    "INV-001", 10:10 UTC).assigned_by is "device"; pushed again while open it returns the open fault, unchanged; an
    asset the fleet lacks raises UnknownAsset and a code the catalogue lacks UnknownFaultCode."""
    # Decision: SP-046 (a pushed code raises a fault the way a failing test does, superseding SP-015 in part)
    check_fault(conn, asset_id, code)
    raised = raise_fault(conn, asset_id, code, DEVICE_ASSIGNER, now)
    if raised is not None:
        return raised
    return next(f for f in ledger.by_asset(conn, asset_id) if f.code == code and f.closed is None)


def open_suggestions(conn: sqlite3.Connection, asset_id: str | None = None) -> tuple[Suggestion, ...]:
    """The open suggestions a store made before 7.7 holds, of one asset or of all: () in a store made since."""
    return suggestion_table.open_suggestions(conn, asset_id)
