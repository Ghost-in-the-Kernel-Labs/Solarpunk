"""The ticket commands (11.2, SOL-14): `ticket list` (the nearest target first, a breach marked, none open said so),
`ticket ack`, `ticket comment` and `ticket resolve` (which closes the fault), each at --at; a refusal is exit 2 with
"error: …" and changes nothing. Over a file store holding the OAHE fleet and two outages."""
import io
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.cli.main import main
from solarpunk.leaf.clock import at

ENGINEER = "site@oahe.example"


class TheCommands(unittest.TestCase):
    def setUp(self) -> None:
        """fleet.db with the OAHE fleet, an INV-001 on OAHE-INV-002 at 11:30 (ticket 1) and one on OAHE-INV-001 at
        12:00 (ticket 2)."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "fleet.db")
        conn = project.open_or_create(self.db)
        project.load_fleet(conn, project.demo_fleet())
        project.assign_fault(conn, "OAHE-INV-002", "INV-001", at(2026, 6, 1, 11, 30), ENGINEER)
        project.assign_fault(conn, "OAHE-INV-001", "INV-001", at(2026, 6, 1, 12), ENGINEER)
        conn.close()

    def cause(self, fault_id: str, words: str) -> None:
        """Writes a fault's root cause through the command line as the fixtures' engineer, 12:10 on 2026-06-01."""
        code, _, _ = self.run_cli(["fault", "cause", fault_id, *words.split(), "--by", ENGINEER, "--at", "2026-06-01T12:10:00+00:00"])
        self.assertEqual(code, 0)

    def run_cli(self, words: list[str]) -> tuple[int, str, str]:
        """One command over the store: (exit code, out, err)."""
        out, err = io.StringIO(), io.StringIO()
        code = main(["--db", self.db, *words], out, err)
        return code, out.getvalue(), err.getvalue()

    def test_list_puts_the_nearest_target_first_and_marks_a_breach(self) -> None:
        code, out, _ = self.run_cli(["ticket", "list", "--at", "2026-06-01T12:45:00+00:00"])
        first, second = out.splitlines()
        self.assertEqual(code, 0)
        self.assertTrue(first.startswith("1  OAHE-INV-002  P1  open  acknowledge overdue (due 2026-06-01T12:30:00+00:00)"))
        self.assertTrue(first.endswith("PAST TARGET"))
        self.assertTrue(second.startswith("2  OAHE-INV-001  P1  open  acknowledge pending (due 2026-06-01T13:00:00+00:00)"))
        self.assertFalse(second.endswith("PAST TARGET"))

    def test_ack_comment_and_resolve(self) -> None:
        self.assertEqual(self.run_cli(["ticket", "ack", "2", "--at", "2026-06-01T12:40:00+00:00"])[:2],
                         (0, "2 acknowledged\n"))
        self.assertEqual(self.run_cli(["ticket", "comment", "2", "--by", ENGINEER, "on", "my", "way",
                                      "--at", "2026-06-01T12:41:00+00:00"])[:2], (0, f"2 comment 1 by {ENGINEER}\n"))
        self.cause("2", "worn fuse holder")
        code, out, _ = self.run_cli(["ticket", "resolve", "2", "--done", "fuse", "swapped",
                                    "--at", "2026-06-01T14:00:00+00:00"])
        self.assertEqual((code, out), (0, "2 closed\n"))
        conn = project.open_or_create(self.db)
        self.addCleanup(conn.close)
        self.assertEqual(list(project.open_outages(conn)), ["OAHE-INV-002"])
        self.assertEqual(project.ticket_of(conn, 2).evidence, "fuse swapped")
        self.assertEqual([c.body for c in project.ticket_comments(conn, 2)], ["on my way"])

    def test_refusals_are_exit_2_and_change_nothing(self) -> None:
        code, _, err = self.run_cli(["ticket", "resolve", "1", "--done", "x"])
        self.assertEqual((code, err), (2, "error: fault 1 has no root cause written: an engineer writes it before its ticket closes\n"))
        self.assertEqual(self.run_cli(["ticket", "show", "1"])[1].count("\n"), 1)  # no move was logged
        code, _, err = self.run_cli(["ticket", "comment", "1", "--by", " ", "x"])
        self.assertEqual(code, 2)
        self.run_cli(["ticket", "ack", "1", "--at", "2026-06-01T12:00:00+00:00"])
        code, _, err = self.run_cli(["ticket", "ack", "1", "--at", "2026-06-01T12:05:00+00:00"])
        self.assertEqual((code, err), (2, "error: a ticket cannot move from acknowledged to acknowledged\n"))
        conn = project.open_or_create(self.db)
        self.addCleanup(conn.close)
        self.assertEqual(project.ticket_of(conn, 1).acknowledged, at(2026, 6, 1, 12))

    def test_none_open_is_said(self) -> None:
        for wo_id in ("1", "2"):
            self.cause(wo_id, "the grid tripped")
            self.run_cli(["ticket", "resolve", wo_id, "--done", "x", "--at", "2026-06-01T15:00:00+00:00"])
        self.assertEqual(self.run_cli(["ticket", "list"])[1], "no open ticket\n")

    def test_the_help_lists_the_commands(self) -> None:
        out = self.run_cli(["help"])[1]
        for line in ("ticket list", "ticket ack ID", "ticket comment ID WORDS", "ticket resolve ID --done WORDS", "fault cause FAULT_ID TEXT"):
            self.assertIn(line, out)

    def test_show_prints_the_line_and_each_move_of_any_status(self) -> None:
        self.run_cli(["ticket", "ack", "2", "--at", "2026-06-01T12:40:00+00:00"])
        code, out, err = self.run_cli(["ticket", "show", "2", "--at", "2026-06-01T12:45:00+00:00"])
        line, first, *rest = out.splitlines()
        self.assertEqual((code, err, rest), (0, "", []))
        self.assertTrue(line.startswith("2  OAHE-INV-001  P1  acknowledged"))
        self.assertEqual(first, "  2026-06-01T12:40:00+00:00  acknowledged  nobody signed in")
        self.cause("2", "worn fuse holder")
        self.run_cli(["ticket", "resolve", "2", "--done", "x", "--at", "2026-06-01T14:00:00+00:00"])
        closed = self.run_cli(["ticket", "show", "2"])[1].splitlines()
        self.assertEqual((closed[0].split("  ")[3], len(closed)), ("closed", 5))
        self.assertEqual(self.run_cli(["ticket", "show", "9"])[0], 2)


if __name__ == "__main__":
    unittest.main()
