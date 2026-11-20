"""Versions (12.2, SOL-16, SP-026, SP-028): an asset, a fault, a suggestion and a ticket each carry a version, 1 when
made and raised by one in the same write as every change to it. A write made from a screen names the version it read;
one read at an older version is refused, writing nothing, so a stale screen never overwrites another person's change.
A write that names no version (the scheduled run, the command line acting on what it reads at once) is not checked.
Each record's version column lives in the module that owns the record; the rule, the refusal and the column's words
live here, so every module says them alike."""
import sqlite3

COLUMN = "version"
COLUMN_SQL = "version INTEGER NOT NULL DEFAULT 1"
BUMP = "version = version + 1"
FIRST = 1


class StaleWrite(ValueError):
    """Raised for a write read at an older version than the record holds: StaleWrite("ticket 1 changed by someone else
    since you read it; refresh")."""


def check(record: str, current: int, read_at: int | None) -> None:
    """Refuses a write read at another version than the record's: check("ticket 1", 2, 2) passes, check("ticket 1", 2,
    None) passes (no screen read it), check("ticket 1", 2, 1) raises StaleWrite("ticket 1 changed by someone else since
    you read it; refresh")."""
    # Invariant: SOL-16 (a stale write is refused, writing nothing)
    if read_at is not None and read_at != current:
        raise StaleWrite(f"{record} changed by someone else since you read it; refresh")


def add_column(conn: sqlite3.Connection, table: str) -> None:
    """Gives a table made before 12.2 its version column, every row at version 1; a table that has it is left as it
    is: add_column(conn, "faults") twice changes nothing the second time."""
    present = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if COLUMN not in present:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {COLUMN_SQL}")
        conn.commit()
