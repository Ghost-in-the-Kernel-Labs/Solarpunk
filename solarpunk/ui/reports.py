"""The reports window (6.3, SP-013): a site and a period chosen, the power-output table of SOL-13 (the site's row first,
then each inverter's), the site's summed power over the period drawn on a canvas with its axes in kW and UTC hours, and
Save as CSV, the same file `solarpunk report --csv` prints. All it shows comes from project.power_report; the numbers on
screen, the axis scale, the ticks and the curve's points are made by chart.py's pure functions, tested headless, and the
widgets only place them. A refusal (an unknown site, a reversed period, an instant that is not UTC) is shown in the
window, never swallowed. A gap is not drawn as zero: the line breaks across it."""
import sqlite3
import tkinter
from collections.abc import Callable
from datetime import datetime
from tkinter import filedialog, ttk

from solarpunk import project
from solarpunk.leaf.clock import Period
from solarpunk.ui.chart import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    MARGIN,
    axis_top,
    default_span,
    segments,
    summary,
    table_values,
    tick_hours,
    x_of,
    y_of,
)

TITLE = "Power output"
SHOW = "Show"
SAVE = "Save as CSV"
HEADINGS = ("Asset", "Rated kW", "Energy kWh", "Peak kW", "kWh/kWp", "Capacity factor", "Records", "Gaps")
LINE_COLOUR = "#2e8b57"
AXIS_COLOUR = "#555555"
ERROR_COLOUR = "#c0392b"
CURVE_TAG = "curve"


def draw_power(canvas: tkinter.Canvas, curve: tuple[tuple[datetime, float], ...], period: Period,
               peak: float | None) -> None:
    """A power curve on a 720 by 260 canvas (6.3, and 10.5's Power tab): the axes, their labels (0, half and the top in
    kW; the hour ticks in UTC) and the curve, run by run, a gap a break in the line (chart.segments), never a zero or a
    bridge; a run of one point is a dot, tagged "curve" as the lines are."""
    top = axis_top(peak)
    bottom, right = CANVAS_HEIGHT - MARGIN, CANVAS_WIDTH - MARGIN
    canvas.create_line(MARGIN, MARGIN, MARGIN, bottom, right, bottom, fill=AXIS_COLOUR)
    for power in (0, top / 2, top):
        label_y = y_of(power, top, CANVAS_HEIGHT)
        canvas.create_text(MARGIN - 4, label_y, text=f"{power:g}", anchor=tkinter.E, fill=AXIS_COLOUR)
    canvas.create_text(MARGIN, MARGIN - 14, text="kW", anchor=tkinter.W, fill=AXIS_COLOUR)
    for tick in tick_hours(period):
        tick_x = x_of(tick, period, CANVAS_WIDTH)
        canvas.create_line(tick_x, bottom, tick_x, bottom + 4, fill=AXIS_COLOUR)
        canvas.create_text(tick_x, bottom + 14, text=tick.strftime("%H:%M"), fill=AXIS_COLOUR)
    canvas.create_text(right, bottom + 30, text="UTC", anchor=tkinter.E, fill=AXIS_COLOUR)
    for run in segments(curve, period, top):
        if len(run) == 1:
            point_x, point_y = run[0]
            canvas.create_oval(point_x - 1.5, point_y - 1.5, point_x + 1.5, point_y + 1.5, fill=LINE_COLOUR, outline=LINE_COLOUR, tags=(CURVE_TAG,))
        else:
            canvas.create_line(*[value for point in run for value in point], fill=LINE_COLOUR, width=2, tags=(CURVE_TAG,))


class ReportsWindow:
    """The reports window in its own Toplevel: ReportsWindow(root, conn) opens on the store's first site and
    project.report_day(conn); .report is the project.PowerReport on screen, None after a refusal, whose message is in
    .error["text"]. ask_path is the save dialog, replaced in the tests."""

    def __init__(self, root: tkinter.Misc, conn: sqlite3.Connection,
                 ask_path: Callable[[], str] = lambda: filedialog.asksaveasfilename(defaultextension=".csv")) -> None:
        """Builds the controls, the table, the summary line and the canvas, then shows the default report."""
        self.conn = conn
        self.ask_path = ask_path
        self.report: project.PowerReport | None = None
        self.window = tkinter.Toplevel(root)
        self.window.title(TITLE)
        sites = project.report_sites(conn)
        start, end = default_span(project.report_day(conn))
        self.site = tkinter.StringVar(value=sites[0] if sites else "")
        self.start = tkinter.StringVar(value=start)
        self.end = tkinter.StringVar(value=end)
        self.build_controls(sites)
        self.table = ttk.Treeview(self.window, columns=HEADINGS, show="headings", height=6)
        for heading in HEADINGS:
            self.table.heading(heading, text=heading)
            self.table.column(heading, width=90, anchor=tkinter.E)
        self.table.pack(fill=tkinter.X, padx=8)
        self.summary_line = ttk.Label(self.window)
        self.summary_line.pack(anchor=tkinter.W, padx=8)
        self.error = ttk.Label(self.window, foreground=ERROR_COLOUR)
        self.error.pack(anchor=tkinter.W, padx=8)
        self.canvas = tkinter.Canvas(self.window, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, background="white")
        self.canvas.pack(padx=8, pady=8)
        self.show()

    def build_controls(self, sites: tuple[str, ...]) -> None:
        """The row of controls: the site dropdown, the start and end entries, Show and Save as CSV."""
        bar = ttk.Frame(self.window)
        bar.pack(fill=tkinter.X, padx=8, pady=8)
        ttk.Label(bar, text="Site").pack(side=tkinter.LEFT)
        self.site_box = ttk.Combobox(bar, textvariable=self.site, values=sites, width=8)
        self.site_box.pack(side=tkinter.LEFT, padx=4)
        for label, variable in (("Start (UTC)", self.start), ("End (UTC)", self.end)):
            ttk.Label(bar, text=label).pack(side=tkinter.LEFT, padx=(8, 0))
            ttk.Entry(bar, textvariable=variable, width=26).pack(side=tkinter.LEFT, padx=4)
        self.show_button = ttk.Button(bar, text=SHOW, command=self.show)
        self.show_button.pack(side=tkinter.LEFT, padx=4)
        self.save_button = ttk.Button(bar, text=SAVE, command=self.save)
        self.save_button.pack(side=tkinter.LEFT)

    def show(self) -> None:
        """Rereads the report for the chosen site and period and redraws; a refusal clears the table and the curve and
        puts its message in .error: a reversed period shows "period … is empty or reversed"."""
        self.table.delete(*self.table.get_children())
        self.canvas.delete(tkinter.ALL)
        try:
            span = project.period(datetime.fromisoformat(self.start.get()), datetime.fromisoformat(self.end.get()))
            self.report = project.power_report(self.conn, self.site.get(), span)
        except ValueError as refusal:
            self.report = None
            self.error.configure(text=str(refusal))
            self.summary_line.configure(text="")
            return
        self.error.configure(text="")
        for row in project.report_rows(self.report):
            self.table.insert("", tkinter.END, values=table_values(row))
        self.summary_line.configure(text=summary(self.report))
        self.draw_curve(self.report)

    def draw_curve(self, found: project.PowerReport) -> None:
        """The axes, their labels and the site's curve, drawn by draw_power."""
        draw_power(self.canvas, found.curve, found.period, found.site.peak_kw)

    def save(self) -> str | None:
        """Asks for a path and writes project.report_csv there, UTF-8; returns the path, or None when the dialog was
        cancelled or no report is on screen."""
        if self.report is None:
            return None
        path = self.ask_path()
        if not path:
            return None
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.write(project.report_csv(self.report))
        return path
