"""The fleet window's headings and readable cells (9.1, SP-023): the six headings, instants in the windows' words, "no
feed" for an asset with no endpoint beside "never run" for one the run has not reached yet, and each column as wide as
its widest text; headless with a made-up measure, then under a display with a 20-character name, where no drawn text
overruns the next column. Skips "no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import unittest
from dataclasses import replace

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind, AssetStatus

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import app

LONG_NAME = "Central inverter 2-B"  # 20 characters
INV1 = "OAHE-INV-001"


def seven(text: str) -> int:
    """A made-up measure: 7 px a character, so seven("Asset") is 35."""
    return 7 * len(text)


def display_available() -> bool:
    """Whether a Tk window can open here: False with no tkinter or no DISPLAY."""
    if not HAS_TKINTER:
        return False
    try:
        tkinter.Tk().destroy()
    except tkinter.TclError:
        return False
    return True


def made_up(has_feed: bool, run: bool) -> "project.AssetRow":
    """A tracker's row, run at 12:00 UTC or never, with or without an endpoint."""
    return project.AssetRow("OAHE-TRK-001", "Tracker 1", AssetKind.TRACKER, AssetStatus.GREEN,
                            at(2026, 6, 1, 12) if run else None, "—", has_feed)


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheWords(unittest.TestCase):
    def test_the_six_headings(self) -> None:
        self.assertEqual(app.HEADINGS, ("Asset", "Name", "Kind", "Status", "Last run", "Failing"))

    def test_an_instant_reads_in_words_and_no_feed_differs_from_never_run(self) -> None:
        self.assertEqual(app.row_text(made_up(True, True))[4], "2026-06-01 12:00 UTC")
        self.assertEqual(app.row_text(made_up(True, False))[4], "never run")
        self.assertEqual(app.row_text(made_up(False, False))[4], "no feed")
        self.assertEqual(app.tooltip_text(made_up(False, False)), "Last status: green, no feed")

    def test_each_column_is_as_wide_as_its_widest_text_and_a_gap(self) -> None:
        self.assertEqual(app.column_xs([], seven), (40, 91, 135, 179, 237, 309))
        lines = [("OAHE-INV-001", LONG_NAME, "inverter", "green", "2026-06-01 12:00 UTC", "—")]
        xs = app.column_xs(lines, seven)
        self.assertEqual(xs[1] - xs[0], 7 * 12 + 16)
        self.assertEqual(xs[2] - xs[1], 7 * len(LONG_NAME) + 16)
        for line in (app.HEADINGS, *lines):
            for index in range(len(xs) - 1):
                self.assertLess(xs[index] + seven(line[index]), xs[index + 1], line[index])

    def test_the_width_holds_the_last_column_and_is_never_under_820(self) -> None:
        self.assertEqual(app.width_for(app.column_xs([], seven), [], seven), 820)
        wide = [("x",) * 5 + ("y" * 200,)]
        xs = app.column_xs(wide, seven)
        self.assertEqual(app.width_for(xs, wide, seven), xs[-1] + 1400 + 12)


class TheRow(unittest.TestCase):
    def test_has_feed_follows_the_endpoint(self) -> None:
        conn = project.open_store()
        self.addCleanup(conn.close)
        fleet = project.demo_fleet()
        project.load_fleet(conn, fleet)
        rows = {row.asset_id: row for row in project.asset_rows(conn)}
        for asset in fleet:
            with self.subTest(asset=asset.asset_id):
                self.assertIs(rows[asset.asset_id].has_feed, asset.host is not None and asset.port is not None)
        self.assertIn(True, [row.has_feed for row in rows.values()])
        self.assertIn(False, [row.has_feed for row in rows.values()])


@unittest.skipUnless(display_available(), "no display")
class TheWindow(unittest.TestCase):
    def setUp(self) -> None:
        """The OAHE fleet with OAHE-INV-001 renamed to a 20-character name, in a fleet window in a hidden root."""
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        fleet = tuple(replace(a, name=LONG_NAME) if a.asset_id == INV1 else a for a in project.demo_fleet())
        project.load_fleet(self.conn, fleet)
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.window = app.FleetWindow(self.root, self.conn)
        self.root.update()

    def test_the_headings_stand_over_their_columns(self) -> None:
        header = self.window.header
        items = header.find_withtag(app.HEADING_TAG)
        self.assertEqual(tuple(header.itemcget(item, "text") for item in items), app.HEADINGS)
        self.assertEqual(tuple(int(header.coords(item)[0]) for item in items), self.window.xs)

    def test_no_drawn_text_runs_into_the_next_column(self) -> None:
        canvas = self.window.canvas
        for row in self.window.rows:
            items = canvas.find_withtag(f"row:{row.asset_id}")
            for index, item in enumerate(items[:-1]):
                with self.subTest(asset=row.asset_id, column=index):
                    self.assertLess(canvas.bbox(item)[2], self.window.xs[index + 1])
        self.assertIn(LONG_NAME, [canvas.itemcget(i, "text") for i in canvas.find_withtag(f"row:{INV1}")])


if __name__ == "__main__":
    unittest.main()
