"""The Manage tests window (9.8, SP-030): the survey of a folder headless (every script with its test, a broken one
with its reason and never raised: a missing field, a script that does not parse, one that raises or exits at import),
the window's words (tests_text.py), then, under a display, the button between Add asset and Reports and the window over
a temporary folder: the rows, a broken script in red, Reload finding a script dropped in, New test writing the scaffold
or saying why not, and Open folder handing the file manager its command. Skips "no tkinter" or "no display" as
test_ui.py does. The real tests' folder is read and never written."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.codes import AssetKind
from solarpunk.ui import tests_text

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import __main__ as entry
    from solarpunk.ui import tests_window

GOOD = '''from solarpunk.leaf.codes import AssetKind
from solarpunk.remote.reactions import Fault
from solarpunk.remote.results import Result

KINDS = (AssetKind.METER,)
CLAUSES = ("9001-9.1.1",)
REACTIONS = {AssetKind.METER: (Fault("MTR-001"),)}


def run(asset, samples):
    return Result(True, "fine")
'''
SCRIPTS = {
    "alpha": GOOD,
    "missing": "KINDS = ()\nREACTIONS = {}\n\n\ndef run(asset, samples):\n    return None\n",
    "unparsed": "KINDS = (\n",
    "raising": "raise RuntimeError('the vendor library is not installed')\n",
    "exiting": "import sys\nsys.exit(3)\n",
}


def folder_with(case: unittest.TestCase, scripts: dict[str, str]) -> Path:
    """A temporary folder holding the scripts (name to text) and an __init__.py, removed when the case ends:
    folder_with(self, {"alpha": GOOD}) holds __init__.py and alpha.py."""
    made = tempfile.TemporaryDirectory()
    case.addCleanup(made.cleanup)
    path = Path(made.name)
    (path / "__init__.py").write_text("", encoding="utf-8")
    for name, text in scripts.items():
        (path / f"{name}.py").write_text(text, encoding="utf-8")
    return path


class TheSurvey(unittest.TestCase):
    def test_the_real_folder_lists_every_test_and_none_broken(self) -> None:
        found = project.survey_remote_tests()
        self.assertEqual([s.name for s in found], [t.name for t in project.remote_tests()])
        self.assertEqual([s.problem for s in found], [None] * len(found))
        self.assertEqual(project.remote_tests_folder().name, "tests")

    def test_a_broken_script_is_listed_with_its_reason(self) -> None:
        found = {s.name: s for s in project.survey_remote_tests(folder_with(self, SCRIPTS))}
        self.assertEqual(sorted(found), ["alpha", "exiting", "missing", "raising", "unparsed"])
        self.assertEqual((found["alpha"].test.kinds, found["alpha"].problem), ((AssetKind.METER,), None))
        self.assertEqual(found["missing"].problem, "missing has no CLAUSES")
        self.assertTrue(found["unparsed"].problem.startswith("SyntaxError: "))
        self.assertEqual(found["raising"].problem, "RuntimeError: the vendor library is not installed")
        self.assertEqual(found["exiting"].problem, "SystemExit: 3")
        self.assertTrue(all(found[n].test is None for n in ("missing", "unparsed", "raising", "exiting")))

    def test_an_edit_shows_at_the_next_look(self) -> None:
        folder = folder_with(self, {"alpha": GOOD})
        self.assertIsNone(project.survey_remote_tests(folder)[0].problem)
        (folder / "alpha.py").write_text(GOOD.replace('CLAUSES = ("9001-9.1.1",)\n', ""), encoding="utf-8")
        self.assertEqual(project.survey_remote_tests(folder)[0].problem, "alpha has no CLAUSES")

    def test_new_test_writes_to_the_folder_given(self) -> None:
        folder = folder_with(self, {})
        path = project.add_remote_test("meter_counts", ("METER",), ("9001-9.1.1",), folder)
        self.assertEqual(path, folder / "meter_counts.py")
        (found,) = project.survey_remote_tests(folder)
        self.assertEqual((found.name, found.test.clauses), ("meter_counts", ("9001-9.1.1",)))


class TheWords(unittest.TestCase):
    def test_a_rows_words(self) -> None:
        records_stored = next(s for s in project.survey_remote_tests() if s.name == "records_stored")
        self.assertEqual(tests_text.row_of(records_stored),
                         ("records_stored", "INVERTER, METER, SENSOR, TRACKER", "55000-9.1",
                          "MTR-001, SEN-001", ""))
        broken = project.Surveyed("broken", None, "broken has no CLAUSES")
        self.assertEqual(tests_text.row_of(broken), ("broken", "", "", "", "broken has no CLAUSES"))

    def test_a_test_that_suggests_nothing_and_the_columns_widths(self) -> None:
        on_grid = next(s for s in project.survey_remote_tests() if s.name == "on_grid")
        self.assertEqual(tests_text.row_of(on_grid)[3], "none")
        rows = [("reachable", "", "", "", ""), ("x", "", "", "", "y" * 100)]
        self.assertEqual(tests_text.widths(rows, lambda text: 7 * len(text)),
                         (18 + 63, 18 + 35, 18 + 49, 18 + 56, tests_text.WIDEST))

    def test_the_line_above_the_list(self) -> None:
        folder = Path("tests")
        good = project.survey_remote_tests()[:2]
        self.assertEqual(tests_text.summary(good, folder), "2 tests in tests")
        self.assertEqual(tests_text.summary(good[:1], folder), "1 test in tests")
        broken = (project.Surveyed("broken", None, "broken has no CLAUSES"),)
        self.assertEqual(tests_text.summary(good + broken, folder), "3 scripts in tests, 1 cannot load")
        self.assertEqual(tests_text.summary((), folder), "no scripts in tests: New test writes one")

    def test_the_fields_and_the_file_manager(self) -> None:
        self.assertEqual(tests_text.kinds_of(" meter, inverter "), ("METER", "INVERTER"))
        self.assertEqual((tests_text.kinds_of("  "), tests_text.words_of("9001-9.1.1")), ((), ("9001-9.1.1",)))
        folder = Path("/srv/tests")
        self.assertEqual([tests_text.open_command(p, folder)[0] for p in ("win32", "darwin", "linux")],
                         ["explorer", "open", "xdg-open"])
        self.assertEqual(tests_text.open_command("linux", folder)[1], str(folder))
        self.assertEqual(tests_text.written(Path("/x/meter_counts.py")),
                         "wrote meter_counts.py: open the folder, fill in its run, then Reload")
        self.assertEqual(tests_text.cannot_open(folder, FileNotFoundError(2, "No such file or directory")),
                         f"cannot open {folder}: No such file or directory; the folder is {folder}")


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheWindow(unittest.TestCase):
    def setUp(self) -> None:
        """A hidden root, or the test skipped with no display, and a folder of a good and a broken script."""
        try:
            self.root = tkinter.Tk()
        except tkinter.TclError:
            self.skipTest("no display")
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.folder = folder_with(self, {"alpha": GOOD, "raising": SCRIPTS["raising"]})
        self.commands: list[list[str]] = []
        self.window = tests_window.ManageTestsWindow(self.root, self.folder, self.commands.append)
        self.root.update()

    def test_the_button_stands_between_add_asset_and_reports(self) -> None:
        conn = project.open_store()
        self.addCleanup(conn.close)
        fleet = entry.open_fleet(self.root, conn)
        buttons = [w.cget("text") for w in fleet.toolbar.pack_slaves()]
        self.assertEqual(buttons[buttons.index("Add asset") + 1:buttons.index("Reports")], ["Manage tests"])
        fleet.tests_button.invoke()
        windows = [w for w in self.root.winfo_children() if isinstance(w, tests_window.ManageTestsWindow)]
        self.assertEqual(windows[-1].folder, project.remote_tests_folder())

    def test_the_rows_and_a_broken_script_in_red(self) -> None:
        tree = self.window.tree
        self.assertEqual(list(tree.get_children()), ["alpha", "raising"])
        self.assertEqual(tree.item("alpha", "values")[1:4], ("METER", "9001-9.1.1", "MTR-001"))
        self.assertEqual(tree.item("raising", "tags"), (tests_text.BROKEN,))
        self.assertEqual(str(tree.tag_configure(tests_text.BROKEN, "foreground")), tests_window.BROKEN_COLOUR)
        self.assertEqual(self.window.line.cget("text"), f"2 scripts in {self.folder}, 1 cannot load")

    def test_reload_finds_a_script_dropped_in(self) -> None:
        (self.folder / "beta.py").write_text(GOOD, encoding="utf-8")
        self.window.reload_button.invoke()
        self.assertEqual(list(self.window.tree.get_children()), ["alpha", "beta", "raising"])

    def test_new_test_writes_the_scaffold_or_says_why_not(self) -> None:
        self.window.new_button.invoke()
        form = [w for w in self.window.winfo_children() if isinstance(w, tests_window.NewTestWindow)][-1]
        form.name.set("alpha")
        form.clause.set("9001-9.1.1")
        form.kinds.set("meter")
        form.create_button.invoke()
        self.assertEqual(form.line.cget("text"), "alpha already exists")
        form.name.set("meter_counts")
        form.create_button.invoke()
        self.assertTrue((self.folder / "meter_counts.py").exists())
        self.assertEqual(self.window.tree.selection(), ("meter_counts",))
        self.assertEqual(self.window.line.cget("text"), tests_text.written(self.folder / "meter_counts.py"))

    def test_open_folder_hands_the_file_manager_the_folder(self) -> None:
        self.window.open_button.invoke()
        (command,) = self.commands
        self.assertEqual(command[-1], str(self.folder))

    def test_a_file_manager_that_cannot_start_is_said(self) -> None:
        def missing(command: list[str]) -> None:
            """Raises as Popen does for a program not installed: missing(["xdg-open", d]) raises FileNotFoundError."""
            raise FileNotFoundError(2, "No such file or directory")
        window = tests_window.ManageTestsWindow(self.root, self.folder, missing)
        window.open_button.invoke()
        self.assertTrue(window.line.cget("text").startswith(f"cannot open {self.folder}: No such file"))


if __name__ == "__main__":
    unittest.main()
