"""The database every module's tables live in: SQLite from the standard library, one file or memory, foreign keys on
(SP-004). A module owns its tables and offers them as schema statements; project applies them all in order."""
import sqlite3
from pathlib import Path

MEMORY = ":memory:"


def connect(path: str | Path = MEMORY) -> sqlite3.Connection:
    """An open connection with foreign keys enforced: connect().execute("PRAGMA foreign_keys").fetchone()[0] is 1."""
    connection = sqlite3.connect(str(path))
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def apply(connection: sqlite3.Connection, statements: tuple[str, ...]) -> None:
    """Runs each schema statement in order and commits: apply(c, ("CREATE TABLE t (x)",)) leaves table t."""
    for statement in statements:
        connection.execute(statement)
    connection.commit()
