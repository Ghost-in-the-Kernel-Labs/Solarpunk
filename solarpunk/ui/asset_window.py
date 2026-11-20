"""The asset window (3.2, SP-007): one asset's fields and status, its open faults with their meanings, its diagnostics
(6.4: every remote test of its kind with its latest result, failing first, then never run, then passing), its
suggested faults with Accept and Dismiss (7.5, SP-015: the tests or the device suggest, an engineer decides), a form
to assign a catalogue code, and the engineer with Save and Cancel. Who an act is recorded as is the account signed in
(12.4): an engineer acts as themself and sees no picker, an operator names the engineer "On the word of"; a store with
no accounts keeps "Assigned by" and "Entered by". A write names the version of the record the window drew (12.2): a
stale one is refused with SOL-16's words, and Refresh rereads and redraws. Every string and colour it shows comes from
a pure function below over one project call, so the tests check them without a display; the AssetWindow class only
lays them out (SP-010: it imports project and the leaf alone)."""
import sqlite3
import tkinter as tk
from collections.abc import Callable
from datetime import datetime, timezone
from tkinter import ttk

from solarpunk.ui import cells
from solarpunk.ui.ticket_panel import TicketPanel

from solarpunk import project
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetStatus, FaultCode, lookup

# The words and colours the window shows live here, at module level, where mutmut does not reach (J-008, J-014).
NONE_WORD = "none"
PASS_WORD = "pass"
FAIL_WORD = "FAIL"
NOT_RUN_WORD = "not run"
FAILING_TAG = "failing"
NOT_RUN_TAG = "notrun"
RED_TEXT = "#c0392b"
GREY_TEXT = "#808080"
# The surface's states (project.Diagnostic.state) in the window's words: a failure shouts, the rest do not.
STATE_WORDS = {"fail": FAIL_WORD, "not run": NOT_RUN_WORD, "pass": PASS_WORD}
OPENED_FORMAT = "%Y-%m-%d %H:%M UTC"
COLOURS: dict[AssetStatus, str] = {
    AssetStatus.GREEN: "#2e8b57",
    AssetStatus.YELLOW: "#e0b000",
    AssetStatus.RED: "#c0392b",
}
FAULT_COLUMNS = ("code", "meaning", "opened", "by")
FAULT_HEADINGS = ("Code", "Meaning", "Opened", "Assigned by")
# The open faults' column widths in px: who assigned it, with an operator and cover, is the longest cell (SP-015).
FAULT_WIDTHS = (70, 175, 165, 470)
RESULT_COLUMNS = ("test", "result", "reason")
RESULT_HEADINGS = ("Test", "Result", "Reason")
# The diagnostics' column widths in px: the reason is the column a reader needs whole (6.4).
RESULT_WIDTHS = (190, 70, 480)
OPEN_FAULTS_TITLE = "Open faults"
DIAGNOSTICS_TITLE = "Diagnostics"
ASSIGN_TITLE = "Assign a fault"
ASSIGN_TEXT = "Assign"
ENGINEER_TITLE = "Engineer"
SAVE_TEXT = "Save"
CANCEL_TEXT = "Cancel"
CHOOSE_CODE = "Choose a code to assign."
CHOOSE_ENGINEER = "Choose the engineer who assigned it: only an engineer assigns a fault (SP-015)."
CHOOSE_WORD = "Choose the engineer whose word it is: an operator enters a fault on an engineer's word (SP-015)."
SUGGESTED_TITLE = "Suggested faults (the tests' and the devices', for an engineer to accept or dismiss)"
SUGGESTION_COLUMNS = ("code", "meaning", "source", "reason", "raised")
SUGGESTION_HEADINGS = ("Code", "Meaning", "From", "Why", "Raised")
SUGGESTION_WIDTHS = (70, 190, 110, 255, 165)
ACCEPT_TEXT = "Accept"
DISMISS_TEXT = "Dismiss"
REASON_TITLE = "Reason (to dismiss)"
CHOOSE_SUGGESTION = "Choose a suggested fault first."
GIVE_REASON = "Give the reason it is dismissed: a dismissal is a decision that says why (SP-015)."
ASSIGNED_BY_TITLE = cells.ASSIGNED_BY
ENTERED_BY_TITLE = "Entered by (operator, if called in)"
REFUSALS = (project.LedgerError, project.RegistryError, project.UnknownAsset, project.UnknownEngineer,
            project.SuggestionError, project.NotPermitted, ValueError)


def shown(value: object) -> str:
    """A field's value as the window writes it: shown(None) is "none", shown("Pad A") is "Pad A", shown(5020) "5020"."""
    return NONE_WORD if value is None else str(value)


def endpoint(asset: Asset) -> str:
    """Where the asset's feed is read: "127.0.0.1:5020" for host 127.0.0.1 and port 5020; "none" with no host."""
    return NONE_WORD if asset.host is None else f"{asset.host}:{asset.port}"


def rated(asset: Asset) -> str:
    """The rated power in words: "100.0 kW" for rated_kw 100.0; "none" for an asset that produces nothing."""
    return NONE_WORD if asset.rated_kw is None else f"{asset.rated_kw} kW"


def field_lines(asset: Asset) -> tuple[str, ...]:
    """The fields block, one line per label: for OAHE-INV-001 under OAHE-SIT-001 at Pad A, ("Kind: Inverter",
    "Site: OAHE", "Parent: OAHE-SIT-001", "Rated: 100.0 kW", "Location: Pad A", "Endpoint: 127.0.0.1:5020",
    "Engineer: inverter@oahe.example"); a missing value reads "none"."""
    return (
        f"Kind: {asset.kind.name.capitalize()}",
        f"Site: {asset.site}",
        f"Parent: {shown(asset.parent_id)}",
        f"Rated: {rated(asset)}",
        f"Location: {shown(asset.location)}",
        f"Endpoint: {endpoint(asset)}",
        f"Engineer: {shown(asset.engineer_email)}",
    )


def window_title(asset: Asset) -> str:
    """The window's title: "OAHE-INV-001 — Inverter 1"."""
    return f"{asset.asset_id} — {asset.name}"


def status_line(status: AssetStatus) -> str:
    """The status line's words: status_line(AssetStatus.RED) is "Status: red"."""
    return f"Status: {status.value}"


def colour_of(status: AssetStatus) -> str:
    """The status colour, the glyph's three: colour_of(AssetStatus.RED) is "#c0392b", GREEN "#2e8b57"."""
    return COLOURS[status]


def assigned_text(fault: project.Fault, cover: bool) -> str:
    """Who assigned a fault, as the window writes it (SP-015): "tech@oahe.example"; entered by an operator,
    "tech@oahe.example, entered by ops@oahe.example"; with cover, " (cover)" after; a fault from before, "unrecorded"."""
    entered = "" if fault.recorded_by is None else f", entered by {fault.recorded_by}"
    return f"{fault.assigned_by}{entered}{' (cover)' if cover else ''}"


def fault_lines(detail: project.AssetDetail) -> tuple[tuple[str, str, str, str], ...]:
    """The open-faults rows (code, meaning, opened, assigned by): an open INV-001 opened 2026-06-01 10:10 UTC by
    tech@oahe.example gives (("INV-001", "Inverter offline: …", "2026-06-01 10:10 UTC", "tech@oahe.example"),); no open
    fault gives ()."""
    return tuple((fault.code, meaning, fault.opened.strftime(OPENED_FORMAT), assigned_text(fault, cover))
                 for (fault, meaning), cover in zip(detail.open_faults, detail.cover))


def result_lines(detail: project.AssetDetail) -> tuple[tuple[str, str, str], ...]:
    """The diagnostics' rows (test, result, reason) in the detail's order (6.4): every remote test of the asset's kind,
    failing first, then never run, then passing: a failed on_grid, five tests never run and a passed reachable give
    ("on_grid", "FAIL", "10:05: off the grid") first and ("reachable", "pass", "3 records") last."""
    return tuple((found.test_name, STATE_WORDS[found.state], found.reason) for found in detail.diagnostics)


def suggestion_lines(detail: project.AssetDetail) -> tuple[tuple[str, str, str, str, str], ...]:
    """The suggested-faults rows (code, meaning, from, why, raised) in the detail's order, a device's first: OAHE-SEN-001's
    gives (("SEN-001", "Irradiance sensor out of range: …", "reachable", "127.0.0.1:9 is unreachable",
    "2026-06-01 13:00 UTC"),); none gives ()."""
    return tuple((found.code, lookup(found.code).meaning, found.source, found.reason,
                  found.raised_at.strftime(OPENED_FORMAT)) for found in detail.suggestions)


def row_tags(line: tuple[str, str, str]) -> tuple[str, ...]:
    """The tags a diagnostics row carries: ("failing",) for a FAIL row, drawn red; ("notrun",) for a test never run,
    drawn grey; () for a pass row."""
    if line[1] == FAIL_WORD:
        return (FAILING_TAG,)
    return (NOT_RUN_TAG,) if line[1] == NOT_RUN_WORD else ()


def code_labels(codes: tuple[FaultCode, ...]) -> tuple[str, ...]:
    """The fault dropdown's entries: INV-004 reads "INV-004 — Firmware update pending"; () gives ()."""
    return tuple(f"{code.code} — {code.meaning}" for code in codes)


def chosen_code(codes: tuple[FaultCode, ...], index: int) -> str | None:
    """The code at the dropdown's index, or None when nothing is chosen (index -1): for the inverter codes,
    chosen_code(codes, 1) is "INV-002" and chosen_code(codes, -1) is None."""
    return codes[index].code if 0 <= index < len(codes) else None


def refusal_text(refusal: Exception) -> str:
    """The message line for a refusal: refusal_text(ValueError("bad address")) is "Refused: bad address"."""
    return f"Refused: {refusal}"


class AssetWindow(tk.Toplevel):
    """One asset's window: AssetWindow(root, conn, "OAHE-INV-001") titled "OAHE-INV-001 — Inverter 1"; on_change is
    called after a fault is assigned or the engineer saved, so the fleet window can reread the store; account is the
    one signed in (None in a store with none), which every act is recorded as (12.4)."""

    def __init__(
        self, parent: tk.Misc, conn: sqlite3.Connection, asset_id: str, on_change: Callable[[], None] = lambda: None,
        account: project.Account | None = None,
    ) -> None:
        """Reads the asset once for its kind's codes, lays out the window and fills it: an id the fleet lacks raises
        UnknownAsset before any window is drawn."""
        detail = project.asset_detail(conn, asset_id)
        super().__init__(parent)
        self.conn = conn
        self.asset_id = asset_id
        self.on_change = on_change
        self.account = account
        self.codes = project.codes_for_kind(detail.asset.kind)
        self.title(window_title(detail.asset))
        self.fields = ttk.Frame(self)
        self.fields.pack(fill="x", padx=8, pady=4)
        self.status_label = tk.Label(self, anchor="w")
        self.status_label.pack(fill="x", padx=8)
        self.fault_tree = self.tree(OPEN_FAULTS_TITLE, FAULT_COLUMNS, FAULT_HEADINGS)
        for column, width in zip(FAULT_COLUMNS, FAULT_WIDTHS):
            self.fault_tree.column(column, width=width, stretch=column == FAULT_COLUMNS[-1])
        self.result_tree = self.tree(DIAGNOSTICS_TITLE, RESULT_COLUMNS, RESULT_HEADINGS, height=7)
        self.result_tree.tag_configure(FAILING_TAG, foreground=RED_TEXT)
        self.result_tree.tag_configure(NOT_RUN_TAG, foreground=GREY_TEXT)
        for column, width in zip(RESULT_COLUMNS, RESULT_WIDTHS):
            self.result_tree.column(column, width=width, stretch=column == RESULT_COLUMNS[-1])
        self.suggestion_tree = self.tree(SUGGESTED_TITLE, SUGGESTION_COLUMNS, SUGGESTION_HEADINGS, height=3)
        for column, width in zip(SUGGESTION_COLUMNS, SUGGESTION_WIDTHS):
            self.suggestion_tree.column(column, width=width, stretch=column == "reason")
        self.build_decide()
        self.build_assign()
        self.build_engineer()
        self.ticket_panel = TicketPanel(self, conn, asset_id, self.ticket_changed, account=account)  # 11.2, 12.4
        self.ticket_panel.pack(fill="x", padx=8, pady=4)
        last = ttk.Frame(self)
        last.pack(fill="x", padx=8, pady=4)
        self.message = tk.Label(last, anchor="w", foreground=RED_TEXT)
        self.message.pack(side="left", fill="x", expand=True)
        self.refresh_button = ttk.Button(last, text=cells.REFRESH, command=self.refresh)
        self.refresh_button.pack(side="right")
        self.fill(detail)

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

    def build_decide(self) -> None:
        """The row under the suggested faults: Accept, Dismiss and the dismissal's reason (7.5); who decides is the
        account signed in, or the engineer in the picker below (cells.picker_title)."""
        row = ttk.Frame(self)
        row.pack(fill="x", padx=8, pady=2)
        self.accept_button = ttk.Button(row, text=ACCEPT_TEXT, command=self.accept)
        self.accept_button.pack(side="left")
        self.dismiss_button = ttk.Button(row, text=DISMISS_TEXT, command=self.dismiss)
        self.dismiss_button.pack(side="left", padx=4)
        ttk.Label(row, text=REASON_TITLE).pack(side="left")
        self.reason_box = ttk.Entry(row, width=50)
        self.reason_box.pack(side="left", padx=4)

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
        for fault_row in fault_lines(detail):
            self.fault_tree.insert("", "end", values=fault_row)
        self.result_tree.delete(*self.result_tree.get_children())
        for result_row in result_lines(detail):
            self.result_tree.insert("", "end", values=result_row, tags=row_tags(result_row))
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
            project.assign_fault_as(self.conn, self.account, self.asset_id, code, datetime.now(timezone.utc), *names)
        except REFUSALS as refusal:
            self.message.configure(text=refusal_text(refusal))
            return
        self.message.configure(text="")
        self.fill(project.asset_detail(self.conn, self.asset_id))
        self.on_change()

    def chosen(self) -> tuple[int, tuple[str | None, str | None, str | None]] | None:
        """The selected suggestion's id and who decides (named), or None with the message saying which is missing."""
        selected = self.suggestion_tree.selection()
        if not selected:
            self.message.configure(text=CHOOSE_SUGGESTION)
            return None
        names = self.named()
        return None if names is None else (int(selected[0]), names)

    def decided(self, act: Callable[[], object]) -> None:
        """Runs an accept or a dismiss; a refusal shows in the message line and changes nothing, a decision rereads the
        window and calls on_change."""
        try:
            act()
        except REFUSALS as refusal:
            self.message.configure(text=refusal_text(refusal))
            return
        self.message.configure(text="")
        self.fill(project.asset_detail(self.conn, self.asset_id))
        self.on_change()

    def accept(self) -> None:
        """Accepts the selected suggestion as the account signed in, or as named (SP-015, 12.4): the fault opens, the
        suggestion leaves the list and the fault appears under Open faults."""
        picked = self.chosen()
        if picked is not None:
            suggestion_id, names = picked
            self.decided(lambda: project.accept_suggestion_as(self.conn, self.account, suggestion_id, *names,
                                                              read_at=cells.drawn(self.detail, suggestion_id)))

    def dismiss(self) -> None:
        """Dismisses the selected suggestion as the account signed in, or as named, with the reason typed; no reason is
        refused here."""
        picked = self.chosen()
        if picked is None:
            return
        if not self.reason_box.get().strip():
            self.message.configure(text=GIVE_REASON)
            return
        suggestion_id, (by, _recorded_by, for_engineer) = picked
        self.decided(lambda: project.dismiss_suggestion_as(self.conn, self.account, suggestion_id, self.reason_box.get(),
                                                           by, for_engineer, cells.drawn(self.detail, suggestion_id)))

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
