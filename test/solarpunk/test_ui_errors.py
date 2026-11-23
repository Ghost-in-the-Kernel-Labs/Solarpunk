"""The Runs window's Errors tab (10.6, SOL-15, SP-024): the bars' geometry headless (bars.py: one row per code, faults
and suggestions apart, each as long as its share of the largest count, a count of 0 no bar, the words beside), the
tab's words (runs_text: the days, the empty line), then the tab under a display over the demo store, its counts SOL-15's.
Skips "no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.ui import bars, demo, runs_text

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import runs_window


class TheBars(unittest.TestCase):
    def test_each_bar_is_its_share_of_the_largest_count(self) -> None:
        rows = bars.bar_rows((("INV-001", 2, 0), ("INV-002", 1, 4)))
        room = bars.WIDTH - bars.LABEL_WIDTH - bars.TEXT_ROOM
        self.assertEqual([r.label for r in rows], ["INV-001", "INV-002"])
        self.assertEqual(rows[0].fault[2] - rows[0].fault[0], room / 2)
        self.assertEqual(rows[0].suggestion[2], rows[0].suggestion[0])  # a count of 0 has no length
        self.assertEqual(rows[1].suggestion[2] - rows[1].suggestion[0], room)
        self.assertLess(rows[0].fault[3], rows[0].suggestion[1])  # the fault bar above the suggestion bar
        self.assertEqual(rows[1].centre_y - rows[0].centre_y, bars.ROW_HEIGHT)

    def test_the_words_the_left_edge_and_the_height(self) -> None:
        self.assertEqual([bars.counted(n, "fault") for n in (0, 1, 2)], ["0 faults", "1 fault", "2 faults"])
        (row,) = bars.bar_rows((("SEN-001", 0, 1),))
        self.assertEqual((row.fault_text, row.suggestion_text), ("0 faults", "1 suggestion"))
        self.assertEqual(row.suggestion, (120, 54.0, 610.0, 66.0))
        self.assertEqual((bars.left_of([80]), bars.left_of([150]), bars.height_of(1)), (120, 166, 82))
        self.assertEqual(bars.bar_rows(()), ())

    def test_the_tabs_words(self) -> None:
        self.assertEqual(runs_text.days_of("2026-06-01", " 2026-06-02 "), (date(2026, 6, 1), date(2026, 6, 2)))
        for first, last in (("June", "2026-06-01"), ("2026-06-02", "2026-06-01")):
            self.assertIsNone(runs_text.days_of(first, last))
        self.assertEqual(runs_text.no_errors(date(2026, 6, 1), date(2026, 6, 2)),
                         "no faults or suggestions from 2026-06-01 to 2026-06-02")
        self.assertEqual(runs_text.code_counts((project.CodeCount("SEN-001", 0, 1),)), (("SEN-001", 0, 1),))


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheTab(unittest.TestCase):
    def setUp(self) -> None:
        """The demo store with its simulator, in a hidden root, or the test skipped with no display."""
        try:
            self.root = tkinter.Tk()
        except tkinter.TclError:
            self.skipTest("no display")
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        server, port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port)
        self.conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        self.addCleanup(self.conn.close)

    def texts(self, window: "runs_window.RunsWindow") -> list[str]:
        """The words drawn for the rows, in drawing order."""
        canvas = window.errors_canvas
        return [canvas.itemcget(i, "text") for i in canvas.find_withtag("bar") if canvas.type(i) == "text"]

    def window(self, asset_id: str) -> "runs_window.RunsWindow":
        """One asset's Runs window, drawn."""
        found = runs_window.RunsWindow(self.root, self.conn, asset_id)
        self.root.update()
        return found

    def test_the_sensors_one_fault_raised_by_its_test_and_the_inverters_one_fault(self) -> None:
        sensor = self.window(demo.SENSOR)
        self.assertIn("Errors", [sensor.tabs.tab(t, "text") for t in sensor.tabs.tabs()])
        self.assertEqual(self.texts(sensor), ["SEN-001", "1 fault", "0 suggestions"])  # SP-046: a fault, not a suggestion
        bar_items = [i for i in sensor.errors_canvas.find_withtag("bar:SEN-001")
                     if sensor.errors_canvas.type(i) == "rectangle"]
        self.assertEqual([sensor.errors_canvas.itemcget(i, "fill") for i in bar_items], [bars.FAULT_COLOUR])
        self.assertEqual(self.texts(self.window(demo.FED)), ["INV-002", "1 fault", "0 suggestions"])

    def test_two_days_count_a_second_code_and_a_bad_or_empty_choice_says_so(self) -> None:
        project.assign_fault(self.conn, demo.DOWN, "INV-002", at(2026, 6, 2, 9), demo.ENGINEER)  # 13.15: the store holds accounts
        window = self.window(demo.DOWN)
        lost_link = ["INV-005", "1 fault", "0 suggestions", "SIT-004", "1 fault", "0 suggestions"]  # SP-047, SP-054: the zero output's floor and the failing reachable, beside the outage
        self.assertEqual(self.texts(window), ["INV-001", "1 fault", "0 suggestions"] + lost_link)
        window.last_day.set("2026-06-02")
        window.errors_button.invoke()
        self.assertEqual(self.texts(window), ["INV-001", "1 fault", "0 suggestions", "INV-002", "1 fault", "0 suggestions"] + lost_link)
        window.first_day.set("2026-06-03")
        window.errors_button.invoke()
        self.assertEqual((window.errors_line.cget("text"), self.texts(window)), (runs_text.BAD_DAYS, []))
        tracker = self.window("OAHE-TRK-001")
        self.assertEqual(tracker.errors_line.cget("text"), "no faults or suggestions from 2026-06-01 to 2026-06-01")


if __name__ == "__main__":
    unittest.main()
