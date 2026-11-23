"""The proof follows the action (13.21, SP-055): a ticket opened from a failed result resolves only after a later pass of the
same test on the same asset, the refusal naming both, from project and the command line alike, after the root-cause refusal
and never for an engineer's fault; the demo's revival is stamped a minute after the asset's last ticket act. The
CONTRACT's hand-checked example over the weather station's reachable: failed 13:00, resolve 13:20 refused, pass 13:25,
resolve 13:30 closes."""
import io
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from solarpunk import project
from solarpunk.cli.main import main
from solarpunk.leaf.clock import at
from solarpunk.remote import results
from solarpunk.ui import demo

SEN = "OAHE-SEN-001"
ENGINEER = "site@oahe.example"
FAILED, OPENED, CAUSED, REFUSED, PASSED, CLOSED = (at(2026, 6, 1, 13, minute) for minute in (0, 5, 10, 20, 25, 30))
WAITS = ("ticket 1 waits for a pass: reachable on OAHE-SEN-001 has not passed since its failure at "
         "2026-06-01T13:00:00+00:00")


def run_at(conn: sqlite3.Connection, moment: datetime, passed: bool) -> int:
    """Records reachable on the weather station as the scheduled run does and gives the result's id."""
    results.record(conn, "reachable", SEN, moment, results.Result(passed, "ok" if passed else "x"))
    project.faults_from_run(conn, (SEN,), moment)
    return conn.execute("SELECT max(result_id) FROM results").fetchone()[0]


class TheProof(unittest.TestCase):
    def setUp(self) -> None:
        """A file store with ticket 1 opened at 13:05 on reachable failed at 13:00; the cause is not yet written."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "fleet.db")
        self.conn = project.open_or_create(self.db)
        self.addCleanup(self.conn.close)
        project.load_fleet(self.conn, project.demo_fleet())
        self.wo_id = project.open_ticket_from_result(self.conn, run_at(self.conn, FAILED, False), OPENED, ENGINEER).ticket.wo_id
        self.fault_id = project.work_orders_for(self.conn, SEN)[0].fault_id

    def cause(self) -> None:
        """Writes the fault's root cause at 13:10."""
        project.write_fault_cause(self.conn, self.fault_id, "loose antenna", ENGINEER, CAUSED)

    def test_the_hand_checked_example_refused_then_closed_after_a_pass(self) -> None:
        self.cause()
        with self.assertRaises(project.NoPassSince) as caught:
            project.resolve_ticket(self.conn, self.wo_id, "cable replaced", REFUSED)
        self.assertEqual(str(caught.exception), WAITS)
        self.assertEqual(project.ticket_moves(self.conn, self.wo_id)[-1].status.value, "open")  # nothing written
        run_at(self.conn, PASSED, True)
        closed = project.resolve_ticket(self.conn, self.wo_id, "cable replaced", CLOSED)
        self.assertEqual(closed.status, project.TicketStatus.CLOSED)

    def test_the_root_cause_is_refused_first(self) -> None:
        with self.assertRaises(project.NoRootCause):
            project.resolve_ticket(self.conn, self.wo_id, "x", REFUSED)

    def test_a_pass_at_the_failures_instant_or_a_later_failure_is_not_proof(self) -> None:
        self.cause()
        results.record(self.conn, "reachable", SEN, FAILED, results.Result(True, "same instant"))
        run_at(self.conn, PASSED, False)
        with self.assertRaises(project.NoPassSince):
            project.resolve_ticket(self.conn, self.wo_id, "x", CLOSED)

    def test_a_ticket_from_an_engineers_fault_needs_no_pass(self) -> None:
        order = project.assign_fault(self.conn, "OAHE-INV-001", "INV-001", OPENED, ENGINEER)
        project.write_fault_cause(self.conn, order.fault_id, "worn fuse", ENGINEER, CAUSED)
        wo_id = project.work_orders_for(self.conn, "OAHE-INV-001")[0].wo_id
        self.assertEqual(project.resolve_ticket(self.conn, wo_id, "swapped", CLOSED).status, project.TicketStatus.CLOSED)

    def test_the_command_line_refuses_with_exit_2_and_writes_nothing(self) -> None:
        self.cause()
        out, err = io.StringIO(), io.StringIO()
        code = main(["--db", self.db, "ticket", "resolve", "1", "--done", "x", "--by", ENGINEER, "--at", REFUSED.isoformat()], out, err)
        self.assertEqual((code, err.getvalue()), (2, f"error: {WAITS}\n"))
        self.assertEqual([move.status.value for move in project.ticket_moves(self.conn, self.wo_id)], ["open"])

    def test_the_last_act_is_the_latest_move_comment_or_cause_and_the_revival_follows_it(self) -> None:
        self.assertEqual(project.last_ticket_act(self.conn, SEN), OPENED)
        self.cause()
        project.comment_on_ticket(self.conn, self.wo_id, ENGINEER, at(2026, 6, 1, 13, 55), "late note")
        self.assertEqual(project.last_ticket_act(self.conn, SEN), at(2026, 6, 1, 13, 55))
        self.assertIsNone(project.last_ticket_act(self.conn, "OAHE-INV-001"))
        revival = demo.Revival(5021, lambda: at(2026, 6, 1, 13, 5))
        self.assertEqual(revival.run_instant(project.last_ticket_act(self.conn, SEN)), at(2026, 6, 1, 13, 56))
        self.assertEqual(revival.run_instant(None), at(2026, 6, 1, 13, 56) + timedelta(seconds=1))


if __name__ == "__main__":
    unittest.main()
