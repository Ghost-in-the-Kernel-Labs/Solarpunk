"""A ticket opens from a failed test result, not from the asset, and one ticket holds a streak of failed results (7.9,
SP-046): the ticket is the corrective work order on the fault telemetry raised for the result, priority from its
code's severity; a failure in the run right after a failure of the same test on the same asset joins that failure's
ticket, a pass or no data ending the streak; opening on a result already in a ticket shows that ticket. Over the OAHE
fleet in a store with no accounts, the engineer one the fleet names."""
import io
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from solarpunk import project
from solarpunk.cli.main import main
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import lookup
from solarpunk.leaf.tickets import TARGETS, priority_of
from solarpunk.remote import results
from solarpunk.workorders import ledger as work_ledger
from solarpunk.workorders import ticket_results

SEN = "OAHE-SEN-001"
ENGINEER = "site@oahe.example"
OPERATOR = "ops@oahe.example"
T = [at(2026, 6, 1, hour) for hour in range(10, 20)]
OPENED = at(2026, 6, 2, 8)


def store() -> sqlite3.Connection:
    """The OAHE fleet in memory."""
    conn = project.open_store()
    project.load_fleet(conn, project.demo_fleet())
    return conn


class Streaks(unittest.TestCase):
    def setUp(self) -> None:
        """The OAHE fleet in memory, no result yet: the weather station's reachable is the test failed below."""
        self.conn = store()
        self.addCleanup(self.conn.close)

    def run_at(self, run_at: datetime, passed: bool, test: str = "reachable", no_data: bool = False) -> int:
        """Records a result and the run's faults as the scheduled run does; gives the result's id."""
        outcome = results.no_data("no records") if no_data else results.Result(passed, "x")
        results.record(self.conn, test, SEN, run_at, outcome)
        project.faults_from_run(self.conn, (SEN,), run_at)
        return self.conn.execute("SELECT max(result_id) FROM results").fetchone()[0]

    def open(self, result_id: int, by: str | None = ENGINEER, recorded_by: str | None = None) -> project.ResultTicket:
        """Opens the ticket for a result as the fleet's engineer: self.open(1) is the ResultTicket opened at 08:00 on 06-02."""
        return project.open_ticket_from_result(self.conn, result_id, OPENED, by, recorded_by)

    def test_a_ticket_opens_on_the_result_with_the_faults_priority_and_links_it(self) -> None:
        first = self.run_at(T[0], False)
        opened = self.open(first)
        self.assertTrue(opened.opened)
        self.assertEqual((opened.ticket.asset_id, opened.ticket.priority, opened.ticket.opened),
                         (SEN, priority_of(lookup("SEN-001").severity), OPENED))
        self.assertEqual(opened.ticket.wo_id, project.work_orders_for(self.conn, SEN)[0].wo_id)
        self.assertEqual([found.result_id for found in opened.results], [first])
        self.assertEqual(project.work_orders_for(self.conn, SEN)[0].fault_id, project.faults_listing(self.conn, True)[0].fault_id)

    def test_a_failure_right_after_a_failure_in_a_ticket_joins_it_and_a_pass_ends_the_streak(self) -> None:
        first = self.run_at(T[0], False)
        order = self.open(first).ticket
        second = self.run_at(T[1], False)
        third = self.run_at(T[2], False)
        self.assertEqual(ticket_results.results_of(self.conn, order.wo_id), (first, second, third))
        self.run_at(T[3], True)
        fourth = self.run_at(T[4], False)  # the pass ended it: no join
        self.assertIsNone(ticket_results.ticket_of(self.conn, fourth))
        self.assertEqual(len(project.work_orders_for(self.conn, SEN)), 1)

    def test_a_closed_ticket_ends_the_streak(self) -> None:
        first = self.run_at(T[0], False)
        order = self.open(first).ticket
        project.write_fault_cause(self.conn, project.work_orders_for(self.conn, SEN)[0].fault_id, "loose cable", ENGINEER, at(2026, 6, 2, 9))
        self.run_at(at(2026, 6, 2, 8), True)  # 13.21: a pass after the failure lets the ticket close
        project.close_work_order(self.conn, order.wo_id, at(2026, 6, 2, 9))
        second = self.run_at(at(2026, 6, 2, 10), False)  # a recurrence: a new fault, no join
        self.assertIsNone(ticket_results.ticket_of(self.conn, second))
        again = self.open(second)
        self.assertTrue(again.opened)
        self.assertEqual([found.result_id for found in again.results], [second])

    def test_a_fault_with_an_open_ticket_shows_that_ticket(self) -> None:
        first = self.run_at(T[0], False)
        fault = project.faults_listing(self.conn, True)[0]
        order = work_ledger.open_corrective(self.conn, SEN, fault.fault_id, T[0], "called in")
        shown = self.open(first)
        self.assertEqual((shown.opened, shown.ticket.wo_id), (False, order.wo_id))
        self.assertEqual(ticket_results.results_of(self.conn, order.wo_id), (first,))

    def test_a_failure_joins_only_a_ticket_the_previous_failure_is_in(self) -> None:
        first = self.run_at(T[0], False)
        second = self.run_at(T[1], False)  # no ticket yet: nothing to join
        self.assertEqual((ticket_results.ticket_of(self.conn, first), ticket_results.ticket_of(self.conn, second)), (None, None))

    def test_another_test_or_asset_is_another_streak(self) -> None:
        first = self.run_at(T[0], False)
        order = self.open(first).ticket
        other = self.run_at(T[1], False, "on_grid")
        self.assertIsNone(ticket_results.ticket_of(self.conn, other))
        self.assertEqual(ticket_results.results_of(self.conn, order.wo_id), (first,))

    def test_no_data_ends_a_streak(self) -> None:
        first = self.run_at(T[0], False)
        self.open(first)
        self.run_at(T[1], False, no_data=True)
        later = self.run_at(T[2], False)
        self.assertIsNone(ticket_results.ticket_of(self.conn, later))

    def test_opening_on_a_failure_in_a_ticket_shows_that_ticket(self) -> None:
        first = self.run_at(T[0], False)
        order = self.open(first).ticket
        second = self.run_at(T[1], False)
        again = self.open(second)
        self.assertEqual((again.opened, again.ticket.wo_id, len(project.work_orders_for(self.conn, SEN))),
                         (False, order.wo_id, 1))

    def test_opening_on_a_later_failure_links_the_unlinked_failures_before_it(self) -> None:
        first, second, third = self.run_at(T[0], False), self.run_at(T[1], False), self.run_at(T[2], False)
        opened = self.open(third)
        self.assertEqual([found.result_id for found in opened.results], [first, second, third])

    def test_a_streak_reaching_a_ticketed_failure_joins_it_and_opens_none(self) -> None:
        first = self.run_at(T[0], False)
        order = self.open(first).ticket
        results.record(self.conn, "reachable", SEN, T[1], results.Result(False, "stored without a run's faults"))
        second = self.conn.execute("SELECT max(result_id) FROM results").fetchone()[0]
        joined = self.open(second)
        self.assertEqual((joined.opened, joined.ticket.wo_id), (False, order.wo_id))
        self.assertEqual(ticket_results.results_of(self.conn, order.wo_id), (first, second))

    def test_a_pass_no_data_unknown_or_faultless_result_is_refused_and_writes_nothing(self) -> None:
        passed = self.run_at(T[0], True)
        gap = self.run_at(T[1], False, no_data=True)
        results.record(self.conn, "reachable", SEN, T[2], results.Result(False, "stored before 7.7"))
        faultless = self.conn.execute("SELECT max(result_id) FROM results").fetchone()[0]
        for result_id, words in ((passed, "pass"), (gap, "no data"), (faultless, "no fault"), (999, "not stored")):
            with self.assertRaisesRegex(project.ResultTicketError, words):
                self.open(result_id)
        self.assertEqual(project.work_orders_for(self.conn, SEN), ())
        self.assertEqual(self.conn.execute("SELECT count(*) FROM ticket_results").fetchone()[0], 0)

    def test_only_an_engineer_the_fleet_names_opens_one(self) -> None:
        first = self.run_at(T[0], False)
        with self.assertRaises(project.UnknownEngineer):
            self.open(first, "nobody@elsewhere.example")
        self.assertEqual(project.work_orders_for(self.conn, SEN), ())

    def test_an_operators_entry_logs_the_engineer_and_the_operators_comment(self) -> None:
        first = self.run_at(T[0], False)
        order = self.open(first, ENGINEER, OPERATOR).ticket
        self.assertEqual([(m.status.value, m.actor) for m in project.ticket_moves(self.conn, order.wo_id)],
                         [("open", ENGINEER)])
        (comment,) = project.ticket_comments(self.conn, order.wo_id)
        self.assertEqual((comment.author, comment.body), (OPERATOR, f"entered on the word of {ENGINEER}"))

    def test_a_result_is_in_at_most_one_ticket_and_nothing_updates_the_table(self) -> None:
        first = self.run_at(T[0], False)
        order = self.open(first).ticket
        with self.assertRaises(sqlite3.IntegrityError):
            ticket_results.link(self.conn, order.wo_id + 1, first)

    def test_a_store_made_before_gains_the_table(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "old.db")
            conn = project.open_or_create(path)
            conn.execute("DROP TABLE ticket_results")
            conn.commit()
            conn.close()
            conn = project.open_or_create(path)
            self.assertEqual(ticket_results.results_of(conn, 1), ())
            conn.close()

    def test_a_failed_diagnostic_carries_the_result_it_opens_from(self) -> None:
        first = self.run_at(T[0], False)
        failing = [d for d in project.asset_detail(self.conn, SEN).diagnostics if d.state == "fail"]
        self.assertEqual([d.result_id for d in failing], [first])


class TargetClock(unittest.TestCase):
    """13.15, SOL-14: a ticket opened from a failed result counts its targets from that result's instant."""

    run_at, open = Streaks.run_at, Streaks.open

    def setUp(self) -> None:
        """The OAHE fleet in memory, no result yet."""
        self.conn = store()
        self.addCleanup(self.conn.close)

    def test_the_targets_count_from_the_failure_and_the_opened_instant_stays(self) -> None:
        first = self.run_at(T[0], False)
        found = self.open(first).ticket
        view = project.view_of(self.conn, found, OPENED)
        priority = priority_of(lookup("SEN-001").severity)
        targets = TARGETS[priority]
        self.assertEqual(found.opened, OPENED)
        self.assertEqual((view.acknowledge_due, view.respond_due), (T[0] + targets.acknowledge, T[0] + targets.respond))
        self.assertEqual(project.target_start(self.conn, found), T[0])

    def test_a_ticket_opened_with_its_fault_starts_at_its_opened_instant_whatever_joins_it(self) -> None:
        project.assign_fault(self.conn, SEN, "SEN-001", T[0], ENGINEER)
        found = project.open_tickets(self.conn)[0]
        later = self.run_at(T[2], False)
        self.open(later)
        self.assertEqual(project.target_start(self.conn, found), T[0])
        self.assertEqual(project.tickets_by_target(self.conn, T[3])[0].acknowledge_due,
                         T[0] + TARGETS[found.priority].acknowledge)

    def test_the_breach_query_counts_from_the_failure_too(self) -> None:
        first = self.run_at(T[0], False)
        found = self.open(first).ticket
        acknowledge = TARGETS[found.priority].acknowledge
        self.assertEqual(project.tickets_past_target(self.conn, T[0] + acknowledge - acknowledge / 100), ())
        (breach,) = [b for b in project.tickets_past_target(self.conn, T[0] + acknowledge * 2) if b.target == "acknowledge"]
        self.assertEqual(breach.ticket.wo_id, found.wo_id)


class TheCommand(unittest.TestCase):
    def setUp(self) -> None:
        """fleet.db with the OAHE fleet and the weather station's reachable failing at 10:00 and 11:00 (results 1, 2)."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "fleet.db")
        conn = project.open_or_create(self.db)
        project.load_fleet(conn, project.demo_fleet())
        for run_at in T[:2]:
            results.record(conn, "reachable", SEN, run_at, results.Result(False, "x"))
            project.faults_from_run(conn, (SEN,), run_at)
        conn.close()

    def run_cli(self, words: list[str]) -> tuple[int, str, str]:
        """One command over the store: (exit code, out, err)."""
        out, err = io.StringIO(), io.StringIO()
        return main(["--db", self.db, *words], out, err), out.getvalue(), err.getvalue()

    def test_open_by_result_opens_then_shows_the_same_ticket_and_show_lists_the_results(self) -> None:
        self.assertEqual(self.run_cli(["ticket", "open", "--result", "2", "--by", ENGINEER, "--at", "2026-06-02T08:00:00+00:00"])[:2],
                         (0, "1 opened on result 2 (2 failed results: 1, 2)\n"))
        self.assertEqual(self.run_cli(["ticket", "open", "--result", "1", "--by", ENGINEER])[:2],
                         (0, "1 already open on result 1 (2 failed results: 1, 2)\n"))
        code, out, _ = self.run_cli(["ticket", "show", "1"])
        self.assertEqual(code, 0)
        self.assertIn("  result 1  reachable  2026-06-01T10:00:00+00:00  x", out)
        self.assertIn("  result 2  reachable  2026-06-01T11:00:00+00:00  x", out)

    def test_a_refusal_is_exit_two_and_names_the_reason(self) -> None:
        code, _, err = self.run_cli(["ticket", "open", "--result", "77", "--by", ENGINEER])
        self.assertEqual(code, 2)
        self.assertTrue(err.endswith("error: result 77 is not stored\n"), err)  # a warning may come before it
        self.assertEqual(self.run_cli(["ticket", "open", "--result", "1"])[0], 2)  # no engineer named


if __name__ == "__main__":
    unittest.main()
