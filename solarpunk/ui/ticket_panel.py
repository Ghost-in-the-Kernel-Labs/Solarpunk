"""The asset window's ticket panel (11.2, SOL-14): the asset's open ticket in one line (its priority, status and two
targets), then Acknowledge; a comment with its author and Comment; what was done, a root cause from the closed list
and Resolve, which resolves and closes in one act and closes the fault (project.resolve_ticket). A refusal is said in
the panel's own line, never swallowed. Every string comes from ticket_text.py; the class only lays them out."""
import sqlite3
import tkinter as tk
from collections.abc import Callable
from datetime import datetime, timezone
from tkinter import ttk

from solarpunk import project
from solarpunk.ui import ticket_text

TITLE = "Ticket"
ACKNOWLEDGE = "Acknowledge"
COMMENT = "Comment"
RESOLVE = "Resolve"
BY = "By"
DONE = "What was done"
CAUSE = "Root cause"
RED_TEXT = "#c0392b"
NO_TICKET_TO_ACT_ON = "this asset has no open ticket"
CHOOSE_CAUSE = "choose a root cause from the list"


class TicketPanel(ttk.Frame):
    """The panel inside an asset window: TicketPanel(window, conn, "OAHE-INV-002", changed) shows the demo outage's
    ticket; changed is called after each act, so the window and the fleet reread the store."""

    def __init__(self, parent: tk.Misc, conn: sqlite3.Connection, asset_id: str, changed: Callable[[], None],
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        """Lays out the line and the three rows of acts."""
        super().__init__(parent)
        self.conn, self.asset_id, self.changed, self.now = conn, asset_id, changed, now
        self.view: project.TicketView | None = None
        ttk.Label(self, text=TITLE).pack(fill="x")
        self.line = ttk.Label(self)
        self.line.pack(fill="x")
        first = self.row()
        self.ack_button = ttk.Button(first, text=ACKNOWLEDGE, command=lambda: self.act(self.acknowledge))
        self.ack_button.pack(side="left")
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
        ttk.Label(second, text=CAUSE).pack(side="left")
        self.cause_box = ttk.Combobox(second, values=ticket_text.cause_choices(), state="readonly", width=34)
        self.cause_box.pack(side="left", padx=4)
        self.resolve_button = ttk.Button(second, text=RESOLVE, command=lambda: self.act(self.resolve))
        self.resolve_button.pack(side="left")
        self.message = tk.Label(self, anchor="w", foreground=RED_TEXT)
        self.message.pack(fill="x")

    def row(self) -> ttk.Frame:
        """One row of the panel, packed."""
        frame = ttk.Frame(self)
        frame.pack(fill="x", pady=2)
        return frame

    def refresh(self) -> None:
        """Rereads the asset's open ticket and writes its line."""
        views = [v for v in project.tickets_by_target(self.conn, self.now()) if v.ticket.asset_id == self.asset_id]
        self.view = views[0] if views else None
        self.line.configure(text=ticket_text.panel_line(self.view))

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
        return project.move_ticket(self.conn, wo_id, project.TicketStatus.ACKNOWLEDGED, self.now())

    def comment(self, wo_id: int) -> object:
        """Comment: the words, by the address in By, now; both kept as written, the box then emptied."""
        found = project.comment_on_ticket(self.conn, wo_id, self.by_box.get(), self.now(), self.comment_box.get())
        self.comment_box.delete(0, "end")
        return found

    def resolve(self, wo_id: int) -> object:
        """Resolve: what was done and the root cause chosen, resolved and closed now; no cause chosen is refused."""
        if not self.cause_box.get():
            raise ValueError(CHOOSE_CAUSE)
        return project.resolve_ticket(self.conn, wo_id, self.done_box.get(), ticket_text.cause_of(self.cause_box.get()),
                                      self.now())
