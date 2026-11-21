"""The local tracker (11.1, SP-022, SP-027): the first adapter, a tracker kept in Solarpunk's own store, in tables of its
own (local_issues, local_comments, local_changes), so the sink and source are real and the contract suite every
adapter must pass has something to hold before a remote tracker exists. A person's edit in the tracker is recorded by
edit and read back by changes_since. It reads no other module's table (MOD-05)."""
import sqlite3
from datetime import datetime

from solarpunk.leaf.clock import utc
from solarpunk.leaf.tickets import OutboxEvent, RemoteChange
from solarpunk.tickets.adapter import UnknownTicket

PREFIX = "local:"
OPENED = "open"
CREATE_ISSUES = (
    "CREATE TABLE IF NOT EXISTS local_issues (issue_id INTEGER PRIMARY KEY, wo_id INTEGER NOT NULL UNIQUE,"
    " asset_id TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL, assignee TEXT NULL, updated TEXT NOT NULL)"
)
CREATE_COMMENTS = (
    "CREATE TABLE IF NOT EXISTS local_comments (comment_id INTEGER PRIMARY KEY, wo_id INTEGER NOT NULL,"
    " at TEXT NOT NULL, words TEXT NOT NULL)"
)
CREATE_CHANGES = (
    "CREATE TABLE IF NOT EXISTS local_changes (change_id INTEGER PRIMARY KEY, wo_id INTEGER NOT NULL, kind TEXT NOT NULL,"
    " at TEXT NOT NULL, author TEXT NOT NULL, detail TEXT NOT NULL)"
)


def schema() -> tuple[str, ...]:
    """The local tracker's tables, for leaf.store.apply: an issue per work order, its comments, people's changes."""
    return (CREATE_ISSUES, CREATE_COMMENTS, CREATE_CHANGES)


class LocalTracker:
    """The local tracker over a store: LocalTracker(conn).create(the outage's create event) is "local:1"."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Keeps the store and makes the tracker's tables where they are missing."""
        self.conn = conn
        for statement in schema():
            conn.execute(statement)
        conn.commit()

    def ref_of(self, wo_id: int) -> str:
        """The reference of a work order's issue: "local:1"; one never created raises UnknownTicket."""
        row = self.conn.execute("SELECT issue_id FROM local_issues WHERE wo_id = ?", (wo_id,)).fetchone()
        if row is None:
            raise UnknownTicket(f"work order {wo_id} is not in the tracker")
        return f"{PREFIX}{row[0]}"

    def issue(self, wo_id: int) -> tuple[str, str, str | None]:
        """An issue as the tracker shows it: (title, status, assignee)."""
        self.ref_of(wo_id)
        title, status, assignee = self.conn.execute("SELECT title, status, assignee FROM local_issues WHERE wo_id = ?",
                                                    (wo_id,)).fetchone()
        return title, status, assignee

    def comments(self, wo_id: int) -> tuple[str, ...]:
        """An issue's comments as the tracker shows them, oldest first."""
        rows = self.conn.execute("SELECT words FROM local_comments WHERE wo_id = ? ORDER BY comment_id", (wo_id,))
        return tuple(words for (words,) in rows)

    def create(self, event: OutboxEvent) -> str:
        """Opens an issue for the work order, or gives back the one opened before (a repeated delivery)."""
        self.conn.execute("INSERT OR IGNORE INTO local_issues (wo_id, asset_id, title, status, updated) VALUES"
                          " (?, ?, ?, ?, ?)", (event.wo_id, event.asset_id, event.detail, OPENED, utc(event.moment).isoformat()))
        self.conn.commit()
        return self.ref_of(event.wo_id)

    def update(self, event: OutboxEvent) -> None:
        """Sets the working assignee the event names ("assignee crew B"; "assignee nobody" clears it)."""
        self.ref_of(event.wo_id)
        name = event.detail.removeprefix("assignee ")
        self.set(event, "assignee", None if name == "nobody" else name)

    def comment(self, event: OutboxEvent) -> None:
        """Adds the event's comment, "<author>: <words>", as written."""
        self.ref_of(event.wo_id)
        self.conn.execute("INSERT INTO local_comments (wo_id, at, words) VALUES (?, ?, ?)",
                          (event.wo_id, utc(event.moment).isoformat(), event.detail))
        self.conn.commit()

    def transition(self, event: OutboxEvent) -> None:
        """Moves the issue to the status the event names, or closes it when the event carries a root cause."""
        self.ref_of(event.wo_id)
        self.set(event, "status", "closed" if event.detail.startswith("RC-") else event.detail)

    def set(self, event: OutboxEvent, column: str, value: str | None) -> None:
        """Sets one of the issue's two changeable columns and its updated instant."""
        if column not in ("assignee", "status"):
            raise ValueError(f"the local tracker has no column {column!r} to set")
        self.conn.execute(f"UPDATE local_issues SET {column} = ?, updated = ? WHERE wo_id = ?",
                          (value, utc(event.moment).isoformat(), event.wo_id))
        self.conn.commit()

    def edit(self, wo_id: int, kind: str, author: str, detail: str, moment: datetime) -> RemoteChange:
        """Records a change a person made in the tracker, for changes_since to give back: edit(1, "comment", "crew B",
        "on site", 12:05 UTC)."""
        ref = self.ref_of(wo_id)
        self.conn.execute("INSERT INTO local_changes (wo_id, kind, at, author, detail) VALUES (?, ?, ?, ?, ?)",
                          (wo_id, kind, utc(moment).isoformat(), author, detail))
        self.conn.commit()
        return RemoteChange(ref, wo_id, kind, utc(moment), author, detail)

    def changes_since(self, cursor: int) -> tuple[tuple[RemoteChange, ...], int]:
        """People's changes after cursor, oldest first, and the cursor after the last; none gives ((), cursor)."""
        rows = self.conn.execute("SELECT change_id, wo_id, kind, at, author, detail FROM local_changes"
                                 " WHERE change_id > ? ORDER BY change_id", (cursor,)).fetchall()
        changes = tuple(RemoteChange(self.ref_of(wo_id), wo_id, kind, datetime.fromisoformat(stamp), author, detail)
                        for _, wo_id, kind, stamp, author, detail in rows)
        return changes, (rows[-1][0] if rows else cursor)
