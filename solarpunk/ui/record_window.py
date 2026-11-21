"""The Tests window (13.7, SP-016, SP-050): every remote test's record over the fleet (name, kinds, assets, last run,
duration, passes, failures, no data) and, for the selected test, its last 100 runs, newest first, a failure red. Every
string comes from record_text.py over project.tests_overview and project.test_log; the class only lays them out (SP-010:
it imports project and the leaf alone). tests_window.py is the Manage tests window (9.8), a different thing."""
import sqlite3
import tkinter as tk
from tkinter import ttk

from solarpunk import project
from solarpunk.ui import record_text

RED_TEXT = "#c0392b"
GREY_TEXT = "#808080"
FAILED_TAG = "failed"
NO_DATA_TAG = "nodata"
LIMIT = 100
OVERVIEW_WIDTHS = (190, 230, 60, 170, 80, 60, 70, 70)
LOG_WIDTHS = (110, 170, 70, 330, 80)


class RecordWindow(tk.Toplevel):
    """The Tests window: RecordWindow(root, conn) titled "Tests — record", its table holding every test in name order
    and, under it, the log of the first, selected at once."""

    def __init__(self, parent: tk.Misc, conn: sqlite3.Connection) -> None:
        """Lays the window out and fills the overview."""
        super().__init__(parent)
        self.conn = conn
        self.records: tuple[project.TestRecord, ...] = ()
        self.title(record_text.TITLE)
        self.overview = self.tree(record_text.OVERVIEW_COLUMNS, OVERVIEW_WIDTHS, height=10, stretch=0)
        self.heading = ttk.Label(self)
        self.heading.pack(anchor="w", padx=8)
        self.log = self.tree(record_text.LOG_COLUMNS, LOG_WIDTHS, height=10, stretch=3)
        self.empty_label = ttk.Label(self, foreground=GREY_TEXT)
        self.empty_label.pack(anchor="w", padx=8, pady=(0, 6))
        self.overview.bind("<<TreeviewSelect>>", lambda _e: self.show_log())
        self.fill()

    def tree(self, columns: tuple[str, ...], widths: tuple[int, ...], height: int, stretch: int) -> ttk.Treeview:
        """A table with its headings and widths, failures red, column number stretch stretching."""
        tree = ttk.Treeview(self, columns=columns, show="headings", height=height, selectmode="browse")
        for index, (column, width) in enumerate(zip(columns, widths)):
            tree.heading(column, text=column)
            tree.column(column, width=width, stretch=index == stretch)
        tree.tag_configure(FAILED_TAG, foreground=RED_TEXT)
        tree.tag_configure(NO_DATA_TAG, foreground=GREY_TEXT)
        tree.pack(fill="both", expand=True, padx=8, pady=4)
        return tree

    def fill(self) -> None:
        """Rereads the overview and lists every test, one with a failure red; the first is selected, so its log shows."""
        self.records = project.tests_overview(self.conn)
        self.overview.delete(*self.overview.get_children())
        for index, found in enumerate(self.records):
            self.overview.insert("", "end", iid=str(index), values=record_text.overview_row(found),
                                 tags=(FAILED_TAG,) if found.failures else ())
        if self.records:
            self.overview.selection_set("0")
        self.show_log()

    def chosen(self) -> str | None:
        """The name of the selected test, None with none."""
        picked = self.overview.selection()
        return self.records[int(picked[0])].name if picked else None

    def show_log(self) -> None:
        """Lists the selected test's last 100 runs, newest first, a failure red and no data grey; with none, says so."""
        name = self.chosen()
        self.log.delete(*self.log.get_children())
        runs = () if name is None else project.test_log(self.conn, name, LIMIT)
        for index, run in enumerate(runs):
            self.log.insert("", "end", iid=str(index), values=record_text.log_row(run),
                            tags=(FAILED_TAG,) if run.verdict == "fail" else (NO_DATA_TAG,) if run.verdict == "no data" else ())
        self.heading.configure(text=record_text.log_heading(name, LIMIT))
        self.empty_label.configure(text="" if runs else record_text.empty_log(name))
