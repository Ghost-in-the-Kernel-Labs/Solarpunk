"""The ticket outbox and its drain (11.1, SP-027): each ticket change writes its event in the change's own commit, a
refused change none; the drain hands events to a tracker oldest first, the local tracker then showing the ticket as
the ledger holds it; a tracker that is down stops the drain without stopping the ledger, and the next drain sends what
waited, in order; an event is never sent twice; a ticket made before the outbox is opened in the tracker first; the
scheduled run drains, and says when the tracker is down."""
import unittest
from datetime import timedelta

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.leaf.tickets import OutboxEvent
from solarpunk.tickets.adapter import Unreachable
from solarpunk.tickets.local import LocalTracker
from solarpunk.workorders import outbox
from solarpunk.workorders.ledger import WorkOrderError

ENGINEER = "site@oahe.example"
INV2 = "OAHE-INV-002"
WORK = project.TicketStatus.IN_PROGRESS


class DownTracker(LocalTracker):
    """A local tracker whose every call fails as an unreachable one does, once down is set."""

    down = False

    def create(self, event: OutboxEvent) -> str:
        """Opens the issue, unless the tracker is down."""
        if self.down:
            raise Unreachable("the tracker did not answer")
        return super().create(event)

    def comment(self, event: OutboxEvent) -> None:
        """Adds the comment, unless the tracker is down."""
        if self.down:
            raise Unreachable("the tracker did not answer")
        super().comment(event)


class Outbox(unittest.TestCase):
    def setUp(self) -> None:
        """The OAHE fleet with an INV-001 assigned on OAHE-INV-002 at 11:30, its ticket work order 1."""
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        project.load_fleet(self.conn, project.demo_fleet())
        project.assign_fault(self.conn, INV2, "INV-001", at(2026, 6, 1, 11, 30), ENGINEER)

    def kinds(self) -> list[tuple[str, str]]:
        """The waiting events' kinds and details, oldest first."""
        return [(e.kind, e.detail) for e in outbox.pending(self.conn)]

    def test_each_change_writes_its_event_and_a_refused_one_none(self) -> None:
        self.assertEqual(self.kinds()[0][0], "create")
        project.move_ticket(self.conn, 1, WORK, at(2026, 6, 1, 12))
        project.set_ticket_assignee(self.conn, 1, "crew B", at(2026, 6, 1, 12, 5))
        project.comment_on_ticket(self.conn, 1, ENGINEER, at(2026, 6, 1, 12, 10), "on site")
        with self.assertRaises(project.BadMove):
            project.move_ticket(self.conn, 1, project.TicketStatus.ACKNOWLEDGED, at(2026, 6, 1, 12, 20))
        project.write_fault_cause(self.conn, 1, "worn fuse holder", ENGINEER, at(2026, 6, 1, 12, 30))
        project.close_work_order(self.conn, 1, at(2026, 6, 1, 13))
        self.assertEqual(self.kinds()[1:], [("transition", "in progress"), ("update", "assignee crew B"),
                                            ("comment", f"{ENGINEER}: on site"), ("transition", "closed")])

    def test_the_drain_sends_oldest_first_and_the_tracker_shows_the_ticket(self) -> None:
        project.set_ticket_assignee(self.conn, 1, "crew B", at(2026, 6, 1, 12))
        project.move_ticket(self.conn, 1, WORK, at(2026, 6, 1, 12, 5))
        tracker = LocalTracker(self.conn)
        drained = project.drain_outbox(self.conn, tracker, at(2026, 6, 1, 13))
        self.assertEqual((drained, project.tickets_waiting(self.conn)), (project.Drained(3, 0, None), ()))
        self.assertEqual(tracker.issue(1), (project.work_orders_for(self.conn, INV2)[0].note, "in progress", "crew B"))
        self.assertEqual(project.drain_outbox(self.conn, tracker, at(2026, 6, 1, 14)), project.Drained(0, 0, None))

    def test_a_tracker_down_stops_the_drain_not_the_ledger(self) -> None:
        tracker = DownTracker(self.conn)
        tracker.down = True
        drained = project.drain_outbox(self.conn, tracker, at(2026, 6, 1, 12))
        self.assertEqual(drained, project.Drained(0, 1, "the tracker did not answer"))
        project.comment_on_ticket(self.conn, 1, ENGINEER, at(2026, 6, 1, 12, 5), "first")
        project.comment_on_ticket(self.conn, 1, ENGINEER, at(2026, 6, 1, 12, 10), "second")
        self.assertEqual(len(project.ticket_comments(self.conn, 1)), 2)  # the ledger never waited
        tracker.down = False
        self.assertEqual(project.drain_outbox(self.conn, tracker, at(2026, 6, 1, 13)), project.Drained(3, 0, None))
        self.assertEqual(tracker.comments(1), (f"{ENGINEER}: first", f"{ENGINEER}: second"))

    def test_an_event_is_never_sent_twice(self) -> None:
        (created,) = outbox.pending(self.conn)
        outbox.mark_sent(self.conn, created.event_id, at(2026, 6, 1, 12))
        with self.assertRaises(WorkOrderError):
            outbox.mark_sent(self.conn, created.event_id, at(2026, 6, 1, 12))

    def test_a_ticket_made_before_the_outbox_is_opened_in_the_tracker_first(self) -> None:
        self.conn.execute("DELETE FROM ticket_outbox")  # as a store made before 11.1 holds no event for it
        self.conn.commit()
        project.comment_on_ticket(self.conn, 1, ENGINEER, at(2026, 6, 1, 12), "still down")
        tracker = LocalTracker(self.conn)
        self.assertEqual(project.drain_outbox(self.conn, tracker, at(2026, 6, 1, 13)), project.Drained(1, 0, None))
        self.assertEqual(tracker.issue(1)[1], "open")
        self.assertEqual(tracker.comments(1), (f"{ENGINEER}: still down",))


class TheScheduledRun(unittest.TestCase):
    def test_the_run_drains_the_outbox_into_the_local_tracker(self) -> None:
        conn = project.open_store()
        self.addCleanup(conn.close)
        project.load_fleet(conn, project.demo_fleet())
        project.assign_fault(conn, INV2, "INV-001", at(2026, 6, 1, 11, 30), ENGINEER)
        report = project.scheduled_run(conn, at(2026, 6, 1, 13))
        self.assertEqual((report.tickets_sent, project.tickets_waiting(conn)), (1, ()))
        self.assertEqual(LocalTracker(conn).issue(1)[1], "open")
        again = project.scheduled_run(conn, at(2026, 6, 1, 13) + timedelta(hours=1))
        self.assertEqual(again.tickets_sent, 0)


if __name__ == "__main__":
    unittest.main()
