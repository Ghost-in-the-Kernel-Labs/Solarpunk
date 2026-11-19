"""The Runs window (10.3, SP-024): one asset's last 100 runs, newest first, a run with a failure in red; selecting a run
shows its results with their reasons, failures first; a search box narrows the list as it is typed (a test's name,
"pass" or "fail", words in a reason). A second tab, "By test" (10.4), draws the same runs as a timeline, one row per
test, one mark per run, green or red, in UTC. Every string comes from runs_text.py and every point from timeline.py
over project.asset_runs (SOL-15); the class only lays them out (SP-010: it imports project and the leaf alone)."""
import sqlite3
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from solarpunk import project
from solarpunk.ui import bars, runs_text, timeline
from solarpunk.ui.chart import CANVAS_HEIGHT, CANVAS_WIDTH
from solarpunk.ui.reports import draw_power

RED_TEXT = "#c0392b"
FAILED_TAG = "failed"
RUN_COLUMNS = ("instant", "results", "verdict")
RUN_HEADINGS = ("Run", "Results", "Verdict")
RUN_WIDTHS = (170, 90, 90)
RESULT_COLUMNS = ("test", "result", "reason")
RESULT_HEADINGS = ("Test", "Result", "Reason")
RESULT_WIDTHS = (180, 60, 360)
SEARCH = "Search"
RUNS_TAB = "Runs"
BY_TEST_TAB = "By test"
AXIS_COLOUR = "#606060"
MARK_TAG = "mark"
UTC = "UTC"
POWER_TAB = "Power"
DAY = "Day (UTC)"
SHOW = "Show"
ERRORS_TAB = "Errors"
FROM, TO = "From", "To"


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
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=4, pady=4)
        runs_tab = ttk.Frame(self.tabs)
        self.tabs.add(runs_tab, text=RUNS_TAB)
        self.run_tree = self.tree(runs_tab, RUN_COLUMNS, RUN_HEADINGS, RUN_WIDTHS, height=10)
        self.result_tree = self.tree(runs_tab, RESULT_COLUMNS, RESULT_HEADINGS, RESULT_WIDTHS, height=8)
        by_test = ttk.Frame(self.tabs)
        self.tabs.add(by_test, text=BY_TEST_TAB)
        self.timeline = tk.Canvas(by_test, width=timeline.WIDTH, height=timeline.height_of(1), background="white",
                                  highlightthickness=0)
        self.timeline.pack(fill="both", expand=True, padx=4, pady=4)
        self.label_font = tkfont.nametofont("TkDefaultFont")
        self.make_power_tab()
        self.make_errors_tab()
        self.run_tree.bind("<<TreeviewSelect>>", lambda _e: self.show_results())
        self.search_text.trace_add("write", lambda *_: self.fill())
        self.fill()

    def make_power_tab(self) -> None:
        """The Power tab (10.5): a day box opening on the day of the store's last run, Show, a line of counts, and the
        asset's power curve for that day, drawn as the reports window draws a site's."""
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text=POWER_TAB)
        bar = ttk.Frame(tab)
        bar.pack(fill="x", padx=4, pady=4)
        ttk.Label(bar, text=DAY).pack(side="left")
        self.day_text = tk.StringVar(value=project.report_day(self.conn).isoformat())
        ttk.Entry(bar, textvariable=self.day_text, width=12).pack(side="left", padx=4)
        self.show_button = ttk.Button(bar, text=SHOW, command=self.draw_power)
        self.show_button.pack(side="left")
        self.power_line = ttk.Label(bar)
        self.power_line.pack(side="left", padx=8)
        self.power_canvas = tk.Canvas(tab, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, background="white",
                                      highlightthickness=0)
        self.power_canvas.pack(padx=4, pady=4)
        self.draw_power()

    def draw_power(self) -> None:
        """Reads the asset's samples for the chosen day and draws them, a gap a break, counted in the line beside; a box
        that holds no day says how one reads, and nothing is drawn."""
        self.power_canvas.delete(tk.ALL)
        day = runs_text.day_of(self.day_text.get())
        if day is None:
            self.power_line.configure(text=runs_text.BAD_DAY)
            return
        series = project.asset_power(self.conn, self.asset_id, project.day_period(day))
        self.power_line.configure(text=runs_text.power_line(series))
        if series.samples:
            draw_power(self.power_canvas, runs_text.power_curve(series), series.period, runs_text.peak_of(series))

    def make_errors_tab(self) -> None:
        """The Errors tab (10.6): From and To days (both counted whole, opening on the day of the store's last run),
        Show, a line for an empty or a bad choice, and a bar per code, faults and suggestions apart (SOL-15)."""
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text=ERRORS_TAB)
        bar = ttk.Frame(tab)
        bar.pack(fill="x", padx=4, pady=4)
        day = project.report_day(self.conn).isoformat()
        self.first_day, self.last_day = tk.StringVar(value=day), tk.StringVar(value=day)
        for words, variable in ((FROM, self.first_day), (TO, self.last_day)):
            ttk.Label(bar, text=words).pack(side="left")
            ttk.Entry(bar, textvariable=variable, width=12).pack(side="left", padx=4)
        self.errors_button = ttk.Button(bar, text=SHOW, command=self.draw_errors)
        self.errors_button.pack(side="left")
        self.errors_line = ttk.Label(bar)
        self.errors_line.pack(side="left", padx=8)
        self.errors_canvas = tk.Canvas(tab, width=bars.WIDTH, height=bars.height_of(1), background="white",
                                       highlightthickness=0)
        self.errors_canvas.pack(padx=4, pady=4)
        self.draw_errors()

    def draw_errors(self) -> None:
        """Counts the asset's faults and suggestions by code over the chosen days and draws a row of bars per code; a
        bad choice or nothing counted is said in the line, and no bar is drawn."""
        self.errors_canvas.delete(tk.ALL)
        days = runs_text.days_of(self.first_day.get(), self.last_day.get())
        if days is None:
            self.errors_line.configure(text=runs_text.BAD_DAYS)
            return
        period = project.period(project.day_period(days[0]).start, project.day_period(days[1]).end)
        counts = runs_text.code_counts(project.asset_code_counts(self.conn, self.asset_id, period))
        self.errors_line.configure(text="" if counts else runs_text.no_errors(*days))
        if counts:
            left = bars.left_of([self.label_font.measure(label) for label, _, _ in counts])
            self.errors_canvas.configure(height=bars.height_of(len(counts)))
            bars.draw_bars(self.errors_canvas, bars.bar_rows(counts, left=left))

    def tree(self, parent: tk.Misc, columns: tuple[str, ...], headings: tuple[str, ...], widths: tuple[int, ...],
             height: int) -> ttk.Treeview:
        """A table in parent with its headings and widths, failures in red, its last column stretching."""
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=height, selectmode="browse")
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
        self.draw_timeline()

    def draw_timeline(self) -> None:
        """Draws the listed runs by test (10.4): each test's name at its row's left, a mark per run, the hour ticks and
        "UTC" below; with no runs, the canvas is left empty."""
        canvas = self.timeline
        canvas.delete(tk.ALL)
        if not self.runs:
            return
        names = timeline.tests_of(self.runs)
        left = timeline.left_of([self.label_font.measure(name) for name in names])
        canvas.configure(height=timeline.height_of(len(names)))
        for row, name in enumerate(names):
            canvas.create_text(8, timeline.y_of(row), text=name, anchor="w")
        for mark in timeline.marks(self.runs, left=left):
            y = timeline.y_of(mark.row)
            colour = timeline.PASS_COLOUR if mark.passed else timeline.FAIL_COLOUR
            canvas.create_rectangle(mark.x - timeline.MARK_WIDTH / 2, y - timeline.MARK_HEIGHT / 2,
                                    mark.x + timeline.MARK_WIDTH / 2, y + timeline.MARK_HEIGHT / 2, fill=colour,
                                    outline="", tags=(MARK_TAG,))
        start, end = timeline.span(self.runs)
        axis_y = timeline.TOP + len(names) * timeline.ROW_HEIGHT + 6
        canvas.create_line(left, axis_y, timeline.WIDTH - timeline.RIGHT, axis_y, fill=AXIS_COLOUR)
        for tick in timeline.ticks(start, end):
            x = timeline.x_of(tick, start, end, left=left)
            canvas.create_line(x, axis_y, x, axis_y + 4, fill=AXIS_COLOUR)
            canvas.create_text(x, axis_y + 14, text=timeline.tick_text(tick, start, end), fill=AXIS_COLOUR)
        canvas.create_text(timeline.WIDTH - timeline.RIGHT, axis_y + 28, text=UTC, anchor="e", fill=AXIS_COLOUR)

    def show_results(self) -> None:
        """Lists the chosen run's results, failures first and red; with no run chosen, none."""
        self.result_tree.delete(*self.result_tree.get_children())
        chosen = self.run_tree.selection()
        if not chosen:
            return
        for result in self.runs[int(chosen[0])].results:
            self.result_tree.insert("", "end", values=runs_text.result_line(result),
                                    tags=() if result.passed else (FAILED_TAG,))
