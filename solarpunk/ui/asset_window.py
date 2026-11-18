"""The asset window (3.2, SP-007): one asset's fields and status, its open faults with their meanings, its diagnostics
(6.4: every remote test of its kind with its latest result, failing first, then never run, then passing), a form to
assign a catalogue code, and the engineer with Save and Cancel. Every string and colour it shows comes from a pure
function below over one project call, so the tests check them without a display; the AssetWindow class only lays them
out (SP-010: it imports project and the leaf alone)."""
import sqlite3
import tkinter as tk
from collections.abc import Callable
from datetime import datetime, timezone
from tkinter import ttk

from solarpunk import project
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetStatus, FaultCode

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
FAULT_COLUMNS = ("code", "meaning", "opened")
FAULT_HEADINGS = ("Code", "Meaning", "Opened")
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
REFUSALS = (project.LedgerError, project.RegistryError, project.UnknownAsset, ValueError)


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


def fault_lines(detail: project.AssetDetail) -> tuple[tuple[str, str, str], ...]:
    """The open-faults rows (code, meaning, opened): an open INV-001 opened 2026-06-01 10:10 UTC gives (("INV-001",
    "Inverter offline: …", "2026-06-01 10:10 UTC"),); no open fault gives ()."""
    return tuple((fault.code, meaning, fault.opened.strftime(OPENED_FORMAT)) for fault, meaning in detail.open_faults)


def result_lines(detail: project.AssetDetail) -> tuple[tuple[str, str, str], ...]:
    """The diagnostics' rows (test, result, reason) in the detail's order (6.4): every remote test of the asset's kind,
    failing first, then never run, then passing: a failed on_grid, five tests never run and a passed reachable give
    ("on_grid", "FAIL", "10:05: off the grid") first and ("reachable", "pass", "3 records") last."""
    return tuple((found.test_name, STATE_WORDS[found.state], found.reason) for found in detail.diagnostics)


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
    called after a fault is assigned or the engineer saved, so the fleet window can reread the store."""

    def __init__(
        self, parent: tk.Misc, conn: sqlite3.Connection, asset_id: str, on_change: Callable[[], None] = lambda: None
    ) -> None:
        """Reads the asset once for its kind's codes, lays out the window and fills it: an id the fleet lacks raises
        UnknownAsset before any window is drawn."""
        detail = project.asset_detail(conn, asset_id)
        super().__init__(parent)
        self.conn = conn
        self.asset_id = asset_id
        self.on_change = on_change
        self.codes = project.codes_for_kind(detail.asset.kind)
        self.title(window_title(detail.asset))
        self.fields = ttk.Frame(self)
        self.fields.pack(fill="x", padx=8, pady=4)
        self.status_label = tk.Label(self, anchor="w")
        self.status_label.pack(fill="x", padx=8)
        self.fault_tree = self.tree(OPEN_FAULTS_TITLE, FAULT_COLUMNS, FAULT_HEADINGS)
        self.result_tree = self.tree(DIAGNOSTICS_TITLE, RESULT_COLUMNS, RESULT_HEADINGS, height=7)
        self.result_tree.tag_configure(FAILING_TAG, foreground=RED_TEXT)
        self.result_tree.tag_configure(NOT_RUN_TAG, foreground=GREY_TEXT)
        for column, width in zip(RESULT_COLUMNS, RESULT_WIDTHS):
            self.result_tree.column(column, width=width, stretch=column == RESULT_COLUMNS[-1])
        self.build_assign()
        self.build_engineer()
        self.message = tk.Label(self, anchor="w", foreground=RED_TEXT)
        self.message.pack(fill="x", padx=8, pady=4)
        self.fill(detail)

    def tree(self, title: str, columns: tuple[str, ...], headings: tuple[str, ...], height: int = 4) -> ttk.Treeview:
        """A titled Treeview of named columns, height rows tall: tree("Diagnostics", ("test", …), ("Test", …), 7) shows
        the headings only."""
        ttk.Label(self, text=title).pack(fill="x", padx=8)
        tree = ttk.Treeview(self, columns=columns, show="headings", height=height)
        for column, heading in zip(columns, headings):
            tree.heading(column, text=heading)
        tree.pack(fill="both", expand=True, padx=8, pady=2)
        return tree

    def build_assign(self) -> None:
        """The "Assign a fault" row: a read-only dropdown of the kind's codes and the Assign button."""
        row = ttk.Frame(self)
        row.pack(fill="x", padx=8, pady=4)
        ttk.Label(row, text=ASSIGN_TITLE).pack(side="left")
        self.code_box = ttk.Combobox(row, values=code_labels(self.codes), state="readonly", width=60)
        self.code_box.pack(side="left", padx=4)
        self.assign_button = ttk.Button(row, text=ASSIGN_TEXT, command=self.assign)
        self.assign_button.pack(side="left")

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
        """Writes one detail into the window: the field labels, the status in its colour, both trees, the engineer."""
        for old in self.fields.winfo_children():
            old.destroy()
        for line in field_lines(detail.asset):
            ttk.Label(self.fields, text=line, anchor="w").pack(fill="x")
        self.status_label.configure(text=status_line(detail.status), foreground=colour_of(detail.status))
        self.fault_tree.delete(*self.fault_tree.get_children())
        for fault_row in fault_lines(detail):
            self.fault_tree.insert("", "end", values=fault_row)
        self.result_tree.delete(*self.result_tree.get_children())
        for result_row in result_lines(detail):
            self.result_tree.insert("", "end", values=result_row, tags=row_tags(result_row))
        self.engineer_box.set(detail.asset.engineer_email or "")

    def assign(self) -> None:
        """Assigns the chosen code now (UTC), rereads the window and calls on_change; a refusal (a second open INV-001)
        shows in the message line and changes nothing."""
        code = chosen_code(self.codes, self.code_box.current())
        if code is None:
            self.message.configure(text=CHOOSE_CODE)
            return
        try:
            project.assign_fault(self.conn, self.asset_id, code, datetime.now(timezone.utc))
        except REFUSALS as refusal:
            self.message.configure(text=refusal_text(refusal))
            return
        self.message.configure(text="")
        self.fill(project.asset_detail(self.conn, self.asset_id))
        self.on_change()

    def save(self) -> None:
        """Saves the engineer box's text as the asset's engineer, calls on_change and closes; a refusal ("not-an-email")
        shows in the message line and keeps the window open."""
        try:
            project.assign_engineer(self.conn, self.asset_id, self.engineer_box.get())
        except REFUSALS as refusal:
            self.message.configure(text=refusal_text(refusal))
            return
        self.on_change()
        self.destroy()
