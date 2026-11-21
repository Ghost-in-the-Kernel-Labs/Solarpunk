"""The asset window's ticket panel (11.2, SOL-14): the asset's open ticket in one line (its priority, status and two
targets) and its history, one line per move with who made it (SP-035), then Acknowledge; a comment with its author
and Comment; what was done and Resolve, which resolves and closes in one act and closes the fault once its root cause is written (project.resolve_ticket; the cause is written in the asset window, SP-046). A refusal is said in
the panel's own line, never swallowed. Each act names the version of the ticket the panel drew (12.2, SOL-16): one
changed since by someone else is refused with SOL-16's words, and Refresh rereads it. Every act is the account signed
in (12.4): its comments are its own and it has no "By" box; a store with no accounts keeps "By". Every string comes
from ticket_text.py; the class only lays them out."""
import sqlite3
import tkinter as tk
from collections.abc import Callable
from datetime import datetime, timezone
from tkinter import ttk

from solarpunk import project
from solarpunk.ui import cells, ticket_text

TITLE = "Ticket"
ACKNOWLEDGE = "Acknowledge"
COMMENT = "Comment"
RESOLVE = "Resolve"
BY = "By"
DONE = "What was done"
RED_TEXT = "#c0392b"
NO_TICKET_TO_ACT_ON = "this asset has no open ticket"


class TicketPanel(ttk.Frame):
    """The panel inside an asset window: TicketPanel(window, conn, "OAHE-INV-002", changed) shows the demo outage's
    ticket; changed is called after each act, so the window and the fleet reread the store; account is the one signed
    in (None in a store with none)."""

    def __init__(self, parent: tk.Misc, conn: sqlite3.Connection, asset_id: str, changed: Callable[[], None],
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 account: project.Account | None = None) -> None:
        """Lays out the line and the three rows of acts."""
        super().__init__(parent)
        self.conn, self.asset_id, self.changed, self.now = conn, asset_id, changed, now
        self.account = account
        self.view: project.TicketView | None = None
        ttk.Label(self, text=TITLE).pack(fill="x")
        self.line = ttk.Label(self)
        self.line.pack(fill="x")
        self.history = ttk.Label(self, justify="left", anchor="w")
        self.history.pack(fill="x")
        first = self.row()
        self.ack_button = ttk.Button(first, text=ACKNOWLEDGE, command=lambda: self.act(self.acknowledge))
        self.ack_button.pack(side="left")
        self.by_box: ttk.Combobox | None = None
        if account is None:  # 12.4: signed in, the comment is the account's own
            ttk.Label(first, text=BY).pack(side="left", padx=(12, 4))
            self.by_box = ttk.Combobox(first, values=project.known_engineers(conn), width=26)
            self.by_box.pack(side="left")
        self.comment_box = ttk.Entry(first, width=34)
        self.comment_box.pack(side="left", padx=4)
        self.comment_button = ttk.Button(first, text=COMMENT, command=lambda: self.act(self.comment))
        self.comment_button.pack(side="left")
        second = self.row()
        ttk.Label(second, text=DONE).pack(side="left")
        self.done_box = ttk.Entry(second, width=30)
        self.done_box.pack(side="left", padx=4)
        self.resolve_button = ttk.Button(second, text=RESOLVE, command=lambda: self.act(self.resolve))
        self.resolve_button.pack(side="left")
        last = self.row()
        self.message = tk.Label(last, anchor="w", foreground=RED_TEXT)
        self.message.pack(side="left", fill="x", expand=True)
        self.refresh_button = ttk.Button(last, text=cells.REFRESH, command=self.reload)
        self.refresh_button.pack(side="right")

    def row(self) -> ttk.Frame:
        """One row of the panel, packed."""
        frame = ttk.Frame(self)
        frame.pack(fill="x", pady=2)
        return frame

    def refresh(self) -> None:
        """Rereads the asset's open ticket and writes its line and its history (none with no open ticket)."""
        views = [v for v in project.tickets_by_target(self.conn, self.now()) if v.ticket.asset_id == self.asset_id]
        self.view = views[0] if views else None
        self.line.configure(text=ticket_text.panel_line(self.view))
        moves = () if self.view is None else project.ticket_moves(self.conn, self.view.ticket.wo_id)
        self.history.configure(text="" if self.view is None else ticket_text.history_text(moves))

    def reload(self) -> None:
        """Refresh (12.2): clears the message line, rereads the ticket and calls changed, so the window redraws too;
        nothing typed is sent again."""
        self.message.configure(text="")
        self.refresh()
        self.changed()

    def read_at(self) -> int | None:
        """The version of the ticket the panel drew, which every act names (12.2): a stale one is refused."""
        # Decision: SP-028 (a write from a screen names the version it read)
        return None if self.view is None else self.view.ticket.version

    def act(self, deed: Callable[[int], object]) -> None:
        """Does one act on the open ticket, then rereads and calls changed; a refusal goes to the message line."""
        if self.view is None:
            self.message.configure(text=NO_TICKET_TO_ACT_ON)
            return
        try:
            deed(self.view.ticket.wo_id)
        except ValueError as refusal:
            self.message.configure(text=str(refusal))
            return
        self.message.configure(text="")
        self.refresh()
        self.changed()

    def acknowledge(self, wo_id: int) -> object:
        """Acknowledge: the open ticket moves to acknowledged now."""
        return project.move_ticket_as(self.conn, self.account, wo_id, project.TicketStatus.ACKNOWLEDGED, self.now(),
                                      read_at=self.read_at())

    def comment(self, wo_id: int) -> object:
        """Comment: the words, by the account signed in (or the address in By, with no accounts), now; kept as
        written, the box then emptied."""
        by = None if self.by_box is None else self.by_box.get()
        found = project.comment_on_ticket_as(self.conn, self.account, wo_id, self.now(), self.comment_box.get(), by)
        self.comment_box.delete(0, "end")
        return found

    def resolve(self, wo_id: int) -> object:
        """Resolve: what was done, resolved and closed now; a fault with no root cause written yet refuses it (SP-046)."""
        return project.resolve_ticket_as(self.conn, self.account, wo_id, self.done_box.get(), self.now(), self.read_at())
