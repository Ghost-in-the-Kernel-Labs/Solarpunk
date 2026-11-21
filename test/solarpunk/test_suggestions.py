"""Faults from telemetry (7.7, SP-046, superseding SP-015 in part): a failing remote test result raises its fault itself,
by its rule table's code or the catalogue's generic one, assigned by the test and opened at the run's instant; a failure
of the same test on the same asset joins the fault still open, and no data raises none; a pushed code is a fault from
the device. Nothing is accepted or dismissed and nothing writes a suggestion; a store made before 7.7 reads the
suggestions it holds as they were; the demo's dead weather station carries SEN-001 raised by its failing reachable."""
import io
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from solarpunk import project
from solarpunk.cli import main as cli
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import GENERIC_TEST_FAILURE, AssetStatus, lookup
from solarpunk.remote import results
from solarpunk.ui import demo
from test.solarpunk.old_store import old_suggestion

SITE_EMAIL = "site@oahe.example"
INV1 = "OAHE-INV-001"
SEN = "OAHE-SEN-001"
RUN_AT = at(2026, 6, 1, 13)
EARLIER = at(2026, 6, 1, 12)
LATER = at(2026, 6, 1, 14)
DAY = project.day_period(RUN_AT.date())


class Raising(unittest.TestCase):
    def setUp(self) -> None:
        """An in-memory store holding the demo fleet."""
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        project.load_fleet(self.conn, project.demo_fleet())

    def result(self, test: str, asset_id: str, run_at: datetime, outcome: results.Result) -> None:
        """Records a result of a test on an asset at an instant, as a run would."""
        results.record(self.conn, test, asset_id, run_at, outcome)

    def failed(self, test: str, asset_id: str, run_at: datetime = RUN_AT) -> None:
        """Records a failing result: self.failed("reachable", SEN)."""
        self.result(test, asset_id, run_at, results.Result(False, f"{test} failed"))


class FromARun(Raising):
    def test_a_failure_raises_its_rule_tables_code_assigned_by_the_test_at_the_runs_instant(self) -> None:
        self.failed("reachable", SEN)
        (fault,) = project.faults_from_run(self.conn, (SEN,), RUN_AT)
        self.assertEqual((fault.asset_id, fault.code, fault.assigned_by, fault.recorded_by, fault.opened, fault.closed),
                         (SEN, "SEN-001", "test:reachable", None, RUN_AT, None))
        self.assertEqual(project.faults_listing(self.conn, True), (fault,))
        self.assertEqual(project.open_suggestions(self.conn), ())  # nothing is suggested since 7.7

    def test_a_failure_whose_table_names_no_code_raises_the_generic_one(self) -> None:
        self.failed("on_grid", SEN)
        (fault,) = project.faults_from_run(self.conn, (SEN,), RUN_AT)
        self.assertEqual((fault.code, fault.assigned_by), (GENERIC_TEST_FAILURE, "test:on_grid"))
        self.assertEqual(lookup(GENERIC_TEST_FAILURE).meaning, "Remote test failed: its cause is not yet known")

    def test_no_data_and_a_pass_raise_none(self) -> None:
        self.result("on_grid", SEN, RUN_AT, results.no_data("no records"))
        self.result("irradiance_in_range", SEN, RUN_AT, results.Result(True, "in range"))
        self.assertEqual(project.faults_from_run(self.conn, (SEN,), RUN_AT), ())
        self.assertEqual(project.faults_listing(self.conn, False), ())

    def test_only_the_runs_own_results_raise(self) -> None:
        self.failed("reachable", INV1, EARLIER)
        self.assertEqual(project.faults_from_run(self.conn, (INV1,), RUN_AT), ())

    def test_a_failure_in_the_next_run_joins_the_open_fault_and_a_closed_one_is_followed_by_a_new_row(self) -> None:
        self.failed("reachable", SEN, EARLIER)
        (first,) = project.faults_from_run(self.conn, (SEN,), EARLIER)
        self.failed("reachable", SEN, RUN_AT)
        self.assertEqual(project.faults_from_run(self.conn, (SEN,), RUN_AT), ())  # joins the earlier failure's fault
        self.assertEqual(project.faults_listing(self.conn, False), (first,))
        project.close_fault(self.conn, first.fault_id, RUN_AT)
        self.failed("reachable", SEN, LATER)
        (second,) = project.faults_from_run(self.conn, (SEN,), LATER)  # a later fact is a new row
        self.assertNotEqual(second.fault_id, first.fault_id)
        self.assertEqual(len(project.faults_listing(self.conn, False)), 2)

    def test_a_code_the_asset_already_carries_open_is_joined_not_raised_again(self) -> None:
        engineers = project.assign_fault(self.conn, INV1, "INV-001", EARLIER, SITE_EMAIL)
        self.failed("reachable", INV1)
        self.assertEqual(project.faults_from_run(self.conn, (INV1,), RUN_AT), ())
        self.assertEqual(project.faults_listing(self.conn, False), (engineers,))

    def test_running_it_again_raises_nothing_more(self) -> None:
        self.failed("reachable", SEN)
        project.faults_from_run(self.conn, (SEN,), RUN_AT)
        self.assertEqual(project.faults_from_run(self.conn, (SEN,), RUN_AT), ())


class FromTheDevice(Raising):
    def test_a_pushed_code_is_a_fault_assigned_by_the_device_and_pushed_again_it_is_the_same_one(self) -> None:
        fault = project.fault_from_device(self.conn, INV1, "INV-001", EARLIER)
        self.assertEqual((fault.assigned_by, fault.opened), ("device", EARLIER))
        self.assertIs(project.asset_status(self.conn, INV1), AssetStatus.RED)
        self.assertEqual(project.fault_from_device(self.conn, INV1, "INV-001", RUN_AT), fault)
        with self.assertRaises(project.UnknownAsset):
            project.fault_from_device(self.conn, "OAHE-INV-009", "INV-001", EARLIER)


class AStoreMadeBefore7_7(Raising):
    def test_its_suggestions_read_as_they_were_and_nothing_decides_them(self) -> None:
        waiting = old_suggestion(self.conn, INV1, "INV-001", EARLIER)
        dismissed = old_suggestion(self.conn, SEN, "SEN-001", EARLIER, "reachable", "silent", "dismissed", SITE_EMAIL,
                                   None, "fibre repaired")
        self.assertEqual(project.open_suggestions(self.conn), (waiting,))
        self.assertEqual((dismissed.state, dismissed.decided_by, dismissed.dismissal),
                         ("dismissed", SITE_EMAIL, "fibre repaired"))
        self.assertIs(project.asset_status(self.conn, INV1), AssetStatus.YELLOW)  # as it was: yellow, never red
        for gone in ("accept_suggestion", "dismiss_suggestion", "accept_suggestion_as", "dismiss_suggestion_as",
                     "suggest_pushed", "suggest_from_run"):
            self.assertFalse(hasattr(project, gone), gone)


class TheDemo(unittest.TestCase):
    def test_the_dead_weather_station_carries_sen001_from_its_test_and_the_red_inverter_its_own(self) -> None:
        server, port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port)
        conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        self.addCleanup(conn.close)
        self.assertEqual(project.open_suggestions(conn), ())
        sensor = [f for f in project.faults_listing(conn, True) if f.asset_id == demo.SENSOR]
        self.assertEqual([(f.code, f.assigned_by) for f in sensor], [("SEN-001", "test:reachable")])
        self.assertIs(project.asset_status(conn, demo.DOWN), AssetStatus.RED)


class OnTheCommandLine(unittest.TestCase):
    """fault suggestions reads an old store; fault accept and fault dismiss are gone (SP-046)."""

    def setUp(self) -> None:
        """A store file holding the demo fleet and one suggestion an old store left open."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "fleet.db")
        conn = project.open_or_create(self.db)
        project.load_fleet(conn, project.demo_fleet())
        old_suggestion(conn, SEN, "SEN-001", RUN_AT, "reachable", "127.0.0.1:9 is unreachable")
        conn.close()

    def cli(self, argv: list[str]) -> tuple[int, list[str], str]:
        """main over self.db: (exit code, stdout's lines, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["--db", self.db, *argv], out, err)
        return code, out.getvalue().splitlines(), err.getvalue()

    def test_the_list_reads_and_accept_and_dismiss_are_not_commands(self) -> None:
        self.assertEqual(self.cli(["fault", "suggestions"])[1],
                         ["1 OAHE-SEN-001 SEN-001 from reachable at 2026-06-01T13:00:00+00:00: 127.0.0.1:9 is unreachable"])
        for gone in ("accept", "dismiss"):
            code, _, err = self.cli(["fault", gone, "1", "--by", SITE_EMAIL])
            self.assertEqual(code, 2, gone)
            self.assertIn("invalid choice", err)
        self.assertEqual(len(self.cli(["fault", "suggestions"])[1]), 1)


if __name__ == "__main__":
    unittest.main()
