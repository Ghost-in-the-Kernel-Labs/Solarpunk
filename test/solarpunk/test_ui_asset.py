"""The asset window (3.2): its pure functions headless, then the window itself under a display (xvfb-run), skipping
with "no display" without one. The store holds a site and an inverter with an open INV-001 and a last run whose
on_grid failed, built as test_project_run.py builds its results."""
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind, AssetStatus, codes_for
from solarpunk.remote import results
from solarpunk.ui import demo

try:
    import tkinter

    from solarpunk.ui import asset_window
except ModuleNotFoundError as missing:  # a Python built without Tk: the fast loop's python3 in some sessions
    if missing.name != "tkinter":
        raise
    tkinter = None  # type: ignore[assignment]
    asset_window = None  # type: ignore[assignment]

SITE_EMAIL = "site@oahe.example"
INVERTER_EMAIL = "inverter@oahe.example"
NEW_EMAIL = "new@oahe.example"
SITE_ID = "OAHE-SIT-001"
INV1 = "OAHE-INV-001"
INV2 = "OAHE-INV-002"
SITE = Asset(SITE_ID, AssetKind.SITE, "OAHE", None, "Oahe", None, location="Pierre, SD", engineer_email=SITE_EMAIL)
INVERTER = Asset(INV1, AssetKind.INVERTER, "OAHE", SITE_ID, "Inverter 1", 100.0, "127.0.0.1", 5020, "Pad A",
                 INVERTER_EMAIL)
OPENED = at(2026, 6, 1, 10, 10)
RUN_AT = at(2026, 6, 1, 12)
# An inverter nobody services, so its engineer box starts empty.
UNSERVICED = Asset(INV2, AssetKind.INVERTER, "OAHE", SITE_ID, "Inverter 2", 100.0)
OFF_GRID = "10:05: off the grid"
NEVER = "no result yet: the scheduled run has not tested this asset"
# The inverter's diagnostics (6.4): its last run failed on_grid and passed reachable; the other five never ran on it.
DIAGNOSTIC_ROWS = (
    ("on_grid", "FAIL", OFF_GRID),
    ("irradiance_in_range", "not run", NEVER),
    ("night_power_near_zero", "not run", NEVER),
    ("performance_above_floor", "not run", NEVER),
    ("power_not_frozen", "not run", NEVER),
    ("power_under_rated", "not run", NEVER),
    ("reachable", "pass", "3 records"),
)


def display_available() -> bool:
    """Whether a Tk window can open here: False without tkinter or without a display, True under xvfb-run."""
    if tkinter is None:
        return False
    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        return False
    root.destroy()
    return True


def fixture_store() -> sqlite3.Connection:
    """The site and inverter, an open INV-001 on the inverter and a run at 12:00 where on_grid failed: its detail's
    status is RED and its latest (on_grid failed, reachable passed)."""
    conn = project.open_store()
    project.register_asset(conn, SITE)
    project.register_asset(conn, INVERTER)
    project.register_asset(conn, UNSERVICED)
    project.assign_fault(conn, INV1, "INV-001", OPENED)
    results.record(conn, "reachable", INV1, RUN_AT - timedelta(hours=1), results.Result(False, "stale"))
    results.record(conn, "reachable", INV1, RUN_AT, results.Result(True, "3 records"))
    results.record(conn, "on_grid", INV1, RUN_AT, results.Result(False, OFF_GRID))
    return conn


@unittest.skipUnless(asset_window is not None, "no tkinter")
class PureTest(unittest.TestCase):
    """The strings and colours the window shows, from project data alone."""

    def setUp(self) -> None:
        """A fresh fixture store and the inverter's detail."""
        self.conn = fixture_store()
        self.detail = project.asset_detail(self.conn, INV1)

    def tearDown(self) -> None:
        """Closes the store."""
        self.conn.close()

    def test_field_lines(self) -> None:
        self.assertEqual(asset_window.field_lines(INVERTER), (
            "Kind: Inverter", "Site: OAHE", "Parent: OAHE-SIT-001", "Rated: 100.0 kW", "Location: Pad A",
            "Endpoint: 127.0.0.1:5020", "Engineer: inverter@oahe.example"))

    def test_field_lines_with_missing_values(self) -> None:
        bare = Asset("OAHE-SEN-001", AssetKind.SENSOR, "OAHE", None, "Sensor", None)
        self.assertEqual(asset_window.field_lines(bare), (
            "Kind: Sensor", "Site: OAHE", "Parent: none", "Rated: none", "Location: none", "Endpoint: none",
            "Engineer: none"))

    def test_shown(self) -> None:
        self.assertEqual(asset_window.shown(None), "none")
        self.assertEqual(asset_window.shown(5020), "5020")

    def test_title_and_status(self) -> None:
        self.assertEqual(asset_window.window_title(INVERTER), "OAHE-INV-001 — Inverter 1")
        self.assertEqual(asset_window.status_line(AssetStatus.RED), "Status: red")
        self.assertEqual(asset_window.status_line(AssetStatus.GREEN), "Status: green")

    def test_colour_of(self) -> None:
        self.assertEqual(asset_window.colour_of(AssetStatus.GREEN), "#2e8b57")
        self.assertEqual(asset_window.colour_of(AssetStatus.YELLOW), "#e0b000")
        self.assertEqual(asset_window.colour_of(AssetStatus.RED), "#c0392b")

    def test_fault_lines(self) -> None:
        meaning = "Inverter offline: no AC output while irradiance is above the start threshold"
        self.assertEqual(asset_window.fault_lines(self.detail), (("INV-001", meaning, "2026-06-01 10:10 UTC"),))

    def test_fault_lines_empty(self) -> None:
        self.assertEqual(asset_window.fault_lines(project.asset_detail(self.conn, SITE_ID)), ())

    def test_result_lines_failing_then_never_run_then_passing(self) -> None:
        self.assertEqual(asset_window.result_lines(self.detail), DIAGNOSTIC_ROWS)

    def test_row_tags(self) -> None:
        self.assertEqual(asset_window.row_tags(("on_grid", "FAIL", OFF_GRID)), ("failing",))
        self.assertEqual(asset_window.row_tags(("power_not_frozen", "not run", NEVER)), ("notrun",))
        self.assertEqual(asset_window.row_tags(("reachable", "pass", "3 records")), ())

    def test_code_labels(self) -> None:
        labels = asset_window.code_labels(codes_for(AssetKind.INVERTER))
        self.assertEqual(len(labels), 4)
        self.assertEqual(labels[3], "INV-004 — Firmware update pending")
        self.assertEqual(asset_window.code_labels(()), ())

    def test_chosen_code(self) -> None:
        codes = codes_for(AssetKind.INVERTER)
        self.assertEqual(asset_window.chosen_code(codes, 0), "INV-001")
        self.assertEqual(asset_window.chosen_code(codes, 3), "INV-004")
        self.assertIsNone(asset_window.chosen_code(codes, -1))
        self.assertIsNone(asset_window.chosen_code(codes, 4))

    def test_refusal_text(self) -> None:
        self.assertEqual(asset_window.refusal_text(ValueError("bad address")), "Refused: bad address")


@unittest.skipUnless(display_available(), "no display")
class WindowTest(unittest.TestCase):
    """The window under a display: built, updated once, inspected, destroyed; never a mainloop."""

    def setUp(self) -> None:
        """A hidden root, the fixture store and the inverter's window, with on_change counted."""
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.conn = fixture_store()
        self.changes: list[int] = []
        self.window = asset_window.AssetWindow(self.root, self.conn, INV1, lambda: self.changes.append(1))
        self.root.update()

    def tearDown(self) -> None:
        """Destroys the root (and any window left) and closes the store."""
        self.root.destroy()
        self.conn.close()

    def rows(self, tree: "tkinter.ttk.Treeview") -> list[tuple[str, ...]]:
        """A tree's rows as string tuples: rows(window.fault_tree)[0][0] is "INV-001"."""
        return [tuple(str(v) for v in tree.item(item, "values")) for item in tree.get_children()]

    def engineer(self) -> str | None:
        """The inverter's stored engineer: "inverter@oahe.example" in the fixture."""
        return project.asset_detail(self.conn, INV1).asset.engineer_email

    def test_fields_status_and_trees(self) -> None:
        self.assertEqual(self.window.title(), "OAHE-INV-001 — Inverter 1")
        texts = tuple(label.cget("text") for label in self.window.fields.winfo_children())
        self.assertEqual(texts, asset_window.field_lines(INVERTER))
        self.assertEqual(self.window.status_label.cget("text"), "Status: red")
        self.assertEqual(str(self.window.status_label.cget("foreground")), "#c0392b")
        self.assertEqual([row[0] for row in self.rows(self.window.fault_tree)], ["INV-001"])
        self.assertEqual(self.rows(self.window.result_tree), list(DIAGNOSTIC_ROWS))
        items = self.window.result_tree.get_children()
        self.assertEqual(tuple(self.window.result_tree.item(items[0], "tags")), ("failing",))
        self.assertEqual(tuple(self.window.result_tree.item(items[1], "tags")), ("notrun",))
        self.assertEqual(self.window.result_tree.item(items[-1], "tags"), "")
        self.assertEqual(self.window.engineer_box.get(), INVERTER_EMAIL)
        self.assertEqual(tuple(self.window.engineer_box.cget("values")), (INVERTER_EMAIL, SITE_EMAIL))

    def test_button_texts(self) -> None:
        self.assertEqual(self.window.save_button.cget("text"), "Save")
        self.assertEqual(self.window.cancel_button.cget("text"), "Cancel")
        self.assertEqual(self.window.assign_button.cget("text"), "Assign")

    def test_layout_holds_its_parts(self) -> None:
        window = self.window
        titles = [child.cget("text") for child in window.winfo_children() if child.winfo_class() == "TLabel"]
        self.assertEqual(titles, ["Open faults", "Diagnostics"])
        self.assertEqual([window.fault_tree.heading(c, "text") for c in ("code", "meaning", "opened")],
                         ["Code", "Meaning", "Opened"])
        self.assertEqual([window.result_tree.heading(c, "text") for c in ("test", "result", "reason")],
                         ["Test", "Result", "Reason"])
        self.assertEqual(str(window.result_tree.tag_configure("failing", "foreground")), "#c0392b")
        self.assertEqual(str(window.result_tree.tag_configure("notrun", "foreground")), "#808080")
        self.assertEqual([window.result_tree.column(c, "width") for c in ("test", "result")], [190, 70])
        self.assertGreaterEqual(window.result_tree.column("reason", "width"), 480)  # it stretches to the window
        self.assertEqual(str(window.message.cget("foreground")), "#c0392b")
        for widget in (window.fields, window.status_label, window.code_box, window.assign_button,
                       window.engineer_box, window.save_button, window.cancel_button, window.message):
            self.assertIs(widget.winfo_toplevel(), window)

    def test_assign_adds_a_fault(self) -> None:
        self.window.code_box.current(3)
        self.window.assign_button.invoke()
        codes = [fault.code for fault, _ in project.asset_detail(self.conn, INV1).open_faults]
        self.assertEqual(codes, ["INV-001", "INV-004"])
        self.assertEqual([row[0] for row in self.rows(self.window.fault_tree)], ["INV-001", "INV-004"])
        self.assertEqual(self.changes, [1])
        self.assertEqual(self.window.message.cget("text"), "")

    def test_assign_refused_is_shown(self) -> None:
        self.window.code_box.current(0)
        self.window.assign_button.invoke()
        self.assertEqual(self.window.message.cget("text"),
                         "Refused: OAHE-INV-001 already carries open fault 1 of INV-001")
        self.assertEqual(len(project.asset_detail(self.conn, INV1).open_faults), 1)
        self.assertEqual(self.changes, [])

    def test_assign_clears_an_earlier_refusal(self) -> None:
        self.window.assign_button.invoke()
        self.window.code_box.current(1)
        self.window.assign_button.invoke()
        self.assertEqual(self.window.message.cget("text"), "")

    def test_assign_with_nothing_chosen(self) -> None:
        self.window.assign_button.invoke()
        self.assertEqual(self.window.message.cget("text"), "Choose a code to assign.")
        self.assertEqual(self.changes, [])

    def test_save_assigns_and_closes(self) -> None:
        self.window.engineer_box.set(NEW_EMAIL)
        self.window.save_button.invoke()
        self.assertEqual(self.engineer(), NEW_EMAIL)
        self.assertEqual(self.changes, [1])
        self.assertFalse(self.window.winfo_exists())

    def test_save_refused_keeps_the_window(self) -> None:
        self.window.engineer_box.set("not-an-email")
        self.window.save_button.invoke()
        self.assertEqual(self.window.message.cget("text"),
                         "Refused: OAHE-INV-001: 'not-an-email' is not an email address")
        self.assertTrue(self.window.winfo_exists())
        self.assertEqual(self.engineer(), INVERTER_EMAIL)
        self.assertEqual(self.changes, [])

    def test_cancel_changes_nothing(self) -> None:
        self.window.engineer_box.set(NEW_EMAIL)
        self.window.cancel_button.invoke()
        self.assertEqual(self.engineer(), INVERTER_EMAIL)
        self.assertEqual(self.changes, [])
        self.assertFalse(self.window.winfo_exists())

    def test_no_engineer_leaves_the_box_empty(self) -> None:
        window = asset_window.AssetWindow(self.root, self.conn, INV2)
        self.root.update()
        self.assertEqual(window.engineer_box.get(), "")
        self.assertIn("Engineer: none", [label.cget("text") for label in window.fields.winfo_children()])

    def test_unknown_asset_draws_nothing(self) -> None:
        with self.assertRaises(project.UnknownAsset):
            asset_window.AssetWindow(self.root, self.conn, "OAHE-INV-009")


class TheDemosDiagnostics(unittest.TestCase):
    """6.4's check over the demo store, headless: the asset window's diagnostics are project.asset_detail's."""

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

    def test_the_fed_inverter_passes_all_seven(self) -> None:
        found = project.asset_detail(self.conn, demo.FED).diagnostics
        self.assertEqual(len(found), 7)
        self.assertEqual({diagnostic.state for diagnostic in found}, {"pass"}, found)

    def test_the_sensors_failing_reachable_comes_first(self) -> None:
        found = project.asset_detail(self.conn, demo.SENSOR).diagnostics
        self.assertEqual((found[0].test_name, found[0].state), ("reachable", "fail"))
        self.assertEqual([d.test_name for d in found], ["reachable", "irradiance_in_range", "on_grid"])

    def test_a_tracker_with_no_feed_shows_its_tests_never_run_and_a_string_shows_none(self) -> None:
        found = project.asset_detail(self.conn, "OAHE-TRK-001").diagnostics
        self.assertEqual([(d.test_name, d.state) for d in found], [("on_grid", "not run"), ("reachable", "not run")])
        self.assertEqual(project.asset_detail(self.conn, "OAHE-STR-001").diagnostics, ())



if __name__ == "__main__":
    unittest.main()
