"""The fleet's Errors window (10.7, SOL-15, SP-024): one catalogue code and two whole days chosen, a row of bars per
asset that raised it, worst first, faults and suggestions told apart and their counts written beside them; a click on
an asset's row opens its Runs window. The bars are bars.py's, the words runs_text.py's, over one project call,
project.code_counts_by_asset; the class only lays them out (SP-010: it imports project and the leaf alone)."""
import sqlite3
import tkinter as tk
from collections.abc import Callable
from tkinter import font as tkfont
from tkinter import ttk

from solarpunk import project
from solarpunk.ui import bars, runs_text

TITLE = "Errors across the fleet"
CODE = "Code"
FROM, TO = "From", "To"
SHOW = "Show"
FIRST_CODE = "INV-001"


class ErrorsWindow(tk.Toplevel):
    """The fleet's Errors window: ErrorsWindow(root, conn, open_runs) opens on INV-001 over the day of the store's last
    run; on_open_runs is handed the asset id of a clicked row."""

    def __init__(self, parent: tk.Misc, conn: sqlite3.Connection, on_open_runs: Callable[[str], None]) -> None:
        """Lays out the choices, the line and the canvas, then draws the first code's bars."""
        super().__init__(parent)
        self.conn = conn
        self.on_open_runs = on_open_runs
        self.title(TITLE)
        self.label_font = tkfont.nametofont("TkDefaultFont")
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=6)
        choices = runs_text.code_choices()
        first = next(choice for choice in choices if runs_text.code_of(choice) == FIRST_CODE)
        self.code_choice = tk.StringVar(value=first)
        ttk.Label(bar, text=CODE).pack(side="left")
        ttk.Combobox(bar, textvariable=self.code_choice, values=choices, state="readonly", width=34).pack(side="left",
                                                                                                         padx=4)
        day = project.report_day(conn).isoformat()
        self.first_day, self.last_day = tk.StringVar(value=day), tk.StringVar(value=day)
        for words, variable in ((FROM, self.first_day), (TO, self.last_day)):
            ttk.Label(bar, text=words).pack(side="left")
            ttk.Entry(bar, textvariable=variable, width=12).pack(side="left", padx=4)
        self.show_button = ttk.Button(bar, text=SHOW, command=self.draw)
        self.show_button.pack(side="left")
        self.line = ttk.Label(self)
        self.line.pack(fill="x", padx=8)
        self.canvas = tk.Canvas(self, width=bars.WIDTH, height=bars.height_of(1), background="white",
                                highlightthickness=0)
        self.canvas.pack(padx=8, pady=6)
        self.canvas.bind("<Button-1>", self.on_click)
        self.draw()

    def draw(self) -> None:
        """Counts the chosen code across the fleet over the chosen days and draws a row per asset, worst first; a bad
        choice of days, or no asset that raised the code, is said in the line, and no bar is drawn."""
        self.canvas.delete(tk.ALL)
        days = runs_text.days_of(self.first_day.get(), self.last_day.get())
        if days is None:
            self.line.configure(text=runs_text.BAD_DAYS)
            return
        code = runs_text.code_of(self.code_choice.get())
        period = project.period(project.day_period(days[0]).start, project.day_period(days[1]).end)
        counts = runs_text.asset_counts(project.code_counts_by_asset(self.conn, code, period))
        self.line.configure(text="" if counts else runs_text.no_asset_errors(code, *days))
        if counts:
            left = bars.left_of([self.label_font.measure(label) for label, _, _ in counts])
            self.canvas.configure(height=bars.height_of(len(counts)))
            bars.draw_bars(self.canvas, bars.bar_rows(counts, left=left))

    def on_click(self, event: tk.Event) -> None:
        """A click on an asset's row (its label, a bar or its words) opens that asset's Runs window; elsewhere, nothing."""
        found = self.canvas.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)
        for item in reversed(found):
            asset_id = runs_text.row_of(self.canvas.gettags(item))
            if asset_id is not None:
                self.on_open_runs(asset_id)
                return
