"""The solar-panel glyph (3.1, SP-007): a 24×16 picture of a panel on a stand, its face in the asset's AssetStatus colour.
The colours and the geometry are pure functions, tested headless; draw_panel only hands them to a tkinter.Canvas, so
this module does not import tkinter at all (the Canvas is a parameter)."""
from typing import TYPE_CHECKING

from solarpunk.leaf.codes import AssetStatus

if TYPE_CHECKING:
    import tkinter

COLOURS: dict[AssetStatus, str] = {
    AssetStatus.GREEN: "#2e8b57",
    AssetStatus.YELLOW: "#e0b000",
    AssetStatus.RED: "#c0392b",
}
STAND_COLOUR = "#606060"
PART_SUFFIX = ":part"
WIDTH = 24
FACE_HEIGHT = 12
HEIGHT = 16
CORNER = 3
CELL_WIDTH = 8
CELL_HEIGHT = 6
STAND_LEFT = 10
STAND_RIGHT = 14


def colour_of(status: AssetStatus) -> str:
    """The glyph's colour for a status: colour_of(AssetStatus.GREEN) is "#2e8b57", YELLOW "#e0b000", RED "#c0392b"."""
    return COLOURS[status]


def darker(colour: str) -> str:
    """The colour at half its brightness, for the cell lines: darker("#2e8b57") is "#17452b"; darker("#c0392b") is
    "#601c15"."""
    channels = (int(colour[start:start + 2], 16) // 2 for start in (1, 3, 5))
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def face_points(left: int, top: int) -> tuple[int, ...]:
    """The panel face's outline as a smoothed polygon's points, its corners rounded by 3 px: face_points(0, 0) starts
    (3, 0, 21, 0, 24, 0, 24, 3) and ends (0, 3, 0, 0); the face spans left..left+24 and top..top+12."""
    right, bottom = left + WIDTH, top + FACE_HEIGHT
    return (
        left + CORNER, top, right - CORNER, top, right, top, right, top + CORNER,
        right, bottom - CORNER, right, bottom, right - CORNER, bottom, left + CORNER, bottom,
        left, bottom, left, bottom - CORNER, left, top + CORNER, left, top,
    )


def cell_lines(left: int, top: int) -> tuple[tuple[int, int, int, int], ...]:
    """The lines that split the face into a 2×3 grid of cells, two upright then one across: cell_lines(0, 0) is
    ((8, 0, 8, 12), (16, 0, 16, 12), (0, 6, 24, 6))."""
    uprights = tuple((left + step, top, left + step, top + FACE_HEIGHT) for step in (CELL_WIDTH, 2 * CELL_WIDTH))
    return uprights + ((left, top + CELL_HEIGHT, left + WIDTH, top + CELL_HEIGHT),)


def stand_box(left: int, top: int) -> tuple[int, int, int, int]:
    """The short stand below the face, as a rectangle's corners: stand_box(0, 0) is (10, 12, 14, 16)."""
    return (left + STAND_LEFT, top + FACE_HEIGHT, left + STAND_RIGHT, top + HEIGHT)


def draw_panel(canvas: "tkinter.Canvas", left: int, top: int, colour: str, tag: str) -> None:
    """Draws the glyph with its top-left corner at (left, top): the face, filled in the colour, carries the tag alone, so
    canvas.find_withtag("glyph:OAHE-INV-001") is that one item; the cell lines and the stand carry tag + ":part"."""
    canvas.create_polygon(face_points(left, top), smooth=True, fill=colour, outline=darker(colour), tags=(tag,))
    for line in cell_lines(left, top):
        canvas.create_line(line, fill=darker(colour), tags=(tag + PART_SUFFIX,))
    canvas.create_rectangle(stand_box(left, top), fill=STAND_COLOUR, outline=STAND_COLOUR, tags=(tag + PART_SUFFIX,))
