"""Versions held headless (12.2, SOL-16, SP-028): SOL-16's second worked example run literally (two screens on one
ticket), then each record kind: an asset, a fault, a suggestion and a ticket made at version 1, raised by one with every
change, and a write read at an older version refused, writing nothing; a write that names no version unchecked; a store
made before 12.2 given the columns at version 1 when it is opened."""
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.leaf import versions
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import at
from solarpunk.project import StaleWrite, TicketStatus
from test.solarpunk.test_accounts import OPENED, SITE, example_store, section
from test.solarpunk.old_store import old_suggestion

STALE = "changed by someone else since you read it; refresh"
LATER = at(2026, 6, 1, 11, 50)
INVERTER = "OAHE-INV-002"
TABLES = ("assets", "faults", "suggestions", "work_orders")


class Store(unittest.TestCase):
    def setUp(self) -> None:
        """SOL-16's example store: an open INV-001 on OAHE-INV-002 with its ticket, work order 1, and a pushed SEN-001
        suggestion on OAHE-SEN-001."""
        self.conn = example_store()
        self.addCleanup(self.conn.close)

    def refused(self, record: str) -> unittest.case._AssertRaisesContext:
        """A context that expects StaleWrite naming the record: with self.refused("ticket 1"): …"""
        return self.assertRaisesRegex(StaleWrite, f"^{record} {STALE}$")

    def inverter(self) -> Asset:
        """OAHE-INV-002 as the fleet holds it now."""
        (found,) = [a for a in project.fleet_assets(self.conn, None) if a.asset_id == INVERTER]
        return found

    def outbox_size(self) -> int:
        """How many events the ticket outbox holds, so a refused write is seen to have added none."""
        return self.conn.execute("SELECT count(*) FROM ticket_outbox").fetchone()[0]


class TheWorkedExample(Store):
    def test_two_screens_on_one_ticket(self) -> None:
        first = second = project.ticket_of(self.conn, 1)
        self.assertEqual((first.version, second.version), (1, 1))
        assigned = project.set_ticket_assignee(self.conn, 1, "crew B", OPENED, read_at=first.version)
        self.assertEqual(assigned.version, 2)
        events = self.outbox_size()
        with self.refused("ticket 1"):
            project.move_ticket(self.conn, 1, TicketStatus.ACKNOWLEDGED, LATER, read_at=second.version)
        after = project.ticket_of(self.conn, 1)
        self.assertEqual((after.status, after.assignee, after.version), (TicketStatus.OPEN, "crew B", 2))
        self.assertEqual(self.outbox_size(), events)
        moved = project.move_ticket(self.conn, 1, TicketStatus.ACKNOWLEDGED, LATER, read_at=after.version)
        self.assertEqual((moved.status, moved.version), (TicketStatus.ACKNOWLEDGED, 3))

    def test_each_line_is_in_the_contract(self) -> None:
        text = section()
        for line in (
            'the first screen sets its assignee to "crew B" allowed: version 2',
            f'the second screen, read at version 1, acknowledges it refused: "ticket 1 {STALE}"',
            "the ticket after the refusal open, assignee crew B, version 2",
            "the second screen refreshes, reads version 2, acknowledges allowed: version 3",
        ):
            with self.subTest(line=line):
                self.assertIn(line, text)


class EachRecord(Store):
    def test_an_asset(self) -> None:
        self.assertEqual(self.inverter().version, 1)
        project.assign_engineer(self.conn, INVERTER, "b@oahe.example", read_at=1)
        self.assertEqual(self.inverter().version, 2)
        with self.refused(f"asset {INVERTER}"):
            project.assign_engineer(self.conn, INVERTER, "c@oahe.example", read_at=1)
        found = self.inverter()
        self.assertEqual((found.engineer_email, found.version), ("b@oahe.example", 2))

    def test_a_fault(self) -> None:
        (fault,) = project.faults_listing(self.conn, True)
        self.assertEqual(fault.version, 1)
        with self.refused(f"fault {fault.fault_id}"):
            project.close_fault(self.conn, fault.fault_id, LATER, read_at=0)
        self.assertEqual(len(project.faults_listing(self.conn, True)), 1)
        self.assertEqual(project.close_fault(self.conn, fault.fault_id, LATER, read_at=1).version, 2)

    def test_a_ticket_every_change_raises_it_and_a_comment_does_not(self) -> None:
        project.comment_on_ticket(self.conn, 1, SITE, LATER, "on my way")
        self.assertEqual(project.ticket_of(self.conn, 1).version, 1)
        project.move_ticket(self.conn, 1, TicketStatus.IN_PROGRESS, LATER)
        project.open_work_order_from_fault(self.conn, 1, OPENED, "swap the fuse")  # the note
        self.assertEqual(project.ticket_of(self.conn, 1).version, 3)
        with self.refused("ticket 1"):
            project.close_work_order(self.conn, 1, "RC-COMPONENT", LATER, read_at=2)
        self.assertEqual(len(project.faults_listing(self.conn, True)), 1)  # neither the order nor its fault closed
        closed = project.close_work_order(self.conn, 1, "RC-COMPONENT", LATER, read_at=3)
        self.assertEqual((closed.version, project.faults_listing(self.conn, True)), (4, ()))

    def test_no_version_named_is_not_checked(self) -> None:
        project.set_ticket_assignee(self.conn, 1, "crew B", OPENED)
        project.set_ticket_assignee(self.conn, 1, "crew C", OPENED)
        self.assertEqual(project.ticket_of(self.conn, 1).version, 3)


class TheRule(unittest.TestCase):
    def test_check(self) -> None:
        versions.check("ticket 1", 2, 2)
        versions.check("ticket 1", 2, None)
        with self.assertRaisesRegex(StaleWrite, f"^ticket 1 {STALE}$"):
            versions.check("ticket 1", 2, 1)

    def test_a_store_made_before_gains_the_columns_at_version_1(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "old.db"
        conn = project.open_or_create(path)
        project.load_fleet(conn, project.demo_fleet())
        project.assign_fault(conn, INVERTER, "INV-001", OPENED, SITE.replace("site", "inverter"))
        old_suggestion(conn, "OAHE-SEN-001", "SEN-001", OPENED)
        for table in TABLES:  # as a store made before 12.2 was
            conn.execute(f"ALTER TABLE {table} DROP COLUMN version")
        conn.commit()
        conn.close()
        reopened = project.open_or_create(path)
        self.addCleanup(reopened.close)
        for table in TABLES:
            with self.subTest(table=table):
                self.assertEqual({row[0] for row in reopened.execute(f"SELECT version FROM {table}")}, {1})
        again = project.open_or_create(path)  # a second opening changes nothing
        self.addCleanup(again.close)
        columns = [row[1] for row in again.execute("PRAGMA table_info(faults)")]
        self.assertEqual(columns.count("version"), 1)


if __name__ == "__main__":
    unittest.main()
