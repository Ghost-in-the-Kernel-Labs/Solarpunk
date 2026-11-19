"""The fleet window (3.1, SP-007): every asset in id order, one 28 px row each on a scrolling Canvas under a strip of
column headings (9.1), the solar-panel glyph in its status colour, then its id, name, kind, status, last run and
failing test; a mouseover shows the last status and the run's instant, a click hands the asset's id to on_open_asset
(3.4 wires the asset window to it), Refresh rereads the store. All the window shows comes from one call,
project.asset_rows; the text is made by the pure functions row_text, tooltip_text, summary and column_xs, tested
headless, and the widgets only place it. A column is as wide as its widest text, heading included, so a long name
never runs into the next column."""
import sqlite3
import tkinter
from collections.abc import Callable, Iterable
from tkinter import font as tkfont
from tkinter import ttk

from solarpunk import project
from solarpunk.leaf.codes import AssetStatus
from solarpunk.ui.cells import band_assets, band_counts, cause_text, filtered, instant_text, showing
from solarpunk.ui.glyph import colour_of, draw_panel

ROW_HEIGHT = 28
GLYPH_X = 8
GLYPH_TOP = 6
FIRST_X = 40
COLUMN_GAP = 16
RIGHT_MARGIN = 12
HEADINGS = ("Asset", "Name", "Kind", "Status", "Cause", "Last run", "Failing")
HEADING_HEIGHT = 24
HEADING_TAG = "heading"
CANVAS_WIDTH = 820
CANVAS_HEIGHT = 420
TOOLTIP_OFFSET = 14
NEVER_RUN = "never run"
NO_FEED = "no feed"
REFRESH = "Refresh"
TOOLTIP_RUN = "Last status: {status} at {instant}"
TOOLTIP_NEVER = "Last status: {status}, {never}"
SUMMARY = "{total} assets: {green} green, {yellow} yellow, {red} red"
GLYPH_TAG = "glyph:{asset_id}"
ROW_TAG = "row:{asset_id}"
TOOLTIP_BACKGROUND = "#ffffe0"


def never_text(row: project.AssetRow) -> str:
    """Why a row has no run: "never run" for an asset with an endpoint, "no feed" for one the run cannot reach."""
    return NEVER_RUN if row.has_feed else NO_FEED


def row_text(row: project.AssetRow) -> tuple[str, str, str, str, str, str, str]:
    """A row's seven words: AssetRow("OAHE-INV-002", "Inverter 2", INVERTER, YELLOW, 12:00 UTC, "reachable") gives
    ("OAHE-INV-002", "Inverter 2", "inverter", "yellow", "reachable", "2026-06-01 12:00 UTC", "reachable"), its cause
    fifth (9.2, cells.cause_text); never run gives "never run" in the sixth place, or "no feed" for an asset with no
    endpoint."""
    last_run = never_text(row) if row.last_run_at is None else instant_text(row.last_run_at)
    return (row.asset_id, row.name, row.kind.name.lower(), row.status.value, cause_text(row), last_run, row.failing)


def tooltip_text(row: project.AssetRow) -> str:
    """The mouseover's line: a yellow row run at 12:00 UTC gives "Last status: yellow at 2026-06-01 12:00 UTC";
    a green row never run gives "Last status: green, never run", one with no endpoint "Last status: green, no feed"."""
    if row.last_run_at is None:
        return TOOLTIP_NEVER.format(status=row.status.value, never=never_text(row))
    return TOOLTIP_RUN.format(status=row.status.value, instant=instant_text(row.last_run_at))


def column_xs(lines: Iterable[tuple[str, ...]], measure: Callable[[str], int]) -> tuple[int, ...]:
    """Each column's left x, the first at 40, each next one the widest text before it (heading included) plus a 16 px
    gap: with measure = 7 px a character, column_xs([("Asset", "Name")], measure) is (40, 91)."""
    widths = [0] * len(HEADINGS)
    for line in (HEADINGS, *lines):
        for index, text in enumerate(line):
            widths[index] = max(widths[index], measure(text))
    xs = [FIRST_X]
    for width in widths[:-1]:
        xs.append(xs[-1] + width + COLUMN_GAP)
    return tuple(xs)


def width_for(xs: tuple[int, ...], lines: Iterable[tuple[str, ...]], measure: Callable[[str], int]) -> int:
    """The width that holds every column, the last one's widest text and a 12 px margin, never under 820."""
    last = max((measure(line[-1]) for line in (HEADINGS, *lines)), default=0)
    return max(CANVAS_WIDTH, xs[-1] + last + RIGHT_MARGIN)


def summary(rows: tuple[project.AssetRow, ...]) -> str:
    """The status line: four green rows, one yellow and one red give "6 assets: 4 green, 1 yellow, 1 red"; no rows give
    "0 assets: 0 green, 0 yellow, 0 red"."""
    counts = {status: sum(1 for row in rows if row.status is status) for status in AssetStatus}
    return SUMMARY.format(total=len(rows), green=counts[AssetStatus.GREEN], yellow=counts[AssetStatus.YELLOW],
                          red=counts[AssetStatus.RED])


def row_at(y: float, count: int) -> int | None:
    """The index of the row under a canvas y, or None below the last or above the first: row_at(0, 3) is 0,
    row_at(27.9, 3) is 0, row_at(28, 3) is 1, row_at(84, 3) is None, row_at(-1, 3) is None."""
    if y < 0:
        return None
    index = int(y) // ROW_HEIGHT
    return index if index < count else None


class FleetWindow:
    """The fleet window inside a root: FleetWindow(tkinter.Tk(), conn).rows is project.asset_rows(conn), drawn; with no
    on_open_asset given, a clicked asset's id is only appended to .opened (3.4 passes the asset window's opener)."""

    def __init__(self, root: tkinter.Misc, conn: sqlite3.Connection,
                 on_open_asset: Callable[[str], None] | None = None) -> None:
        """Builds the canvas, its scrollbar, Refresh and the status line, then reads the store: after
        FleetWindow(root, conn), .status_line["text"] is summary(project.asset_rows(conn))."""
        self.conn = conn
        self.opened: list[str] = []
        self.on_open_asset = self.opened.append if on_open_asset is None else on_open_asset
        self.rows: tuple[project.AssetRow, ...] = ()
        self.all_rows: tuple[project.AssetRow, ...] = ()
        self.filter_key: str | None = None
        self.frame = ttk.Frame(root)
        self.frame.pack(fill=tkinter.BOTH, expand=True)
        self.band = ttk.Frame(self.frame)
        self.band_buttons: dict[str, ttk.Button] = {}
        self.font = tkfont.nametofont("TkDefaultFont")
        self.heading_font = self.font.copy()
        self.heading_font.configure(weight="bold")
        self.xs = column_xs((), self.measure)
        self.canvas = tkinter.Canvas(self.frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, highlightthickness=0)
        self.header = tkinter.Canvas(self.frame, width=CANVAS_WIDTH, height=HEADING_HEIGHT, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient=tkinter.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.refresh_button = ttk.Button(self.frame, text=REFRESH, command=self.refresh)
        self.status_line = ttk.Label(self.frame)
        self.band.grid(row=0, column=0, sticky="w", pady=(2, 4))
        self.header.grid(row=1, column=0, sticky="ew")
        self.canvas.grid(row=2, column=0, sticky="nsew")
        self.scrollbar.grid(row=2, column=1, sticky="ns")
        self.refresh_button.grid(row=3, column=0, sticky="w")
        self.status_line.grid(row=4, column=0, sticky="w")
        self.frame.rowconfigure(2, weight=1)
        self.frame.columnconfigure(0, weight=1)
        self.tooltip = self.make_tooltip(root)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", self.hide_tooltip)
        self.refresh()

    def make_tooltip(self, root: tkinter.Misc) -> ttk.Label:
        """A borderless window holding one label, hidden until a mouseover: make_tooltip(root).master is that window,
        withdrawn."""
        window = tkinter.Toplevel(root)
        window.overrideredirect(True)
        window.withdraw()
        label = ttk.Label(window, background=TOOLTIP_BACKGROUND, relief=tkinter.SOLID, borderwidth=1)
        label.pack()
        return label

    def measure(self, text: str) -> int:
        """The pixel width of text in the wider of the two fonts the window writes in (the headings' bold)."""
        return max(self.font.measure(text), self.heading_font.measure(text))

    def refresh(self) -> None:
        """Rereads the store and redraws the headings and every row, the columns as wide as their text: after a fault
        opens an outage on OAHE-INV-001, refresh() turns its glyph "#c0392b"."""
        self.all_rows = project.asset_rows(self.conn)
        found = project.attention(self.conn)
        self.draw_band(found)
        assets = None if self.filter_key is None else band_assets(found, self.filter_key)
        self.rows = filtered(self.all_rows, assets)
        lines = [row_text(row) for row in self.all_rows]
        self.xs = column_xs(lines, self.measure)
        width = width_for(self.xs, lines, self.measure)
        self.header.delete(tkinter.ALL)
        for x, text in zip(self.xs, HEADINGS):
            self.header.create_text(x, HEADING_HEIGHT // 2, text=text, anchor=tkinter.W, font=self.heading_font,
                                    tags=(HEADING_TAG,))
        self.header.configure(width=width)
        self.canvas.delete(tkinter.ALL)
        for index, row in enumerate(self.rows):
            self.draw_row(index, row)
        self.canvas.configure(width=width, scrollregion=(0, 0, width, len(self.rows) * ROW_HEIGHT))
        self.status_line.configure(text=summary(self.all_rows) + showing(self.filter_key))

    def draw_band(self, found: project.Attention) -> None:
        """The attention band (9.3): a button per count, zero shown; the one filtering the list stays pressed."""
        for key, text in band_counts(found):
            button = self.band_buttons.get(key)
            if button is None:
                button = ttk.Button(self.band, command=lambda k=key: self.toggle(k))
                button.pack(side=tkinter.LEFT, padx=(0, 6))
                self.band_buttons[key] = button
            button.configure(text=text)
            button.state(["pressed"] if key == self.filter_key else ["!pressed"])

    def toggle(self, key: str) -> None:
        """Filters the list to one count's assets, or clears the filter when that count is clicked again."""
        self.filter_key = None if self.filter_key == key else key
        self.refresh()

    def draw_row(self, index: int, row: project.AssetRow) -> None:
        """Draws one row at index * 28 px: the glyph tagged "glyph:<id>", the six words tagged "row:<id>"."""
        top = index * ROW_HEIGHT
        draw_panel(self.canvas, GLYPH_X, top + GLYPH_TOP, colour_of(row.status), GLYPH_TAG.format(asset_id=row.asset_id))
        for x, text in zip(self.xs, row_text(row)):
            self.canvas.create_text(x, top + ROW_HEIGHT // 2, text=text, anchor=tkinter.W,
                                    tags=(ROW_TAG.format(asset_id=row.asset_id),))

    def row_under(self, event: tkinter.Event) -> project.AssetRow | None:
        """The row under the pointer, the canvas scrolled or not: an event at y 30 on an unscrolled canvas is row 1."""
        index = row_at(self.canvas.canvasy(event.y), len(self.rows))
        return None if index is None else self.rows[index]

    def on_click(self, event: tkinter.Event) -> None:
        """A click on a row hands its id to on_open_asset: a click at y 30 calls on_open_asset("OAHE-INV-001") when
        that is the second row; a click below the last row calls nothing."""
        row = self.row_under(event)
        if row is not None:
            self.on_open_asset(row.asset_id)

    def on_motion(self, event: tkinter.Event) -> None:
        """Over a row, shows tooltip_text(row) beside the pointer; below the last row, hides it."""
        row = self.row_under(event)
        if row is None:
            self.hide_tooltip(event)
            return
        self.tooltip.configure(text=tooltip_text(row))
        window = self.tooltip.winfo_toplevel()
        window.geometry(f"+{event.x_root + TOOLTIP_OFFSET}+{event.y_root + TOOLTIP_OFFSET}")
        window.deiconify()

    def hide_tooltip(self, event: tkinter.Event | None = None) -> None:
        """Withdraws the tooltip's window: after hide_tooltip(), its state() is "withdrawn"."""
        self.tooltip.winfo_toplevel().withdraw()
