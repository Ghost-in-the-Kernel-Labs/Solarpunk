"""The suggestions table (7.4, SP-015): a likely fault a failing remote test's rules name, or a code an asset pushed,
waiting for an engineer. A suggestion is never a fault: an engineer accepts it (project opens the fault, through the one
door that requires an engineer, and the suggestion keeps its id) or dismisses it with a reason, and either is recorded
with who, and the operator who entered it on the engineer's word (SP-035). One open suggestion per asset and code: raising the same one again returns the open one. The module offers
its schema; project applies it. It imports the leaf alone (MOD-05)."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from solarpunk.leaf import versions
from solarpunk.leaf.clock import Period, utc
from solarpunk.leaf.codes import lookup

DEVICE = "device"
OPEN = "open"
ACCEPTED = "accepted"
DISMISSED = "dismissed"
RECORDED_BY = "recorded_by"
RECORDED_BY_SQL = "recorded_by TEXT NULL"  # 12.4, SP-035: the operator who entered a decision on an engineer's word
# The SQL lives here, at module level, where mutmut does not reach (docs/MUTATION.md, J-008).
SCHEMA = (
    "CREATE TABLE suggestions ("
    " suggestion_id INTEGER PRIMARY KEY,"
    " asset_id TEXT NOT NULL,"
    " code TEXT NOT NULL,"
    " source TEXT NOT NULL,"
    " reason TEXT NOT NULL,"
    " raised_at TEXT NOT NULL,"
    " state TEXT NOT NULL DEFAULT 'open',"
    " decided_by TEXT NULL,"
    " fault_id INTEGER NULL,"
    " dismissal TEXT NULL,"
    f" {versions.COLUMN_SQL},"
    f" {RECORDED_BY_SQL})",
)
COLUMNS = ("suggestion_id, asset_id, code, source, reason, raised_at, state, decided_by, fault_id, dismissal, version,"
           " recorded_by")
INSERT = "INSERT INTO suggestions (asset_id, code, source, reason, raised_at) VALUES (?, ?, ?, ?, ?)"
BY_ID = f"SELECT {COLUMNS} FROM suggestions WHERE suggestion_id = ?"
OPEN_OF = f"SELECT {COLUMNS} FROM suggestions WHERE state = 'open' AND asset_id = ? AND code = ?"
OPEN_ALL = f"SELECT {COLUMNS} FROM suggestions WHERE state = 'open' ORDER BY asset_id, source != 'device', raised_at DESC, suggestion_id"
OPEN_FOR = (f"SELECT {COLUMNS} FROM suggestions WHERE state = 'open' AND asset_id = ?"
            " ORDER BY source != 'device', raised_at DESC, suggestion_id")
ACCEPT = (f"UPDATE suggestions SET state = 'accepted', decided_by = ?, recorded_by = ?, fault_id = ?, {versions.BUMP}"
          " WHERE suggestion_id = ? AND state = 'open'")
DISMISS = (f"UPDATE suggestions SET state = 'dismissed', decided_by = ?, recorded_by = ?, dismissal = ?, {versions.BUMP}"
           " WHERE suggestion_id = ? AND state = 'open'")


class SuggestionError(ValueError):
    """Raised for a suggestion the table does not hold or that is no longer open, or a dismissal with no reason:
    SuggestionError("suggestion 9 is not in the table")."""


@dataclass(frozen=True)
class Suggestion:
    """One suggestion: Suggestion(1, "OAHE-SEN-001", "SEN-001", "reachable", "127.0.0.1:9 is unreachable", 13:00 UTC,
    "open", None, None, None); source is the test that raised it, or "device" for a pushed code; decided_by, fault_id and
    dismissal are set when an engineer acts, and recorded_by when an operator entered that on the engineer's word."""

    suggestion_id: int
    asset_id: str
    code: str
    source: str
    reason: str
    raised_at: datetime
    state: str
    decided_by: str | None
    fault_id: int | None
    dismissal: str | None
    version: int = 1  # 12.2: raised by one when an engineer accepts or dismisses it
    recorded_by: str | None = None  # 12.4, SP-035: the operator who entered the decision, None when the engineer did


def schema() -> tuple[str, ...]:
    """The statements that make the suggestions table: schema()[0] starts with "CREATE TABLE suggestions"."""
    return SCHEMA


def _row(row: tuple) -> Suggestion:
    """A stored row as a Suggestion, its instant aware: the raised_at text "2026-06-01T13:00:00+00:00" reads 13:00 UTC."""
    return Suggestion(row[0], row[1], row[2], row[3], row[4], datetime.fromisoformat(row[5]), *row[6:])


def get(conn: sqlite3.Connection, suggestion_id: int) -> Suggestion:
    """The suggestion with this id: get(conn, 1).code is "SEN-001"; an id the table lacks raises SuggestionError."""
    row = conn.execute(BY_ID, (suggestion_id,)).fetchone()
    if row is None:
        raise SuggestionError(f"suggestion {suggestion_id} is not in the table")
    return _row(row)


def raise_suggestion(conn: sqlite3.Connection, asset_id: str, code: str, source: str, reason: str,
                     raised_at: datetime) -> Suggestion:
    """Stores an open suggestion and returns it, or returns the open one of the same asset and code, unchanged (never
    two open of one code on one asset): raise_suggestion(conn, "OAHE-SEN-001", "SEN-001", "reachable", "…", 13:00 UTC)
    twice gives the same suggestion_id. A code the catalogue lacks raises UnknownFaultCode; a naive instant NotUtc."""
    # Decision: SP-015 (a test or a device suggests; nothing here opens a fault)
    lookup(code)
    stamp = utc(raised_at).isoformat()
    existing = conn.execute(OPEN_OF, (asset_id, code)).fetchone()
    if existing is not None:
        return _row(existing)
    cursor = conn.execute(INSERT, (asset_id, code, source, reason, stamp))
    conn.commit()
    return get(conn, cursor.lastrowid)


def open_suggestions(conn: sqlite3.Connection, asset_id: str | None = None) -> tuple[Suggestion, ...]:
    """The open suggestions, of one asset or of all by asset, a device's first, then the newest: after a pushed SEN-001
    and a run's suggestion on OAHE-SEN-001, open_suggestions(conn, "OAHE-SEN-001")[0].source is "device"."""
    rows = conn.execute(OPEN_ALL).fetchall() if asset_id is None else conn.execute(OPEN_FOR, (asset_id,)).fetchall()
    return tuple(_row(row) for row in rows)


def raised_in(conn: sqlite3.Connection, period: Period) -> tuple[Suggestion, ...]:
    """Every suggestion raised inside the half-open period, open, accepted or dismissed, in suggestion_id order (SOL-15:
    a dismissed suggestion was raised all the same)."""
    rows = conn.execute(f"SELECT {COLUMNS} FROM suggestions WHERE raised_at >= ? AND raised_at < ? ORDER BY suggestion_id",
                        (utc(period.start).isoformat(), utc(period.end).isoformat())).fetchall()
    return tuple(_row(row) for row in rows)


def upgrade(conn: sqlite3.Connection) -> None:
    """Gives a suggestions table made before 12.2 its version column, every suggestion at version 1, and one made
    before 12.4 its recorded_by column, empty (SP-035); a table that has them is left as it is."""
    versions.add_column(conn, "suggestions")
    if RECORDED_BY not in {row[1] for row in conn.execute("PRAGMA table_info(suggestions)")}:
        conn.execute(f"ALTER TABLE suggestions ADD COLUMN {RECORDED_BY_SQL}")
        conn.commit()


def check_read(conn: sqlite3.Connection, suggestion_id: int, read_at: int | None) -> Suggestion:
    """The suggestion, once a screen that read it at read_at may act on it (12.2): one changed since raises StaleWrite;
    project asks before it opens the fault an accept names, so a stale accept opens nothing."""
    current = get(conn, suggestion_id)
    versions.check(f"suggestion {suggestion_id}", current.version, read_at)
    return current


def _decide(conn: sqlite3.Connection, statement: str, values: tuple, suggestion_id: int,
            read_at: int | None) -> Suggestion:
    """Applies an accept or a dismiss to an open suggestion, raising its version, and returns it; one read at an older
    version raises StaleWrite, one no longer open SuggestionError naming its state, each changing nothing."""
    current = check_read(conn, suggestion_id, read_at)
    if current.state != OPEN:
        raise SuggestionError(f"suggestion {suggestion_id} is already {current.state}")
    conn.execute(statement, values)
    conn.commit()
    return get(conn, suggestion_id)


def mark_accepted(conn: sqlite3.Connection, suggestion_id: int, engineer: str, fault_id: int,
                  read_at: int | None = None, recorded_by: str | None = None) -> Suggestion:
    """Records that an engineer accepted the suggestion into the fault named, entered by the operator recorded_by names
    when it was called in: mark_accepted(conn, 1, "a@x", 3).state is "accepted" and .fault_id 3. Whether the engineer
    may, and the fault itself, are project's (SP-015)."""
    return _decide(conn, ACCEPT, (engineer, recorded_by, fault_id, suggestion_id), suggestion_id, read_at)


def mark_dismissed(conn: sqlite3.Connection, suggestion_id: int, engineer: str, reason: str,
                   read_at: int | None = None, recorded_by: str | None = None) -> Suggestion:
    """Records that an engineer dismissed the suggestion, and why, entered by the operator recorded_by names when it
    was called in (SP-035): mark_dismissed(conn, 1, "a@x", "sensor cleaned").state is "dismissed"; a blank reason
    raises SuggestionError, since a dismissal is a decision that says why."""
    if not reason.strip():
        raise SuggestionError(f"suggestion {suggestion_id}: a dismissal needs a reason")
    return _decide(conn, DISMISS, (engineer, recorded_by, reason.strip(), suggestion_id), suggestion_id, read_at)
