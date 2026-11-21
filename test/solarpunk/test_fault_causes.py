"""A fault's root cause is blank until an engineer writes it (7.8, SP-046): free text, never a list; each writing a new
row with who wrote it and when (and the operator who entered it on the engineer's word), the latest the fault's cause and
an earlier one superseded, never erased; a blank refused; a writer who is no engineer refused; a ticket on the fault closes
only once it is written (9001-10.2.1); a store made before gains the table; `fault cause` and the asset window write it.
Over the OAHE fleet in a store with no accounts, so the engineer is one the fleet names."""
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.cli.main import main
from solarpunk.faults import ledger
from solarpunk.leaf.clock import NotUtc, at
from solarpunk.ui import asset_text
from test.solarpunk.test_ui_suggestions import HAS_TKINTER, display_available

if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import asset_window

INV1 = "OAHE-INV-001"
ENGINEER = "site@oahe.example"
OPERATOR = "ops@oahe.example"
OPENED, WRITTEN, LATER = at(2026, 6, 1, 10), at(2026, 6, 1, 10, 20), at(2026, 6, 1, 11)


def store() -> sqlite3.Connection:
    """The OAHE fleet with one open INV-001 on OAHE-INV-001 (fault 1, its ticket 1) and no cause written."""
    conn = project.open_store()
    project.load_fleet(conn, project.demo_fleet())
    project.assign_fault(conn, INV1, "INV-001", OPENED, ENGINEER)
    return conn


class TheLedger(unittest.TestCase):
    def setUp(self) -> None:
        """A store with fault 1 open and its cause blank."""
        self.conn = store()
        self.addCleanup(self.conn.close)

    def rows(self) -> list[tuple]:
        """Every stored cause row, oldest first: rows() is [] until one is written."""
        return [tuple(row) for row in self.conn.execute("SELECT fault_id, cause, written_by, written_at, recorded_by FROM fault_causes ORDER BY cause_id")]

    def test_a_fault_has_no_cause_until_an_engineer_writes_one(self) -> None:
        self.assertIsNone(ledger.cause_of(self.conn, 1))
        self.assertEqual(ledger.causes_of(self.conn, 1), ())
        written = project.write_fault_cause(self.conn, 1, "worn fuse holder", ENGINEER, WRITTEN)
        self.assertEqual(written, project.FaultCause(1, "worn fuse holder", ENGINEER, WRITTEN, None))
        self.assertEqual(ledger.cause_of(self.conn, 1), written)

    def test_a_later_writing_supersedes_an_earlier_one_without_erasing_it(self) -> None:
        project.write_fault_cause(self.conn, 1, "worn fuse", ENGINEER, WRITTEN)
        project.write_fault_cause(self.conn, 1, "worn fuse holder, found when the cover came off", ENGINEER, LATER)
        self.assertEqual(ledger.cause_of(self.conn, 1).cause, "worn fuse holder, found when the cover came off")
        self.assertEqual([found.cause for found in ledger.causes_of(self.conn, 1)],
                         ["worn fuse", "worn fuse holder, found when the cover came off"])
        self.assertEqual([row[3] for row in self.rows()], [WRITTEN.isoformat(), LATER.isoformat()])

    def test_the_text_is_free_whatever_it_says(self) -> None:
        for words in ("RC-GRID", "somebody left the door open", "  padded  "):
            project.write_fault_cause(self.conn, 1, words, ENGINEER, WRITTEN)
        self.assertEqual([found.cause for found in ledger.causes_of(self.conn, 1)],
                         ["RC-GRID", "somebody left the door open", "padded"])

    def test_a_blank_is_refused_and_writes_nothing(self) -> None:
        for blank in ("", "   ", "\n\t"):
            with self.subTest(blank=blank), self.assertRaises(project.LedgerError):
                project.write_fault_cause(self.conn, 1, blank, ENGINEER, WRITTEN)
        self.assertEqual(self.rows(), [])

    def test_an_unknown_fault_a_naive_instant_and_a_non_engineer_are_refused(self) -> None:
        with self.assertRaises(project.LedgerError):
            project.write_fault_cause(self.conn, 9, "x", ENGINEER, WRITTEN)
        with self.assertRaises(NotUtc):
            project.write_fault_cause(self.conn, 1, "x", ENGINEER, WRITTEN.replace(tzinfo=None))
        with self.assertRaises(project.UnknownEngineer):
            project.write_fault_cause(self.conn, 1, "x", "nobody@example.com", WRITTEN)
        self.assertEqual(self.rows(), [])

    def test_an_operators_entry_on_an_engineers_word_records_both(self) -> None:
        written = project.write_fault_cause(self.conn, 1, "worn fuse holder", ENGINEER, WRITTEN, f" {OPERATOR} ")
        self.assertEqual((written.written_by, written.recorded_by), (ENGINEER, OPERATOR))

    def test_nothing_updates_or_deletes_a_row(self) -> None:
        source = Path(ledger.__file__).read_text() + Path(project.write_fault_cause.__code__.co_filename).read_text()
        self.assertNotIn("UPDATE fault_causes", source)
        self.assertNotIn("DELETE FROM fault_causes", source)


class TheTicket(unittest.TestCase):
    def test_a_ticket_on_a_fault_closes_only_once_the_cause_is_written(self) -> None:
        conn = store()
        self.addCleanup(conn.close)
        with self.assertRaises(project.NoRootCause) as caught:
            project.resolve_ticket(conn, 1, "fuse swapped", LATER)
        self.assertEqual(str(caught.exception), "fault 1 has no root cause written: an engineer writes it before its ticket closes")
        self.assertEqual((project.ticket_of(conn, 1).status, project.ticket_moves(conn, 1)), (project.TicketStatus.OPEN, ()))
        self.assertEqual(len(project.faults_listing(conn, True)), 1)
        project.write_fault_cause(conn, 1, "worn fuse holder", ENGINEER, WRITTEN)
        self.assertIs(project.resolve_ticket(conn, 1, "fuse swapped", LATER).status, project.TicketStatus.CLOSED)
        self.assertEqual(project.faults_listing(conn, True), ())

    def test_a_preventive_ticket_has_no_fault_and_closes_without_one(self) -> None:
        conn = store()
        self.addCleanup(conn.close)
        order = project.open_preventive_work_order(conn, INV1, OPENED, "clean the filters")
        self.assertIs(project.resolve_ticket(conn, order.wo_id, "cleaned", LATER).status, project.TicketStatus.CLOSED)


class AnOldStore(unittest.TestCase):
    def test_a_store_made_before_gains_the_table_and_keeps_its_codes_as_text(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "old.db"
        old = project.open_store(path)
        old.execute("DROP TABLE fault_causes")
        project.load_fleet(old, project.demo_fleet())
        project.assign_fault(old, INV1, "INV-001", OPENED, ENGINEER)
        old.execute("UPDATE work_orders SET closed = ?, status = 'closed', root_cause = 'RC-GRID'", (LATER.isoformat(),))
        old.commit()
        old.close()
        conn = project.open_or_create(path)
        self.addCleanup(conn.close)
        self.assertEqual(project.work_orders_for(conn, INV1)[0].root_cause, "RC-GRID")
        self.assertIsNone(ledger.cause_of(conn, 1))
        self.assertEqual(project.write_fault_cause(conn, 1, "the grid tripped", ENGINEER, WRITTEN).cause, "the grid tripped")


class TheCommand(unittest.TestCase):
    def test_fault_cause_writes_and_a_later_one_supersedes(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        db = str(Path(folder.name) / "fleet.db")
        conn = project.open_or_create(db)
        project.load_fleet(conn, project.demo_fleet())
        project.assign_fault(conn, INV1, "INV-001", OPENED, ENGINEER)
        conn.close()

        def run(words: list[str]) -> tuple[int, str, str]:
            """One command over the store: run(["fault", "cause", "1", "melted", "--by", ENGINEER]) is (0, "1 cause melted …", "")."""
            out, err = io.StringIO(), io.StringIO()
            code = main(["--db", db, *words], out, err)
            return code, out.getvalue(), err.getvalue()

        code, out, _ = run(["fault", "cause", "1", "worn", "fuse", "holder", "--by", ENGINEER, "--at", WRITTEN.isoformat()])
        self.assertEqual((code, out), (0, f"1 cause worn fuse holder by {ENGINEER} at {WRITTEN.isoformat()}\n"))
        code, out, _ = run(["fault", "cause", "1", "melted", "--by", ENGINEER, "--recorded-by", OPERATOR, "--at", LATER.isoformat()])
        self.assertEqual((code, out),
                         (0, f"1 cause melted by {ENGINEER} entered by {OPERATOR} at {LATER.isoformat()}\n"))
        code, _, err = run(["fault", "cause", "1", " ", "--by", ENGINEER])
        self.assertEqual(code, 2)
        self.assertIn("root cause", err)
        code, _, err = run(["fault", "cause", "1", "x", "--by", "nobody@example.com"])
        self.assertEqual(code, 2)
        conn = project.open_or_create(db)
        self.addCleanup(conn.close)
        self.assertEqual([found.cause for found in ledger.causes_of(conn, 1)], ["worn fuse holder", "melted"])


class TheWords(unittest.TestCase):
    def test_the_window_shows_the_cause_or_says_it_is_not_written(self) -> None:
        conn = store()
        self.addCleanup(conn.close)
        self.assertEqual(asset_text.fault_lines(project.asset_detail(conn, INV1))[0][4], "not written")
        project.write_fault_cause(conn, 1, "worn fuse holder", ENGINEER, WRITTEN)
        self.assertEqual(asset_text.fault_lines(project.asset_detail(conn, INV1))[0][4], "worn fuse holder")


@unittest.skipUnless(HAS_TKINTER and display_available(), "no tkinter or no display")
class TheWindow(unittest.TestCase):
    def test_the_box_writes_the_selected_faults_cause_as_free_text(self) -> None:
        conn = store()
        self.addCleanup(conn.close)
        root = tkinter.Tk()
        self.addCleanup(root.destroy)
        root.withdraw()
        changes: list[int] = []
        window = asset_window.AssetWindow(root, conn, INV1, lambda: changes.append(1))
        window.cause_box.insert(0, "worn fuse holder")
        window.cause_button.invoke()  # no engineer chosen where one is asked: refused, nothing written
        self.assertEqual(ledger.causes_of(conn, 1), ())
        window.assigned_by_box.set(ENGINEER)
        window.cause_button.invoke()
        self.assertEqual(ledger.cause_of(conn, 1).cause, "worn fuse holder")
        self.assertEqual(window.cause_box.get(), "")
        self.assertEqual(window.fault_tree.item("1", "values")[4], "worn fuse holder")
        self.assertEqual(changes, [1])
        window.cause_button.invoke()  # a blank is refused in the message line
        self.assertTrue(window.message.cget("text").startswith("Refused:"))
        self.assertEqual(len(ledger.causes_of(conn, 1)), 1)


if __name__ == "__main__":
    unittest.main()
