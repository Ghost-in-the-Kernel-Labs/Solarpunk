"""Suggestions (7.4, SP-015): the table keeps one open suggestion per asset and code; a run's failures raise the codes
their tests' rules name, never one the asset already carries open; an engineer the fleet holds accepts one into a fault
(opened at the suggestion's instant, linked) or dismisses it with a reason; a suggestion turns an asset yellow, never
red, and no KPI reads it; the demo's dead weather station waits with a suggestion of SEN-001."""
import io
import tempfile
from datetime import datetime
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.cli import main as cli
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetStatus
from solarpunk.remote import results
from solarpunk.remote import suggestions as table
from solarpunk.ui import demo

SITE_EMAIL = "site@oahe.example"
INV1 = "OAHE-INV-001"
SEN = "OAHE-SEN-001"
RUN_AT = at(2026, 6, 1, 13)
EARLIER = at(2026, 6, 1, 12)
DAY = project.day_period(RUN_AT.date())


class Suggesting(unittest.TestCase):
    def setUp(self) -> None:
        """An in-memory store holding the demo fleet."""
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        project.load_fleet(self.conn, project.demo_fleet())

    def failed(self, test: str, asset_id: str, run_at: datetime = RUN_AT) -> None:
        """Records a failing result of a test on an asset at an instant, as a run would: self.failed("reachable", SEN)."""
        results.record(self.conn, test, asset_id, run_at, results.Result(False, f"{test} failed"))


class TheTable(Suggesting):
    def test_one_open_suggestion_per_asset_and_code_and_a_devices_first(self) -> None:
        first = table.raise_suggestion(self.conn, SEN, "SEN-001", "reachable", "silent", EARLIER)
        again = table.raise_suggestion(self.conn, SEN, "SEN-001", "irradiance_in_range", "1600 W/m2", RUN_AT)
        self.assertEqual(again, first)
        pushed = table.raise_suggestion(self.conn, INV1, "INV-002", table.DEVICE, "pushed", EARLIER)
        newer = table.raise_suggestion(self.conn, INV1, "INV-001", "reachable", "silent", RUN_AT)
        self.assertEqual(table.open_suggestions(self.conn, INV1), (pushed, newer))

    def test_a_decided_suggestion_cannot_be_decided_again_and_a_dismissal_says_why(self) -> None:
        found = table.raise_suggestion(self.conn, SEN, "SEN-001", "reachable", "silent", RUN_AT)
        with self.assertRaisesRegex(table.SuggestionError, "a dismissal needs a reason"):
            table.mark_dismissed(self.conn, found.suggestion_id, SITE_EMAIL, "  ")
        table.mark_dismissed(self.conn, found.suggestion_id, SITE_EMAIL, "fibre repaired")
        with self.assertRaisesRegex(table.SuggestionError, "is already dismissed"):
            table.mark_accepted(self.conn, found.suggestion_id, SITE_EMAIL, 1)
        with self.assertRaisesRegex(table.SuggestionError, "suggestion 9 is not in the table"):
            table.get(self.conn, 9)


class FromARun(Suggesting):
    def test_a_failure_whose_rule_names_a_code_raises_it_and_others_raise_nothing(self) -> None:
        self.failed("reachable", SEN)
        self.failed("on_grid", SEN)
        self.failed("reachable", INV1, EARLIER)
        raised = project.suggest_from_run(self.conn, (SEN, INV1), RUN_AT)
        self.assertEqual([(s.asset_id, s.code, s.source) for s in raised], [(SEN, "SEN-001", "reachable")])

    def test_a_code_the_asset_already_carries_open_is_not_suggested(self) -> None:
        project.assign_fault(self.conn, INV1, "INV-001", EARLIER, SITE_EMAIL)
        self.failed("reachable", INV1)
        self.assertEqual(project.suggest_from_run(self.conn, (INV1,), RUN_AT), ())


class AnEngineerDecides(Suggesting):
    def test_accepting_opens_the_fault_as_the_engineer_at_the_suggestions_instant_and_links_it(self) -> None:
        found = project.suggest_pushed(self.conn, INV1, "INV-001", EARLIER)
        self.assertIs(project.asset_status(self.conn, INV1), AssetStatus.YELLOW)
        fault = project.accept_suggestion(self.conn, found.suggestion_id, SITE_EMAIL, "ops@oahe.example")
        self.assertEqual((fault.code, fault.opened, fault.assigned_by, fault.recorded_by),
                         ("INV-001", EARLIER, SITE_EMAIL, "ops@oahe.example"))
        decided = table.get(self.conn, found.suggestion_id)
        self.assertEqual((decided.state, decided.decided_by, decided.fault_id), ("accepted", SITE_EMAIL, fault.fault_id))
        self.assertIs(project.asset_status(self.conn, INV1), AssetStatus.RED)

    def test_an_engineer_the_fleet_does_not_hold_changes_nothing(self) -> None:
        found = project.suggest_pushed(self.conn, INV1, "INV-001", EARLIER)
        for act in (lambda: project.accept_suggestion(self.conn, found.suggestion_id, "nobody@x.example"),
                    lambda: project.dismiss_suggestion(self.conn, found.suggestion_id, "nobody@x.example", "why")):
            with self.subTest(), self.assertRaises(project.UnknownEngineer):
                act()
        self.assertEqual(project.open_suggestions(self.conn, INV1), (found,))
        self.assertEqual(project.faults_listing(self.conn, False), ())

    def test_dismissing_records_who_and_why_and_the_asset_falls_back_to_green(self) -> None:
        found = project.suggest_pushed(self.conn, INV1, "INV-001", EARLIER)
        decided = project.dismiss_suggestion(self.conn, found.suggestion_id, SITE_EMAIL, "a test push")
        self.assertEqual((decided.state, decided.decided_by, decided.dismissal), ("dismissed", SITE_EMAIL, "a test push"))
        self.assertIs(project.asset_status(self.conn, INV1), AssetStatus.GREEN)


class StatusAndKpis(Suggesting):
    def test_an_outage_suggestion_is_yellow_never_red_and_no_kpi_reads_it(self) -> None:
        project.generate_and_store(self.conn, "OAHE", DAY, 7)
        before = project.kpis_for(self.conn, "OAHE", DAY)
        project.suggest_pushed(self.conn, INV1, "INV-001", EARLIER)
        after = project.kpis_for(self.conn, "OAHE", DAY)
        self.assertIs(project.asset_status(self.conn, INV1), AssetStatus.YELLOW)
        self.assertEqual((after.availability, after.reliability, after.faults_open),
                         (before.availability, before.reliability, before.faults_open))


class TheDemo(unittest.TestCase):
    def test_the_dead_weather_station_waits_with_sen001_and_the_red_inverter_with_none(self) -> None:
        server, port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port)
        conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        self.addCleanup(conn.close)
        waiting = project.open_suggestions(conn)
        self.assertEqual([(s.asset_id, s.code, s.source) for s in waiting], [(demo.SENSOR, "SEN-001", "reachable")])
        self.assertIs(project.asset_status(conn, demo.DOWN), AssetStatus.RED)



class OnTheCommandLine(unittest.TestCase):
    """7.5: fault suggestions, accept and dismiss over a store file."""

    def setUp(self) -> None:
        """A store file holding the demo fleet and a pushed INV-001 and a run's SEN-001 waiting."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "fleet.db")
        conn = project.open_or_create(self.db)
        project.load_fleet(conn, project.demo_fleet())
        project.suggest_pushed(conn, INV1, "INV-001", EARLIER)
        table.raise_suggestion(conn, SEN, "SEN-001", "reachable", "127.0.0.1:9 is unreachable", RUN_AT)
        conn.close()

    def cli(self, argv: list[str]) -> tuple[int, list[str], str]:
        """main over self.db: (exit code, stdout's lines, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["--db", self.db, *argv], out, err)
        return code, out.getvalue().splitlines(), err.getvalue()

    def test_the_list_then_accept_then_dismiss(self) -> None:
        self.assertEqual(self.cli(["fault", "suggestions"])[1], [
            "1 OAHE-INV-001 INV-001 from device at 2026-06-01T12:00:00+00:00: pushed by the asset",
            "2 OAHE-SEN-001 SEN-001 from reachable at 2026-06-01T13:00:00+00:00: 127.0.0.1:9 is unreachable"])
        self.assertEqual(self.cli(["fault", "suggestions", "--asset", SEN])[1][0][:2], "2 ")
        self.assertEqual(self.cli(["fault", "accept", "1", "--by", SITE_EMAIL, "--recorded-by", "ops@oahe.example"]),
                         (0, [f"1 OAHE-INV-001 INV-001 2026-06-01T12:00:00+00:00 open by {SITE_EMAIL}"
                              " entered by ops@oahe.example"], ""))
        self.assertEqual(self.cli(["fault", "dismiss", "2", "--by", SITE_EMAIL, "--reason", "fibre repaired"]),
                         (0, [f"dismissed 2 by {SITE_EMAIL}: fibre repaired"], ""))
        self.assertEqual(self.cli(["fault", "suggestions"])[1], [])

    def test_refusals_are_error_lines(self) -> None:
        self.assertEqual(self.cli(["fault", "accept", "1", "--by", "nobody@x.example"]),
                         (2, [], "error: nobody@x.example is not an engineer the fleet holds\n"))
        self.assertEqual(self.cli(["fault", "accept", "9", "--by", SITE_EMAIL]),
                         (2, [], "error: suggestion 9 is not in the table\n"))
        code, _, err = self.cli(["fault", "dismiss", "2", "--by", SITE_EMAIL])
        self.assertEqual(code, 2)
        self.assertIn("the following arguments are required: --reason", err)

if __name__ == "__main__":
    unittest.main()
