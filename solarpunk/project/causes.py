"""A fault's root cause (7.8, SP-046), split from orchestrator.py: the words an engineer writes for why the fault
happened, checked as an assignment is (SP-015, SP-035), and the rule that a ticket on a fault closes only once they are
written. The ledger keeps every writing; the fault's cause is the latest."""
import sqlite3
from datetime import datetime

from solarpunk.faults import ledger
from solarpunk.faults.ledger import FaultCause
from solarpunk.project.engineers import check_engineer
from solarpunk.workorders.ledger import WorkOrder, WorkOrderError


class NoRootCause(WorkOrderError):
    """Raised for a ticket closed on a fault whose root cause is not yet written: NoRootCause("fault 4 has no root cause
    written: an engineer writes it before its ticket closes")."""


def write_fault_cause(conn: sqlite3.Connection, fault_id: int, cause: str, written_by: str, written_at: datetime,
                      recorded_by: str | None = None) -> FaultCause:
    """Appends the root cause an engineer writes for a fault, check_engineer passing them for the fault's asset and,
    when it is entered on their word, the operator in recorded_by: write_fault_cause(conn, 1, "worn fuse holder",
    "inverter@oahe.example", 10:20 UTC) gives that FaultCause; a later call supersedes it and erases nothing. A blank
    cause or an unknown fault raises LedgerError, a writer who is no engineer UnknownEngineer; each writes nothing."""
    # Decision: SP-046 (an engineer writes the root cause as free text, append-only); SP-035 (who counts as an engineer)
    fault = ledger.get(conn, fault_id)
    check_engineer(conn, written_by, fault.asset_id)
    entered = recorded_by.strip() if recorded_by is not None else None
    return ledger.write_cause(conn, fault_id, cause, written_by, written_at, entered or None)


def require_cause(conn: sqlite3.Connection, order: WorkOrder) -> None:
    """Refuses a close of an order on a fault whose root cause is blank: for order 1 on fault 4 with no cause written,
    NoRootCause; a preventive order, which has no fault, and an order whose fault has a cause pass, returning None."""
    # Decision: SP-046 (a ticket on a fault closes only once the fault's root cause is written)
    if order.fault_id is not None and ledger.cause_of(conn, order.fault_id) is None:
        raise NoRootCause(f"fault {order.fault_id} has no root cause written: an engineer writes it before its ticket closes")
