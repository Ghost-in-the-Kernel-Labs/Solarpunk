"""The asset window (3.2, SP-007): one asset's fields and status, its open faults with their meanings, its diagnostics
(6.4: every remote test of its kind with its latest result, failing first, then no data and never run, both grey,
then passing), its
earlier suggestions, read only (7.7, SP-046: a failing test or a device raises its fault itself, so nothing is accepted
or dismissed; a store made before 7.7 shows what it holds), a form
to assign a catalogue code, each open fault's root cause beside it and a box to write the selected fault's (7.8, SP-046:
free text an engineer writes, a new writing superseding the last), and the engineer with Save and Cancel. Who an act is recorded as is the account signed in
(12.4): an engineer acts as themself and sees no picker, an operator names the engineer "On the word of"; a store with
no accounts keeps "Assigned by" and "Entered by". A write names the version of the record the window drew (12.2): a
stale one is refused with SOL-16's words, and Refresh rereads and redraws. Every string and colour it shows comes from
a pure function in asset_text.py over one project call, so the tests check them without a display; the AssetWindow
class only lays them out (SP-010: it imports project and the leaf alone)."""
import sqlite3
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from tkinter import ttk

from solarpunk.leaf.assets import Asset
from solarpunk.ui import cells, ticket_text
from solarpunk.ui.open_ticket import OpenTicketButton
from solarpunk.ui.asset_text import (ASSIGN_TEXT, ASSIGN_TITLE, CANCEL_TEXT, CAUSE_TITLE, CAUSE_WRITE_TEXT, CHOOSE_CODE,
    CHOOSE_FAULT,
    CHOOSE_ENGINEER, CHOOSE_WORD, DIAGNOSTICS_TITLE, ENGINEER_TITLE,
    ENTERED_BY_TITLE, FAILING_TAG, FAULT_COLUMNS, FAULT_HEADINGS, FAULT_WIDTHS, GREEN_TEXT, GREY_TEXT, NOT_RUN_TAG,
    OPEN_FAULTS_TITLE, RED_TEXT, REFUSALS, RESULT_COLUMNS, RESULT_HEADINGS, RESULT_WIDTHS, SAVE_TEXT,
    SUGGESTED_TITLE, SUGGESTION_COLUMNS, SUGGESTION_HEADINGS, SUGGESTION_WIDTHS, chosen_code, code_labels, colour_of,
    fault_lines, field_lines, refusal_text, result_lines, row_tags, status_line, suggestion_lines, window_title)
from solarpunk.ui.ticket_panel import TicketPanel

from solarpunk import project
from solarpunk.ui.demo import Revival

REVIVE_TEXT = "Bring the feed back (demo)"


class AssetWindow(tk.Toplevel):
    """One asset's window: AssetWindow(root, conn, "OAHE-INV-001") titled "OAHE-INV-001 — Inverter 1"; on_change is
    called after a fault is assigned or the engineer saved, so the fleet window can reread the store; account is the
    one signed in (None in a store with none), which every act is recorded as (12.4). The demo passes a revival (13.16):
    for a dead inverter of its own the window shows "Bring the feed back (demo)"; with none the control does not exist. now
    gives the instant its acts are stamped (the wall clock; the demo's day in the demo, 13.15)."""

    def __init__(
        self, parent: tk.Misc, conn: sqlite3.Connection, asset_id: str, on_change: Callable[[], None] = lambda: None,
        account: project.Account | None = None, revival: Revival | None = None, now: Callable[[], datetime] = cells.wall_now,
    ) -> None:
        """Reads the asset once for its kind's codes, lays out the window and fills it: an id the fleet lacks raises
        UnknownAsset before any window is drawn."""
        detail = project.asset_detail(conn, asset_id)
        super().__init__(parent)
        self.conn = conn
        self.asset_id = asset_id
        self.on_change = on_change
        self.account = account
        self.revival, self.now = revival, now
        self.codes = project.codes_for_kind(detail.asset.kind)
        self.title(window_title(detail.asset))
        self.fields = ttk.Frame(self)
        self.fields.pack(fill="x", padx=8, pady=4)
        self.status_label = tk.Label(self, anchor="w")
        self.status_label.pack(fill="x", padx=8)
        self.fault_tree = self.tree(OPEN_FAULTS_TITLE, FAULT_COLUMNS, FAULT_HEADINGS)
        for column, width in zip(FAULT_COLUMNS, FAULT_WIDTHS):
            self.fault_tree.column(column, width=width, stretch=column == FAULT_COLUMNS[-1])
        self.result_tree = self.tree(DIAGNOSTICS_TITLE, RESULT_COLUMNS, RESULT_HEADINGS, height=len(detail.diagnostics) or 1)
        self.result_tree.tag_configure(FAILING_TAG, foreground=RED_TEXT)
        self.result_tree.tag_configure(NOT_RUN_TAG, foreground=GREY_TEXT)
        for column, width in zip(RESULT_COLUMNS, RESULT_WIDTHS):
            self.result_tree.column(column, width=width, stretch=column == RESULT_COLUMNS[-1])
        self.build_open_ticket()
        self.build_revival(detail.asset)
        self.suggestion_tree = self.tree(SUGGESTED_TITLE, SUGGESTION_COLUMNS, SUGGESTION_HEADINGS, height=3)
        for column, width in zip(SUGGESTION_COLUMNS, SUGGESTION_WIDTHS):
            self.suggestion_tree.column(column, width=width, stretch=column == "reason")
        self.build_assign()
        self.build_cause()
        self.build_engineer()
        self.ticket_panel = TicketPanel(self, conn, asset_id, self.ticket_changed, now, account)  # 11.2, 12.4
        self.ticket_panel.pack(fill="x", padx=8, pady=4)
        self.build_message_line()
        self.fill(detail)

    def build_message_line(self) -> None:
        """The message line under the ticket panel, where a refusal shows, and its Refresh button (12.2)."""
        last = ttk.Frame(self)
        last.pack(fill="x", padx=8, pady=4)
        self.message = tk.Label(last, anchor="w", foreground=RED_TEXT)
        self.message.pack(side="left", fill="x", expand=True)
        self.refresh_button = ttk.Button(last, text=cells.REFRESH, command=self.refresh)
        self.refresh_button.pack(side="right")

    def refresh(self) -> None:
        """Refresh (12.2, SOL-16): clears the message lines, rereads the asset and redraws; nothing is resubmitted."""
        self.message.configure(text="")
        self.ticket_panel.message.configure(text="")
        self.fill(project.asset_detail(self.conn, self.asset_id))

    def ticket_changed(self) -> None:
        """After a ticket act: the window rereads its asset and the fleet window the store."""
        self.fill(project.asset_detail(self.conn, self.asset_id))
        self.on_change()

    def tree(self, title: str, columns: tuple[str, ...], headings: tuple[str, ...], height: int = 4) -> ttk.Treeview:
        """A titled Treeview of named columns, height rows tall: tree("Diagnostics", ("test", …), ("Test", …), 7) shows
        the headings only."""
        ttk.Label(self, text=title).pack(fill="x", padx=8)
        tree = ttk.Treeview(self, columns=columns, show="headings", height=height)
        for column, heading in zip(columns, headings):
            tree.heading(column, text=heading)
        tree.pack(fill="both", expand=True, padx=8, pady=2)
        return tree

    def build_open_ticket(self) -> None:
        """The "Open a ticket" control under the diagnostics (7.9, SP-046): it acts on the failed result selected there,
        recorded as the engineer the "Assigned by" or "On the word of" picker names, and shows the ticket it opens."""
        row = self.ticket_row = ttk.Frame(self)
        row.pack(fill="x", padx=8, pady=2)
        self.open_ticket_button = OpenTicketButton(row, self.conn, self.account, self.chosen_result, self.named,
                                                   lambda words: self.message.configure(text=words, foreground=RED_TEXT), self.ticket_opened, self.now)
        self.open_ticket_button.pack(side="left")

    def build_revival(self, asset: Asset) -> None:
        """The demo's "Bring the feed back (demo)" button under the diagnostics (13.16): made only when the revival handed
        in offers this asset, so on any other store, and for OAHE-SEN-001, there is no such widget."""
        self.revive_button: ttk.Button | None = None
        if self.revival is None or not self.revival.offers(asset):
            return
        self.revive_button = ttk.Button(self.ticket_row, text=REVIVE_TEXT,
                                        command=self.bring_back)
        self.revive_button.pack(side="left", padx=8)

    def bring_back(self) -> None:
        """Starts the asset's feed and runs its tests once, then redraws this window and has the fleet window reread."""
        self.revival.bring_back(self.conn, self.asset_id)
        self.fill(project.asset_detail(self.conn, self.asset_id))
        self.on_change()

    def chosen_result(self) -> int | None:
        """The id of the failed result selected in the diagnostics, or None when none is selected or it is not a failure."""
        chosen = self.result_tree.selection()
        found = self.detail.diagnostics[int(chosen[0])] if chosen else None
        return None if found is None or found.state != "fail" else found.result_id

    def ticket_opened(self, found: project.ResultTicket) -> None:
        """After a ticket opened or shown from a result: the window rereads (its ticket panel shows it) and says so."""
        self.fill(project.asset_detail(self.conn, self.asset_id))
        self.on_change()
        self.message.configure(text=ticket_text.opened_text(found), foreground=GREEN_TEXT)

    def build_assign(self) -> None:
        """The "Assign a fault" row: a read-only dropdown of the kind's codes and the Assign button; under it the
        engineer picker cells.picker_title names, if any (12.4), and "Entered by" where the store has no accounts."""
        row = ttk.Frame(self)
        row.pack(fill="x", padx=8, pady=4)
        ttk.Label(row, text=ASSIGN_TITLE).pack(side="left")
        self.code_box = ttk.Combobox(row, values=code_labels(self.codes), state="readonly", width=60)
        self.code_box.pack(side="left", padx=4)
        self.assign_button = ttk.Button(row, text=ASSIGN_TEXT, command=self.assign)
        self.assign_button.pack(side="left")
        self.assigned_by_box: ttk.Combobox | None = None
        self.entered_by_box: ttk.Entry | None = None
        title = cells.picker_title(self.account)
        if title is None:
            return
        who = ttk.Frame(self)
        who.pack(fill="x", padx=8)
        ttk.Label(who, text=title).pack(side="left")
        engineers = (project.known_engineers(self.conn) if self.account is None
                     else project.word_engineers(self.conn, self.asset_id))
        self.assigned_by_box = ttk.Combobox(who, values=engineers, state="readonly", width=30)
        self.assigned_by_box.pack(side="left", padx=4)
        if self.account is None:
            ttk.Label(who, text=ENTERED_BY_TITLE).pack(side="left")
            self.entered_by_box = ttk.Entry(who, width=30)
            self.entered_by_box.pack(side="left", padx=4)

    def build_cause(self) -> None:
        """The "Root cause" row: a free-text box, never a list, and Write, which records it for the selected open fault."""
        row = ttk.Frame(self)
        row.pack(fill="x", padx=8, pady=4)
        ttk.Label(row, text=CAUSE_TITLE).pack(side="left")
        self.cause_box = ttk.Entry(row, width=60)
        self.cause_box.pack(side="left", padx=4)
        self.cause_button = ttk.Button(row, text=CAUSE_WRITE_TEXT, command=self.write_cause)
        self.cause_button.pack(side="left")

    def build_engineer(self) -> None:
        """The "Engineer" row: an editable dropdown of the fleet's known addresses, then Save and Cancel."""
        row = ttk.Frame(self)
        row.pack(fill="x", padx=8, pady=4)
        ttk.Label(row, text=ENGINEER_TITLE).pack(side="left")
        self.engineer_box = ttk.Combobox(row, values=project.known_engineers(self.conn), width=40)
        self.engineer_box.pack(side="left", padx=4)
        self.save_button = ttk.Button(row, text=SAVE_TEXT, command=self.save)
        self.save_button.pack(side="left")
        self.cancel_button = ttk.Button(row, text=CANCEL_TEXT, command=self.destroy)
        self.cancel_button.pack(side="left")

    def fill(self, detail: project.AssetDetail) -> None:
        """Writes one detail into the window: the field labels, the status in its colour, both trees, the engineer; the
        detail is kept, as every write names the versions it drew (12.2)."""
        self.detail = detail
        for old in self.fields.winfo_children():
            old.destroy()
        for line in field_lines(detail.asset):
            ttk.Label(self.fields, text=line, anchor="w").pack(fill="x")
        self.status_label.configure(text=status_line(detail.status), foreground=colour_of(detail.status))
        self.ticket_panel.refresh()
        self.fault_tree.delete(*self.fault_tree.get_children())
        for (found, _meaning), fault_row in zip(detail.open_faults, fault_lines(detail)):
            self.fault_tree.insert("", "end", iid=str(found.fault_id), values=fault_row)
        kept = self.result_tree.selection()  # the chosen result stays chosen across a reread
        self.result_tree.delete(*self.result_tree.get_children())
        self.result_tree.configure(height=len(detail.diagnostics) or 1)  # every test of the kind, none hidden (13.16)
        for index, result_row in enumerate(result_lines(detail)):
            self.result_tree.insert("", "end", iid=str(index), values=result_row, tags=row_tags(result_row))
        self.result_tree.selection_set(*(item for item in kept if self.result_tree.exists(item)))
        self.suggestion_tree.delete(*self.suggestion_tree.get_children())
        for found, line in zip(detail.suggestions, suggestion_lines(detail)):
            self.suggestion_tree.insert("", "end", iid=str(found.suggestion_id), values=line)
        self.engineer_box.set(detail.asset.engineer_email or "")

    def named(self) -> tuple[str | None, str | None, str | None] | None:
        """Who the act is recorded as, for project (cells.who_named), or None with the message asking for the engineer
        when the picker is shown and empty (12.4)."""
        chosen = "" if self.assigned_by_box is None else self.assigned_by_box.get()
        if self.assigned_by_box is not None and not chosen:
            self.message.configure(text=CHOOSE_ENGINEER if self.account is None else CHOOSE_WORD)
            return None
        entered = "" if self.entered_by_box is None else self.entered_by_box.get()
        return cells.who_named(self.account, chosen, entered)

    def assign(self) -> None:
        """Assigns the chosen code now (UTC) as the account signed in, or as named (SP-015, 12.4), rereads the window
        and calls on_change; no engineer chosen where one is asked, or a refusal (a second open INV-001, an admin),
        shows in the message line and changes nothing."""
        code = chosen_code(self.codes, self.code_box.current())
        if code is None:
            self.message.configure(text=CHOOSE_CODE)
            return
        names = self.named()
        if names is None:
            return
        try:
            project.assign_fault_as(self.conn, self.account, self.asset_id, code, self.now(), *names)
        except REFUSALS as refusal:
            self.message.configure(text=refusal_text(refusal))
            return
        self.message.configure(text="")
        self.fill(project.asset_detail(self.conn, self.asset_id))
        self.on_change()

    def write_cause(self) -> None:
        """Writes the box's words as the selected open fault's root cause (the only open fault when none is selected), now
        (UTC), as the account signed in or as named (SP-046, 12.4); a new writing supersedes the last and erases nothing. No
        fault chosen, no engineer chosen where one is asked, a blank or any refusal shows in the message line."""
        chosen = self.fault_tree.selection()
        if not chosen and len(self.detail.open_faults) == 1:
            chosen = (str(self.detail.open_faults[0][0].fault_id),)
        if not chosen:
            self.message.configure(text=CHOOSE_FAULT)
            return
        names = self.named()
        if names is None:
            return
        try:
            project.write_cause_as(self.conn, self.account, int(chosen[0]), self.cause_box.get(),
                                   self.now(), *names)
        except REFUSALS as refusal:
            self.message.configure(text=refusal_text(refusal))
            return
        self.message.configure(text="")
        self.cause_box.delete(0, "end")
        self.fill(project.asset_detail(self.conn, self.asset_id))
        self.on_change()

    def save(self) -> None:
        """Saves the engineer box's text as the asset's engineer, calls on_change and closes; a refusal ("not-an-email")
        shows in the message line and keeps the window open."""
        try:
            project.assign_engineer(self.conn, self.asset_id, self.engineer_box.get(), self.detail.asset.version)
        except REFUSALS as refusal:
            self.message.configure(text=refusal_text(refusal))
            return
        self.on_change()
        self.destroy()
