"""The tickets in the windows (11.2, SOL-14): the words headless (ticket_text: a target in words, a ticket's row, the
panel's line, the root causes), then under a display over the demo store at 13:00: the Tickets window's rows, the
nearest target first, a breach red, a double click opening the asset; the asset window's ticket panel acknowledging,
commenting (an author needed) and resolving (a cause needed), which closes the fault and turns the asset green.
Skips "no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetStatus
from solarpunk.ui import demo, ticket_text

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import __main__ as entry
    from solarpunk.ui import asset_window, tickets_window

ONE = at(2026, 6, 1, 13)
OVERDUE = "OVERDUE, due 2026-06-01 12:30 UTC"
PENDING = "pending, due 2026-06-01 15:30 UTC"


class TheWords(unittest.TestCase):
    def test_a_target_in_words(self) -> None:
        self.assertEqual(ticket_text.target_cell(project.TargetState.OVERDUE, at(2026, 6, 1, 12, 30)), OVERDUE)
        self.assertEqual(ticket_text.target_cell(project.TargetState.PENDING, at(2026, 6, 1, 15, 30)), PENDING)
        self.assertEqual(ticket_text.target_cell(project.TargetState.MET, at(2026, 6, 1, 12, 30)), "met")
        self.assertEqual(ticket_text.target_cell(None, None), "—")

    def test_no_root_cause_list_is_offered(self) -> None:
        self.assertFalse(hasattr(ticket_text, "cause_choices"))  # SP-046: the cause is free text, written in the asset window


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheWindows(unittest.TestCase):
    def setUp(self) -> None:
        """The demo store with its simulator, in a hidden root, or skipped with no display."""
        try:
            self.root = tkinter.Tk()
        except tkinter.TclError:
            self.skipTest("no display")
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        server, port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port)
        self.conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        self.addCleanup(self.conn.close)

    def test_the_tickets_window_lists_the_nearest_target_first_a_breach_red(self) -> None:
        project.assign_fault(self.conn, demo.FED, "INV-001", at(2026, 6, 1, 12, 50), demo.ENGINEER)  # 13.15: the store holds accounts
        opened: list[str] = []
        window = tickets_window.TicketsWindow(self.root, self.conn, opened.append, now=lambda: ONE)
        self.root.update()
        first, second = window.tree.get_children()
        self.assertEqual(window.tree.item(first, "values"),
                         ("3", demo.DOWN, "P1", "open", OVERDUE, PENDING, "2026-06-01 11:30 UTC"))
        self.assertEqual(window.tree.item(first, "tags"), (tickets_window.BREACHED_TAG,))
        self.assertEqual(window.tree.item(second, "values")[1], demo.FED)
        self.assertEqual(window.tree.item(second, "tags"), "")
        window.tree.selection_set(second)
        window.open_chosen()
        self.assertEqual(opened, [demo.FED])

    def test_show_closed_adds_closed_tickets_and_the_chosen_ticket_shows_its_trail(self) -> None:
        project.write_fault_cause(self.conn, 3, "the AC breaker tripped", demo.ENGINEER, at(2026, 6, 1, 12))
        project.resolve_ticket(self.conn, 3, "AC breaker reset", at(2026, 6, 1, 12, 30))
        window = tickets_window.TicketsWindow(self.root, self.conn, lambda asset_id: None, now=lambda: ONE)
        self.root.update()
        open_rows = window.tree.get_children()
        window.closed_check.invoke()
        row = next(item for item in window.tree.get_children() if window.views[int(item)].ticket.wo_id == 3)
        self.assertEqual(window.tree.item(row, "values")[3], "closed")
        window.tree.selection_set(row)
        self.root.update()
        shown = window.trail.get("1.0", "end").strip()
        self.assertEqual(shown, project.trail_text(project.ticket_trail(self.conn, 3)))
        self.assertIn("the AC breaker tripped  (stands)", shown)
        self.assertIn("closed 2026-06-01T12:30:00+00:00  AC breaker reset", shown)
        self.assertEqual(str(window.trail.cget("state")), "disabled")
        window.closed_check.invoke()
        self.assertEqual(window.tree.get_children(), open_rows)

    def test_the_panel_acknowledges_comments_and_resolves(self) -> None:
        changes: list[int] = []
        window = asset_window.AssetWindow(self.root, self.conn, demo.DOWN, lambda: changes.append(1),
                                          project.account_of(self.conn, demo.ENGINEER))  # 13.15: the engineer acts, no By box
        panel = window.ticket_panel
        panel.now = lambda: ONE
        panel.refresh()
        self.assertEqual(panel.line.cget("text"), f"Ticket 3 · P1 · open · acknowledge {OVERDUE} · respond {PENDING}")
        panel.ack_button.invoke()
        self.assertEqual(project.ticket_of(self.conn, 3).acknowledged, ONE)
        self.assertIn("acknowledge late", panel.line.cget("text"))
        self.assertEqual([m.actor for m in project.ticket_moves(self.conn, 3)], [demo.ENGINEER])
        panel.comment_button.invoke()
        self.assertEqual(panel.message.cget("text"), "a comment on work order 3 needs an author and words")  # no words yet
        panel.comment_box.insert(0, "on my way")
        panel.comment_button.invoke()
        self.assertEqual([(c.body, c.author) for c in project.ticket_comments(self.conn, 3)], [("on my way", demo.ENGINEER)])
        panel.done_box.insert(0, "AC breaker reset")
        panel.resolve_button.invoke()
        self.assertEqual(panel.message.cget("text"),
                         "fault 3 has no root cause written: an engineer writes it before its ticket closes")
        window.fault_tree.selection_set("3")  # SP-047: the lost link's SIT-004 is open beside the outage, so the fault is chosen
        # the cause is written in the asset window, as free text, by the engineer signed in (SP-046)
        window.cause_box.insert(0, "the AC breaker tripped on a grid surge")
        window.cause_button.invoke()
        self.assertEqual(window.message.cget("text"), "")
        panel.resolve_button.invoke()
        self.assertEqual((panel.message.cget("text"), panel.line.cget("text")), ("", "No open ticket"))
        self.assertIs(project.asset_status(self.conn, demo.DOWN), AssetStatus.YELLOW)  # outage closed; ping still fails
        self.assertEqual(len(changes), 4)

    def test_the_program_opens_the_tickets_window(self) -> None:
        top = tkinter.Toplevel(self.root)
        fleet = entry.open_fleet(top, self.conn)
        fleet.tickets_button.invoke()
        self.root.update()
        self.assertEqual(len([w for w in top.winfo_children() if isinstance(w, tickets_window.TicketsWindow)]), 1)


if __name__ == "__main__":
    unittest.main()
