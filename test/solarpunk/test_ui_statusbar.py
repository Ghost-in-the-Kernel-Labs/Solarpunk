"""The fleet window's status bar and toolbar (9.5, SP-023): the store's file name and the fleet's last run at the foot
("demo.db, last run 2026-06-01 13:00 UTC"; a store never run "fleet.db, never run"), Refresh in the toolbar beside Add
asset and Reports, and the window sized to its rows with a minimum size. Headless first, then under a display. Skips
"no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.ui import cells, demo

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import __main__ as entry
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


class DemoStore(unittest.TestCase):
    def setUp(self) -> None:
        """The demo store built in a temporary folder with its simulator running, then opened, and an empty fleet.db
        beside it holding the OAHE fleet and no run."""
        server, port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port)
        self.conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        self.addCleanup(self.conn.close)
        self.empty = project.open_or_create(Path(folder.name) / "fleet.db")
        self.addCleanup(self.empty.close)
        project.load_fleet(self.empty, project.demo_fleet())


class TheWords(DemoStore):
    def test_the_store_and_its_last_run(self) -> None:
        self.assertEqual((project.store_name(self.conn), project.fleet_last_run(self.conn)),
                         ("demo.db", at(2026, 6, 1, 13)))
        self.assertEqual(cells.store_line("demo.db", at(2026, 6, 1, 13)), "demo.db, last run 2026-06-01 13:00 UTC")
        self.assertEqual(cells.store_line(project.store_name(self.empty), project.fleet_last_run(self.empty)),
                         "fleet.db, never run")

    def test_a_store_in_memory_says_so(self) -> None:
        conn = project.open_store()
        self.addCleanup(conn.close)
        self.assertEqual(project.store_name(conn), "in memory")


@unittest.skipUnless(display_available(), "no display")
class TheWindow(DemoStore):
    def setUp(self) -> None:
        """The demo store's fleet window, wired as the program wires it, in a hidden root."""
        super().setUp()
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.window = entry.open_fleet(self.root, self.conn)
        self.root.update()

    def test_the_status_bar_stands_at_the_foot_with_the_store_and_the_summary(self) -> None:
        self.assertEqual(self.window.store_label.cget("text"), "demo.db, last run 2026-06-01 13:00 UTC")
        self.assertEqual(self.window.status_line.cget("text"), "11 assets: 9 green, 1 yellow, 1 red")
        rows = [w.grid_info()["row"] for w in self.window.frame.grid_slaves()]
        self.assertEqual(self.window.status_bar.grid_info()["row"], max(rows))

    def test_refresh_stands_in_the_toolbar_beside_add_asset_and_reports(self) -> None:
        buttons = [w.cget("text") for w in self.window.toolbar.winfo_children()]
        self.assertEqual(sorted(buttons), ["Add asset", "Errors", "Refresh", "Reports"])  # Errors since 10.7
        self.assertEqual(self.window.toolbar.grid_info()["row"], 0)

    def test_the_list_fits_the_fleet_and_the_window_has_a_minimum_size(self) -> None:
        self.assertEqual(int(self.window.canvas.cget("height")), 11 * app.ROW_HEIGHT)
        self.assertEqual(self.root.minsize(), (app.MIN_WIDTH, app.MIN_HEIGHT))

    def test_a_store_never_run_says_so(self) -> None:
        window = app.FleetWindow(tkinter.Toplevel(self.root), self.empty)
        self.assertEqual(window.store_label.cget("text"), "fleet.db, never run")
        self.assertEqual(int(window.canvas.cget("height")), 11 * app.ROW_HEIGHT)


if __name__ == "__main__":
    unittest.main()
