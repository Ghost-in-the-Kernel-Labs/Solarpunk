"""The Runs window (10.3, SP-024): one asset's last 100 runs, newest first, a run with a failure in red; selecting a run
shows its results with their reasons, failures first; a search box narrows the list as it is typed (a test's name,
"pass" or "fail", words in a reason). Every string comes from runs_text.py over project.asset_runs (SOL-15); the class
only lays them out (SP-010: it imports project and the leaf alone)."""
import sqlite3
import tkinter as tk
from tkinter import ttk

from solarpunk import project
from solarpunk.ui import runs_text

RED_TEXT = "#c0392b"
FAILED_TAG = "failed"
RUN_COLUMNS = ("instant", "results", "verdict")
RUN_HEADINGS = ("Run", "Results", "Verdict")
RUN_WIDTHS = (170, 90, 90)
RESULT_COLUMNS = ("test", "result", "reason")
RESULT_HEADINGS = ("Test", "Result", "Reason")
RESULT_WIDTHS = (180, 60, 360)
SEARCH = "Search"


class RunsWindow(tk.Toplevel):
    """One asset's runs: RunsWindow(root, conn, "OAHE-INV-002") titled "Runs — OAHE-INV-002 Inverter 2", its list
    holding the demo's one run; an id the fleet lacks raises UnknownAsset before any window is drawn."""

    def __init__(self, parent: tk.Misc, conn: sqlite3.Connection, asset_id: str) -> None:
        """Reads the asset once for its name and endpoint, lays the window out and fills the list."""
        asset = project.asset_detail(conn, asset_id).asset
        super().__init__(parent)
        self.conn = conn
        self.asset_id = asset_id
        self.has_feed = asset.host is not None and asset.port is not None
        self.runs: tuple[project.Run, ...] = ()
        self.title(runs_text.title(asset_id, asset.name))
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=(6, 2))
        ttk.Label(bar, text=SEARCH).pack(side="left")
        self.search_text = tk.StringVar()
        self.search_box = ttk.Entry(bar, textvariable=self.search_text, width=30)
        self.search_box.pack(side="left", padx=4)
        self.empty_label = ttk.Label(bar, foreground="#808080")
        self.empty_label.pack(side="left", padx=8)
        self.run_tree = self.tree(RUN_COLUMNS, RUN_HEADINGS, RUN_WIDTHS, height=10)
        self.result_tree = self.tree(RESULT_COLUMNS, RESULT_HEADINGS, RESULT_WIDTHS, height=8)
        self.run_tree.bind("<<TreeviewSelect>>", lambda _e: self.show_results())
        self.search_text.trace_add("write", lambda *_: self.fill())
        self.fill()

    def tree(self, columns: tuple[str, ...], headings: tuple[str, ...], widths: tuple[int, ...],
             height: int) -> ttk.Treeview:
        """A table with its headings and widths, failures in red, its last column stretching."""
        tree = ttk.Treeview(self, columns=columns, show="headings", height=height, selectmode="browse")
        for column, heading, width in zip(columns, headings, widths):
            tree.heading(column, text=heading)
            tree.column(column, width=width, stretch=column == columns[-1])
        tree.tag_configure(FAILED_TAG, foreground=RED_TEXT)
        tree.pack(fill="both", expand=True, padx=8, pady=4)
        return tree

    def fill(self) -> None:
        """Rereads the asset's runs for the search and lists them, newest first, a failed run red; the first is
        selected, so its results show at once; with none, the bar says why."""
        self.runs = project.asset_runs(self.conn, self.asset_id, search=self.search_text.get() or None)
        self.run_tree.delete(*self.run_tree.get_children())
        for index, run in enumerate(self.runs):
            self.run_tree.insert("", "end", iid=str(index), values=runs_text.run_line(run),
                                 tags=(FAILED_TAG,) if run.failed else ())
        empty = "" if self.runs else runs_text.empty_text(self.has_feed, self.search_text.get())
        self.empty_label.configure(text=empty)
        if self.runs:
            self.run_tree.selection_set("0")
        self.show_results()

    def show_results(self) -> None:
        """Lists the chosen run's results, failures first and red; with no run chosen, none."""
        self.result_tree.delete(*self.result_tree.get_children())
        chosen = self.run_tree.selection()
        if not chosen:
            return
        for result in self.runs[int(chosen[0])].results:
            self.result_tree.insert("", "end", values=runs_text.result_line(result),
                                    tags=() if result.passed else (FAILED_TAG,))
