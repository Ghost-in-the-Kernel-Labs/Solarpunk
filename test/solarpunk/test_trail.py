"""The closed trail read back (13.17, SP-053): from a failed result to a closed ticket (open from the result, comment, two
causes, a passing re-run, resolve), project.ticket_trail holds every part, trail_text words it, `ticket show` prints it,
and an engineer's fault has the empty parts. Over the OAHE fleet in memory, the weather station's reachable."""
import io
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from solarpunk import project
from solarpunk.cli.main import main
from solarpunk.leaf.clock import at
from solarpunk.remote import results

SEN = "OAHE-SEN-001"
ENGINEER = "site@oahe.example"
OPERATOR = "ops@oahe.example"
REACHABLE_CLAUSES = next(found.clauses for found in project.remote_tests() if found.name == "records_stored")
FAILED, OPENED, COMMENTED, CAUSED, CORRECTED, PASSED, RESOLVED = (at(2026, 6, 1, hour) for hour in (10, 11, 12, 13, 14, 15, 16))


def run_at(conn: sqlite3.Connection, moment: datetime, passed: bool) -> int:
    """Records reachable on the weather station as the scheduled run does and gives the result's id."""
    results.record(conn, "reachable", SEN, moment, results.Result(passed, "x" if not passed else "ok"))
    project.faults_from_run(conn, (SEN,), moment)
    return conn.execute("SELECT max(result_id) FROM results").fetchone()[0]


def closed_ticket(db: str) -> int:
    """Walks a store at db from a failed result to a closed ticket and returns its id."""
    conn = project.open_or_create(db)
    project.load_fleet(conn, project.demo_fleet())
    failed = run_at(conn, FAILED, False)
    opened = project.open_ticket_from_result(conn, failed, OPENED, ENGINEER)
    wo_id = opened.ticket.wo_id
    project.comment_on_ticket(conn, wo_id, OPERATOR, COMMENTED, "crew on the way")
    fault_id = project.work_orders_for(conn, SEN)[0].fault_id
    project.write_fault_cause(conn, fault_id, "loose antenna", ENGINEER, CAUSED)
    project.write_fault_cause(conn, fault_id, "antenna cable corroded", ENGINEER, CORRECTED)
    run_at(conn, PASSED, True)  # 13.21: the proof stored before the close
    project.resolve_ticket(conn, wo_id, "cable replaced", RESOLVED, actor=ENGINEER)
    conn.close()
    return wo_id


class TheTrail(unittest.TestCase):
    def setUp(self) -> None:
        """A file store walked to a closed ticket."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "fleet.db")
        self.wo_id = closed_ticket(self.db)
        self.conn = project.open_or_create(self.db)
        self.addCleanup(self.conn.close)
        self.trail = project.ticket_trail(self.conn, self.wo_id)

    def test_the_fault_and_who_assigned_it(self) -> None:
        fault = self.trail.fault
        self.assertEqual((fault.code, fault.assigned_by, fault.recorded_by), ("SEN-001", "test:reachable", None))
        self.assertIsNotNone(fault.closed)

    def test_every_cause_with_author_and_instant_the_newest_standing(self) -> None:
        shown = [(held.cause.cause, held.cause.written_by, held.cause.written_at, held.stands) for held in self.trail.causes]
        self.assertEqual(shown, [("loose antenna", ENGINEER, CAUSED, False), ("antenna cable corroded", ENGINEER, CORRECTED, True)])

    def test_the_comments_moves_and_closeout(self) -> None:
        self.assertEqual([(held.author, held.moment, held.body) for held in self.trail.comments],
                         [(OPERATOR, COMMENTED, "crew on the way")])
        self.assertEqual([(held.status.value, held.actor) for held in self.trail.moves][-3:],
                         [("in progress", ENGINEER), ("resolved", ENGINEER), ("closed", ENGINEER)])
        self.assertEqual(self.trail.closeout, "cable replaced")

    def test_the_failed_result_its_clauses_and_the_next_result(self) -> None:
        (held,) = self.trail.results
        self.assertEqual((held.result.test_name, held.result.run_at, held.result.failed), ("reachable", FAILED, True))
        self.assertEqual(held.clauses, REACHABLE_CLAUSES)
        self.assertTrue(held.clauses)
        self.assertEqual((held.next_result.run_at, held.next_result.passed), (PASSED, True))

    def test_a_failure_with_no_later_result_has_no_next(self) -> None:
        later = project.ticket_trail(self.conn, self.wo_id)
        self.conn.execute("DELETE FROM results WHERE run_at = ?", (PASSED.isoformat(),))
        self.assertIsNone(project.ticket_trail(self.conn, self.wo_id).results[0].next_result)
        self.assertIsNotNone(later.results[0].next_result)

    def test_the_text_has_every_heading_and_part(self) -> None:
        text = project.trail_text(self.trail)
        self.assertEqual([line for line in text.splitlines() if not line.startswith(" ")],
                         ["Fault", "Causes", "Comments", "Moves", "Closeout", "Results"])
        for words in ("assigned by test:reachable", f"{CORRECTED.isoformat()}  {ENGINEER}  antenna cable corroded  (stands)",
                      f"{COMMENTED.isoformat()}  {OPERATOR}  crew on the way", f"closed {RESOLVED.isoformat()}  cable replaced",
                      "clauses ", f"next result 2  {PASSED.isoformat()}  pass  ok"):
            self.assertIn(words, text)

    def test_show_prints_the_trail(self) -> None:
        out = io.StringIO()
        self.assertEqual(main(["--db", self.db, "ticket", "show", str(self.wo_id)], out, io.StringIO()), 0)
        self.assertIn(project.trail_text(self.trail), out.getvalue())
        self.assertTrue(out.getvalue().startswith(f"{self.wo_id}  {SEN}"))

    def test_the_tests_overview_carries_the_clauses(self) -> None:
        record = next(found for found in project.tests_overview(self.conn) if found.name == "reachable")
        self.assertEqual(record.clauses, REACHABLE_CLAUSES)


class AnEngineersFault(unittest.TestCase):
    def test_a_ticket_from_a_called_in_fault_has_empty_results_and_no_cause_yet(self) -> None:
        conn = project.open_store()
        self.addCleanup(conn.close)
        project.load_fleet(conn, project.demo_fleet())
        project.assign_fault(conn, "OAHE-INV-002", "INV-001", at(2026, 6, 1, 11, 30), ENGINEER)
        trail = project.ticket_trail(conn, 1)
        self.assertEqual((trail.fault.assigned_by, trail.causes, trail.comments, trail.results, trail.closeout),
                         (ENGINEER, (), (), (), None))
        text = project.trail_text(trail)
        self.assertIn("Closeout\n  not closed", text)
        self.assertTrue(text.endswith("Results\n  none"))

    def test_an_unknown_ticket_is_refused(self) -> None:
        conn = project.open_store()
        self.addCleanup(conn.close)
        with self.assertRaises(project.WorkOrderError):
            project.ticket_trail(conn, 9)


if __name__ == "__main__":
    unittest.main()
