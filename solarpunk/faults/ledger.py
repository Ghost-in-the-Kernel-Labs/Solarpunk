"""The fault ledger: the faults table, assigning a catalogue code to an asset, closing the fault, and the queries by
open, asset, code, period and repeat. Every stored code is one `lookup` accepts (Invariant: SOL-04); every instant is
stored as the ISO 8601 text of an aware UTC datetime and read back aware (Invariant: SOL-06). The asset id is not
checked against the assets table: project does that, since faults imports the leaf alone (MOD-05)."""
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from solarpunk.leaf import versions
from solarpunk.leaf.clock import Period, utc
from solarpunk.leaf.codes import lookup
from solarpunk.leaf.faults import UNRECORDED, Fault

SELECT_FAULTS = "SELECT fault_id, asset_id, code, opened, closed, assigned_by, recorded_by, version FROM faults"
# The columns SP-015 added, each with the statement that adds it to a table made before: upgrade() applies the missing.
LATER_COLUMNS = (
    ("assigned_by", "ALTER TABLE faults ADD COLUMN assigned_by TEXT NOT NULL DEFAULT 'unrecorded'"),
    ("recorded_by", "ALTER TABLE faults ADD COLUMN recorded_by TEXT NULL"),
    (versions.COLUMN, f"ALTER TABLE faults ADD COLUMN {versions.COLUMN_SQL}"),  # 12.2
)
CLOSE_FAULT = f"UPDATE faults SET closed = ?, {versions.BUMP} WHERE fault_id = ?"
# SP-046: a fault's root cause is free text an engineer writes, one row per writing, never updated or deleted; the
# fault's cause is its latest row, an earlier one superseded and still on record.
CREATE_CAUSES = (
    "CREATE TABLE IF NOT EXISTS fault_causes (cause_id INTEGER PRIMARY KEY, fault_id INTEGER NOT NULL, cause TEXT NOT NULL,"
    " written_by TEXT NOT NULL, written_at TEXT NOT NULL, recorded_by TEXT NULL)"
)
INSERT_CAUSE = "INSERT INTO fault_causes (fault_id, cause, written_by, written_at, recorded_by) VALUES (?, ?, ?, ?, ?)"
SELECT_CAUSES = ("SELECT fault_id, cause, written_by, written_at, recorded_by FROM fault_causes WHERE fault_id = ?"
                 " ORDER BY cause_id")
INSERT_FAULT = "INSERT INTO faults (asset_id, code, opened, assigned_by, recorded_by) VALUES (?, ?, ?, ?, ?)"


class LedgerError(ValueError):
    """Raised for a ledger refusal (a second open fault of one code on one asset, an unknown fault id, a close at or
    before the opening, a second close): LedgerError("fault 9 is not in the ledger")."""


def schema() -> tuple[str, ...]:
    """The ledger's schema statements, for leaf.store.apply: schema()[0] starts with "CREATE TABLE faults"."""
    return (
        "CREATE TABLE faults (fault_id INTEGER PRIMARY KEY, asset_id TEXT NOT NULL, code TEXT NOT NULL,"
        " opened TEXT NOT NULL, closed TEXT NULL, assigned_by TEXT NOT NULL DEFAULT 'unrecorded', recorded_by TEXT NULL,"
        f" {versions.COLUMN_SQL})",
    )


def causes_schema() -> tuple[str, ...]:
    """The fault_causes table's statement (SP-046), for leaf.store.apply: causes_schema()[0] starts with "CREATE TABLE IF NOT
    EXISTS fault_causes"; a store made before 7.8 gains it on reopening."""
    return (CREATE_CAUSES,)


@dataclass(frozen=True)
class FaultCause:
    """One writing of a fault's root cause: FaultCause(1, "worn fuse holder", "tech@oahe.example", 10:20 UTC, None); the
    text is the engineer's own words, never a code; recorded_by names the operator who entered it on the engineer's word."""

    fault_id: int
    cause: str
    written_by: str
    written_at: datetime
    recorded_by: str | None = None


def upgrade(conn: sqlite3.Connection) -> None:
    """Adds to a faults table made before SP-015 the columns it lacks, its old rows reading assigned_by "unrecorded";
    a table that has them is left as it is: upgrade(conn) twice changes nothing the second time."""
    present = {row[1] for row in conn.execute("PRAGMA table_info(faults)")}
    for name, statement in LATER_COLUMNS:
        if name not in present:
            conn.execute(statement)
    conn.commit()


def _stamp(moment: datetime) -> str:
    """The stored text of a UTC instant: _stamp(at(2026, 6, 1, 10, 10)) is "2026-06-01T10:10:00+00:00"; a naive one
    raises NotUtc."""
    # Invariant: SOL-06
    return utc(moment).isoformat()


def _instant(text: str | None) -> datetime | None:
    """The aware instant stored text names: _instant("2026-06-01T10:10:00+00:00") is at(2026, 6, 1, 10, 10);
    _instant(None) is None."""
    return None if text is None else datetime.fromisoformat(text)


def _select(conn: sqlite3.Connection, where: str, params: tuple[str | int | None, ...]) -> tuple[Fault, ...]:
    """The faults a WHERE clause (with its leading space) picks, in fault_id order: _select(conn, " WHERE code = ?", ("INV-001",)) holds every
    INV-001 fault; _select(conn, "", ()) holds them all."""
    rows = conn.execute(SELECT_FAULTS + where + " ORDER BY fault_id", params).fetchall()
    faults = []
    for fault_id, asset_id, code, opened, closed, assigned_by, recorded_by, version in rows:
        faults.append(Fault(fault_id, asset_id, code, datetime.fromisoformat(opened), _instant(closed), assigned_by,
                            recorded_by, version))
    return tuple(faults)


def _get(conn: sqlite3.Connection, fault_id: int | None) -> Fault:
    """The fault with this id: _get(conn, 1).fault_id is 1; _get(conn, 9) on a ledger without it raises LedgerError."""
    found = _select(conn, " WHERE fault_id = ?", (fault_id,))
    if not found:
        raise LedgerError(f"fault {fault_id} is not in the ledger")
    return found[0]


def assign(conn: sqlite3.Connection, asset_id: str, code: str, opened: datetime, assigned_by: str = UNRECORDED,
           recorded_by: str | None = None) -> Fault:
    """Opens a fault of a catalogue code on an asset, stored with who assigned it (whether that is an engineer is
    project's check, SP-015): assign(conn, "OAHE-INV-003", "INV-001", 10:10 UTC) is Fault(1, "OAHE-INV-003", "INV-001",
    10:10 UTC, None, "unrecorded", None). Refuses an unknown code (UnknownFaultCode), a naive or non-UTC
    instant (NotUtc) and a second open fault of the code on the asset (LedgerError)."""
    # Invariant: SOL-04
    lookup(code)
    stamp = _stamp(opened)
    clash = _select(conn, " WHERE asset_id = ? AND code = ? AND closed IS NULL", (asset_id, code))
    if clash:
        raise LedgerError(f"{asset_id} already carries open fault {clash[0].fault_id} of {code}")
    cursor = conn.execute(INSERT_FAULT, (asset_id, code, stamp, assigned_by, recorded_by))
    conn.commit()
    return _get(conn, cursor.lastrowid)


def close(conn: sqlite3.Connection, fault_id: int, closed: datetime, read_at: int | None = None) -> Fault:
    """Closes an open fault and raises its version: close(conn, 1, 10:30 UTC) is Fault(1, "OAHE-INV-003", "INV-001",
    10:10 UTC, 10:30 UTC) at version 2. Refuses a naive or non-UTC instant (NotUtc), an unknown fault id, a close at or
    before the opening and a second close (LedgerError), and a fault read at an older version (StaleWrite, 12.2)."""
    stamp = _stamp(closed)
    fault = _get(conn, fault_id)
    versions.check(f"fault {fault_id}", fault.version, read_at)
    if fault.closed is not None:
        raise LedgerError(f"fault {fault_id} is already closed")
    if closed <= fault.opened:
        raise LedgerError(f"fault {fault_id} cannot close at {stamp}, at or before it opened")
    conn.execute(CLOSE_FAULT, (stamp, fault_id))
    conn.commit()
    return _get(conn, fault_id)


def open_faults(conn: sqlite3.Connection) -> tuple[Fault, ...]:
    """Every fault not yet closed, in fault_id order: with fault 1 closed and fault 2 open, open_faults(conn) is (fault 2,)."""
    return _select(conn, " WHERE closed IS NULL", ())


def by_asset(conn: sqlite3.Connection, asset_id: str) -> tuple[Fault, ...]:
    """Every fault an asset carried or carries, in fault_id order: by_asset(conn, "OAHE-INV-003") holds its faults alone."""
    return _select(conn, " WHERE asset_id = ?", (asset_id,))


def by_code(conn: sqlite3.Connection, code: str) -> tuple[Fault, ...]:
    """Every fault of a catalogue code, in fault_id order: by_code(conn, "INV-001") holds the INV-001 faults alone;
    by_code(conn, "INV-999") raises UnknownFaultCode rather than answer an empty tuple."""
    # Invariant: SOL-04
    lookup(code)
    return _select(conn, " WHERE code = ?", (code,))


def in_period(conn: sqlite3.Connection, period: Period) -> tuple[Fault, ...]:
    """The faults whose [opened, closed) overlaps the period, an open one when it opened before the period's end, in
    fault_id order: for Period(10:00, 11:00), a fault over [09:00, 10:00) is out and one over [09:00, 10:05) is in."""
    found = []
    for fault in _select(conn, "", ()):
        if fault.opened < period.end and (fault.closed is None or fault.closed > period.start):
            found.append(fault)
    return tuple(found)


def repeated(conn: sqlite3.Connection, period: Period, at_least: int) -> tuple[tuple[str, str, int], ...]:
    """(asset_id, code, count) for each pair assigned at least `at_least` times with opened inside the period, most
    repeated first, then by asset_id and code: three INV-001 faults on OAHE-INV-003 in June give
    repeated(conn, june, 2) == (("OAHE-INV-003", "INV-001", 3),). The preventive-action signal."""
    counts = Counter((fault.asset_id, fault.code) for fault in _select(conn, "", ()) if period.start <= fault.opened < period.end)
    pairs = [(asset_id, code, count) for (asset_id, code), count in counts.items() if count >= at_least]
    return tuple(sorted(pairs, key=lambda pair: (-pair[2], pair[0], pair[1])))


def get(conn: sqlite3.Connection, fault_id: int) -> Fault:
    """The fault with this id: get(conn, 1).fault_id is 1; get(conn, 9) on a ledger without it raises LedgerError."""
    return _get(conn, fault_id)


def write_cause(conn: sqlite3.Connection, fault_id: int, cause: str, written_by: str, written_at: datetime,
                recorded_by: str | None = None) -> FaultCause:
    """Appends one writing of a fault's root cause, who and when beside it, and returns it: write_cause(conn, 1, "worn
    fuse holder", "tech@oahe.example", 10:20 UTC) is FaultCause(1, "worn fuse holder", "tech@oahe.example", 10:20 UTC,
    None). A later writing supersedes an earlier one without erasing it (causes_of keeps both). Refuses, writing
    nothing, a blank or whitespace-only cause, an unknown fault id (LedgerError) and a naive or non-UTC instant (NotUtc);
    whether the writer is an engineer is project's check (SP-035)."""
    # Decision: SP-046 (a root cause is free text an engineer writes, kept append-only)
    stamp = _stamp(written_at)
    _get(conn, fault_id)
    text = cause.strip()
    if not text:
        raise LedgerError(f"fault {fault_id} needs a root cause written in words, not a blank")
    conn.execute(INSERT_CAUSE, (fault_id, text, written_by, stamp, recorded_by))
    conn.commit()
    return causes_of(conn, fault_id)[-1]


def causes_of(conn: sqlite3.Connection, fault_id: int) -> tuple[FaultCause, ...]:
    """Every writing of a fault's root cause, oldest first: after "worn fuse" and then "worn fuse holder",
    causes_of(conn, 1) holds both; a fault never written gives (). An unknown fault id raises LedgerError."""
    _get(conn, fault_id)
    return tuple(FaultCause(found, text, written_by, datetime.fromisoformat(stamp), recorded)
                 for found, text, written_by, stamp, recorded in conn.execute(SELECT_CAUSES, (fault_id,)))


def cause_of(conn: sqlite3.Connection, fault_id: int) -> FaultCause | None:
    """The fault's root cause, its latest writing, or None while blank: cause_of(conn, 1).cause is "worn fuse holder"
    after the two writings of causes_of's example; a fault never written gives None."""
    written = causes_of(conn, fault_id)
    return written[-1] if written else None
