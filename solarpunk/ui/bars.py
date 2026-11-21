"""The error counts' bars (10.6, 10.7, SOL-15, SP-024): one row per code (or per asset), two bars in it, faults and
suggestions told apart and never added together, each bar's count written beside it. The geometry is pure, with no
tkinter, as chart.py's is, so the fast loop tests it; draw_bars only places what bar_rows returns on a canvas it is
given. The longest bar is the largest count; a count of 0 is a bar of no length and the words "0 faults"."""
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter

WIDTH = 720
LABEL_WIDTH = 120
LABEL_GAP = 16
TEXT_ROOM = 110
TOP = 30
ROW_HEIGHT = 42
BAR_HEIGHT = 12
BAR_GAP = 3
FAULT_COLOUR = "#c0392b"
SUGGESTION_COLOUR = "#e0b000"
LEGEND = (("faults", FAULT_COLOUR), ("suggestions", SUGGESTION_COLOUR))
Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class BarRow:
    """One row's label and its two bars with their words: for ("SEN-001", 0, 1) on the default canvas, the fault bar has
    no length and reads "0 faults", the suggestion bar runs the full length and reads "1 suggestion"."""

    label: str
    centre_y: float
    fault: Box
    suggestion: Box
    fault_text: str
    suggestion_text: str


def counted(count: int, word: str) -> str:
    """A count with its word: counted(1, "fault") is "1 fault", counted(0, "fault") "0 faults"."""
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def left_of(label_widths: list[int]) -> int:
    """Where the bars start: past the widest label and a 16 px gap, never before 120."""
    return max([LABEL_WIDTH, *(width + LABEL_GAP for width in label_widths)])


def height_of(rows: int) -> int:
    """The canvas's height for so many rows under the legend: height_of(1) is 82."""
    return TOP + rows * ROW_HEIGHT + 10


def bar_rows(counts: tuple[tuple[str, int, int], ...], width: int = WIDTH,
             left: int = LABEL_WIDTH) -> tuple[BarRow, ...]:
    """The rows for (label, faults, suggestions) counts, in the order given, each bar as long as its count's share of the
    largest count of either kind over the room left of the words: one row of ("SEN-001", 0, 1) on 720 px from 120
    gives a suggestion bar from 120 to 610."""
    room = width - left - TEXT_ROOM
    largest = max((max(faults, suggestions) for _, faults, suggestions in counts), default=0) or 1
    found = []
    for index, (label, faults, suggestions) in enumerate(counts):
        centre_y = TOP + index * ROW_HEIGHT + ROW_HEIGHT / 2
        fault = (left, centre_y - BAR_HEIGHT - BAR_GAP, left + faults / largest * room, centre_y - BAR_GAP)
        suggestion = (left, centre_y + BAR_GAP, left + suggestions / largest * room, centre_y + BAR_HEIGHT + BAR_GAP)
        found.append(BarRow(label, centre_y, fault, suggestion, counted(faults, "fault"), counted(suggestions, "suggestion")))
    return tuple(found)


def draw_bars(canvas: "tkinter.Canvas", rows: tuple[BarRow, ...], tag: str = "bar") -> None:
    """Draws the legend, then each row's label, its two bars (a bar of no length not drawn) and their words, every item
    of a row tagged "<tag>:<label>" as well as tag, so a click can tell which row it was."""
    legend_x = WIDTH - 220
    for word, colour in LEGEND:
        canvas.create_rectangle(legend_x, 8, legend_x + 12, 18, fill=colour, outline="")
        canvas.create_text(legend_x + 16, 13, text=word, anchor="w")
        legend_x += 100
    for row in rows:
        tags = (tag, f"{tag}:{row.label}")
        canvas.create_text(8, row.centre_y, text=row.label, anchor="w", tags=tags)
        for box, words, colour in ((row.fault, row.fault_text, FAULT_COLOUR),
                                   (row.suggestion, row.suggestion_text, SUGGESTION_COLOUR)):
            if box[2] > box[0]:
                canvas.create_rectangle(*box, fill=colour, outline="", tags=tags)
            canvas.create_text(box[2] + 6, (box[1] + box[3]) / 2, text=words, anchor="w", tags=tags)
