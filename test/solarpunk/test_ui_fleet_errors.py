"""The fleet's Errors window (10.7, SOL-15, SP-024): its words headless (runs_text: the code box's choices, the code a
choice names, the rows' counts, the empty line, the row a clicked item belongs to), then the window under a display
over the demo store: one code's rows worst first, faults and suggestions apart, a click on a row opening that asset's
Runs window, the program's Errors button. Skips "no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import CATALOGUE
from solarpunk.ui import demo, runs_text

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import __main__ as entry
    from solarpunk.ui import errors_window

DEMO_CODES = {"INV-001", "INV-002", "SIT-002", "SEN-001"}


class Click:
    """A stand-in for a click event, holding only the x and y the window reads."""

    def __init__(self, x: float, y: float) -> None:
        """Click(300, 47) is a click on the first row's fault bar."""
        self.x = x
        self.y = y


class TheWords(unittest.TestCase):
    def test_the_choices_and_the_code_they_name(self) -> None:
        choices = runs_text.code_choices()
        self.assertEqual(len(choices), len(CATALOGUE))
        self.assertTrue(choices[0].startswith(CATALOGUE[0].code + " "))
        self.assertEqual([runs_text.code_of(c) for c in choices], [row.code for row in CATALOGUE])

    def test_the_counts_the_empty_line_and_the_clicked_row(self) -> None:
        found = (project.AssetCount("OAHE-INV-002", 1, 0), project.AssetCount("OAHE-INV-001", 0, 2))
        self.assertEqual(runs_text.asset_counts(found), (("OAHE-INV-002", 1, 0), ("OAHE-INV-001", 0, 2)))
        self.assertEqual(runs_text.no_asset_errors("INV-005", date(2026, 6, 1), date(2026, 6, 1)),
                         "no asset raised INV-005 from 2026-06-01 to 2026-06-01")
        self.assertEqual(runs_text.row_of(("bar", "bar:OAHE-INV-002", "current")), "OAHE-INV-002")
        self.assertIsNone(runs_text.row_of(("legend",)))


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheWindow(unittest.TestCase):
    def setUp(self) -> None:
        """The demo store with its simulator and a pushed INV-001 on OAHE-INV-001, in a hidden root, or skipped with no
        display."""
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
        project.suggest_pushed(self.conn, demo.FED, "INV-001", at(2026, 6, 1, 14))
        self.opened: list[str] = []
        self.window = errors_window.ErrorsWindow(self.root, self.conn, self.opened.append)
        self.root.update()

    def texts(self) -> list[str]:
        """The words drawn for the rows, in drawing order."""
        canvas = self.window.canvas
        return [canvas.itemcget(i, "text") for i in canvas.find_withtag("bar") if canvas.type(i) == "text"]

    def test_it_opens_on_inv_001_worst_first_faults_and_suggestions_apart(self) -> None:
        self.assertEqual(runs_text.code_of(self.window.code_choice.get()), "INV-001")
        self.assertEqual(self.texts(), [demo.DOWN, "1 fault", "0 suggestions", demo.FED, "0 faults", "1 suggestion"])

    def test_a_click_on_a_row_opens_that_assets_runs(self) -> None:
        canvas = self.window.canvas
        bar = next(i for i in canvas.find_withtag(f"bar:{demo.FED}") if canvas.type(i) == "rectangle")
        x0, y0, x1, y1 = canvas.coords(bar)
        self.window.on_click(Click((x0 + x1) / 2, (y0 + y1) / 2))
        self.window.on_click(Click(2, 2))  # the corner: no row
        self.assertEqual(self.opened, [demo.FED])

    def test_a_code_nobody_raised_and_a_bad_choice_of_days(self) -> None:
        quiet = next(c for c in runs_text.code_choices() if runs_text.code_of(c) not in DEMO_CODES)
        self.window.code_choice.set(quiet)
        self.window.show_button.invoke()
        self.assertEqual(self.window.line.cget("text"),
                         f"no asset raised {runs_text.code_of(quiet)} from 2026-06-01 to 2026-06-01")
        self.assertEqual(self.texts(), [])
        self.window.first_day.set("2026-06-02")
        self.window.show_button.invoke()
        self.assertEqual(self.window.line.cget("text"), runs_text.BAD_DAYS)

    def test_the_programs_errors_button_opens_it(self) -> None:
        top = tkinter.Toplevel(self.root)
        fleet = entry.open_fleet(top, self.conn)
        self.assertEqual(fleet.errors_button.cget("text"), "Errors")
        fleet.errors_button.invoke()
        self.root.update()
        self.assertEqual(len([w for w in top.winfo_children() if isinstance(w, errors_window.ErrorsWindow)]), 1)


if __name__ == "__main__":
    unittest.main()
