"""No data is not a pass (12.9, SP-039 calls 0 and 4): a remote test with no stored record that is not a gap has nothing
to check, so `reachable` fails it, a disconnection, and every other test returns the third result, no data, which the
results table stores, the status, the suggestions, the mail's cause, the runs and the windows' words read as neither a
pass nor a failure. A window of real records with none of the kind a test needs is judged, not no data. A store made
before 12.9 keeps opening, its rows read as the pass or fail they were."""
import io
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetStatus
from solarpunk.leaf.telemetry import gap
from solarpunk.project.field import Baseline, DayResult, tallies
from solarpunk.project.run import cause_of
from solarpunk.project.runs import Run, matches
from solarpunk.remote import results, run
from solarpunk.remote.results import NotAVerdict, Recorded, Result, no_data, nothing_to_check
from solarpunk.remote.tests import (irradiance_in_range, night_power_near_zero, on_grid, performance_above_floor,
                                    power_not_frozen, power_under_rated, records_stored)
from solarpunk.ui import asset_text, runs_text, timeline
from test.solarpunk.test_remote import INV1, SEN, T0, T1, UNRATED, fresh, reading

NIGHT = at(2026, 6, 1, 2, 0)
GAPS = (gap(INV1.asset_id, T0), gap(INV1.asset_id, T1))
NOTHING = Result(False, "no records", no_data=True)
TWO_GAPS = Result(False, "no records: 2 gaps", no_data=True)
# Every remote test but records_stored, each over an inverter (irradiance_in_range and on_grid run on the sensor too).
OTHERS = (irradiance_in_range, night_power_near_zero, on_grid, performance_above_floor, power_not_frozen,
          power_under_rated)


class TheThirdResult(unittest.TestCase):
    def test_no_data_is_neither_a_pass_nor_a_failure(self) -> None:
        self.assertEqual(no_data("no records"), NOTHING)
        self.assertEqual((NOTHING.passed, NOTHING.failed), (False, False))
        self.assertEqual((Result(True, "x").failed, Result(False, "x").failed), (False, True))

    def test_a_result_cannot_pass_with_no_data(self) -> None:
        with self.assertRaises(NotAVerdict):
            Result(True, "3 records", no_data=True)

    def test_nothing_to_check(self) -> None:
        self.assertEqual(nothing_to_check(()), "no records")
        self.assertEqual(nothing_to_check(GAPS), "no records: 2 gaps")
        self.assertIsNone(nothing_to_check(GAPS + (reading(INV1, at(2026, 6, 1, 10, 10), None, None),)))


class TheTests(unittest.TestCase):
    def test_records_stored_fails_when_every_record_is_a_gap(self) -> None:
        """SP-039 call 4: J-101's six empty channels passed because a gap counted as a record."""
        self.assertEqual(records_stored.run(INV1, GAPS), Result(False, "no records: 2 gaps"))
        self.assertEqual(records_stored.run(INV1, ()), Result(False, "no records"))
        self.assertEqual(records_stored.run(INV1, (reading(INV1, T0, 800.0, 60.0), gap(INV1.asset_id, T1))),
                         Result(True, "2 records"))

    def test_every_other_test_has_no_data_over_nothing_or_gaps(self) -> None:
        for module in OTHERS:
            with self.subTest(test=module.__name__):
                self.assertEqual(module.run(INV1, ()), NOTHING)
                self.assertEqual(module.run(INV1, GAPS), TWO_GAPS)
        for module in (irradiance_in_range, on_grid):
            with self.subTest(sensor=module.__name__):
                self.assertEqual(module.run(SEN, ()), NOTHING)

    def test_a_day_with_none_of_the_kind_a_test_needs_is_judged(self) -> None:
        """An overcast day is no daylight record and a night with no record is no night record: both pass as before,
        never no data, or an overcast day would read as a disconnection."""
        overcast = (reading(INV1, T0, 120.0, 10.0), gap(INV1.asset_id, T1))
        self.assertEqual(performance_above_floor.run(INV1, overcast), Result(True, "no daylight records"))
        self.assertEqual(night_power_near_zero.run(INV1, overcast), Result(True, "0 night records near zero"))
        no_power = (reading(SEN, T0, 300.0, None),)
        self.assertEqual(power_under_rated.run(INV1, no_power), Result(True, "1 records at or under rated 100.0 kW + 1%"))
        self.assertEqual(irradiance_in_range.run(INV1, (reading(INV1, NIGHT, None, 0.0),)),
                         Result(True, "0 irradiance readings in range"))

    def test_no_rating_still_fails_first(self) -> None:
        self.assertEqual(power_under_rated.run(UNRATED, ()), Result(False, "no rating"))


class TheTable(unittest.TestCase):
    def test_no_data_is_stored_and_read_after_the_failures(self) -> None:
        conn = fresh()
        self.addCleanup(conn.close)
        results.record(conn, "on_grid", SEN.asset_id, T1, NOTHING)
        results.record(conn, "reachable", SEN.asset_id, T1, Result(False, "no records"))
        results.record(conn, "zz_pass", SEN.asset_id, T1, Result(True, "fine"))
        self.assertEqual(conn.execute("SELECT passed, no_data FROM results WHERE test_name = 'on_grid'").fetchone()[:],
                         (0, 1))
        self.assertEqual(results.latest_for(conn, SEN.asset_id), (
            Recorded("reachable", SEN.asset_id, T1, False, "no records"),
            Recorded("on_grid", SEN.asset_id, T1, False, "no records", True),
            Recorded("zz_pass", SEN.asset_id, T1, True, "fine"),
        ))

    def test_a_store_made_before_keeps_its_rows_as_pass_or_fail(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "old.db"
        conn = project.open_or_create(path)
        project.load_fleet(conn, project.demo_fleet())
        results.record(conn, "reachable", SEN.asset_id, T0, Result(False, "no records"))
        results.record(conn, "on_grid", SEN.asset_id, T0, Result(True, "0 records on the grid and in range"))
        conn.execute("ALTER TABLE results DROP COLUMN no_data")  # as a store made before 12.9 was
        conn.commit()
        conn.close()
        reopened = project.open_or_create(path)
        self.addCleanup(reopened.close)
        self.assertEqual([(r.test_name, r.passed, r.no_data) for r in results.latest_for(reopened, SEN.asset_id)],
                         [("reachable", False, False), ("on_grid", True, False)])
        results.record(reopened, "on_grid", SEN.asset_id, T1, NOTHING)
        self.assertTrue(results.latest_for(reopened, SEN.asset_id)[0].no_data)
        again = project.open_or_create(path)  # a second opening changes nothing
        self.addCleanup(again.close)
        self.assertEqual([row[1] for row in again.execute("PRAGMA table_info(results)")].count("no_data"), 1)


class TheReaders(unittest.TestCase):
    def setUp(self) -> None:
        """The demo fleet in a store of its own, no result stored: asset_status(OAHE-SEN-001) is GREEN."""
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        project.load_fleet(self.conn, project.demo_fleet())

    def record(self, name: str, result: Result) -> None:
        """Stores one result on the sensor at 10:05: record("on_grid", NOTHING) leaves it no data."""
        results.record(self.conn, name, SEN.asset_id, T1, result)

    def test_no_data_alone_is_no_failure_and_raises_no_fault(self) -> None:
        self.record("on_grid", NOTHING)
        self.assertIs(project.asset_status(self.conn, SEN.asset_id), AssetStatus.GREEN)
        self.assertEqual(project.faults_from_run(self.conn, (SEN.asset_id,), T1), ())
        self.assertIs(run.status_of(False, (NOTHING,)), AssetStatus.GREEN)

    def test_the_colour_and_the_cause_come_from_records_stored_failure(self) -> None:
        self.record("irradiance_in_range", NOTHING)
        self.record("records_stored", Result(False, "no records"))
        self.assertIs(project.asset_status(self.conn, SEN.asset_id), AssetStatus.YELLOW)
        self.assertEqual(cause_of(self.conn, SEN.asset_id, {}).test_name, "records_stored")
        self.assertEqual([(f.code, f.assigned_by) for f in project.faults_from_run(self.conn, (SEN.asset_id,), T1)],
                         [("SEN-001", "test:records_stored")])  # SP-046
        self.assertEqual([(d.test_name, d.state) for d in project.asset_detail(self.conn, SEN.asset_id).diagnostics],
                         [("records_stored", "fail"), ("irradiance_in_range", "no data"), ("on_grid", "not run")])
        row = next(found for found in project.asset_rows(self.conn) if found.asset_id == SEN.asset_id)
        self.assertEqual(row.failing, "records_stored")

    def test_the_runs_read_no_data_apart(self) -> None:
        self.record("on_grid", NOTHING)
        (found,) = project.asset_runs(self.conn, SEN.asset_id)
        self.assertFalse(found.failed)
        self.assertTrue(matches(found.results[0], "no data"))
        self.assertFalse(matches(found.results[0], "pass") or matches(found.results[0], "fail"))


class TheWords(unittest.TestCase):
    def test_the_runs_window_never_says_all_passed_over_no_data(self) -> None:
        empty = Recorded("on_grid", SEN.asset_id, T1, False, "no records", True)
        passed = Recorded("reachable", SEN.asset_id, T1, True, "3 records")
        failed = Recorded("reachable", SEN.asset_id, T1, False, "no records")
        self.assertEqual(runs_text.run_line(Run(SEN.asset_id, T1, (empty, passed)))[2], "1 no data")
        self.assertEqual(runs_text.run_line(Run(SEN.asset_id, T1, (failed, empty)))[2], "1 failed")
        self.assertEqual(runs_text.run_line(Run(SEN.asset_id, T1, (passed,)))[2], "all passed")
        self.assertEqual(runs_text.result_line(empty), ("on_grid", "no data", "no records"))

    def test_the_timeline_marks_no_data_grey(self) -> None:
        empty = Recorded("on_grid", SEN.asset_id, T1, False, "no records", True)
        failed = Recorded("reachable", SEN.asset_id, T1, False, "no records")
        marks = timeline.marks((Run(SEN.asset_id, T1, (failed, empty)),))
        self.assertEqual([(m.row, m.colour) for m in marks],
                         [(0, timeline.NO_DATA_COLOUR), (1, timeline.FAIL_COLOUR)])
        self.assertNotEqual(timeline.NO_DATA_COLOUR, timeline.PASS_COLOUR)

    def test_the_asset_window_draws_no_data_grey(self) -> None:
        self.assertEqual(asset_text.STATE_WORDS["no data"], "no data")
        self.assertEqual(asset_text.row_tags(("on_grid", "no data", "no records")), (asset_text.NOT_RUN_TAG,))
        self.assertEqual(asset_text.row_tags(("reachable", "FAIL", "no records")), (asset_text.FAILING_TAG,))


class TheBaselineAndTheCommandLine(unittest.TestCase):
    def test_a_day_of_no_data_is_no_alarm(self) -> None:
        day = T0.date()
        found = (DayResult("on_grid", SEN.asset_id, day, False, "no records", True),
                 DayResult("reachable", SEN.asset_id, day, False, "no records"))
        self.assertEqual(Baseline(tallies(found), found).alarms(), (found[1],))
        self.assertEqual([(t.test, t.days_alarmed) for t in tallies(found)], [("on_grid", 0), ("reachable", 1)])

    def test_the_command_line_says_no_data(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "store.db"
            conn = project.open_or_create(path)
            project.load_fleet(conn, project.demo_fleet())
            conn.close()
            out = io.StringIO()
            self.assertEqual(run.main(["on_grid", SEN.asset_id, "--db", str(path)], out), run.NO_DATA_EXIT)
            self.assertEqual(out.getvalue(), "no data no records\n")


if __name__ == "__main__":
    unittest.main()
