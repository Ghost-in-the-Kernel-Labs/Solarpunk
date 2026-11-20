"""The fleet window (3.1): the glyph's colours and geometry and the window's words, headless; the window itself under a
display (xvfb-run -a .venv/bin/pytest test/solarpunk/test_ui.py), skipping with "no display" where tkinter.Tk() raises
TclError. The store is built as test_project_run.py builds its run fixture, copied, never imported: GREEN OAHE-INV-001
(a passing run), YELLOW OAHE-INV-002 (a failing reachable), RED OAHE-INV-003 (an open INV-001), and four never run."""
import importlib.util
import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind, AssetStatus
from solarpunk.remote import results
from solarpunk.ui import glyph

ENGINEER = "site@oahe.example"  # SP-015: a fault names the engineer who assigned it; the fixtures' site engineer

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import __main__ as entry
    from solarpunk.ui import app

INV1 = "OAHE-INV-001"
INV2 = "OAHE-INV-002"
INV3 = "OAHE-INV-003"
SITE = Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None, location="Pierre, SD",
             engineer_email=ENGINEER)
FLEET = (
    SITE,
    Asset(INV1, AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 1", 100.0),
    Asset(INV2, AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 2", 100.0),
    Asset(INV3, AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 3", 100.0),
    Asset("OAHE-STR-001", AssetKind.STRING, "OAHE", INV1, "String 1", 50.0),
    Asset("OAHE-STR-002", AssetKind.STRING, "OAHE", INV1, "String 2", 50.0),
    Asset("OAHE-STR-003", AssetKind.STRING, "OAHE", INV2, "String 3", 50.0),
)
IDS = (INV1, INV2, INV3, "OAHE-SIT-001", "OAHE-STR-001", "OAHE-STR-002", "OAHE-STR-003")
RUN_AT = at(2026, 6, 1, 12)
GREEN = "#2e8b57"
YELLOW = "#e0b000"
RED = "#c0392b"


def display_available() -> bool:
    """Whether a Tk window can open here: False with no DISPLAY (tkinter.Tk() raises TclError) or no tkinter at all."""
    if not HAS_TKINTER:
        return False
    try:
        tkinter.Tk().destroy()
    except tkinter.TclError:
        return False
    return True


def fill_store(conn: sqlite3.Connection) -> None:
    """The three colours in one store: after fill_store(conn), project.asset_status(conn, INV3) is RED."""
    project.load_fleet(conn, FLEET)
    results.record(conn, "reachable", INV1, RUN_AT, results.Result(True, "24 records"))
    results.record(conn, "reachable", INV2, RUN_AT, results.Result(False, "127.0.0.1:1 is unreachable"))
    project.assign_fault(conn, INV3, "INV-001", at(2026, 6, 1, 9), ENGINEER)


def three_colour_store() -> sqlite3.Connection:
    """An in-memory store filled by fill_store: len(project.asset_rows(three_colour_store())) is 7."""
    conn = project.open_store()
    fill_store(conn)
    return conn


def row(status: AssetStatus, last_run: bool) -> "project.AssetRow":
    """A made-up row: row(AssetStatus.YELLOW, True) is OAHE-INV-002's, run at 12:00 UTC with reachable failing."""
    return project.AssetRow(INV2, "Inverter 2", AssetKind.INVERTER, status, RUN_AT if last_run else None,
                            "reachable" if last_run else "—")


class TheGlyph(unittest.TestCase):
    def test_the_three_colours(self) -> None:
        self.assertEqual(glyph.colour_of(AssetStatus.GREEN), GREEN)
        self.assertEqual(glyph.colour_of(AssetStatus.YELLOW), YELLOW)
        self.assertEqual(glyph.colour_of(AssetStatus.RED), RED)
        self.assertEqual(len(set(glyph.COLOURS.values())), len(AssetStatus))

    def test_darker_halves_each_channel(self) -> None:
        self.assertEqual(glyph.darker(GREEN), "#17452b")
        self.assertEqual(glyph.darker(RED), "#601c15")
        self.assertEqual(glyph.darker("#ffffff"), "#7f7f7f")
        self.assertEqual(glyph.darker("#010203"), "#000101")

    def test_the_face_is_24_by_12_with_rounded_corners(self) -> None:
        self.assertEqual(glyph.face_points(0, 0), (3, 0, 21, 0, 24, 0, 24, 3, 24, 9, 24, 12, 21, 12, 3, 12,
                                                   0, 12, 0, 9, 0, 3, 0, 0))
        moved = glyph.face_points(8, 6)
        self.assertEqual(moved, tuple(v + (8 if i % 2 == 0 else 6) for i, v in enumerate(glyph.face_points(0, 0))))

    def test_the_cells_are_a_2_by_3_grid(self) -> None:
        self.assertEqual(glyph.cell_lines(0, 0), ((8, 0, 8, 12), (16, 0, 16, 12), (0, 6, 24, 6)))
        self.assertEqual(glyph.cell_lines(8, 6), ((16, 6, 16, 18), (24, 6, 24, 18), (8, 12, 32, 12)))

    def test_the_stand_fills_the_glyph_to_16(self) -> None:
        self.assertEqual(glyph.stand_box(0, 0), (10, 12, 14, 16))
        self.assertEqual(glyph.stand_box(8, 6), (18, 18, 22, 22))


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheWords(unittest.TestCase):
    def test_row_text_run_and_never_run(self) -> None:
        self.assertEqual(app.row_text(row(AssetStatus.YELLOW, True)),
                         (INV2, "Inverter 2", "inverter", "yellow", "reachable", "2026-06-01 12:00 UTC", "reachable"))
        self.assertEqual(app.row_text(row(AssetStatus.GREEN, False)),
                         (INV2, "Inverter 2", "inverter", "green", "—", "never run", "—"))

    def test_the_tooltip_run_and_never_run(self) -> None:
        self.assertEqual(app.tooltip_text(row(AssetStatus.YELLOW, True)),
                         "Last status: yellow at 2026-06-01 12:00 UTC")
        self.assertEqual(app.tooltip_text(row(AssetStatus.RED, False)), "Last status: red, never run")

    def test_the_summary_counts_each_colour(self) -> None:
        self.assertEqual(app.summary(()), "0 assets: 0 green, 0 yellow, 0 red")
        rows = (row(AssetStatus.GREEN, False), row(AssetStatus.YELLOW, True), row(AssetStatus.RED, True),
                row(AssetStatus.RED, False))
        self.assertEqual(app.summary(rows), "4 assets: 1 green, 1 yellow, 2 red")

    def test_row_at_maps_a_canvas_y_to_its_row(self) -> None:
        self.assertEqual([app.row_at(y, 3) for y in (0, 27.9, 28, 55, 56, 83.9)], [0, 0, 1, 1, 2, 2])
        self.assertIsNone(app.row_at(84, 3))
        self.assertIsNone(app.row_at(-0.5, 3))
        self.assertIsNone(app.row_at(0, 0))

    def test_the_store_the_window_reads_headless(self) -> None:
        conn = three_colour_store()
        self.addCleanup(conn.close)
        rows = project.asset_rows(conn)
        self.assertEqual(tuple(r.asset_id for r in rows), IDS)
        self.assertEqual(app.summary(rows), "7 assets: 5 green, 1 yellow, 1 red")
        self.assertEqual([glyph.colour_of(r.status) for r in rows[:3]], [GREEN, YELLOW, RED])
        self.assertEqual(app.tooltip_text(rows[1]), "Last status: yellow at 2026-06-01 12:00 UTC")
        self.assertEqual(app.tooltip_text(rows[3]), "Last status: green, no feed")  # no endpoint (9.1)
        self.assertEqual(app.row_text(rows[1])[6], "reachable")


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheEntryHeadless(unittest.TestCase):
    def test_the_arguments(self) -> None:
        self.assertEqual(vars(entry.parse([])), {"db": "solarpunk.db", "demo": False, "shortcut": False})
        self.assertEqual(vars(entry.parse(["--db", "f.db", "--demo"])), {"db": "f.db", "demo": True, "shortcut": False})
        shown = io.StringIO()
        with redirect_stdout(shown), self.assertRaises(SystemExit):
            entry.parse(["--help"])
        self.assertTrue(shown.getvalue().startswith("usage: solarpunk.ui [-h] [--db DB] [--demo] [--shortcut]"))


@unittest.skipUnless(display_available(), "no display")
class TheFleetWindow(unittest.TestCase):
    def setUp(self) -> None:
        """A root holding a FleetWindow over the three-colour store, drawn: self.window.rows has 7 rows."""
        self.conn = three_colour_store()
        self.addCleanup(self.conn.close)
        self.root = tkinter.Tk()
        self.addCleanup(self.root.destroy)
        self.window = app.FleetWindow(self.root, self.conn)
        self.root.update()

    def fill_of(self, asset_id: str) -> str:
        """The fill of an asset's glyph face, the one item tagged glyph:<id>: fill_of(INV3) is "#c0392b"."""
        items = self.window.canvas.find_withtag(f"glyph:{asset_id}")
        self.assertEqual(len(items), 1)
        return self.window.canvas.itemcget(items[0], "fill")

    def click(self, y: int) -> None:
        """A left click on the canvas at x 100 and a canvas y, then the events handled: click(30) is on row 1."""
        self.window.canvas.event_generate("<Button-1>", x=100, y=y)
        self.root.update()

    def test_one_glyph_per_asset_in_its_colour(self) -> None:
        self.assertEqual([self.fill_of(asset_id) for asset_id in IDS], [GREEN, YELLOW, RED] + [GREEN] * 4)
        self.assertEqual(len(self.window.canvas.find_withtag(f"glyph:{INV1}:part")), 4)

    def test_the_text_items_hold_the_ids_and_words(self) -> None:
        canvas = self.window.canvas
        for index, asset_id in enumerate(IDS):
            words = tuple(canvas.itemcget(item, "text") for item in canvas.find_withtag(f"row:{asset_id}"))
            self.assertEqual(words, app.row_text(self.window.rows[index]))
            self.assertEqual(words[0], asset_id)

    def test_the_rows_scroll_and_the_status_line(self) -> None:
        width = self.window.canvas.cget("width")  # as wide as its columns since 9.1, never under 820
        self.assertGreaterEqual(int(width), 820)
        self.assertEqual(self.window.canvas.cget("scrollregion"), f"0 0 {width} 196")
        self.assertEqual(self.window.status_line.cget("text"), "7 assets: 5 green, 1 yellow, 1 red")
        self.assertEqual(self.window.refresh_button.cget("text"), "Refresh")

    def test_a_click_on_a_row_opens_that_asset_and_below_the_rows_nothing(self) -> None:
        x0, y0, x1, y1 = self.window.canvas.bbox(f"row:{INV2}")
        self.click((y0 + y1) // 2)
        self.click(7 * 28 + 5)
        self.assertEqual(self.window.opened, [INV2])

    def test_the_hook_given_is_called(self) -> None:
        seen: list[str] = []
        window = app.FleetWindow(tkinter.Toplevel(self.root), self.conn, seen.append)
        self.root.update()
        window.canvas.event_generate("<Button-1>", x=100, y=3 * 28 + 2)
        self.root.update()
        self.assertEqual((seen, window.opened), (["OAHE-SIT-001"], []))

    def test_refresh_rereads_the_store(self) -> None:
        project.assign_fault(self.conn, INV1, "INV-001", at(2026, 6, 1, 13), ENGINEER)
        self.assertEqual(self.fill_of(INV1), GREEN)
        self.window.refresh_button.invoke()
        self.assertEqual(self.fill_of(INV1), RED)
        self.assertEqual(self.window.status_line.cget("text"), "7 assets: 4 green, 1 yellow, 2 red")

    def test_the_tooltip_shows_the_last_status_and_hides_on_leave(self) -> None:
        tip = self.window.tooltip
        self.assertEqual(tip.winfo_toplevel().state(), "withdrawn")
        self.window.canvas.event_generate("<Motion>", x=100, y=28 + 5)
        self.root.update()
        self.assertEqual(tip.cget("text"), "Last status: yellow at 2026-06-01 12:00 UTC")
        self.assertEqual(tip.winfo_toplevel().state(), "normal")
        self.window.canvas.event_generate("<Motion>", x=100, y=7 * 28 + 5)
        self.root.update()
        self.assertEqual(tip.winfo_toplevel().state(), "withdrawn")
        self.window.canvas.event_generate("<Motion>", x=100, y=3 * 28 + 5)
        self.root.update()
        self.assertEqual(tip.cget("text"), "Last status: green, no feed")  # no endpoint (9.1)
        self.assertEqual(tip.winfo_toplevel().state(), "normal")
        self.window.canvas.event_generate("<Leave>")
        self.root.update()
        self.assertEqual(tip.winfo_toplevel().state(), "withdrawn")


@unittest.skipUnless(display_available(), "no display")
class TheEntry(unittest.TestCase):
    def test_main_opens_the_fleet_window_on_the_file_store(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = str(Path(folder.name) / "fleet.db")
        conn = project.open_or_create(path)
        fill_store(conn)
        conn.close()
        seen: list[tuple[str, int]] = []

        def look(root: "tkinter.Tk") -> None:
            """Records the window's title and its glyph count, then closes it: look(root) leaves one entry in seen."""
            root.update()
            canvas = next(w for w in root.winfo_children()[0].winfo_children() if isinstance(w, tkinter.Canvas))
            seen.append((root.title(), len(canvas.find_withtag("glyph:" + INV3))))
            root.destroy()

        self.assertEqual(entry.main(["--db", path], io.StringIO(), look), 0)
        self.assertEqual(seen, [("Solarpunk fleet", 1)])
