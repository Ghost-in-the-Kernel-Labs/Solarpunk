"""The contract every tracker adapter must pass (11.1, SP-027), as a suite a later adapter's test subclasses with its own
make_tracker: create opens an issue and gives a reference, and a second create of one work order gives the first's back
(a repeated delivery makes no second issue); update sets and clears the working assignee; comment keeps each comment as
written, in order; transition moves the status, and a root cause closes; a ticket never created is refused by name;
the source gives back people's changes after a cursor, oldest first, and a cursor that moves past them; deliver hands
each kind to its method. The local tracker passes it here."""
import unittest

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.leaf.tickets import COMMENT, CREATE, TRANSITION, UPDATE, OutboxEvent
from solarpunk.tickets.adapter import UnknownTicket, deliver
from solarpunk.tickets.local import LocalTracker

ASSET = "OAHE-INV-002"


def event(kind: str, detail: str, wo_id: int = 1, hour: int = 11) -> OutboxEvent:
    """An outbox event of a kind for a work order at an hour of 2026-06-01."""
    return OutboxEvent(0, wo_id, kind, at(2026, 6, 1, hour), ASSET, detail)


class AdapterContract:
    """The suite: a subclass names make_tracker and its issue(wo_id) giving (title, status, assignee) and comments(wo_id),
    and edit for a person's change in the tracker, as the local tracker's are."""

    def make_tracker(self) -> LocalTracker:
        """The tracker under test, empty."""
        raise NotImplementedError

    def setUp(self) -> None:
        """An empty tracker."""
        self.tracker = self.make_tracker()

    def test_create_opens_once_and_gives_its_reference_back(self) -> None:
        ref = self.tracker.create(event(CREATE, "Inverter offline"))
        self.assertEqual(self.tracker.create(event(CREATE, "Inverter offline")), ref)
        self.assertEqual(self.tracker.issue(1), ("Inverter offline", "open", None))
        self.assertNotEqual(self.tracker.create(event(CREATE, "another", wo_id=2)), ref)

    def test_update_sets_and_clears_the_assignee(self) -> None:
        self.tracker.create(event(CREATE, "x"))
        self.tracker.update(event(UPDATE, "assignee crew B"))
        self.assertEqual(self.tracker.issue(1)[2], "crew B")
        self.tracker.update(event(UPDATE, "assignee nobody"))
        self.assertIsNone(self.tracker.issue(1)[2])

    def test_comments_are_kept_as_written_in_order(self) -> None:
        self.tracker.create(event(CREATE, "x"))
        self.tracker.comment(event(COMMENT, "site@oahe.example: on my way"))
        self.tracker.comment(event(COMMENT, "crew B: on site", hour=12))
        self.assertEqual(self.tracker.comments(1), ("site@oahe.example: on my way", "crew B: on site"))

    def test_transition_moves_and_a_root_cause_closes(self) -> None:
        self.tracker.create(event(CREATE, "x"))
        self.tracker.transition(event(TRANSITION, "in progress"))
        self.assertEqual(self.tracker.issue(1)[1], "in progress")
        self.tracker.transition(event(TRANSITION, "RC-COMPONENT"))
        self.assertEqual(self.tracker.issue(1)[1], "closed")

    def test_a_ticket_never_created_is_refused_by_name(self) -> None:
        for kind, detail in ((UPDATE, "assignee x"), (COMMENT, "a: b"), (TRANSITION, "resolved")):
            with self.subTest(kind=kind), self.assertRaises(UnknownTicket) as caught:
                deliver(self.tracker, event(kind, detail, wo_id=9))
            self.assertEqual(str(caught.exception), "work order 9 is not in the tracker")

    def test_the_source_gives_changes_after_a_cursor(self) -> None:
        self.tracker.create(event(CREATE, "x"))
        self.assertEqual(self.tracker.changes_since(0), ((), 0))
        first = self.tracker.edit(1, COMMENT, "crew B", "on site", at(2026, 6, 1, 12))
        second = self.tracker.edit(1, TRANSITION, "crew B", "resolved", at(2026, 6, 1, 13))
        changes, cursor = self.tracker.changes_since(0)
        self.assertEqual(changes, (first, second))
        self.assertEqual(self.tracker.changes_since(cursor), ((), cursor))
        later, _ = self.tracker.changes_since(cursor - 1)
        self.assertEqual(later, (second,))

    def test_deliver_hands_each_kind_to_its_method_and_refuses_another(self) -> None:
        deliver(self.tracker, event(CREATE, "x"))
        deliver(self.tracker, event(UPDATE, "assignee crew B"))
        self.assertEqual(self.tracker.issue(1)[2], "crew B")
        with self.assertRaises(ValueError):
            deliver(self.tracker, event("delete", "x"))


class TheLocalTracker(AdapterContract, unittest.TestCase):
    def make_tracker(self) -> LocalTracker:
        """The local tracker over a fresh in-memory store."""
        conn = project.open_store()
        self.addCleanup(conn.close)
        return LocalTracker(conn)


if __name__ == "__main__":
    unittest.main()
