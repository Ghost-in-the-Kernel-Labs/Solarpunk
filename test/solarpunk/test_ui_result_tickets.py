"""The "Open a ticket" control on a failed test result (7.9, SP-046): in the asset window's diagnostics and the Runs
window's results, acting on the selected failed result and never on the asset; a result already in a ticket shows that
ticket; a pass, or no result selected, is refused in the window's own line; the Tickets window lists the failed results of
the chosen ticket. Over the demo store, whose weather station's reachable failed at 13:00 and raised SEN-001, no ticket
yet. Skips "no tkinter" or "no display" as test_ui_tickets.py does."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.ui import demo, ticket_text

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import asset_window, runs_window, tickets_window


class TheWords(unittest.TestCase):
    def test_what_the_control_says(self) -> None:
        self.assertEqual(ticket_text.OPEN_TICKET, "Open a ticket")
        self.assertEqual(ticket_text.results_text(()), ticket_text.NO_RESULTS)
        self.assertEqual(ticket_text.result_row(project.Recorded("reachable", "OAHE-SEN-001", at(2026, 6, 1, 13), False, "x")),
                         ("reachable", "2026-06-01 13:00 UTC", "x"))


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

    def open_in_asset_window(self) -> "asset_window.AssetWindow":
        """The weather station's asset window, drawn: its diagnostics hold the failed reachable."""
        window = asset_window.AssetWindow(self.root, self.conn, demo.SENSOR)
        self.root.update()
        return window

    def failing_row(self, window: "asset_window.AssetWindow") -> str:
        """The diagnostics row of the failed test, as the tree's id: "0" when it is listed first."""
        return next(str(i) for i, d in enumerate(window.detail.diagnostics) if d.state == "fail")

    def test_the_asset_window_opens_a_ticket_on_the_selected_failed_result_then_shows_it(self) -> None:
        window = self.open_in_asset_window()
        window.assigned_by_box.set(demo.SITE_ENGINEER)
        window.result_tree.selection_set(self.failing_row(window))
        window.open_ticket_button.invoke()
        (order,) = [o for o in project.work_orders_for(self.conn, demo.SENSOR) if o.closed is None]
        self.assertEqual(len(project.results_of_ticket(self.conn, order.wo_id)), 1)
        self.assertIn(f"Ticket {order.wo_id} opened", window.message.cget("text"))
        window.open_ticket_button.invoke()
        self.assertIn("already holds", window.message.cget("text"))
        self.assertEqual(len([o for o in project.work_orders_for(self.conn, demo.SENSOR) if o.closed is None]), 1)
        self.assertIn("Failed results: 1", window.ticket_panel.results.cget("text"))

    def test_a_pass_or_nothing_selected_opens_no_ticket(self) -> None:
        window = self.open_in_asset_window()
        window.assigned_by_box.set(demo.SITE_ENGINEER)
        window.open_ticket_button.invoke()
        self.assertEqual(window.message.cget("text"), ticket_text.CHOOSE_FAILED)
        passing = next((str(i) for i, d in enumerate(window.detail.diagnostics) if d.state == "pass"), None)
        if passing is not None:
            window.result_tree.selection_set(passing)
            window.open_ticket_button.invoke()
            self.assertEqual(window.message.cget("text"), ticket_text.CHOOSE_FAILED)
        self.assertEqual(project.work_orders_for(self.conn, demo.SENSOR), ())

    def test_the_runs_window_opens_it_on_a_runs_failed_result(self) -> None:
        window = runs_window.RunsWindow(self.root, self.conn, demo.SENSOR)
        self.root.update()
        window.who.chosen.set(demo.SITE_ENGINEER)
        failed = next(str(i) for i, r in enumerate(window.runs[0].results) if r.failed)
        window.result_tree.selection_set(failed)
        window.open_ticket_button.invoke()
        self.assertIn("opened", window.ticket_line.cget("text"))
        self.assertEqual(len(project.open_tickets(self.conn)), 2)  # the demo's outage ticket and this one

    def test_the_tickets_window_lists_the_chosen_tickets_failed_results(self) -> None:
        window = self.open_in_asset_window()
        window.assigned_by_box.set(demo.SITE_ENGINEER)
        window.result_tree.selection_set(self.failing_row(window))
        window.open_ticket_button.invoke()
        tickets = tickets_window.TicketsWindow(self.root, self.conn, lambda asset_id: None, lambda: at(2026, 6, 1, 14))
        self.root.update()
        for item in tickets.tree.get_children():
            tickets.tree.selection_set(item)
            self.root.update()
            if tickets.views[int(item)].ticket.asset_id == demo.SENSOR:
                (row,) = tickets.result_tree.get_children()
                self.assertEqual(tickets.result_tree.item(row, "values")[0], "reachable")


if __name__ == "__main__":
    unittest.main()
