"""The "Open a ticket" control (7.9, SP-046): a button that opens the ticket for the chosen failed test result, never
for an asset, in the asset window's diagnostics and the Runs window's results. It asks its window for the result chosen
(None when none is a failure) and for who the act is recorded as, as the other engineer acts do (12.4: an engineer acts as
themself, an operator names the engineer, a store with no accounts "Assigned by" and "Entered by"); a result already in a
ticket shows that ticket. A refusal is said in the window's own line. Its words come from ticket_text.py; the classes
only lay them out (SP-010)."""
import sqlite3
import tkinter as tk
from collections.abc import Callable
from datetime import datetime, timezone
from tkinter import ttk

from solarpunk import project
from solarpunk.ui import cells, ticket_text

NamedBy = tuple[str | None, str | None, str | None]
CHOOSE_ENGINEER = "Choose the engineer who opens it: only an engineer opens a ticket (SP-046)."
CHOOSE_WORD = "Choose the engineer whose word it is: an operator opens a ticket on an engineer's word (SP-015)."
ENTERED_BY = "Entered by"


class Who(ttk.Frame):
    """The picker of who an act is recorded as: Who(parent, conn, account, asset_id).named(say) is (by, recorded_by,
    for_engineer) for project (cells.who_named), or None after saying what is missing; with an engineer, an admin or a
    viewer signed in there is no picker and the account acts."""

    def __init__(self, parent: tk.Misc, conn: sqlite3.Connection, account: project.Account | None, asset_id: str) -> None:
        """Lays out the picker cells.picker_title names, if any, and "Entered by" where the store has no accounts."""
        super().__init__(parent)
        self.account = account
        self.chosen: ttk.Combobox | None = None
        self.entered: ttk.Entry | None = None
        title = cells.picker_title(account)
        if title is None:
            return
        ttk.Label(self, text=title).pack(side="left")
        engineers = project.known_engineers(conn) if account is None else project.word_engineers(conn, asset_id)
        self.chosen = ttk.Combobox(self, values=engineers, state="readonly", width=30)
        self.chosen.pack(side="left", padx=4)
        if account is None:
            ttk.Label(self, text=ENTERED_BY).pack(side="left")
            self.entered = ttk.Entry(self, width=30)
            self.entered.pack(side="left", padx=4)

    def named(self, say: Callable[[str], None]) -> NamedBy | None:
        """Who the act is recorded as; with the picker shown and empty, says so through say and gives None."""
        chosen = "" if self.chosen is None else self.chosen.get()
        if self.chosen is not None and not chosen:
            say(CHOOSE_ENGINEER if self.account is None else CHOOSE_WORD)
            return None
        return cells.who_named(self.account, chosen, "" if self.entered is None else self.entered.get())


class OpenTicketButton(ttk.Button):
    """The control: OpenTicketButton(parent, conn, account, chosen, named, say, opened) reads the result chosen through
    chosen() (its id, or None), who acts through named(), and on a press opens the ticket now (UTC) and calls
    opened(found); a refusal goes to say, nothing written."""

    def __init__(self, parent: tk.Misc, conn: sqlite3.Connection, account: project.Account | None,
                 chosen: Callable[[], int | None], named: Callable[[], NamedBy | None], say: Callable[[str], None],
                 opened: Callable[[project.ResultTicket], None]) -> None:
        """Makes the button, labelled "Open a ticket"."""
        super().__init__(parent, text=ticket_text.OPEN_TICKET, command=self.press)
        self.conn, self.account, self.chosen, self.named, self.say, self.opened = conn, account, chosen, named, say, opened

    def press(self) -> None:
        """Opens the ticket for the chosen failed result as who is named, or shows the one it is in; no failed result
        chosen, no engineer chosen where one is asked, or a refusal, says so and changes nothing."""
        result_id = self.chosen()
        if result_id is None:
            self.say(ticket_text.CHOOSE_FAILED)
            return
        names = self.named()
        if names is None:
            return
        try:
            found = project.open_ticket_from_result_as(self.conn, self.account, result_id, datetime.now(timezone.utc), *names)
        except (ValueError, project.NotPermitted, project.UnknownEngineer) as refusal:
            self.say(f"Refused: {refusal}")
            return
        self.say("")
        self.opened(found)
