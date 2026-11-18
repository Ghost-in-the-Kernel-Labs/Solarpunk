"""The fleet window (3.1, SP-007): every asset in id order, one 28 px row each on a scrolling Canvas, the solar-panel
glyph in its status colour, then its id, name, kind, status, last run and failing test; a mouseover shows the last
status and the run's instant, a click hands the asset's id to on_open_asset (3.4 wires the asset window to it), Refresh
rereads the store. All the window shows comes from one call, project.asset_rows; the text is made by the pure functions
row_text, tooltip_text and summary, tested headless, and the widgets only place it."""
import sqlite3
import tkinter
from collections.abc import Callable
from tkinter import ttk

from solarpunk import project
from solarpunk.leaf.codes import AssetStatus
from solarpunk.ui.glyph import colour_of, draw_panel

ROW_HEIGHT = 28
GLYPH_X = 8
GLYPH_TOP = 6
COLUMN_XS = (40, 150, 260, 340, 410, 650)
CANVAS_WIDTH = 820
CANVAS_HEIGHT = 420
TOOLTIP_OFFSET = 14
NEVER_RUN = "never run"
REFRESH = "Refresh"
TOOLTIP_RUN = "Last status: {status} at {instant}"
TOOLTIP_NEVER = "Last status: {status}, never run"
SUMMARY = "{total} assets: {green} green, {yellow} yellow, {red} red"
GLYPH_TAG = "glyph:{asset_id}"
ROW_TAG = "row:{asset_id}"
TOOLTIP_BACKGROUND = "#ffffe0"


def row_text(row: project.AssetRow) -> tuple[str, str, str, str, str, str]:
    """A row's six words: AssetRow("OAHE-INV-002", "Inverter 2", INVERTER, YELLOW, 12:00 UTC, "reachable") gives
    ("OAHE-INV-002", "Inverter 2", "inverter", "yellow", "2026-06-01T12:00:00+00:00", "reachable"); never run gives
    "never run" in the fifth place."""
    last_run = NEVER_RUN if row.last_run_at is None else row.last_run_at.isoformat()
    return (row.asset_id, row.name, row.kind.name.lower(), row.status.value, last_run, row.failing)


def tooltip_text(row: project.AssetRow) -> str:
    """The mouseover's line: a yellow row run at 12:00 UTC gives "Last status: yellow at 2026-06-01T12:00:00+00:00";
    a green row never run gives "Last status: green, never run"."""
    if row.last_run_at is None:
        return TOOLTIP_NEVER.format(status=row.status.value)
    return TOOLTIP_RUN.format(status=row.status.value, instant=row.last_run_at.isoformat())


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
        self.frame = ttk.Frame(root)
        self.frame.pack(fill=tkinter.BOTH, expand=True)
        self.canvas = tkinter.Canvas(self.frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient=tkinter.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.refresh_button = ttk.Button(self.frame, text=REFRESH, command=self.refresh)
        self.status_line = ttk.Label(self.frame)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.refresh_button.grid(row=1, column=0, sticky="w")
        self.status_line.grid(row=2, column=0, sticky="w")
        self.frame.rowconfigure(0, weight=1)
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

    def refresh(self) -> None:
        """Rereads the store and redraws every row: after a fault opens an outage on OAHE-INV-001, refresh() turns its
        glyph "#c0392b"."""
        self.rows = project.asset_rows(self.conn)
        self.canvas.delete(tkinter.ALL)
        for index, row in enumerate(self.rows):
            self.draw_row(index, row)
        self.canvas.configure(scrollregion=(0, 0, CANVAS_WIDTH, len(self.rows) * ROW_HEIGHT))
        self.status_line.configure(text=summary(self.rows))

    def draw_row(self, index: int, row: project.AssetRow) -> None:
        """Draws one row at index * 28 px: the glyph tagged "glyph:<id>", the six words tagged "row:<id>"."""
        top = index * ROW_HEIGHT
        draw_panel(self.canvas, GLYPH_X, top + GLYPH_TOP, colour_of(row.status), GLYPH_TAG.format(asset_id=row.asset_id))
        for x, text in zip(COLUMN_XS, row_text(row)):
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
