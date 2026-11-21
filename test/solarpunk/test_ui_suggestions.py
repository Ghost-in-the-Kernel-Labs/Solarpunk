"""The asset window's earlier suggestions (7.7, SP-046, superseding 7.5): a store made before 7.7 keeps its suggestions,
which the window lists read only; there is no Accept, no Dismiss and no reason box, and the demo's dead weather station
carries SEN-001, raised by its failing reachable and assigned by that test, under Open faults. Skips "no tkinter" or
"no display" as test_ui.py does."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.ui import demo
from test.solarpunk.old_store import old_suggestion

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import asset_text, asset_window

UNREACHABLE = "127.0.0.1:9 is unreachable"


def display_available() -> bool:
    """Whether a Tk window can open here: False with no tkinter or no DISPLAY."""
    if not HAS_TKINTER:
        return False
    try:
        tkinter.Tk().destroy()
    except tkinter.TclError:
        return False
    return True


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


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheRows(DemoStore):
    def test_an_old_stores_suggestion_reads_with_its_meaning_source_and_why(self) -> None:
        old_suggestion(self.conn, demo.FED, "INV-002", at(2026, 6, 1, 13), "reachable", UNREACHABLE)
        (line,) = asset_text.suggestion_lines(project.asset_detail(self.conn, demo.FED))
        self.assertEqual((line[0], line[2], line[3], line[4]), ("INV-002", "reachable", UNREACHABLE, "2026-06-01 13:00 UTC"))
        self.assertTrue(line[1].startswith("Inverter over-temperature"))
        self.assertEqual(asset_text.suggestion_lines(project.asset_detail(self.conn, demo.SENSOR)), ())

    def test_the_weather_stations_fault_is_the_tests_and_is_not_called_cover(self) -> None:
        detail = project.asset_detail(self.conn, demo.SENSOR)
        (row,) = asset_text.fault_lines(detail)
        self.assertEqual((row[0], row[3]), ("SEN-001", "test:reachable"))


@unittest.skipUnless(display_available(), "no display")
class TheWindow(DemoStore):
    def setUp(self) -> None:
        """The weather station's window over the demo store, in a hidden root, with on_change counted."""
        super().setUp()
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.window = asset_window.AssetWindow(self.root, self.conn, demo.SENSOR)
        self.root.update()

    def test_the_fault_the_test_raised_is_listed_and_nothing_waits_to_be_decided(self) -> None:
        self.assertEqual(self.window.suggestion_tree.get_children(), ())
        rows = [self.window.fault_tree.item(i, "values") for i in self.window.fault_tree.get_children()]
        self.assertEqual([(r[0], r[3]) for r in rows], [("SEN-001", "test:reachable")])

    def test_there_is_no_accept_dismiss_or_reason(self) -> None:
        for gone in ("accept_button", "dismiss_button", "reason_box", "accept", "dismiss"):
            self.assertFalse(hasattr(self.window, gone), gone)
        for gone in ("ACCEPT_TEXT", "DISMISS_TEXT", "GIVE_REASON", "CHOOSE_SUGGESTION"):
            self.assertFalse(hasattr(asset_text, gone), gone)

    def test_the_section_is_titled_and_its_columns_named(self) -> None:
        titles = [c.cget("text") for c in self.window.winfo_children() if c.winfo_class() == "TLabel"]
        self.assertIn(asset_text.SUGGESTED_TITLE, titles)
        self.assertEqual([self.window.suggestion_tree.heading(c, "text") for c in asset_text.SUGGESTION_COLUMNS],
                         ["Code", "Meaning", "From", "Why", "Raised"])


if __name__ == "__main__":
    unittest.main()
