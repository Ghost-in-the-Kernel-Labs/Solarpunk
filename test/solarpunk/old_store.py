"""A store made before 7.7 (SP-046): its suggestions, as they were left. Nothing in the product writes a suggestion now,
so a test that needs one inserts the row the old code would have stored."""
import sqlite3
from datetime import datetime

from solarpunk.remote.suggestions import Suggestion, get

INSERT = ("INSERT INTO suggestions (asset_id, code, source, reason, raised_at, state, decided_by, fault_id, dismissal)"
          " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")


def old_suggestion(conn: sqlite3.Connection, asset_id: str, code: str, raised_at: datetime, source: str = "device",
                   reason: str = "pushed by the asset", state: str = "open", decided_by: str | None = None,
                   fault_id: int | None = None, dismissal: str | None = None) -> Suggestion:
    """The suggestion row a store made before 7.7 holds: old_suggestion(conn, "OAHE-SEN-001", "SEN-001", 13:00 UTC) is the
    open Suggestion from "device"; state "accepted" or "dismissed" with who and why is one an engineer decided."""
    cursor = conn.execute(INSERT, (asset_id, code, source, reason, raised_at.isoformat(), state, decided_by, fault_id,
                                   dismissal))
    conn.commit()
    return get(conn, cursor.lastrowid)
