"""The windows pass the version they read (12.4, 12.2, SOL-16, SP-028): the asset window's engineer Save, Accept and
Dismiss, and the ticket panel's Acknowledge and Resolve each name the version of the record the window drew, so a
screen another person's change has made stale is refused with SOL-16's words, writing nothing, and Refresh rereads it;
after a write the window rereads, so its next write carries the new version. Resolve's version is held headless too.
Over test_attribution's store with accounts (made once), an open INV-001 on OAHE-INV-002 and a pushed SEN-001 on
OAHE-SEN-001, the site engineer signed in; the windows skip "no tkinter" or "no display" as test_ui.py does."""
import sqlite3
import unittest

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.project import StaleWrite, TicketStatus
from solarpunk.ui import cells
from test.solarpunk.test_attribution import ENGINEER, SITE, stored
from test.solarpunk.test_ui_suggestions import HAS_TKINTER, display_available
from test.solarpunk.old_store import old_suggestion

if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import asset_window

INVERTER, SENSOR = "OAHE-INV-002", "OAHE-SEN-001"
OPENED, LATER, LATEST = at(2026, 6, 1, 11, 30), at(2026, 6, 1, 11, 40), at(2026, 6, 1, 11, 50)
STALE = "changed by someone else since you read it; refresh"
OTHER = "other@oahe.example"


def example() -> sqlite3.Connection:
    """The store with accounts, OAHE-INV-002's outage (ticket 1) and SEN-001 suggested on OAHE-SEN-001."""
    conn = stored(project.open_store())
    project.assign_fault(conn, INVERTER, "INV-001", OPENED, SITE)
    old_suggestion(conn, SENSOR, "SEN-001", OPENED)
    return conn


class Headless(unittest.TestCase):
    def setUp(self) -> None:
        """The example store, in memory."""
        self.conn = example()
        self.addCleanup(self.conn.close)

    def test_resolve_checks_the_version_read_and_writes_nothing_when_stale(self) -> None:
        project.write_cause_as(self.conn, ENGINEER, 1, "the breaker tripped on a surge", LATEST)
        project.set_ticket_assignee(self.conn, 1, "crew B", LATER)
        with self.assertRaisesRegex(StaleWrite, f"^ticket 1 {STALE}$"):
            project.resolve_ticket_as(self.conn, ENGINEER, 1, "breaker reset", LATEST, 1)
        found = project.ticket_of(self.conn, 1)
        self.assertEqual((found.status, found.version), (TicketStatus.OPEN, 2))
        closed = project.resolve_ticket_as(self.conn, ENGINEER, 1, "breaker reset", LATEST, 2)
        self.assertIs(closed.status, TicketStatus.CLOSED)

    def test_resolve_from_in_progress_checks_its_one_move(self) -> None:
        project.write_cause_as(self.conn, ENGINEER, 1, "the breaker tripped on a surge", LATEST)
        project.move_ticket(self.conn, 1, TicketStatus.IN_PROGRESS, LATER)
        with self.assertRaisesRegex(StaleWrite, f"^ticket 1 {STALE}$"):
            project.resolve_ticket(self.conn, 1, "breaker reset", LATEST, 1)
        self.assertIs(project.resolve_ticket(self.conn, 1, "breaker reset", LATEST, 2).status,
                      TicketStatus.CLOSED)

    def test_the_version_a_suggestion_was_drawn_at(self) -> None:
        detail = project.asset_detail(self.conn, SENSOR)
        (found,) = detail.suggestions
        self.assertEqual(cells.drawn(detail, found.suggestion_id), 1)


@unittest.skipUnless(display_available(), "no display")
class StaleScreens(unittest.TestCase):
    def setUp(self) -> None:
        """The example store and a hidden root."""
        self.conn = example()
        self.addCleanup(self.conn.close)
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def window(self, asset_id: str) -> "asset_window.AssetWindow":
        """The asset's window, the site engineer signed in."""
        window = asset_window.AssetWindow(self.root, self.conn, asset_id, account=ENGINEER)
        self.root.update()
        return window

    def test_a_stale_engineer_save_is_refused_and_refresh_rereads(self) -> None:
        window = self.window(INVERTER)
        project.assign_engineer(self.conn, INVERTER, OTHER)  # another screen saves first
        window.engineer_box.set("mine@oahe.example")
        window.save_button.invoke()
        self.assertEqual(window.message.cget("text"), f"Refused: asset {INVERTER} {STALE}")
        self.assertEqual(project.asset_detail(self.conn, INVERTER).asset.engineer_email, OTHER)
        window.refresh_button.invoke()
        self.assertEqual((window.message.cget("text"), window.engineer_box.get()), ("", OTHER))
        window.engineer_box.set("mine@oahe.example")
        window.save_button.invoke()
        self.assertEqual(project.asset_detail(self.conn, INVERTER).asset.engineer_email, "mine@oahe.example")

    def test_the_window_has_no_accept_or_dismiss_since_7_7(self) -> None:
        window = self.window(SENSOR)
        for gone in ("accept_button", "dismiss_button", "reason_box"):
            self.assertFalse(hasattr(window, gone), gone)  # SP-046: nothing is accepted or dismissed
        self.assertEqual(len(window.suggestion_tree.get_children()), 1)  # the old store's suggestion still reads

    def test_the_panel_refuses_a_stale_act_and_its_next_carries_the_new_version(self) -> None:
        panel = self.window(INVERTER).ticket_panel
        panel.now = lambda: LATER
        project.set_ticket_assignee(self.conn, 1, "crew B", OPENED)  # another screen, read at 1, writes version 2
        panel.ack_button.invoke()
        self.assertEqual(panel.message.cget("text"), f"ticket 1 {STALE}")
        self.assertIs(project.ticket_of(self.conn, 1).status, TicketStatus.OPEN)
        panel.refresh_button.invoke()
        self.assertEqual(panel.message.cget("text"), "")
        panel.ack_button.invoke()
        self.assertEqual((panel.message.cget("text"), project.ticket_of(self.conn, 1).version), ("", 3))
        panel.now = lambda: LATEST
        panel.done_box.insert(0, "breaker reset")
        project.write_cause_as(self.conn, ENGINEER, 1, "the breaker tripped on a surge", LATEST)
        project.move_ticket(self.conn, 1, TicketStatus.IN_PROGRESS, LATER)  # version 4, under the panel
        panel.resolve_button.invoke()
        self.assertEqual(panel.message.cget("text"), f"ticket 1 {STALE}")
        panel.refresh_button.invoke()
        panel.resolve_button.invoke()
        self.assertIs(project.ticket_of(self.conn, 1).status, TicketStatus.CLOSED)


if __name__ == "__main__":
    unittest.main()
