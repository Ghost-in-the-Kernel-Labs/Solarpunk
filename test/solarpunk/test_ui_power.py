"""The Runs window's Power tab (10.5, SOL-15, SP-024): the words headless (runs_text: the curve leaves a gap out, the
peak, the line of counts, the day box), over the demo store; then the tab under a display: the line, one drawn run of
the curve per stretch between gaps (chart.segments), a box that holds no day, a day with no samples, an asset with
none. Skips "no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path

from solarpunk import project
from solarpunk.ui import chart, demo, runs_text

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import reports, runs_window

DAY = project.day_period(date(2026, 6, 1))
LINE = "288 samples: records 279, gaps 9; peak 94.35 kW"


class DemoStore(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """The demo store, built once in a temporary folder with its simulator, then opened."""
        server, port = demo.start_simulator(demo.simulator_samples())
        cls.addClassCleanup(server.server_close)
        cls.addClassCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(folder.cleanup)
        demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port)
        cls.conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        cls.addClassCleanup(cls.conn.close)


class TheWords(DemoStore):
    def test_the_curve_leaves_the_gaps_out_and_the_line_counts_them(self) -> None:
        series = project.asset_power(self.conn, demo.FED, DAY)
        curve = runs_text.power_curve(series)
        self.assertEqual(len(curve), 279)
        gap_at = next(s.moment for s in series.samples if s.gap)
        self.assertNotIn(gap_at, [at for at, _ in curve])
        self.assertEqual((runs_text.peak_of(series), runs_text.power_line(series)), (94.35, LINE))

    def test_no_samples_and_the_day_box(self) -> None:
        empty = project.asset_power(self.conn, "OAHE-TRK-001", DAY)
        self.assertEqual((runs_text.power_line(empty), runs_text.peak_of(empty)), ("no power samples on 2026-06-01", None))
        self.assertEqual(runs_text.day_of(" 2026-06-01 "), date(2026, 6, 1))
        self.assertIsNone(runs_text.day_of("June"))


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheTab(DemoStore):
    def setUp(self) -> None:
        """A hidden root, or the test skipped with no display."""
        try:
            self.root = tkinter.Tk()
        except tkinter.TclError:
            self.skipTest("no display")
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def window(self, asset_id: str) -> "runs_window.RunsWindow":
        """One asset's Runs window, drawn."""
        found = runs_window.RunsWindow(self.root, self.conn, asset_id)
        self.root.update()
        return found

    def test_the_tab_opens_on_the_runs_day_with_its_line_and_one_drawn_run_per_stretch(self) -> None:
        window = self.window(demo.FED)
        self.assertIn("Power", [window.tabs.tab(t, "text") for t in window.tabs.tabs()])
        self.assertEqual((window.day_text.get(), window.power_line.cget("text")), ("2026-06-01", LINE))
        series = project.asset_power(self.conn, demo.FED, DAY)
        stretches = chart.segments(runs_text.power_curve(series), DAY, chart.axis_top(94.35))
        self.assertEqual(len(window.power_canvas.find_withtag(reports.CURVE_TAG)), len(stretches))
        self.assertGreater(len(stretches), 1)  # the gaps break the line

    def test_a_box_that_holds_no_day_and_a_day_with_no_samples(self) -> None:
        window = self.window(demo.FED)
        window.day_text.set("June")
        window.show_button.invoke()
        self.assertEqual((window.power_line.cget("text"), window.power_canvas.find_all()), (runs_text.BAD_DAY, ()))
        window.day_text.set("2026-06-02")
        window.show_button.invoke()
        self.assertEqual(window.power_line.cget("text"), "no power samples on 2026-06-02")
        self.assertEqual(window.power_canvas.find_all(), ())

    def test_an_asset_with_no_samples_says_so(self) -> None:
        self.assertEqual(self.window("OAHE-TRK-001").power_line.cget("text"), "no power samples on 2026-06-01")


if __name__ == "__main__":
    unittest.main()
