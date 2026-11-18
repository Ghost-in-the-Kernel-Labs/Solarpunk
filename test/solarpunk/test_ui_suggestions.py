"""The asset window's suggested faults (7.5, SP-015): the rows headless, then the window under a display over the demo
store, where the dead weather station waits with SEN-001: Accept and Dismiss need a suggestion chosen and an engineer
chosen, Dismiss a reason; accepting opens the fault as that engineer and moves it to Open faults, dismissing empties the
list and the asset falls back from the suggestion's yellow. Skips "no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.ui import demo

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import asset_window

SITE_EMAIL = "site@oahe.example"
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
    def test_the_weather_stations_suggestion_reads_with_its_meaning_source_and_why(self) -> None:
        (line,) = asset_window.suggestion_lines(project.asset_detail(self.conn, demo.SENSOR))
        self.assertEqual((line[0], line[2], line[3], line[4]), ("SEN-001", "reachable", UNREACHABLE, "2026-06-01 13:00 UTC"))
        self.assertTrue(line[1].startswith("Irradiance sensor out of range"))
        self.assertEqual(asset_window.suggestion_lines(project.asset_detail(self.conn, demo.FED)), ())


@unittest.skipUnless(display_available(), "no display")
class TheWindow(DemoStore):
    def setUp(self) -> None:
        """The weather station's window over the demo store, in a hidden root, with on_change counted."""
        super().setUp()
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.changes: list[int] = []
        self.window = asset_window.AssetWindow(self.root, self.conn, demo.SENSOR, lambda: self.changes.append(1))
        self.root.update()

    def message(self) -> str:
        """The window's message line."""
        return str(self.window.message.cget("text"))

    def test_the_list_holds_the_suggestion_by_its_id(self) -> None:
        (item,) = self.window.suggestion_tree.get_children()
        self.assertEqual(int(item), project.open_suggestions(self.conn, demo.SENSOR)[0].suggestion_id)
        self.assertEqual(self.window.suggestion_tree.item(item, "values")[0], "SEN-001")

    def test_accept_needs_a_suggestion_then_an_engineer_then_opens_the_fault(self) -> None:
        self.window.accept_button.invoke()
        self.assertEqual(self.message(), asset_window.CHOOSE_SUGGESTION)
        self.window.suggestion_tree.selection_set(self.window.suggestion_tree.get_children()[0])
        self.window.accept_button.invoke()
        self.assertEqual(self.message(), asset_window.CHOOSE_ENGINEER)
        self.window.assigned_by_box.set(SITE_EMAIL)
        self.window.accept_button.invoke()
        self.assertEqual((self.message(), self.changes), ("", [1]))
        (fault, _), = project.asset_detail(self.conn, demo.SENSOR).open_faults
        self.assertEqual((fault.code, fault.assigned_by), ("SEN-001", SITE_EMAIL))
        self.assertEqual(self.window.suggestion_tree.get_children(), ())
        self.assertEqual([self.window.fault_tree.item(i, "values")[0] for i in self.window.fault_tree.get_children()],
                         ["SEN-001"])

    def test_dismiss_needs_a_reason_and_records_it(self) -> None:
        self.window.suggestion_tree.selection_set(self.window.suggestion_tree.get_children()[0])
        self.window.assigned_by_box.set(SITE_EMAIL)
        self.window.dismiss_button.invoke()
        self.assertEqual(self.message(), asset_window.GIVE_REASON)
        self.window.reason_box.insert(0, "station rebooted, feed back")
        self.window.dismiss_button.invoke()
        self.assertEqual((self.message(), self.changes, project.open_suggestions(self.conn, demo.SENSOR)), ("", [1], ()))
        self.assertEqual(project.faults_listing(self.conn, True)[0].asset_id, demo.DOWN)  # no fault on the station

    def test_the_section_is_titled_and_its_columns_named(self) -> None:
        titles = [c.cget("text") for c in self.window.winfo_children() if c.winfo_class() == "TLabel"]
        self.assertIn(asset_window.SUGGESTED_TITLE, titles)
        self.assertEqual([self.window.suggestion_tree.heading(c, "text") for c in asset_window.SUGGESTION_COLUMNS],
                         ["Code", "Meaning", "From", "Why", "Raised"])


if __name__ == "__main__":
    unittest.main()
