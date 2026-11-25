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
from solarpunk.remote import registry as remote_registry
from solarpunk.remote import results
from solarpunk.ui import asset_text, demo

ENGINEER = "site@oahe.example"  # SP-015: a fault names the engineer who assigned it; the fixtures' site engineer

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
# The inverter's diagnostics (6.4): its last run failed on_grid and passed records_stored; every other inverter test the
# registry holds never ran on it, so it follows the folder (SP-017).
NEVER_RUN = sorted(test.name for test in remote_registry.tests_for(AssetKind.INVERTER)
                   if test.name not in ("on_grid", "records_stored"))
# 13.6: on_grid ran at 12:00 taking 42 ms; records_stored ran then untimed (duration "—"); the others never ran ("never", "—").
LAST_RUN = "2026-06-01 12:00 UTC"
DIAGNOSTIC_ROWS = (("on_grid", "FAIL", LAST_RUN, "42 ms", OFF_GRID),
                   *[(name, "not run", "never", "—", NEVER) for name in NEVER_RUN],
                   ("records_stored", "pass", LAST_RUN, "—", "3 records"))


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
    status is RED and its latest (on_grid failed, records_stored passed)."""
    conn = project.open_store()
    project.register_asset(conn, SITE)
    project.register_asset(conn, INVERTER)
    project.register_asset(conn, UNSERVICED)
    project.assign_fault(conn, INV1, "INV-001", OPENED, ENGINEER)
    results.record(conn, "records_stored", INV1, RUN_AT - timedelta(hours=1), results.Result(False, "stale"))
    results.record(conn, "records_stored", INV1, RUN_AT, results.Result(True, "3 records"))
    results.record(conn, "on_grid", INV1, RUN_AT, results.Result(False, OFF_GRID), duration_ms=42)
    return conn


class DurationWordsTest(unittest.TestCase):
    """13.6: a duration in the window's words, headless."""

    def test_milliseconds_below_a_second_seconds_above_dash_for_none(self) -> None:
        self.assertEqual([asset_text.duration_words(ms) for ms in (0, 42, 999, 1000, 1049, 1050, 2350, 61000)],
                         ["0 ms", "42 ms", "999 ms", "1.0 s", "1.0 s", "1.1 s", "2.4 s", "61.0 s"])
        self.assertEqual(asset_text.duration_words(None), "\u2014")


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
        self.assertEqual(asset_text.field_lines(INVERTER), (
            "Kind: Inverter", "Site: OAHE", "Parent: OAHE-SIT-001", "Rated: 100.0 kW", "Location: Pad A",
            "Endpoint: 127.0.0.1:5020", "Engineer: inverter@oahe.example"))

    def test_field_lines_with_missing_values(self) -> None:
        bare = Asset("OAHE-SEN-001", AssetKind.SENSOR, "OAHE", None, "Sensor", None)
        self.assertEqual(asset_text.field_lines(bare), (
            "Kind: Sensor", "Site: OAHE", "Parent: none", "Rated: none", "Location: none", "Endpoint: none",
            "Engineer: none"))

    def test_shown(self) -> None:
        self.assertEqual(asset_text.shown(None), "none")
        self.assertEqual(asset_text.shown(5020), "5020")

    def test_title_and_status(self) -> None:
        self.assertEqual(asset_text.window_title(INVERTER), "OAHE-INV-001 — Inverter 1")
        self.assertEqual(asset_text.status_line(AssetStatus.RED), "Status: red")
        self.assertEqual(asset_text.status_line(AssetStatus.GREEN), "Status: green")

    def test_colour_of(self) -> None:
        self.assertEqual(asset_text.colour_of(AssetStatus.GREEN), "#2e8b57")
        self.assertEqual(asset_text.colour_of(AssetStatus.YELLOW), "#e0b000")
        self.assertEqual(asset_text.colour_of(AssetStatus.RED), "#c0392b")

    def test_fault_lines(self) -> None:
        meaning = "Inverter offline: no AC output while irradiance is above the start threshold"
        self.assertEqual(asset_text.fault_lines(self.detail),
                         (("INV-001", meaning, "2026-06-01 10:10 UTC", "site@oahe.example", "not written"),))

    def test_assigned_text_says_who_entered_it_and_cover(self) -> None:
        fault = project.Fault(1, INV1, "INV-001", OPENED, None, "a@oahe.example", "ops@oahe.example")
        self.assertEqual(asset_text.assigned_text(fault, True), "a@oahe.example, entered by ops@oahe.example (cover)")
        self.assertEqual(asset_text.assigned_text(project.Fault(1, INV1, "INV-001", OPENED, None), False), "unrecorded")

    def test_fault_lines_empty(self) -> None:
        self.assertEqual(asset_text.fault_lines(project.asset_detail(self.conn, SITE_ID)), ())

    def test_result_lines_failing_then_never_run_then_passing(self) -> None:
        self.assertEqual(asset_text.result_lines(self.detail), DIAGNOSTIC_ROWS)

    def test_row_tags(self) -> None:
        self.assertEqual(asset_text.row_tags(("on_grid", "FAIL", LAST_RUN, "42 ms", OFF_GRID)), ("failing",))
        self.assertEqual(asset_text.row_tags((NEVER_RUN[0], "not run", "never", "—", NEVER)), ("notrun",))
        self.assertEqual(asset_text.row_tags(("records_stored", "pass", LAST_RUN, "—", "3 records")), ())

    def test_code_labels(self) -> None:
        labels = asset_text.code_labels(codes_for(AssetKind.INVERTER))
        self.assertEqual(len(labels), 5)  # SP-054: INV-005 is the fifth
        self.assertEqual(labels[3], "INV-004 — Firmware update pending")
        self.assertEqual(asset_text.code_labels(()), ())

    def test_chosen_code(self) -> None:
        codes = codes_for(AssetKind.INVERTER)
        self.assertEqual(asset_text.chosen_code(codes, 0), "INV-001")
        self.assertEqual(asset_text.chosen_code(codes, 3), "INV-004")
        self.assertIsNone(asset_text.chosen_code(codes, -1))
        self.assertEqual(asset_text.chosen_code(codes, 4), "INV-005")
        self.assertIsNone(asset_text.chosen_code(codes, 5))

    def test_refusal_text(self) -> None:
        self.assertEqual(asset_text.refusal_text(ValueError("bad address")), "Refused: bad address")


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
        self.assertEqual(texts, asset_text.field_lines(INVERTER))
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
        self.assertEqual(titles, ["Open faults", "Diagnostics", asset_text.SUGGESTED_TITLE])  # 7.5
        self.assertEqual([window.fault_tree.heading(c, "text") for c in ("code", "meaning", "opened", "by")],
                         ["Code", "Meaning", "Opened", "Assigned by"])
        self.assertEqual([window.result_tree.heading(c, "text") for c in asset_text.RESULT_COLUMNS],
                         ["Test", "Result", "Last run", "Duration", "Reason"])
        self.assertEqual(str(window.result_tree.tag_configure("failing", "foreground")), "#c0392b")
        self.assertEqual(str(window.result_tree.tag_configure("notrun", "foreground")), "#808080")
        self.assertEqual([window.result_tree.column(c, "width") for c in ("test", "result", "last_run", "duration")],
                         [190, 70, 165, 80])
        self.assertGreaterEqual(window.result_tree.column("reason", "width"), 480)  # it stretches to the window
        self.assertEqual([window.fault_tree.column(c, "width") for c in ("code", "meaning", "opened")], [70, 175, 165])
        self.assertGreaterEqual(window.fault_tree.column("by", "width"), 470)
        self.assertEqual(str(window.message.cget("foreground")), "#c0392b")
        for widget in (window.fields, window.status_label, window.code_box, window.assign_button,
                       window.engineer_box, window.save_button, window.cancel_button, window.message):
            self.assertIs(widget.winfo_toplevel(), window)

    def test_assign_adds_a_fault(self) -> None:
        self.window.code_box.current(3)
        self.window.assigned_by_box.set(INVERTER_EMAIL)
        self.window.assign_button.invoke()
        codes = [fault.code for fault, _ in project.asset_detail(self.conn, INV1).open_faults]
        self.assertEqual(codes, ["INV-001", "INV-004"])
        self.assertEqual([row[0] for row in self.rows(self.window.fault_tree)], ["INV-001", "INV-004"])
        self.assertEqual(self.changes, [1])
        self.assertEqual(self.window.message.cget("text"), "")

    def test_assign_refused_is_shown(self) -> None:
        self.window.code_box.current(0)
        self.window.assigned_by_box.set(INVERTER_EMAIL)
        self.window.assign_button.invoke()
        self.assertEqual(self.window.message.cget("text"),
                         "Refused: OAHE-INV-001 already carries open fault 1 of INV-001")
        self.assertEqual(len(project.asset_detail(self.conn, INV1).open_faults), 1)
        self.assertEqual(self.changes, [])

    def test_assign_clears_an_earlier_refusal(self) -> None:
        self.window.assign_button.invoke()
        self.window.code_box.current(1)
        self.window.assigned_by_box.set(INVERTER_EMAIL)
        self.window.assign_button.invoke()
        self.assertEqual(self.window.message.cget("text"), "")

    def test_assign_needs_the_engineer_who_assigned_it(self) -> None:
        """SP-015: a code with no engineer chosen is refused in the window and assigns nothing."""
        self.window.code_box.current(3)
        self.window.assign_button.invoke()
        self.assertEqual(self.window.message.cget("text"), asset_text.CHOOSE_ENGINEER)
        self.assertEqual(len(project.asset_detail(self.conn, INV1).open_faults), 1)
        self.assertEqual(tuple(self.window.assigned_by_box.cget("values")), (INVERTER_EMAIL, SITE_EMAIL))

    def test_assign_records_the_operator_who_entered_it(self) -> None:
        self.window.code_box.current(3)
        self.window.assigned_by_box.set(INVERTER_EMAIL)
        self.window.entered_by_box.insert(0, "ops@oahe.example")
        self.window.assign_button.invoke()
        added = project.asset_detail(self.conn, INV1).open_faults[-1][0]
        self.assertEqual((added.assigned_by, added.recorded_by), (INVERTER_EMAIL, "ops@oahe.example"))
        self.assertEqual(self.rows(self.window.fault_tree)[-1][3], f"{INVERTER_EMAIL}, entered by ops@oahe.example")

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
        self.dead = demo.reserve_port()
        demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port, self.dead)
        self.conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        self.addCleanup(self.conn.close)

    def test_the_fed_inverter_passes_every_inverter_test(self) -> None:
        found = project.asset_detail(self.conn, demo.FED).diagnostics
        # every script of the kind, and the ping's own `reachable` beside them (SP-056)
        self.assertEqual(sorted(d.test_name for d in found),
                         sorted([*(t.name for t in remote_registry.tests_for(AssetKind.INVERTER)), "reachable"]))
        # power_ripple is judged on the five reads the demo's run takes from the simulator (13.13, SP-049)
        self.assertEqual({d.state for d in found}, {"pass"}, found)

    def test_the_sensors_failing_reachable_is_in_the_failures_shown_first(self) -> None:
        found = project.asset_detail(self.conn, demo.SENSOR).diagnostics
        self.assertIn(("reachable", "fail"), [(d.test_name, d.state) for d in found])
        order = ("fail", "no data", "not run", "pass")
        self.assertEqual(list(found), sorted(found, key=lambda d: (order.index(d.state), d.test_name)))  # failing first
        # SP-039: the ping and records_stored fail first, the sensor's other two tests had nothing to check: no data, never a pass
        self.assertEqual([(d.test_name, d.state) for d in found],
                         [("reachable", "fail"), ("records_stored", "fail"), ("irradiance_in_range", "no data"),
                          ("on_grid", "no data")])
        self.assertEqual(sorted(d.test_name for d in found),
                         sorted([*(t.name for t in remote_registry.tests_for(AssetKind.SENSOR)), "reachable"]))

    def test_the_dead_inverters_failed_reachable_is_not_hidden_by_the_suites_pass(self) -> None:
        """OAHE-INV-002's run stores the ping's `reachable` failure and a `records_stored` pass over its stored samples at one instant;
        the diagnostics show the failure, first (J-050)."""
        found = project.asset_detail(self.conn, demo.DOWN).diagnostics
        self.assertEqual((found[0].test_name, found[0].state), ("performance_above_floor", "fail"))  # 13.15: zero output
        self.assertEqual((found[1].test_name, found[1].state), ("reachable", "fail"))
        self.assertEqual(found[1].reason, f"127.0.0.1:{self.dead} is unreachable")

    def test_a_tracker_with_no_feed_shows_its_tests_never_run_and_a_string_shows_none(self) -> None:
        found = project.asset_detail(self.conn, "OAHE-TRK-001").diagnostics
        tracker = [test.name for test in remote_registry.tests_for(AssetKind.TRACKER)]
        self.assertEqual([(d.test_name, d.state) for d in found], [(name, "not run") for name in tracker])
        self.assertEqual(project.asset_detail(self.conn, "OAHE-STR-001").diagnostics, ())



if __name__ == "__main__":
    unittest.main()
