"""The Runs window's "By test" timeline (10.4, SP-024): its geometry headless (timeline.py: the rows, the span, the x of
an instant, one mark per run per test, red when either of a test's two results in one run failed, the UTC ticks), then
the tab under a display over the demo store and a second run. Skips "no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.ui import demo, timeline

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import runs_window

ONE = at(2026, 6, 1, 13)


def result(name: str, passed: bool, when: object = ONE) -> "project.Recorded":
    """A result of OAHE-INV-002 at an instant."""
    return project.Recorded(name, demo.DOWN, when, passed, "x")


def run(when: object, results: tuple["project.Recorded", ...]) -> "project.Run":
    """A run of OAHE-INV-002 at an instant holding the results given."""
    return project.Run(demo.DOWN, when, results)


class TheGeometry(unittest.TestCase):
    def test_the_rows_and_the_span(self) -> None:
        runs = (run(ONE + timedelta(hours=2, minutes=30), (result("on_grid", True),)), run(ONE, (result("reachable", False),)))
        self.assertEqual(timeline.tests_of(runs), ("on_grid", "reachable"))
        self.assertEqual(timeline.span(runs), (ONE, at(2026, 6, 1, 16)))
        self.assertEqual(timeline.span(runs[1:]), (ONE, at(2026, 6, 1, 14)))

    def test_the_x_y_and_height(self) -> None:
        self.assertEqual(timeline.x_of(ONE + timedelta(minutes=30), ONE, ONE + timedelta(hours=1)), 463.0)
        self.assertEqual(timeline.x_of(ONE, ONE, ONE + timedelta(hours=1)), timeline.LABEL_WIDTH)
        self.assertEqual((timeline.y_of(0), timeline.y_of(1), timeline.height_of(7)), (23.0, 45.0, 200))
        self.assertEqual((timeline.left_of([120, 166]), timeline.left_of([200]), timeline.left_of([])), (190, 224, 190))
        self.assertEqual(timeline.x_of(ONE, ONE, ONE + timedelta(hours=1), left=224), 224)

    def test_one_mark_per_run_per_test_red_when_either_result_failed(self) -> None:
        demo_run = run(ONE, (result("reachable", False), result("on_grid", True), result("reachable", True)))
        marks = timeline.marks((demo_run,))
        self.assertEqual([(m.row, m.passed) for m in marks], [(0, True), (1, False)])
        self.assertEqual({m.centre_x for m in marks}, {timeline.LABEL_WIDTH})
        later = run(ONE + timedelta(minutes=30), (result("reachable", True),))
        self.assertEqual([(m.row, m.passed, m.centre_x) for m in timeline.marks((later, demo_run)) if m.row == 1],
                         [(1, True, 463.0), (1, False, timeline.LABEL_WIDTH)])
        self.assertEqual(timeline.marks(()), ())

    def test_the_ticks_and_their_words(self) -> None:
        self.assertEqual(timeline.ticks(ONE, ONE + timedelta(hours=1)), (ONE, ONE + timedelta(hours=1)))
        day = timeline.ticks(at(2026, 6, 1), at(2026, 6, 2))
        self.assertEqual((len(day), day[1]), (9, at(2026, 6, 1, 3)))
        self.assertEqual(timeline.tick_text(ONE, ONE, ONE + timedelta(hours=1)), "13:00")
        self.assertEqual(timeline.tick_text(ONE, ONE, ONE + timedelta(days=2)), "06-01 13:00")


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheTab(unittest.TestCase):
    def setUp(self) -> None:
        """The demo store with its simulator and a second run at 14:00, in a hidden root, or skipped with no display."""
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
        project.scheduled_run(self.conn, ONE + timedelta(hours=1))

    def test_the_tab_draws_a_mark_per_run_per_test_in_its_colour(self) -> None:
        window = runs_window.RunsWindow(self.root, self.conn, demo.DOWN)
        self.root.update()
        self.assertEqual([window.tabs.tab(t, "text") for t in window.tabs.tabs()][:2], ["Runs", "By test"])  # then 10.5's
        canvas = window.timeline
        items = canvas.find_withtag(runs_window.MARK_TAG)
        self.assertEqual(len(items), 2 * 8)  # two runs, eight tests each
        fills = [canvas.itemcget(i, "fill") for i in items]
        self.assertEqual(fills.count(timeline.FAIL_COLOUR), 4)  # reachable and (13.15, zero output) performance_above_floor failed in both runs
        texts = {canvas.itemcget(i, "text") for i in canvas.find_all() if canvas.type(i) == "text"}
        self.assertTrue({"reachable", "on_grid", "13:00", "15:00", "UTC"} <= texts)
        labels = [i for i in canvas.find_all() if canvas.type(i) == "text" and canvas.itemcget(i, "anchor") == "w"]
        first_mark = min(canvas.bbox(i)[0] for i in items)
        self.assertLess(max(canvas.bbox(i)[2] for i in labels), first_mark)  # no name runs into the marks

    def test_a_search_redraws_and_no_runs_draw_nothing(self) -> None:
        window = runs_window.RunsWindow(self.root, self.conn, demo.DOWN)
        window.search_text.set("nothing like it")
        self.assertEqual(window.timeline.find_all(), ())
        self.assertEqual(runs_window.RunsWindow(self.root, self.conn, "OAHE-TRK-001").timeline.find_all(), ())


if __name__ == "__main__":
    unittest.main()
