"""The fleet window's attention band (9.3, SP-023): what waits on a person, counted above the list. Headless, each count
is the length of its project listing and the demo gives 1, 1, 1; a count of zero is shown. Under a display, clicking a
count filters the list to its assets and clicking it again clears the filter. Skips "no display" as test_ui.py does."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.codes import Severity
from solarpunk.ui import cells, demo

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import app


def display_available() -> bool:
    """Whether a Tk window can open here: False with no tkinter or no DISPLAY."""
    if not HAS_TKINTER:
        return False
    try:
        tkinter.Tk().destroy()
    except tkinter.TclError:
        return False
    return True


class Click:
    """A stand-in for a click event, holding only the x and y the window reads."""

    def __init__(self, x: int, y: int) -> None:
        """Click(100, 10) is a click on the first row."""
        self.x = x
        self.y = y


class DemoStore(unittest.TestCase):
    def setUp(self) -> None:
        """The demo store built in a temporary folder with its simulator running, then opened."""
        server, port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port)
        self.conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        self.addCleanup(self.conn.close)


class TheCounts(DemoStore):
    def test_each_count_is_its_listings_length_and_the_demo_gives_an_outage_and_an_order(self) -> None:
        found = project.attention(self.conn)
        outages = [f for f in project.faults_listing(self.conn, True) if f.catalogue_row().severity is Severity.OUTAGE]
        self.assertEqual(len(found.outages), len(outages))
        self.assertEqual(len(found.orders), len(project.open_tickets(self.conn)))
        self.assertEqual(cells.band_counts(found), (("outages", "Open outages: 1"),
                                                    ("orders", "Open work orders: 1")))

    def test_each_count_names_its_assets(self) -> None:
        found = project.attention(self.conn)
        self.assertEqual(cells.band_assets(found, "outages"), {demo.DOWN})
        self.assertEqual(cells.band_assets(found, "orders"), {demo.DOWN})

    def test_a_derate_is_not_counted_as_an_outage(self) -> None:
        project.assign_fault(self.conn, demo.FED, "INV-002", demo.at(2026, 6, 1, 14), demo.ENGINEER)  # 13.15: the store holds accounts
        found = project.attention(self.conn)
        self.assertEqual(len(found.outages), 1)
        self.assertEqual(len(found.orders), 2)  # the derate's ticket is open work all the same

    def test_the_attention_changes_no_status(self) -> None:
        before = project.asset_rows(self.conn)
        project.attention(self.conn)
        self.assertEqual(project.asset_rows(self.conn), before)


class TheWords(unittest.TestCase):
    def test_zero_is_shown_and_the_filter_keeps_the_order(self) -> None:
        conn = project.open_store()
        self.addCleanup(conn.close)
        project.load_fleet(conn, project.demo_fleet())
        found = project.attention(conn)
        self.assertEqual([text for _, text in cells.band_counts(found)],
                         ["Open outages: 0", "Open work orders: 0"])
        rows = project.asset_rows(conn)
        self.assertEqual(cells.filtered(rows, None), rows)
        kept = cells.filtered(rows, frozenset({"OAHE-TRK-001", "OAHE-INV-001"}))
        self.assertEqual([r.asset_id for r in kept], ["OAHE-INV-001", "OAHE-TRK-001"])
        self.assertEqual((cells.showing(None), cells.showing("orders")), ("", "; showing open work orders alone"))


@unittest.skipUnless(display_available(), "no display")
class TheBand(DemoStore):
    def setUp(self) -> None:
        """The demo store's fleet window in a hidden root."""
        super().setUp()
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.window = app.FleetWindow(self.root, self.conn)
        self.root.update()

    def shown(self) -> list[str]:
        """The ids of the rows the list holds now."""
        return [row.asset_id for row in self.window.rows]

    def test_the_band_stands_above_the_list_with_its_three_counts(self) -> None:
        texts = [self.window.band_buttons[key].cget("text") for key, _ in cells.BAND]
        self.assertEqual(texts, ["Open outages: 1", "Open work orders: 1"])
        self.assertLess(self.window.band.grid_info()["row"], self.window.canvas.grid_info()["row"])

    def test_a_click_filters_and_a_second_clears(self) -> None:
        self.window.band_buttons["outages"].invoke()
        self.assertEqual(self.shown(), [demo.DOWN])
        self.assertIn("pressed", self.window.band_buttons["outages"].state())
        self.assertTrue(str(self.window.status_line.cget("text")).endswith("; showing open outages alone"))
        self.window.band_buttons["outages"].invoke()
        self.assertEqual(len(self.shown()), 11)
        self.assertNotIn("pressed", self.window.band_buttons["outages"].state())

    def test_another_count_replaces_the_filter_and_a_click_opens_the_kept_row(self) -> None:
        self.window.band_buttons["outages"].invoke()
        self.assertEqual(self.shown(), [demo.DOWN])
        self.window.band_buttons["orders"].invoke()
        self.assertEqual(self.shown(), [demo.DOWN])
        self.window.on_click(Click(100, 10))
        self.assertEqual(self.window.opened, [demo.DOWN])


if __name__ == "__main__":
    unittest.main()
