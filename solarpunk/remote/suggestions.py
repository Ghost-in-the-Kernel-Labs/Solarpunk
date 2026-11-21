"""The suggestions table, read only since 7.7 (SP-046, superseding SP-015 in part): what a store made before 7.7
suggested, open, accepted or dismissed as it was left. Nothing writes to it now: a failing remote test and a pushed
code raise a fault themselves, and nobody accepts or dismisses anything. The module offers its schema (a new store
still makes the table, so an old store and a new one read the same) and its reads; project applies the schema. It
imports the leaf alone (MOD-05)."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from solarpunk.leaf import versions
from solarpunk.leaf.clock import Period, utc

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
BY_ID = f"SELECT {COLUMNS} FROM suggestions WHERE suggestion_id = ?"
OPEN_ALL = f"SELECT {COLUMNS} FROM suggestions WHERE state = 'open' ORDER BY asset_id, source != 'device', raised_at DESC, suggestion_id"
OPEN_FOR = (f"SELECT {COLUMNS} FROM suggestions WHERE state = 'open' AND asset_id = ?"
            " ORDER BY source != 'device', raised_at DESC, suggestion_id")


class SuggestionError(ValueError):
    """Raised for a suggestion the table does not hold:
    SuggestionError("suggestion 9 is not in the table")."""


@dataclass(frozen=True)
class Suggestion:
    """One suggestion: Suggestion(1, "OAHE-SEN-001", "SEN-001", "reachable", "127.0.0.1:9 is unreachable", 13:00 UTC,
    "open", None, None, None); source is the test that raised it, or "device" for a pushed code; decided_by, fault_id and
    dismissal are set on one an engineer decided before 7.7, and recorded_by when an operator entered that."""

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
    version: int = 1  # 12.2: raised by one when an engineer decided it, before 7.7
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


def open_suggestions(conn: sqlite3.Connection, asset_id: str | None = None) -> tuple[Suggestion, ...]:
    """The open suggestions, of one asset or of all by asset, a device's first, then the newest: after a pushed SEN-001
    and a run's suggestion on OAHE-SEN-001, open_suggestions(conn, "OAHE-SEN-001")[0].source is "device"."""
    rows = conn.execute(OPEN_ALL).fetchall() if asset_id is None else conn.execute(OPEN_FOR, (asset_id,)).fetchall()
    return tuple(_row(row) for row in rows)


def raised_in(conn: sqlite3.Connection, period: Period) -> tuple[Suggestion, ...]:
    """Every suggestion raised inside the half-open period, open, accepted or dismissed, in suggestion_id order (SOL-15:
    a dismissed suggestion was raised all the same); () in a store made since 7.7."""
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
