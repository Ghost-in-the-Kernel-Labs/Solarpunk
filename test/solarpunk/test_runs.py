"""The runs' surface (10.2, SOL-15, SP-024): asset_runs, asset_power, asset_code_counts and code_counts_by_asset held to
SOL-15's worked examples over the demo store; then a store of 120 runs, the newest 100 shown and none deleted; the
search; the counting rules (faults and suggestions apart, a dismissed suggestion counted, an accepted one's fault
counted as a fault, the period half-open); the refusals."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from solarpunk import project
from test.solarpunk.old_store import old_suggestion
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import UnknownFaultCode
from solarpunk.remote import results
from solarpunk.ui import demo

DAY = project.day_period(date(2026, 6, 1))
ENGINEER = "site@oahe.example"
INV1, INV2, SEN = "OAHE-INV-001", "OAHE-INV-002", "OAHE-SEN-001"


class TheExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """The demo store, built once in a temporary folder with its simulator, then opened."""
        server, port = demo.start_simulator(demo.simulator_samples())
        cls.addClassCleanup(server.server_close)
        cls.addClassCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(folder.cleanup)
        demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port)
        cls.conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        cls.addClassCleanup(cls.conn.close)

    def test_the_down_inverters_run(self) -> None:
        (run,) = project.asset_runs(self.conn, INV2)
        self.assertEqual((run.run_at, len(run.results), run.failed), (at(2026, 6, 1, 13), 9, True))
        first = run.results[0]
        self.assertEqual((first.test_name, first.passed, first.reason), ("reachable", False, "127.0.0.1:9 is unreachable"))
        self.assertIn(("reachable", True, "156 records"), [(r.test_name, r.passed, r.reason) for r in run.results])
        self.assertEqual([r.passed for r in run.results], [False, False] + [True] * 7)  # power_ripple, with no live reads taken, says no data (13.3)

    def test_the_sensors_run(self) -> None:
        (run,) = project.asset_runs(self.conn, SEN)
        self.assertEqual([(r.test_name, r.passed, r.no_data) for r in run.results],
                         [("reachable", False, False), ("reachable", False, False),
                          ("irradiance_in_range", False, True), ("on_grid", False, True)])  # SP-039: no data, not a pass

    def test_the_error_counts(self) -> None:
        self.assertEqual(project.asset_code_counts(self.conn, SEN, DAY), (project.CodeCount("SEN-001", 1, 0),))  # SP-046: a fault, not a suggestion
        self.assertEqual(project.asset_code_counts(self.conn, INV2, DAY),
                         (project.CodeCount("INV-001", 1, 0), project.CodeCount("SIT-004", 1, 0)))  # SP-047: the lost link raises the generic code
        self.assertEqual(project.asset_code_counts(self.conn, INV1, DAY), (project.CodeCount("INV-002", 1, 0),))
        self.assertEqual(project.code_counts_by_asset(self.conn, "INV-001", DAY), (project.AssetCount(INV2, 1, 0),))

    def test_the_power_series(self) -> None:
        series = project.asset_power(self.conn, INV1, DAY)
        self.assertEqual((len(series.samples), series.records, series.gaps), (288, 279, 9))
        self.assertEqual(next(s.at for s in series.samples if s.gap), at(2026, 6, 1, 4, 25))
        self.assertEqual(project.asset_power(self.conn, "OAHE-TRK-001", DAY).samples, ())

    def test_the_search(self) -> None:
        for words in ("unreachable", "FAIL", "reachable", "performance_above"):
            with self.subTest(words=words):
                self.assertEqual(len(project.asset_runs(self.conn, INV2, search=words)), 1)
        self.assertEqual(project.asset_runs(self.conn, INV1, search="fail"), ())
        self.assertEqual(len(project.asset_runs(self.conn, INV1, search="pass")), 1)
        self.assertEqual(len(project.asset_runs(self.conn, INV1, search="   ")), 1)


class ManyRuns(unittest.TestCase):
    def test_the_newest_100_of_120_newest_first_and_none_deleted(self) -> None:
        conn = project.open_store()
        self.addCleanup(conn.close)
        project.load_fleet(conn, project.demo_fleet())
        start = at(2026, 6, 1)
        for n in range(120):
            results.record(conn, "reachable", INV1, start + timedelta(hours=n), results.Result(n % 10 != 0, f"run {n}"))
        runs = project.asset_runs(conn, INV1)
        self.assertEqual(len(runs), 100)
        self.assertEqual((runs[0].run_at, runs[-1].run_at), (start + timedelta(hours=119), start + timedelta(hours=20)))
        self.assertEqual(conn.execute("SELECT count(*) FROM results").fetchone()[0], 120)
        self.assertEqual(len(project.asset_runs(conn, INV1, limit=500)), 120)
        failed = project.asset_runs(conn, INV1, search="fail")
        self.assertEqual([r.results[0].reason for r in failed[:2]], ["run 110", "run 100"])
        self.assertEqual(len(failed), 12)


class TheCountingRules(unittest.TestCase):
    def setUp(self) -> None:
        """The OAHE fleet, with no fault and no suggestion yet."""
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        project.load_fleet(self.conn, project.demo_fleet())

    def test_a_store_made_before_7_7_still_counts_its_decided_suggestions_beside_the_fault(self) -> None:
        old_suggestion(self.conn, INV1, "INV-001", at(2026, 6, 1, 9), state="dismissed", decided_by=ENGINEER,
                       dismissal="a reboot, not a fault")
        fault = project.assign_fault(self.conn, INV1, "INV-001", at(2026, 6, 1, 10), ENGINEER)
        old_suggestion(self.conn, INV1, "INV-001", at(2026, 6, 1, 10), state="accepted", decided_by=ENGINEER,
                       fault_id=fault.fault_id)
        self.assertEqual(project.asset_code_counts(self.conn, INV1, DAY), (project.CodeCount("INV-001", 1, 2),))

    def test_the_period_is_half_open_and_counts_by_opening(self) -> None:
        project.assign_fault(self.conn, INV1, "INV-001", at(2026, 6, 1), ENGINEER)
        project.assign_fault(self.conn, INV1, "INV-002", at(2026, 6, 2), ENGINEER)
        old_suggestion(self.conn, INV2, "INV-001", at(2026, 6, 1, 23, 55))
        self.assertEqual(project.asset_code_counts(self.conn, INV1, DAY), (project.CodeCount("INV-001", 1, 0),))
        self.assertEqual(project.code_counts_by_asset(self.conn, "INV-001", DAY),
                         (project.AssetCount(INV1, 1, 0), project.AssetCount(INV2, 0, 1)))

    def test_the_refusals(self) -> None:
        for call in (lambda: project.asset_runs(self.conn, "OAHE-INV-009"),
                     lambda: project.asset_power(self.conn, "OAHE-INV-009", DAY),
                     lambda: project.asset_code_counts(self.conn, "OAHE-INV-009", DAY)):
            with self.assertRaises(project.UnknownAsset):
                call()
        with self.assertRaises(UnknownFaultCode):
            project.code_counts_by_asset(self.conn, "INV-999", DAY)
        self.assertEqual(project.asset_runs(self.conn, INV1), ())


if __name__ == "__main__":
    unittest.main()
