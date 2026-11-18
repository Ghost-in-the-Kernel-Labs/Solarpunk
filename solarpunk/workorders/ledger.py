"""The work-order ledger: the work_orders table, opening a corrective order from a fault or a preventive one on its
own, closing it with a root-cause code, and the queries by open, asset and repeated cause. Every stored root cause is
one `lookup_root_cause` accepts (SP-011, the pattern of SOL-04); every instant is stored as the ISO 8601 text of an
aware UTC datetime and read back aware (Invariant: SOL-06). Neither the asset id nor the fault id is checked against
its table: project does that, since workorders imports the leaf alone (MOD-05)."""
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from solarpunk.leaf.clock import Period, utc
from solarpunk.leaf.root_causes import RootCause, lookup_root_cause

CORRECTIVE = "corrective"
PREVENTIVE = "preventive"
CREATE_TABLE = (
    "CREATE TABLE work_orders (wo_id INTEGER PRIMARY KEY, asset_id TEXT NOT NULL, fault_id INTEGER NULL,"
    " kind TEXT NOT NULL CHECK (kind IN ('corrective', 'preventive')), opened TEXT NOT NULL, closed TEXT NULL,"
    " root_cause TEXT NULL, note TEXT NOT NULL)"
)
SELECT_ORDERS = "SELECT wo_id, asset_id, fault_id, kind, opened, closed, root_cause, note FROM work_orders"
INSERT_ORDER = "INSERT INTO work_orders (asset_id, fault_id, kind, opened, note) VALUES (?, ?, ?, ?, ?)"
CLOSE_ORDER = "UPDATE work_orders SET closed = ?, root_cause = ? WHERE wo_id = ?"
BY_ID = " WHERE wo_id = ?"
OPEN_FOR_FAULT = " WHERE fault_id = ? AND kind = 'corrective' AND closed IS NULL"
STILL_OPEN = " WHERE closed IS NULL"
OF_ASSET = " WHERE asset_id = ?"
CLOSED_WITH_CAUSE = " WHERE closed IS NOT NULL"
IN_ID_ORDER = " ORDER BY wo_id"


@dataclass(frozen=True)
class WorkOrder:
    """One row of the ledger: WorkOrder(1, "OAHE-INV-003", 4, "corrective", 10:10 UTC, None, None, "replace fuse") is
    an open corrective order for fault 4; a preventive one has fault_id None; a closed one carries its RootCause."""

    wo_id: int
    asset_id: str
    fault_id: int | None
    kind: str
    opened: datetime
    closed: datetime | None
    root_cause: RootCause | None
    note: str


class WorkOrderError(ValueError):
    """Raised for a ledger refusal (a second open corrective order for one fault, an unknown order id, a close at or
    before the opening, a second close): WorkOrderError("work order 9 is not in the ledger")."""


def schema() -> tuple[str, ...]:
    """The ledger's schema statements, for leaf.store.apply: schema()[0] starts with "CREATE TABLE work_orders"."""
    return (CREATE_TABLE,)


def _stamp(moment: datetime) -> str:
    """The stored text of a UTC instant: _stamp(at(2026, 6, 1, 10, 10)) is "2026-06-01T10:10:00+00:00"; a naive one
    raises NotUtc."""
    # Invariant: SOL-06
    return utc(moment).isoformat()


def _select(conn: sqlite3.Connection, where: str, params: tuple[str | int | None, ...]) -> tuple[WorkOrder, ...]:
    """The orders a WHERE clause (with its leading space) picks, in wo_id order: _select(conn, STILL_OPEN, ()) holds
    every open order; _select(conn, "", ()) holds them all."""
    rows = conn.execute(SELECT_ORDERS + where + IN_ID_ORDER, params).fetchall()
    found = []
    for wo_id, asset_id, fault_id, kind, opened, closed, cause, note in rows:
        closed_at = None if closed is None else datetime.fromisoformat(closed)
        root_cause = None if cause is None else lookup_root_cause(cause)
        found.append(WorkOrder(wo_id, asset_id, fault_id, kind, datetime.fromisoformat(opened), closed_at, root_cause, note))
    return tuple(found)


def get(conn: sqlite3.Connection, wo_id: int | None) -> WorkOrder:
    """The order with this id: get(conn, 1).wo_id is 1; get(conn, 9) on a ledger without it raises WorkOrderError."""
    found = _select(conn, BY_ID, (wo_id,))
    if not found:
        raise WorkOrderError(f"work order {wo_id} is not in the ledger")
    return found[0]


def _insert(conn: sqlite3.Connection, asset_id: str, fault_id: int | None, kind: str, opened: str, note: str) -> WorkOrder:
    """Stores one open order and returns it: _insert(conn, "OAHE-INV-003", None, "preventive", "2026-06-01T10:10:00+00:00",
    "clean") is WorkOrder(1, "OAHE-INV-003", None, "preventive", 10:10 UTC, None, None, "clean")."""
    cursor = conn.execute(INSERT_ORDER, (asset_id, fault_id, kind, opened, note))
    conn.commit()
    return get(conn, cursor.lastrowid)


def open_corrective(conn: sqlite3.Connection, asset_id: str, fault_id: int, opened: datetime, note: str) -> WorkOrder:
    """Opens a corrective order for a fault on an asset: open_corrective(conn, "OAHE-INV-003", 4, 10:10 UTC, "fuse") is
    WorkOrder(1, "OAHE-INV-003", 4, "corrective", 10:10 UTC, None, None, "fuse"). Refuses a naive or non-UTC instant
    (NotUtc) and a second open corrective order for the same fault (WorkOrderError)."""
    stamp = _stamp(opened)
    clash = _select(conn, OPEN_FOR_FAULT, (fault_id,))
    if clash:
        raise WorkOrderError(f"fault {fault_id} already has open work order {clash[0].wo_id}")
    return _insert(conn, asset_id, fault_id, CORRECTIVE, stamp, note)


def open_preventive(conn: sqlite3.Connection, asset_id: str, opened: datetime, note: str) -> WorkOrder:
    """Opens a preventive order on an asset, with no fault: open_preventive(conn, "OAHE-TRK-001", 10:10 UTC, "grease")
    is WorkOrder(1, "OAHE-TRK-001", None, "preventive", 10:10 UTC, None, None, "grease"); a naive instant raises NotUtc."""
    return _insert(conn, asset_id, None, PREVENTIVE, _stamp(opened), note)


def close(conn: sqlite3.Connection, wo_id: int, root_cause: str, closed: datetime) -> WorkOrder:
    """Closes an open order with its root-cause code: close(conn, 1, "RC-COMPONENT", 10:30 UTC) gives the order with
    closed 10:30 UTC and root_cause RootCause.COMPONENT. Refuses, writing nothing, a code outside the list
    (UnknownRootCause), a naive instant (NotUtc), an unknown order id, a close at or before the opening and a second
    close (WorkOrderError)."""
    # Invariant: SOL-04's rule for causes (SP-011): no order closes without a code from the closed list
    cause = lookup_root_cause(root_cause)
    stamp = _stamp(closed)
    order = get(conn, wo_id)
    if order.closed is not None:
        raise WorkOrderError(f"work order {wo_id} is already closed")
    if closed <= order.opened:
        raise WorkOrderError(f"work order {wo_id} cannot close at {stamp}, at or before it opened")
    conn.execute(CLOSE_ORDER, (stamp, cause.value, wo_id))
    conn.commit()
    return get(conn, wo_id)


def open_orders(conn: sqlite3.Connection) -> tuple[WorkOrder, ...]:
    """Every order not yet closed, in wo_id order: with order 1 closed and order 2 open, open_orders(conn) is (order 2,)."""
    return _select(conn, STILL_OPEN, ())


def by_asset(conn: sqlite3.Connection, asset_id: str) -> tuple[WorkOrder, ...]:
    """Every order an asset had or has, in wo_id order: by_asset(conn, "OAHE-INV-003") holds its orders alone."""
    return _select(conn, OF_ASSET, (asset_id,))


def repeated_causes(conn: sqlite3.Connection, period: Period, at_least: int) -> tuple[tuple[str, str, int], ...]:
    """(asset_id, root-cause code, count) for each pair closed at least `at_least` times inside the period, most first,
    then by asset_id and code: three orders on OAHE-INV-003 closed in June with RC-COMPONENT give
    repeated_causes(conn, june, 2) == (("OAHE-INV-003", "RC-COMPONENT", 3),). The root-cause analysis as a query."""
    counts = Counter(
        (order.asset_id, order.root_cause.value)
        for order in _select(conn, CLOSED_WITH_CAUSE, ())
        if order.closed is not None and order.root_cause is not None and period.start <= order.closed < period.end
    )
    pairs = [(asset_id, code, count) for (asset_id, code), count in counts.items() if count >= at_least]
    return tuple(sorted(pairs, key=lambda pair: (-pair[2], pair[0], pair[1])))
