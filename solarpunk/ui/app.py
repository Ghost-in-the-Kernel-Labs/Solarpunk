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
from solarpunk.leaf.codes import AssetKind, AssetStatus
from solarpunk.ui.cells import band_assets, band_counts, filtered, instant_text, never_text, row_text, showing, store_line
from solarpunk.ui.order import matching, sorted_by
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
SORT_MARK = {False: " ▲", True: " ▼"}
CANVAS_WIDTH = 820
CANVAS_HEIGHT = 420
FEWEST_ROWS = 6
MOST_ROWS = 20
MIN_WIDTH = 820
MIN_HEIGHT = 420
STATUS_BAR = "status_bar"
TOOLTIP_OFFSET = 14
REFRESH = "Refresh"
TOOLTIP_RUN = "Last status: {status} at {instant}"
TOOLTIP_NEVER = "Last status: {status}, {never}"
SUMMARY = "{total} assets: {green} green, {yellow} yellow, {red} red"
GLYPH_TAG = "glyph:{asset_id}"
ROW_TAG = "row:{asset_id}"
TOOLTIP_BACKGROUND = "#ffffe0"
SELECTED_FILL = "#cfe2f3"
SELECTED_TAG = "selected"
ANY_STATUS = "any status"
ANY_KIND = "any kind"
SEARCH = "Search (Ctrl+F)"
SHOWN = "; {shown} of {total} shown"



def tooltip_text(row: project.AssetRow) -> str:
    """The mouseover's line: a yellow row run at 12:00 UTC gives "Last status: yellow at 2026-06-01 12:00 UTC";
    a green row never run gives "Last status: green, never run", one with no endpoint "Last status: green, no feed"."""
    if row.last_run_at is None:
        return TOOLTIP_NEVER.format(status=row.status.value, never=never_text(row))
    return TOOLTIP_RUN.format(status=row.status.value, instant=instant_text(row.last_run_at))


def marked_headings() -> tuple[str, ...]:
    """The headings as wide as they can be drawn, each with a sort mark: ("Asset ▲", "Name ▲", …)."""
    return tuple(heading + SORT_MARK[False] for heading in HEADINGS)


def column_xs(lines: Iterable[tuple[str, ...]], measure: Callable[[str], int]) -> tuple[int, ...]:
    """Each column's left x, the first at 40, each next one the widest text before it plus a 16 px gap, a heading
    measured with room for its sort mark (9.4): with measure = 7 px a character, column_xs([], measure) starts
    (40, 105), "Asset ▲" being 49 px."""
    widths = [0] * len(HEADINGS)
    for line in (marked_headings(), *lines):
        for index, text in enumerate(line):
            widths[index] = max(widths[index], measure(text))
    xs = [FIRST_X]
    for width in widths[:-1]:
        xs.append(xs[-1] + width + COLUMN_GAP)
    return tuple(xs)


def width_for(xs: tuple[int, ...], lines: Iterable[tuple[str, ...]], measure: Callable[[str], int]) -> int:
    """The width that holds every column, the last one's widest text and a 12 px margin, never under 820."""
    last = max((measure(line[-1]) for line in (marked_headings(), *lines)), default=0)
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
        self.found: project.Attention | None = None
        self.sort_column = 0
        self.sort_reverse = False
        self.selected: str | None = None
        self.frame = ttk.Frame(root)
        self.frame.pack(fill=tkinter.BOTH, expand=True)
        self.band = ttk.Frame(self.frame)
        self.band_buttons: dict[str, ttk.Button] = {}
        self.make_list()
        self.make_bars()
        self.lay_out()
        self.tooltip = self.make_tooltip(root)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", self.hide_tooltip)
        self.header.bind("<Button-1>", self.on_heading)
        self.bind_keys(root.winfo_toplevel())
        self.refresh()
        self.fit(root.winfo_toplevel())

    def make_list(self) -> None:
        """The fonts, the list's canvas, the heading strip above it and the scrollbar beside it (the list made before
        the strip, so a window's first canvas is the list)."""
        self.font = tkfont.nametofont("TkDefaultFont")
        self.heading_font = self.font.copy()
        self.heading_font.configure(weight="bold")
        self.xs = column_xs((), self.measure)
        self.canvas = tkinter.Canvas(self.frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, highlightthickness=0)
        self.header = tkinter.Canvas(self.frame, width=CANVAS_WIDTH, height=HEADING_HEIGHT, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient=tkinter.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

    def make_bars(self) -> None:
        """The toolbar with Refresh at its right, and the status bar: the store and its last run on the left, the
        summary on the right (9.5)."""
        self.toolbar = ttk.Frame(self.frame)
        self.refresh_button = ttk.Button(self.toolbar, text=REFRESH, command=self.refresh)
        self.refresh_button.pack(side=tkinter.RIGHT)
        self.status_bar = ttk.Frame(self.frame, name=STATUS_BAR, relief=tkinter.SUNKEN, borderwidth=1)
        self.store_label = ttk.Label(self.status_bar)
        self.store_label.pack(side=tkinter.LEFT, padx=4)
        self.status_line = ttk.Label(self.status_bar)
        self.status_line.pack(side=tkinter.RIGHT, padx=4)

    def lay_out(self) -> None:
        """Top to bottom: the toolbar, the band, the filter row, the headings, the list and its scrollbar (which
        stretch), the status bar."""
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.band.grid(row=1, column=0, sticky="w", pady=(2, 4))
        self.make_filters()
        self.filters.grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.header.grid(row=3, column=0, sticky="ew")
        self.canvas.grid(row=4, column=0, sticky="nsew")
        self.scrollbar.grid(row=4, column=1, sticky="ns")
        self.status_bar.grid(row=5, column=0, columnspan=2, sticky="ew")
        self.frame.rowconfigure(4, weight=1)
        self.frame.columnconfigure(0, weight=1)

    def fit(self, window: tkinter.Misc) -> None:
        """Sizes the list to the fleet, at least 6 rows and at most 20 before it scrolls, and gives the window a
        minimum size of 820 by 420 (9.5): the demo's eleven rows open without dead space below them."""
        rows = min(max(len(self.all_rows), FEWEST_ROWS), MOST_ROWS)
        self.canvas.configure(height=rows * ROW_HEIGHT)
        window.minsize(MIN_WIDTH, MIN_HEIGHT)

    def make_filters(self) -> None:
        """The filter row (9.4): a search box, a status box and a kind box; each change redraws the list."""
        self.filters = ttk.Frame(self.frame)
        self.search_text = tkinter.StringVar()
        self.status_choice = tkinter.StringVar(value=ANY_STATUS)
        self.kind_choice = tkinter.StringVar(value=ANY_KIND)
        ttk.Label(self.filters, text=SEARCH).pack(side=tkinter.LEFT)
        self.search_box = ttk.Entry(self.filters, textvariable=self.search_text, width=24)
        self.search_box.pack(side=tkinter.LEFT, padx=(4, 12))
        self.status_box = ttk.Combobox(self.filters, textvariable=self.status_choice, state="readonly", width=12,
                                       values=(ANY_STATUS, *(s.value for s in AssetStatus)))
        self.status_box.pack(side=tkinter.LEFT, padx=(0, 8))
        self.kind_box = ttk.Combobox(self.filters, textvariable=self.kind_choice, state="readonly", width=12,
                                     values=(ANY_KIND, *(k.name.lower() for k in AssetKind)))
        self.kind_box.pack(side=tkinter.LEFT)
        for variable in (self.search_text, self.status_choice, self.kind_choice):
            variable.trace_add("write", lambda *_: self.redraw())

    def bind_keys(self, window: tkinter.Misc) -> None:
        """Ctrl+F to the search box, Esc clears the filters, F5 refreshes, Up and Down move the selection, Enter opens
        the selected asset; each on the fleet's own window, so an asset window's keys stay its own."""
        window.bind("<Control-f>", lambda _e: self.search_box.focus_set())
        window.bind("<Escape>", lambda _e: self.clear_filters())
        window.bind("<F5>", lambda _e: self.refresh())
        window.bind("<Up>", lambda _e: self.move_selection(-1))
        window.bind("<Down>", lambda _e: self.move_selection(1))
        window.bind("<Return>", lambda _e: self.open_selected())

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
        """Rereads the store, then redraws: after a fault opens an outage on OAHE-INV-001, refresh() turns its glyph
        "#c0392b"."""
        self.all_rows = project.asset_rows(self.conn)
        self.found = project.attention(self.conn)
        self.store_label.configure(text=store_line(project.store_name(self.conn), project.fleet_last_run(self.conn)))
        self.redraw()

    def banded(self) -> tuple[project.AssetRow, ...]:
        """The rows the band's filter keeps (9.3), every row with none."""
        assert self.found is not None
        return filtered(self.all_rows, None if self.filter_key is None else band_assets(self.found, self.filter_key))

    def kept(self) -> tuple[project.AssetRow, ...]:
        """The rows the band's filter, the search, the status and the kind keep, in the chosen sort."""
        status = None if self.status_choice.get() == ANY_STATUS else AssetStatus(self.status_choice.get())
        kind = None if self.kind_choice.get() == ANY_KIND else AssetKind[self.kind_choice.get().upper()]
        rows = matching(self.banded(), self.search_text.get(), status, kind)
        return sorted_by(rows, self.sort_column, self.sort_reverse)

    def redraw(self) -> None:
        """Redraws the band, the headings and the rows the filters keep, without rereading the store, the columns as
        wide as the whole fleet's text so a filter never moves them."""
        if self.found is None:
            return
        self.draw_band(self.found)
        self.rows = self.kept()
        lines = [row_text(row) for row in self.all_rows]
        self.xs = column_xs(lines, self.measure)
        width = width_for(self.xs, lines, self.measure)
        self.header.delete(tkinter.ALL)
        for index, (x, text) in enumerate(zip(self.xs, HEADINGS)):
            sorted_here = index == self.sort_column and (index, self.sort_reverse) != (0, False)  # id order is unmarked
            mark = SORT_MARK[self.sort_reverse] if sorted_here else ""
            self.header.create_text(x, HEADING_HEIGHT // 2, text=text + mark, anchor=tkinter.W, font=self.heading_font,
                                    tags=(HEADING_TAG,))
        self.header.configure(width=width)
        self.canvas.delete(tkinter.ALL)
        if self.selected not in [row.asset_id for row in self.rows]:
            self.selected = None
        for index, row in enumerate(self.rows):
            if row.asset_id == self.selected:
                self.canvas.create_rectangle(0, index * ROW_HEIGHT, width, (index + 1) * ROW_HEIGHT, fill=SELECTED_FILL,
                                             outline="", tags=(SELECTED_TAG,))
            self.draw_row(index, row)
        self.canvas.configure(width=width, scrollregion=(0, 0, width, len(self.rows) * ROW_HEIGHT))
        narrowed = len(self.rows) != len(self.banded())  # the band's own filter is said by showing()
        shown = SHOWN.format(shown=len(self.rows), total=len(self.all_rows)) if narrowed else ""
        self.status_line.configure(text=summary(self.all_rows) + showing(self.filter_key) + shown)

    def on_heading(self, event: tkinter.Event) -> None:
        """A click on a heading sorts by its column; a second click on the same one turns the order round."""
        column = max((i for i, x in enumerate(self.xs) if x <= event.x), default=0)
        self.sort_reverse = not self.sort_reverse if column == self.sort_column else False
        self.sort_column = column
        self.redraw()

    def clear_filters(self) -> None:
        """Esc: empties the search, sets the status and kind boxes to any, and lifts the band's filter."""
        self.filter_key = None
        self.search_text.set("")
        self.status_choice.set(ANY_STATUS)
        self.kind_choice.set(ANY_KIND)
        self.redraw()

    def move_selection(self, step: int) -> None:
        """Up or Down: the selection moves one row, starting at the first, never past either end."""
        if not self.rows:
            return
        ids = [row.asset_id for row in self.rows]
        index = -1 if self.selected is None else ids.index(self.selected)
        self.selected = ids[min(max(index + step, 0), len(ids) - 1)]
        self.redraw()

    def open_selected(self) -> None:
        """Enter: opens the selected asset, as a click on its row does; with nothing selected, nothing opens."""
        if self.selected is not None:
            self.on_open_asset(self.selected)

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
        self.redraw()

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
            self.selected = row.asset_id
            self.redraw()
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
