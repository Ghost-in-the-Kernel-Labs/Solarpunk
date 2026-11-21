"""The record's surface and its timing (13.5, SP-016): the results table's duration_ms column (an old store gains it on
opening, its rows None), the suite runs storing each test's duration, tests_overview and test_log over a store of 120 runs
(newest first, nothing deleted), and a result with no duration reading None, never 0."""
import sqlite3
import unittest
from datetime import timedelta

from solarpunk import project
from solarpunk.fleet import registry as fleet
from solarpunk.leaf import store
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote import results, run
from solarpunk.remote.results import Result
from solarpunk.remote.suite_registry import Suite
from solarpunk.telemetry import samples as telemetry

T0 = at(2026, 6, 1, 10)
INV1 = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", None, "Inverter 1", 100.0)
INV2 = Asset("OAHE-INV-002", AssetKind.INVERTER, "OAHE", None, "Inverter 2", 100.0)
RUNS = 120


def fresh() -> sqlite3.Connection:
    """An in-memory store with the assets, samples and results tables."""
    conn = store.connect()
    store.apply(conn, fleet.schema() + telemetry.schema() + results.schema())
    return conn


class TheColumn(unittest.TestCase):
    def test_a_store_made_before_gains_the_column_and_its_old_rows_are_none(self) -> None:
        old = sqlite3.connect(":memory:")
        self.addCleanup(old.close)
        old.execute("CREATE TABLE results (result_id INTEGER PRIMARY KEY, test_name TEXT NOT NULL, asset_id TEXT NOT NULL,"
                    " run_at TEXT NOT NULL, passed INTEGER NOT NULL, reason TEXT NOT NULL,"
                    " no_data INTEGER NOT NULL DEFAULT 0, suite TEXT NOT NULL DEFAULT 'all')")
        old.execute("INSERT INTO results (test_name, asset_id, run_at, passed, reason) VALUES"
                    " ('reachable', 'A', '2026-06-01T10:00:00+00:00', 1, 'ok')")
        results.upgrade(old)
        results.upgrade(old)  # a table that has it is left as it is
        self.assertIsNone(results.results_of(old, "A")[0].duration_ms)
        self.assertIsNone(old.execute("SELECT duration_ms FROM results").fetchone()[0])

    def test_a_result_recorded_without_a_duration_reads_none_never_zero(self) -> None:
        conn = fresh()
        self.addCleanup(conn.close)
        results.record(conn, "reachable", "A", T0, Result(False, "unreachable"))
        results.record(conn, "reachable", "A", T0 + timedelta(hours=1), Result(True, "ok"), duration_ms=0)
        first, second = results.results_of(conn, "A")[::-1]
        self.assertIsNone(first.duration_ms)
        self.assertEqual(second.duration_ms, 0)  # a measured 0 ms is kept as 0
        self.assertIsNone(project.test_log(conn, "reachable")[1].duration_ms)


class TheRuns(unittest.TestCase):
    def test_run_suite_and_run_named_store_each_tests_duration(self) -> None:
        conn = fresh()
        self.addCleanup(conn.close)
        samples = {INV1.asset_id: (Sample(INV1.asset_id, T0, 500.0, 50.0, False),)}
        run.run_suite(conn, (INV1,), samples, {}, T0)
        stored = results.results_of(conn, INV1.asset_id)
        self.assertTrue(stored)
        self.assertTrue(all(isinstance(found.duration_ms, int) and found.duration_ms >= 0 for found in stored))
        written = run.run_named(conn, Suite("only_ping", ("reachable",), (), (), "hourly"), (INV1,), samples, T0 + timedelta(hours=1))
        self.assertEqual(written, 1)
        named = [found for found in results.results_of(conn, INV1.asset_id) if found.suite == "only_ping"]
        self.assertTrue(isinstance(named[0].duration_ms, int))


class TheViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """A store of 120 runs of reachable on two inverters, direct inserts: run n is at T0 + n minutes, takes n ms, fails
        every 10th; one no-data result of on_grid, one named-suite run of reachable, one result never timed."""
        cls.conn = fresh()
        cls.addClassCleanup(cls.conn.close)
        for n in range(RUNS):
            results.record(cls.conn, "reachable", (INV1, INV2)[n % 2].asset_id, T0 + timedelta(minutes=n),
                           Result(n % 10 != 0, "x"), duration_ms=n)
        results.record(cls.conn, "on_grid", INV1.asset_id, T0, results.no_data("no records"))
        results.record(cls.conn, "reachable", INV1.asset_id, T0 + timedelta(days=1), Result(True, "named"), "hourly_check", 5)

    def entry(self, name: str) -> project.TestRecord:
        """One test's row of the overview."""
        return next(item for item in project.tests_overview(self.conn) if item.name == name)

    def test_the_overview_counts_the_default_suite_with_no_data_apart(self) -> None:
        reach = self.entry("reachable")
        self.assertEqual((reach.passes, reach.failures, reach.no_data), (108, 12, 0))
        self.assertEqual((reach.assets, reach.last_run, reach.last_duration_ms),
                         ((INV1.asset_id, INV2.asset_id), T0 + timedelta(minutes=RUNS - 1), RUNS - 1))
        self.assertIn(AssetKind.INVERTER, reach.kinds)
        grid = self.entry("on_grid")
        self.assertEqual((grid.passes, grid.failures, grid.no_data, grid.last_duration_ms), (0, 0, 1, None))

    def test_a_test_never_run_reads_empty_and_the_names_are_in_order(self) -> None:
        names = [item.name for item in project.tests_overview(self.conn)]
        self.assertEqual(names, sorted(names))
        idle = self.entry("power_under_rated")
        self.assertEqual((idle.assets, idle.last_run, idle.last_duration_ms, idle.passes, idle.failures, idle.no_data),
                         ((), None, None, 0, 0, 0))
        empty = fresh()
        self.addCleanup(empty.close)
        self.assertEqual({item.name: item.passes for item in project.tests_overview(empty)}.get("reachable"), 0)

    def test_the_log_gives_the_newest_100_of_120_and_deletes_nothing(self) -> None:
        log = project.test_log(self.conn, "reachable")
        self.assertEqual(len(log), 100)
        self.assertEqual(log[0].suite, "hourly_check")  # the named suite's run, a day later, is newest
        self.assertEqual([entry.duration_ms for entry in log[1:4]], [119, 118, 117])
        self.assertEqual([entry.run_at for entry in log], sorted((entry.run_at for entry in log), reverse=True))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM results WHERE test_name = 'reachable'").fetchone()[0],
                         RUNS + 1)
        self.assertEqual(len(project.test_log(self.conn, "reachable", limit=5)), 5)
        self.assertEqual(len(project.test_log(self.conn, "reachable", limit=500)), RUNS + 1)
        self.assertEqual(project.test_log(self.conn, "reachable", limit=0), ())

    def test_a_verdict_is_a_word_and_an_unknown_test_gives_nothing(self) -> None:
        self.assertEqual(project.test_log(self.conn, "on_grid")[0].verdict, "no data")
        self.assertEqual(project.test_log(self.conn, "reachable", 3)[2].verdict, "pass")
        self.assertEqual(project.test_log(self.conn, "nope"), ())


if __name__ == "__main__":
    unittest.main()
