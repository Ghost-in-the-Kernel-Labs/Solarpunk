"""The Runs button and window (10.3, SP-024): the window's words headless (runs_text.py); then, under a display over the
demo store, the "Runs" link on every fleet row opening the window while a click elsewhere still opens the asset window,
the window's list newest first with a failed run red, the chosen run's results with their reasons, the search, and an
asset with no runs. Skips "no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.ui import demo, runs_text

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import __main__ as entry
    from solarpunk.ui import app, runs_window

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


class Click:
    """A stand-in for a click event, holding only the x and y the window reads."""

    def __init__(self, x: int, y: int) -> None:
        """Click(100, 10) is a click on the first row's id."""
        self.x = x
        self.y = y


class TheWords(unittest.TestCase):
    def test_a_run_and_a_result(self) -> None:
        ping = project.Recorded("reachable", demo.DOWN, at(2026, 6, 1, 13), False, UNREACHABLE)
        passed = project.Recorded("on_grid", demo.DOWN, at(2026, 6, 1, 13), True, "156 records")
        self.assertEqual(runs_text.run_line(project.Run(demo.DOWN, at(2026, 6, 1, 13), (ping, passed))),
                         ("2026-06-01 13:00 UTC", "2 results", "1 failed"))
        self.assertEqual(runs_text.run_line(project.Run(demo.DOWN, at(2026, 6, 1, 13), (passed,))),
                         ("2026-06-01 13:00 UTC", "1 result", "all passed"))
        self.assertEqual(runs_text.result_line(ping), ("reachable", "FAIL", UNREACHABLE))
        self.assertEqual(runs_text.result_line(passed), ("on_grid", "pass", "156 records"))

    def test_the_title_and_the_empty_list(self) -> None:
        self.assertEqual(runs_text.title(demo.DOWN, "Inverter 2"), "Runs — OAHE-INV-002 Inverter 2")
        self.assertEqual(runs_text.empty_text(True, ""), "no runs yet")
        self.assertEqual(runs_text.empty_text(False, " "), "no feed")
        self.assertEqual(runs_text.empty_text(True, " grid "), "no run matches “grid”")


@unittest.skipUnless(display_available(), "no display")
class TheWindows(unittest.TestCase):
    def setUp(self) -> None:
        """The demo store with its simulator, its fleet window wired as the program wires it, in a hidden root."""
        server, port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.dead = demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port).dead_port
        self.conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        self.addCleanup(self.conn.close)
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.fleet = app.FleetWindow(self.root, self.conn)
        self.root.update()

    def runs_of(self, asset_id: str) -> "runs_window.RunsWindow":
        """The Runs window of one asset, drawn."""
        window = runs_window.RunsWindow(self.root, self.conn, asset_id)
        self.root.update()
        return window

    def test_every_row_has_a_runs_link_and_it_opens_the_runs_not_the_asset(self) -> None:
        canvas = self.fleet.canvas
        for row in self.fleet.rows:
            (link,) = canvas.find_withtag(f"runs:{row.asset_id}")
            self.assertEqual(canvas.itemcget(link, "text"), "Runs")
        self.fleet.on_click(Click(self.fleet.runs_x + 4, 10))
        self.assertEqual((self.fleet.runs_opened, self.fleet.opened), ([demo.FED], []))
        self.fleet.on_click(Click(100, 38))
        self.assertEqual(self.fleet.opened, [demo.DOWN])
        last = self.fleet.xs[-1]
        self.assertLess(max(canvas.bbox(i)[2] for i in canvas.find_withtag(f"row:{demo.DOWN}")), self.fleet.runs_x)
        self.assertGreater(self.fleet.runs_x, last)

    def test_the_program_opens_a_runs_window_from_the_link(self) -> None:
        top = tkinter.Toplevel(self.root)
        fleet = entry.open_fleet(top, self.conn)
        fleet.on_click(Click(fleet.runs_x + 4, 38))
        self.root.update()
        opened = [w for w in top.winfo_children() if isinstance(w, runs_window.RunsWindow)]
        self.assertEqual([w.asset_id for w in opened], [demo.DOWN])

    def test_the_list_and_the_chosen_runs_results(self) -> None:
        window = self.runs_of(demo.DOWN)
        self.assertEqual(window.title(), "Runs — OAHE-INV-002 Inverter 2")
        (item,) = window.run_tree.get_children()
        self.assertEqual(window.run_tree.item(item, "values"), ("2026-06-01 13:00 UTC", "9 results", "1 failed"))
        self.assertEqual(window.run_tree.item(item, "tags"), (runs_window.FAILED_TAG,))
        results = window.result_tree.get_children()
        self.assertEqual(len(results), 9)
        self.assertEqual(window.result_tree.item(results[0], "values"), ("reachable", "FAIL", f"127.0.0.1:{self.dead} is unreachable"))
        self.assertEqual(window.result_tree.item(results[0], "tags"), (runs_window.FAILED_TAG,))
        self.assertEqual(window.result_tree.item(results[1], "tags"), ("nodata",))  # power_ripple: INV-002's feed is dead, so its reads hold no value
        self.assertEqual(window.result_tree.item(results[2], "tags"), "")

    def test_the_search_narrows_and_says_when_it_finds_none(self) -> None:
        window = self.runs_of(demo.DOWN)
        window.search_text.set("nothing like it")
        self.assertEqual((window.run_tree.get_children(), window.result_tree.get_children()), ((), ()))
        self.assertEqual(window.empty_label.cget("text"), "no run matches “nothing like it”")
        window.search_text.set("unreachable")
        self.assertEqual(len(window.run_tree.get_children()), 1)
        self.assertEqual(window.empty_label.cget("text"), "")

    def test_an_asset_with_no_runs_says_why(self) -> None:
        self.assertEqual(self.runs_of("OAHE-TRK-001").empty_label.cget("text"), "no feed")

    def test_newest_first_with_a_passing_run_in_black(self) -> None:
        project.scheduled_run(self.conn, at(2026, 6, 1, 13) + timedelta(hours=1))
        window = self.runs_of(demo.FED)
        lines = [window.run_tree.item(i, "values")[0] for i in window.run_tree.get_children()]
        self.assertEqual(lines, ["2026-06-01 14:00 UTC", "2026-06-01 13:00 UTC"])
        # The demo's 13:00 run took five reads and passed: black. The 14:00 run here hands no acquirer, so power_ripple
        # says no data (13.3) and it is grey.
        kids = window.run_tree.get_children()
        self.assertEqual((window.run_tree.item(kids[0], "tags"), window.run_tree.item(kids[1], "tags")), (("nodata",), ""))


if __name__ == "__main__":
    unittest.main()
