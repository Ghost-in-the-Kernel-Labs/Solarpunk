"""The Tickets window (11.2, SOL-14, SP-022): every open ticket, the nearest target first, a ticket past a target in
red, its two targets in words with their due instants; Refresh rereads; a double click opens the ticket's asset
window, where it is acknowledged, commented on and resolved. Every string comes from ticket_text.py over
project.tickets_by_target; the class only lays them out (SP-010)."""
import sqlite3
import tkinter as tk
from collections.abc import Callable
from datetime import datetime, timezone
from tkinter import ttk

from solarpunk import project
from solarpunk.ui import ticket_text

TITLE = "Tickets"
REFRESH = "Refresh"
NONE_OPEN = "No open ticket"
BREACHED_TAG = "breached"
RED_TEXT = "#c0392b"
WIDTHS = (60, 120, 60, 90, 280, 280, 180)


class TicketsWindow(tk.Toplevel):
    """The open tickets: TicketsWindow(root, conn, open_asset) lists the demo's one outage ticket, red; now is the
    instant the targets are read at (the clock when not given)."""

    def __init__(self, parent: tk.Misc, conn: sqlite3.Connection, on_open_asset: Callable[[str], None],
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        """Lays out the table, Refresh and the line, then reads the tickets."""
        super().__init__(parent)
        self.conn = conn
        self.on_open_asset = on_open_asset
        self.now = now
        self.views: tuple[project.TicketView, ...] = ()
        self.title(TITLE)
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=6)
        self.refresh_button = ttk.Button(bar, text=REFRESH, command=self.fill)
        self.refresh_button.pack(side="left")
        self.line = ttk.Label(bar)
        self.line.pack(side="left", padx=8)
        self.tree = ttk.Treeview(self, columns=ticket_text.COLUMNS, show="headings", height=12, selectmode="browse")
        for column, heading, width in zip(ticket_text.COLUMNS, ticket_text.HEADINGS, WIDTHS):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, stretch=column == ticket_text.COLUMNS[-1])
        self.tree.tag_configure(BREACHED_TAG, foreground=RED_TEXT)
        self.tree.pack(fill="both", expand=True, padx=8, pady=4)
        self.tree.bind("<Double-1>", lambda _e: self.open_chosen())
        self.fill()

    def fill(self) -> None:
        """Rereads the open tickets at now, the nearest target first, a breached one red; with none, the line says so."""
        self.views = project.tickets_by_target(self.conn, self.now())
        self.tree.delete(*self.tree.get_children())
        for index, view in enumerate(self.views):
            self.tree.insert("", "end", iid=str(index), values=ticket_text.ticket_line(view),
                             tags=(BREACHED_TAG,) if view.breached else ())
        self.line.configure(text="" if self.views else NONE_OPEN)

    def open_chosen(self) -> None:
        """Opens the chosen ticket's asset window; with none chosen, nothing."""
        chosen = self.tree.selection()
        if chosen:
            self.on_open_asset(self.views[int(chosen[0])].ticket.asset_id)
