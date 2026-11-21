"""The ticket ledger (8.2, SOL-14, SP-022): a work order is a ticket; assigning a fault opens it in the same call, a
suggestion never does; its status moves only as the contract allows, each move stamped; resolving needs evidence;
comments keep their author and instant; closing takes a root cause and closes the fault; a store made before 8.2
gains the ticket's columns and its old orders their status and priority; a query reports the tickets past a target;
no move changes a fault, so the KPIs read what they read before."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.faults import ledger as fault_ledger
from solarpunk.fleet import registry
from solarpunk.leaf import store
from solarpunk.leaf.clock import at
from solarpunk.project import BadMove, Priority, TargetState, TicketStatus, WorkOrderError
from solarpunk.workorders import tickets as ticket_ledger

ENGINEER = "site@oahe.example"
INV1 = "OAHE-INV-001"
INV2 = "OAHE-INV-002"
TRK = "OAHE-TRK-001"
OPEN, ACK, WORK, DONE, CLOSED = (TicketStatus.OPEN, TicketStatus.ACKNOWLEDGED, TicketStatus.IN_PROGRESS,
                                 TicketStatus.RESOLVED, TicketStatus.CLOSED)
# The work_orders table as 4.1 made it, before the ticket's columns (8.2).
OLD_WORK_ORDERS = (
    "CREATE TABLE work_orders (wo_id INTEGER PRIMARY KEY, asset_id TEXT NOT NULL, fault_id INTEGER NULL,"
    " kind TEXT NOT NULL CHECK (kind IN ('corrective', 'preventive')), opened TEXT NOT NULL, closed TEXT NULL,"
    " root_cause TEXT NULL, note TEXT NOT NULL)"
)


def fleet() -> sqlite3.Connection:
    """An in-memory store holding the OAHE fleet and nothing else."""
    conn = project.open_store()
    project.load_fleet(conn, project.demo_fleet())
    return conn


class Opening(unittest.TestCase):
    def setUp(self) -> None:
        """An OAHE fleet with no fault yet."""
        self.conn = fleet()
        self.addCleanup(self.conn.close)

    def test_assigning_a_fault_opens_its_ticket_in_the_same_call(self) -> None:
        fault = project.assign_fault(self.conn, INV1, "INV-001", at(2026, 6, 1, 10), ENGINEER)
        (order,) = project.work_orders_for(self.conn, INV1)
        self.assertEqual((order.fault_id, order.kind, order.opened), (fault.fault_id, "corrective", fault.opened))
        self.assertTrue(order.note.startswith("Inverter offline"))
        ticket = project.ticket_of(self.conn, order.wo_id)
        self.assertEqual((ticket.status, ticket.priority, ticket.acknowledged, ticket.assignee), (OPEN, Priority.P1, None, None))

    def test_the_priority_follows_the_codes_severity_and_a_preventive_order_is_p3(self) -> None:
        project.assign_fault(self.conn, INV1, "INV-002", at(2026, 6, 1, 10), ENGINEER)
        project.assign_fault(self.conn, "OAHE-SIT-001", "SIT-002", at(2026, 6, 1, 10), ENGINEER)
        preventive = project.open_preventive_work_order(self.conn, TRK, at(2026, 6, 1, 10), "grease the drive")
        priorities = [t.priority for t in project.open_tickets(self.conn)]
        self.assertEqual(priorities, [Priority.P2, Priority.P2, Priority.P3])
        self.assertEqual(project.ticket_of(self.conn, preventive.wo_id).kind, "preventive")

    def test_a_fault_telemetry_raises_opens_no_ticket_here(self) -> None:
        # SP-046: a ticket opens from a failed test result in 7.9; until then only an engineer's assignment opens one.
        project.fault_from_device(self.conn, INV1, "INV-001", at(2026, 6, 1, 10))
        self.assertEqual(project.open_tickets(self.conn), ())

    def test_a_refused_assignment_opens_no_ticket(self) -> None:
        with self.assertRaises(project.UnknownEngineer):
            project.assign_fault(self.conn, INV1, "INV-001", at(2026, 6, 1, 10), "nobody@example")
        self.assertEqual(project.open_tickets(self.conn), ())

    def test_opening_an_order_from_an_assigned_fault_gives_its_ticket_with_the_note(self) -> None:
        fault = project.assign_fault(self.conn, INV1, "INV-001", at(2026, 6, 1, 10), ENGINEER)
        order = project.open_work_order_from_fault(self.conn, fault.fault_id, at(2026, 6, 1, 10, 5), "swap the fuse")
        self.assertEqual((order.wo_id, order.opened, order.note), (1, at(2026, 6, 1, 10), "swap the fuse"))
        self.assertEqual(len(project.work_orders_for(self.conn, INV1)), 1)


class Moving(unittest.TestCase):
    def setUp(self) -> None:
        """An INV-001 on OAHE-INV-001 at 10:00, its ticket work order 1, open and P1."""
        self.conn = fleet()
        self.addCleanup(self.conn.close)
        self.fault = project.assign_fault(self.conn, INV1, "INV-001", at(2026, 6, 1, 10), ENGINEER)
        self.wo = project.work_orders_for(self.conn, INV1)[0].wo_id

    def move(self, status: TicketStatus, hour: int, minute: int = 0, evidence: str | None = None) -> project.Ticket:
        """Moves the ticket at an instant on 2026-06-01."""
        return project.move_ticket(self.conn, self.wo, status, at(2026, 6, 1, hour, minute), evidence)

    def test_each_move_stamps_its_instant_once(self) -> None:
        self.move(ACK, 10, 40)
        self.move(WORK, 14, 30)
        resolved = self.move(DONE, 15, evidence="fuse replaced, output restored")
        self.assertEqual((resolved.acknowledged, resolved.responded, resolved.resolved, resolved.evidence),
                         (at(2026, 6, 1, 10, 40), at(2026, 6, 1, 14, 30), at(2026, 6, 1, 15), "fuse replaced, output restored"))
        again = self.move(WORK, 15, 10)
        self.assertEqual((again.status, again.responded, again.resolved, again.evidence),
                         (WORK, at(2026, 6, 1, 14, 30), None, None))

    def test_open_straight_to_in_progress_acknowledges_and_responds_at_once(self) -> None:
        ticket = self.move(WORK, 10, 20)
        self.assertEqual((ticket.acknowledged, ticket.responded), (at(2026, 6, 1, 10, 20), at(2026, 6, 1, 10, 20)))

    def test_every_move_the_contract_lacks_is_refused_and_writes_nothing(self) -> None:
        for target in (OPEN, DONE):
            with self.subTest(target=target), self.assertRaises(BadMove):
                self.move(target, 11)
        with self.assertRaises(WorkOrderError) as caught:
            self.move(CLOSED, 11)
        self.assertEqual(str(caught.exception), f"work order {self.wo} closes by close, once its fault's root cause is written")
        self.assertEqual(project.ticket_of(self.conn, self.wo).status, OPEN)
        self.assertIsNone(project.ticket_of(self.conn, self.wo).acknowledged)

    def test_resolving_needs_evidence_and_a_move_cannot_go_back_in_time(self) -> None:
        self.move(WORK, 11)
        for blank in (None, "  "):
            with self.assertRaises(WorkOrderError):
                self.move(DONE, 12, evidence=blank)
        with self.assertRaises(WorkOrderError):
            self.move(DONE, 10, 30, evidence="x")
        self.assertEqual(project.ticket_of(self.conn, self.wo).status, WORK)

    def test_closing_waits_for_the_root_cause_closes_the_fault_and_is_final(self) -> None:
        self.move(WORK, 11)
        self.move(DONE, 12, evidence="fuse replaced")
        with self.assertRaises(project.NoRootCause):
            project.close_work_order(self.conn, self.wo, at(2026, 6, 1, 12, 30))
        self.assertEqual(project.ticket_of(self.conn, self.wo).status, DONE)
        project.write_fault_cause(self.conn, 1, "worn fuse holder", ENGINEER, at(2026, 6, 1, 12, 10))
        with self.assertRaises(WorkOrderError):
            project.close_work_order(self.conn, self.wo, at(2026, 6, 1, 11, 30))
        project.close_work_order(self.conn, self.wo, at(2026, 6, 1, 12, 30))
        ticket = project.ticket_of(self.conn, self.wo)
        self.assertEqual((ticket.status, ticket.closed, ticket.resolved), (CLOSED, at(2026, 6, 1, 12, 30), at(2026, 6, 1, 12)))
        self.assertEqual(fault_ledger.by_asset(self.conn, INV1)[0].closed, at(2026, 6, 1, 12, 30))
        for target in TicketStatus:
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.move(target, 13)

    def test_the_one_step_close_out_takes_the_moves_at_its_instant(self) -> None:
        self.move(ACK, 10, 40)
        project.write_fault_cause(self.conn, 1, "the grid tripped", ENGINEER, at(2026, 6, 1, 10, 50))
        project.close_work_order(self.conn, self.wo, at(2026, 6, 1, 13))
        ticket = project.ticket_of(self.conn, self.wo)
        self.assertEqual((ticket.acknowledged, ticket.responded, ticket.resolved, ticket.closed),
                         (at(2026, 6, 1, 10, 40), at(2026, 6, 1, 13), at(2026, 6, 1, 13), at(2026, 6, 1, 13)))

    def test_no_move_changes_the_fault_so_the_kpis_read_the_same(self) -> None:
        period = project.day_period(at(2026, 6, 1).date())
        before = project.kpis_for(self.conn, "OAHE", period)
        self.move(ACK, 10, 40)
        self.move(WORK, 11)
        self.move(DONE, 12, evidence="fuse replaced")
        project.set_ticket_assignee(self.conn, self.wo, "crew B")
        project.comment_on_ticket(self.conn, self.wo, ENGINEER, at(2026, 6, 1, 12, 5), "awaiting sign-off")
        self.assertEqual(project.kpis_for(self.conn, "OAHE", period), before)
        self.assertEqual(project.open_outages(self.conn), {INV1: self.fault})

    def test_the_working_assignee_is_set_and_cleared(self) -> None:
        self.assertEqual(project.set_ticket_assignee(self.conn, self.wo, " crew B ").assignee, "crew B")
        self.assertIsNone(project.set_ticket_assignee(self.conn, self.wo, "  ").assignee)


class Comments(unittest.TestCase):
    def setUp(self) -> None:
        """An INV-001 on OAHE-INV-001 at 10:00, its ticket work order 1."""
        self.conn = fleet()
        self.addCleanup(self.conn.close)
        project.assign_fault(self.conn, INV1, "INV-001", at(2026, 6, 1, 10), ENGINEER)

    def test_comments_keep_their_author_and_instant_oldest_first(self) -> None:
        first = project.comment_on_ticket(self.conn, 1, ENGINEER, at(2026, 6, 1, 10, 5), " on my way ")
        project.comment_on_ticket(self.conn, 1, "operator@oahe.example", at(2026, 6, 1, 10, 6), "gate code sent")
        self.assertEqual((first.author, first.at, first.body), (ENGINEER, at(2026, 6, 1, 10, 5), "on my way"))
        self.assertEqual([c.body for c in project.ticket_comments(self.conn, 1)], ["on my way", "gate code sent"])

    def test_a_comment_without_author_or_words_or_before_the_opening_is_refused(self) -> None:
        for author, body, moment in (("", "x", at(2026, 6, 1, 11)), (ENGINEER, " ", at(2026, 6, 1, 11)),
                                     (ENGINEER, "x", at(2026, 6, 1, 9))):
            with self.subTest(author=author, body=body), self.assertRaises(WorkOrderError):
                project.comment_on_ticket(self.conn, 1, author, moment, body)
        with self.assertRaises(WorkOrderError):
            project.comment_on_ticket(self.conn, 9, ENGINEER, at(2026, 6, 1, 11), "x")
        self.assertEqual(project.ticket_comments(self.conn, 1), ())

    def test_the_ledger_offers_no_edit_and_no_delete(self) -> None:
        names = {name for name in dir(ticket_ledger) if not name.startswith("_")}
        self.assertFalse({n for n in names if "edit" in n or "delete" in n or "remove" in n})


class PastTarget(unittest.TestCase):
    def setUp(self) -> None:
        """An OAHE fleet with no fault yet."""
        self.conn = fleet()
        self.addCleanup(self.conn.close)

    def test_the_worked_example(self) -> None:
        project.assign_fault(self.conn, INV1, "INV-001", at(2026, 6, 1, 10), ENGINEER)
        project.assign_fault(self.conn, INV2, "INV-002", at(2026, 6, 1, 10), ENGINEER)
        project.move_ticket(self.conn, 1, ACK, at(2026, 6, 1, 10, 40))
        self.assertEqual(project.tickets_past_target(self.conn, at(2026, 6, 1, 13)), ())
        overdue = project.tickets_past_target(self.conn, at(2026, 6, 1, 14, 15))
        self.assertEqual([(b.ticket.wo_id, b.target, b.state) for b in overdue],
                         [(1, "respond", TargetState.OVERDUE), (2, "acknowledge", TargetState.OVERDUE)])
        project.move_ticket(self.conn, 1, WORK, at(2026, 6, 1, 14, 30))
        at_three = project.tickets_past_target(self.conn, at(2026, 6, 1, 15))
        self.assertEqual([(b.ticket.wo_id, b.target, b.state) for b in at_three],
                         [(1, "respond", TargetState.LATE), (2, "acknowledge", TargetState.OVERDUE)])

    def test_a_closed_ticket_is_past_no_target(self) -> None:
        project.assign_fault(self.conn, INV1, "INV-001", at(2026, 6, 1, 10), ENGINEER)
        project.write_fault_cause(self.conn, 1, "worn fuse holder", ENGINEER, at(2026, 6, 1, 11))
        project.close_work_order(self.conn, 1, at(2026, 6, 1, 18))
        self.assertEqual(project.tickets_past_target(self.conn, at(2026, 6, 2)), ())


class AnOldStore(unittest.TestCase):
    def test_a_store_made_before_gains_the_columns_statuses_and_priorities(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "old.db"
        old = project.open_store(path)
        old.execute("DROP TABLE work_orders")
        old.execute("DROP TABLE ticket_comments")
        old.execute(OLD_WORK_ORDERS)
        project.load_fleet(old, project.demo_fleet())
        fault = fault_ledger.assign(old, INV1, "INV-001", at(2026, 6, 1, 10), ENGINEER)
        old.execute("INSERT INTO work_orders (asset_id, fault_id, kind, opened, note) VALUES (?, ?, 'corrective', ?, 'x')",
                    (INV1, fault.fault_id, at(2026, 6, 1, 10).isoformat()))
        old.execute("INSERT INTO work_orders (asset_id, fault_id, kind, opened, closed, root_cause, note)"
                    " VALUES (?, NULL, 'preventive', ?, ?, 'RC-UNKNOWN', 'y')",
                    (TRK, at(2026, 6, 1, 9).isoformat(), at(2026, 6, 1, 9, 30).isoformat()))
        old.commit()
        old.close()
        for _ in range(2):
            conn = project.open_or_create(path)
            first, second = project.ticket_of(conn, 1), project.ticket_of(conn, 2)
            self.assertEqual((first.status, first.priority), (OPEN, Priority.P1))
            self.assertEqual((second.status, second.priority), (CLOSED, Priority.P3))
            self.assertEqual(project.ticket_comments(conn, 1), ())
            conn.close()

    def test_upgrade_twice_changes_nothing_the_second_time(self) -> None:
        conn = store.connect(store.MEMORY)
        store.apply(conn, registry.schema())
        conn.execute(OLD_WORK_ORDERS)
        ticket_ledger.upgrade(conn)
        columns = list(conn.execute("PRAGMA table_info(work_orders)"))
        ticket_ledger.upgrade(conn)
        self.assertEqual(list(conn.execute("PRAGMA table_info(work_orders)")), columns)


class TheDemo(unittest.TestCase):
    def test_the_demos_closed_faults_closed_through_their_tickets_and_its_outage_is_overdue(self) -> None:
        from solarpunk.ui import demo
        server, port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port)
        conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        self.addCleanup(conn.close)
        (ticket,) = project.open_tickets(conn)
        self.assertEqual((ticket.asset_id, ticket.priority, ticket.status), (demo.DOWN, Priority.P1, OPEN))
        (breach,) = project.tickets_past_target(conn, at(2026, 6, 1, 13))
        self.assertEqual((breach.target, breach.state), ("acknowledge", TargetState.OVERDUE))
        closed = [project.ticket_of(conn, wo) for wo in (1, 2)]
        self.assertEqual([(t.status, t.evidence is not None) for t in closed], [(CLOSED, True), (CLOSED, True)])


if __name__ == "__main__":
    unittest.main()
