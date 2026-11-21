"""A ticket's every move on record (12.4, SOL-14, SOL-16, SP-035): each move, the close included, appends one row to the
ticket's history with the status, the instant and the account that made it (none where nobody is signed in), in the
move's own transaction, so a refused or stale move adds none; rows are only ever added; a store made before gains the
empty history on opening, and a suggestions table its recorded_by. SOL-16's second worked example for "Every act is
the account's" is run literally here: the history, an operator's dismissal and the engineer accounts. Over
test_attribution's store with accounts (made once, no extra hashing); the panel skips "no display" as test_ui.py does."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.project import BadMove, Role, StaleWrite, TicketStatus, UnknownEngineer, UnknownRootCause, WorkOrderError
from solarpunk.ui import ticket_text
from test.solarpunk.test_accounts import BIGS, CREW, SITE, section
from test.solarpunk.test_attribution import ASSET, ENGINEER, INVERTER, OPENED, OPERATOR, OPS, held, stored
from test.solarpunk.test_ui_suggestions import HAS_TKINTER, display_available
from test.support import ROOT
from test.solarpunk.old_store import old_suggestion

if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import asset_window

ACKED, CLOSED = at(2026, 6, 1, 11, 40), at(2026, 6, 1, 12)
NOT_AN_ACCOUNT = "inverter@oahe.example is not an active engineer of site OAHE"


def with_accounts() -> sqlite3.Connection:
    """test_attribution's store with accounts, BIGS-INV-001 (whose engineer the fleet names nowhere) loaded beside it."""
    conn = stored(project.open_store())
    project.load_fleet(conn, BIGS)
    return conn


def with_no_account() -> sqlite3.Connection:
    """The demo fleet with no account and an open INV-001 on OAHE-INV-001 (ticket 1) assigned by its engineer."""
    conn = project.open_store()
    project.load_fleet(conn, project.demo_fleet())
    project.assign_fault(conn, ASSET, "INV-001", OPENED, INVERTER)
    return conn


def history(conn: sqlite3.Connection, wo_id: int = 1) -> list[str]:
    """The ticket's history as the panel writes it, one line per move."""
    return [ticket_text.move_line(found) for found in project.ticket_moves(conn, wo_id)]


class TheWorkedExample(unittest.TestCase):
    def setUp(self) -> None:
        """The store with accounts and BIGS, and SOL-16's text."""
        self.conn = with_accounts()
        self.addCleanup(self.conn.close)
        self.text = section()

    def says(self, act: str, outcome: str) -> None:
        """Asserts the example holds the act beside its outcome."""
        self.assertIn(f"{act} {outcome}", self.text)

    def test_a_tickets_history_names_who_moved_it(self) -> None:
        project.assign_fault_as(self.conn, ENGINEER, ASSET, "INV-001", OPENED)
        project.move_ticket_as(self.conn, OPERATOR, 1, TicketStatus.ACKNOWLEDGED, ACKED)
        project.resolve_ticket_as(self.conn, ENGINEER, 1, "fuse swapped", "RC-COMPONENT", CLOSED)
        lines = history(self.conn)
        self.assertEqual(lines, ["2026-06-01 11:40 UTC · acknowledged · ops@oahe.example",
                                 "2026-06-01 12:00 UTC · in progress · site@oahe.example",
                                 "2026-06-01 12:00 UTC · resolved · site@oahe.example",
                                 "2026-06-01 12:00 UTC · closed · site@oahe.example"])
        self.says("ops@oahe.example acknowledges OAHE-INV-001's ticket at 11:40", lines[0])
        self.says("site@oahe.example resolves and closes it at 12:00", " ".join(lines[1:]))

    def test_a_move_where_nobody_is_signed_in_is_nobodys(self) -> None:
        conn = with_no_account()
        self.addCleanup(conn.close)
        project.move_ticket_as(conn, None, 1, TicketStatus.ACKNOWLEDGED, ACKED)
        (line,) = history(conn)
        self.assertEqual(line, "2026-06-01 11:40 UTC · acknowledged · nobody signed in")
        self.says("a ticket acknowledged at 11:40 in a store with no account", line)

    def test_an_engineer_account_is_an_engineer_and_a_fleet_address_alone_is_not(self) -> None:
        crew = held(CREW, Role.ENGINEER, ("BIGS",))
        fault = project.assign_fault_as(self.conn, crew, "BIGS-INV-001", "INV-001", OPENED)
        self.assertEqual(project.known_engineers(self.conn), (INVERTER, SITE))  # the fleet names crew nowhere
        self.says("crew@bigs.example assigns INV-001 on BIGS-INV-001", f"open by {fault.assigned_by}")
        with self.assertRaises(UnknownEngineer) as caught:
            project.assign_fault(self.conn, ASSET, "INV-001", OPENED, INVERTER)
        self.assertEqual(str(caught.exception), NOT_AN_ACCOUNT)
        self.assertEqual([f.asset_id for f in project.faults_listing(self.conn, False)], ["BIGS-INV-001"])
        self.says("a fault assigned as inverter@oahe.example, which the fleet names and no account holds",
                  f'refused: "{caught.exception}"')


class TheLog(unittest.TestCase):
    def setUp(self) -> None:
        """The demo fleet with no account and ticket 1 open."""
        self.conn = with_no_account()
        self.addCleanup(self.conn.close)

    def test_a_refused_or_stale_move_adds_no_row(self) -> None:
        refusals = ((BadMove, lambda: project.move_ticket(self.conn, 1, TicketStatus.RESOLVED, ACKED, "x")),
                    (WorkOrderError, lambda: project.move_ticket(self.conn, 1, TicketStatus.CLOSED, ACKED)),
                    (StaleWrite, lambda: project.move_ticket(self.conn, 1, TicketStatus.ACKNOWLEDGED, ACKED, read_at=9)),
                    (StaleWrite, lambda: project.close_work_order(self.conn, 1, "RC-COMPONENT", CLOSED, read_at=9)),
                    (UnknownRootCause, lambda: project.close_work_order(self.conn, 1, "RC-NONE", CLOSED, actor=SITE)))
        for error, act in refusals:
            with self.subTest(error=error.__name__), self.assertRaises(error):
                act()
        self.assertEqual(project.ticket_moves(self.conn, 1), ())

    def test_a_reopen_adds_a_row_and_changes_none(self) -> None:
        project.move_ticket(self.conn, 1, TicketStatus.IN_PROGRESS, ACKED, actor=SITE)
        project.move_ticket(self.conn, 1, TicketStatus.RESOLVED, ACKED, "fuse", actor=SITE)
        before = project.ticket_moves(self.conn, 1)
        project.move_ticket(self.conn, 1, TicketStatus.IN_PROGRESS, CLOSED, actor=OPS)
        project.close_work_order(self.conn, 1, "RC-COMPONENT", CLOSED)
        after = project.ticket_moves(self.conn, 1)
        self.assertEqual(after[:2], before)
        self.assertEqual([(m.status, m.actor) for m in after[2:]],
                         [(TicketStatus.IN_PROGRESS, OPS), (TicketStatus.CLOSED, None)])

    def test_no_code_updates_or_deletes_a_row(self) -> None:
        for path in (ROOT / "solarpunk").rglob("*.py"):
            text = " ".join(path.read_text(encoding="utf-8").split()).lower()
            for words in ("update ticket_moves", "delete from ticket_moves", "drop table ticket_moves"):
                with self.subTest(path=path.name, words=words):
                    self.assertNotIn(words, text)

    def test_a_ticket_never_moved_says_so(self) -> None:
        self.assertEqual(ticket_text.history_text(project.ticket_moves(self.conn, 1)), ticket_text.NO_MOVES)


class AnOlderStore(unittest.TestCase):
    def test_it_gains_the_empty_history_and_recorded_by_on_opening(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "old.db"
        conn = project.open_or_create(path)
        project.load_fleet(conn, project.demo_fleet())
        project.assign_fault(conn, ASSET, "INV-001", OPENED, INVERTER)
        project.move_ticket(conn, 1, TicketStatus.ACKNOWLEDGED, ACKED, actor=INVERTER)
        old_suggestion(conn, "OAHE-SEN-001", "SEN-001", OPENED)
        conn.execute("DROP TABLE ticket_moves")  # as a store made before 12.4 holds neither
        conn.execute("ALTER TABLE suggestions DROP COLUMN recorded_by")
        conn.commit()
        conn.close()
        again = project.open_or_create(path)
        self.addCleanup(again.close)
        self.assertEqual(project.ticket_moves(again, 1), ())  # nothing back-filled
        self.assertIsNone(project.open_suggestions(again)[0].recorded_by)
        project.move_ticket(again, 1, TicketStatus.IN_PROGRESS, CLOSED, actor=SITE)
        self.assertEqual(history(again), ["2026-06-01 12:00 UTC · in progress · site@oahe.example"])


@unittest.skipUnless(display_available(), "no display")
class ThePanel(unittest.TestCase):
    def test_the_panel_shows_the_history_with_who(self) -> None:
        conn = with_accounts()
        self.addCleanup(conn.close)
        project.assign_fault_as(conn, ENGINEER, ASSET, "INV-001", OPENED)
        root = tkinter.Tk()
        root.withdraw()
        self.addCleanup(root.destroy)
        panel = asset_window.AssetWindow(root, conn, ASSET, account=OPERATOR).ticket_panel
        root.update()
        self.assertEqual(panel.history.cget("text"), ticket_text.NO_MOVES)
        panel.now = lambda: ACKED
        panel.ack_button.invoke()
        self.assertEqual(panel.history.cget("text"), "2026-06-01 11:40 UTC · acknowledged · ops@oahe.example")


if __name__ == "__main__":
    unittest.main()
