"""The Tests window (13.7, SP-016, SP-050): its words headless (record_text.py), then, under a display over the demo
store, the Tests button in the fleet window opening it, the overview holding every test, the selected test's log with
its failures red, and a test never run. Skips "no tkinter" or "no display" as test_ui_runs.py does."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind
from solarpunk.ui import demo, record_text

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import __main__ as entry
    from solarpunk.ui import record_window

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


class TheWords(unittest.TestCase):
    def test_a_duration(self) -> None:
        self.assertEqual([record_text.duration_words(ms) for ms in (None, 0, 12, 999, 1000, 1250, 12000)],
                         ["—", "0 ms", "12 ms", "999 ms", "1.0 s", "1.2 s", "12.0 s"])

    def test_a_test_row_and_one_never_run(self) -> None:
        record = project.TestRecord("reachable", (AssetKind.INVERTER, AssetKind.SENSOR),
                                    ("A-1", "A-2", "A-3"), at(2026, 6, 1, 11), 12, 40, 3, 1)
        self.assertEqual(record_text.overview_row(record),
                         ("reachable", "inverter, sensor", "3", "2026-06-01 11:00 UTC", "12 ms", "40", "3", "1"))
        never = project.TestRecord("idle", (), (), None, None, 0, 0, 0)
        self.assertEqual(record_text.overview_row(never), ("idle", "", "0", "never", "—", "0", "0", "0"))

    def test_a_logged_run(self) -> None:
        run = project.LoggedRun("reachable", "OAHE-INV-002", at(2026, 6, 1, 13), "fail", UNREACHABLE, "all", 3, 17)
        self.assertEqual(record_text.log_row(run),
                         ("OAHE-INV-002", "2026-06-01 13:00 UTC", "FAIL", UNREACHABLE, "3 ms"))
        for verdict, word in (("pass", "pass"), ("no data", "no data")):
            self.assertEqual(record_text.verdict_word(verdict), word)

    def test_the_lines(self) -> None:
        self.assertEqual(record_text.log_heading("reachable"), "Last 100 runs of reachable")
        self.assertEqual(record_text.log_heading(None), "")
        self.assertEqual(record_text.empty_log("idle"), "idle has not run yet")
        self.assertEqual(record_text.empty_log(None), "")


@unittest.skipUnless(display_available(), "no display")
class TheWindow(unittest.TestCase):
    def setUp(self) -> None:
        """The demo store with its simulator, in a hidden root."""
        server, port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.folder = folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port)
        self.conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        self.addCleanup(self.conn.close)
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def select(self, window: "record_window.RecordWindow", name: str) -> None:
        """Selects a test by name, as a click would."""
        window.overview.selection_set(str([r.name for r in window.records].index(name)))
        self.root.update()

    def test_the_fleet_window_has_a_tests_button_that_opens_it(self) -> None:
        fleet = entry.open_fleet(self.root, self.conn)
        self.assertEqual(fleet.record_button.cget("text"), "Tests")
        before = len(self.root.winfo_children())
        fleet.record_button.invoke()
        self.assertEqual(len(self.root.winfo_children()), before + 1)
        self.assertEqual(self.root.winfo_children()[-1].title(), record_text.TITLE)

    def test_the_overview_lists_every_test(self) -> None:
        window = record_window.RecordWindow(self.root, self.conn)
        found = project.tests_overview(self.conn)
        rows = [window.overview.item(i, "values") for i in window.overview.get_children()]
        self.assertEqual(rows, [tuple(record_text.overview_row(r)) for r in found])
        self.assertEqual([row[0] for row in rows], [r.name for r in found])
        reachable = next(row for row in rows if row[0] == "reachable")
        self.assertEqual(reachable[3], "2026-06-01 13:00 UTC")
        self.assertEqual(reachable[6], "3")  # SEN-001 twice, INV-002 once (a dead feed adds the ping's own result)

    def test_the_selected_tests_log_with_failures_red(self) -> None:
        window = record_window.RecordWindow(self.root, self.conn)
        self.select(window, "reachable")
        rows = [(window.log.item(i, "values"), window.log.item(i, "tags")) for i in window.log.get_children()]
        expected = project.test_log(self.conn, "reachable", 100)
        self.assertEqual([values for values, _ in rows], [record_text.log_row(r) for r in expected])
        failed = [values for values, tags in rows if tags == (record_window.FAILED_TAG,)]
        self.assertEqual({values[0] for values in failed}, {demo.DOWN, demo.SENSOR})
        self.assertTrue(all(values[2] == "FAIL" for values in failed))
        self.assertEqual(window.heading.cget("text"), "Last 100 runs of reachable")

    def test_a_test_never_run_says_so(self) -> None:
        empty = project.open_or_create(Path(self.folder.name) / "empty.db")  # a store never run: every test unrun
        self.addCleanup(empty.close)
        window = record_window.RecordWindow(self.root, empty)
        never = window.records[0].name
        self.assertEqual(window.overview.item("0", "values")[3:], ("never", "\u2014", "0", "0", "0"))
        self.select(window, never)
        self.assertEqual(window.log.get_children(), ())
        self.assertEqual(window.empty_label.cget("text"), f"{never} has not run yet")


if __name__ == "__main__":
    unittest.main()
