"""The demo's ISO walk clicked end to end (13.22, SP-053), under a display: on the live demo store OAHE-INV-002's asset
window opens a ticket from the failed `reachable` result, the ticket panel chooses it over the overdue INV-001 ticket,
acknowledges, comments, is refused on resolve for want of a root cause, the cause is written in the asset window, resolve
is refused again for want of a pass (13.21, SP-055), "Bring the feed back (demo)" is pressed, the ticket resolves, and the
closed ticket's trail reads in time order, every move the engineer's, the failed result followed by the ping's pass, stamped
after the last act before the revival. Also the chooser's words, headless. Skips with "no display"."""
import gc
import io
import itertools
import os
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.ui import demo, ticket_text
from test.solarpunk import test_demo

INV2 = test_demo.INV2
ENGINEER = demo.ENGINEER
if test_demo.HAS_TKINTER:
    from solarpunk.ui import __main__ as entry
    from solarpunk.ui import asset_window


class TheChooserWords(test_demo.DemoFixture):
    def test_a_ticket_in_the_chooser_reads_its_id_code_priority_and_status(self) -> None:
        demo.build_demo_store(self.path, self.port, self.dead)
        conn = self.opened()
        (view,) = project.tickets_by_target(conn, at(2026, 6, 1, 13))
        self.assertEqual(ticket_text.choice_text(view, "INV-001"), "3 INV-001 P1 open")
        self.assertEqual(ticket_text.choice_text(view, None), "3 preventive P1 open")


@unittest.skipUnless(test_demo.display_available(), "no display")
class TheWalkInTheWindows(test_demo.DemoFixture):
    def setUp(self) -> None:
        """The demo run in the fixture's folder, put back when the test ends; collected so Tk is freed on this thread."""
        super().setUp()
        here = Path.cwd()
        os.chdir(self.folder)
        self.addCleanup(os.chdir, here)
        self.addCleanup(gc.collect)  # Tk freed off the main thread aborts the run (J-146)

    def walk(self, root: "entry.tkinter.Tk") -> None:
        """Does steps 4 and 5 of DEMO.md's walk in OAHE-INV-002's asset window and keeps what it saw in self.seen."""
        root.update()
        frame = root.demo_fleet
        window = frame.on_open_asset(INV2)
        root.update()
        panel = window.ticket_panel
        minutes = itertools.count(5)  # the wall seconds of a real walk, made minutes so each act is later than the last

        def step() -> datetime:
            """The next instant of the walk: 13:05 on the demo's day, then a minute later at each call."""
            return at(2026, 6, 1, 13) + timedelta(minutes=next(minutes))

        window.now = panel.now = window.open_ticket_button.now = root.demo_revival.now = step
        self.seen["first"] = panel.view.ticket.wo_id  # the overdue INV-001 ticket stands nearest
        failed = next(i for i, d in enumerate(window.detail.diagnostics) if d.test_name == "reachable")
        window.result_tree.selection_set(str(failed))
        window.open_ticket_button.invoke()
        self.seen["opened"] = panel.view.ticket.wo_id
        self.seen["choices"] = tuple(panel.chooser.cget("values"))
        self.act_and_resolve(window)
        self.seen["acts"] = project.last_ticket_act(frame.conn, INV2)  # the last act stored before the feed comes back
        window.revive_button.invoke()
        panel.done_box.delete(0, "end")
        panel.done_box.insert(0, "Reseated the uplink cable")
        panel.resolve_button.invoke()
        self.seen["trail"] = project.ticket_trail(frame.conn, 4)
        window.destroy()
        root.destroy()

    def act_and_resolve(self, window: "asset_window.AssetWindow") -> None:
        """Acknowledges, comments, is refused on resolve, writes the cause in the asset window and is refused again."""
        panel = window.ticket_panel
        panel.ack_button.invoke()
        panel.comment_box.insert(0, "Feed did not answer at the 13:00 run; datalogger link being traced.")
        panel.comment_button.invoke()
        panel.done_box.insert(0, "Reseated the uplink cable")
        panel.resolve_button.invoke()
        self.seen["refusal"] = panel.message.cget("text")
        window.fault_tree.selection_set("5")
        window.cause_box.insert(0, "Datalogger uplink cable unplugged before the 13:00 run")
        window.cause_button.invoke()
        panel.resolve_button.invoke()
        self.seen["no pass"] = panel.message.cget("text")

    def test_the_corrective_acts_are_clicked_on_the_ticket_chosen_and_the_trail_reads_in_order(self) -> None:
        self.seen: dict[str, object] = {}
        entry.main(["--demo"], io.StringIO(), self.walk)
        seen = self.seen
        self.assertEqual(seen["first"], 3)
        self.assertEqual(seen["opened"], 4)
        self.assertEqual(seen["choices"], ("3 INV-001 P1 open", "4 SIT-004 P3 open"))
        self.assertEqual(seen["refusal"], "fault 5 has no root cause written: an engineer writes it before its ticket closes")
        self.assertEqual(seen["no pass"], "ticket 4 waits for a pass: reachable on OAHE-INV-002 has not passed since its "
                                          "failure at 2026-06-01T13:00:00+00:00")
        trail = seen["trail"]
        moments = [move.moment for move in trail.moves]
        self.assertEqual(moments, sorted(moments))
        self.assertEqual({move.actor for move in trail.moves}, {ENGINEER})
        self.assertEqual([move.status.value for move in trail.moves], ["open", "acknowledged", "in progress", "resolved", "closed"])
        self.assertEqual({comment.author for comment in trail.comments}, {ENGINEER})
        (held,) = trail.results
        self.assertFalse(held.result.passed)
        self.assertTrue(held.next_result is not None and held.next_result.passed)
        self.assertEqual((held.next_result.test_name, held.next_result.reason), ("reachable", "answered: 0 new records"))
        self.assertGreater(held.next_result.run_at, seen["acts"])  # the pass follows the last act stored before it
        self.assertGreaterEqual(held.next_result.run_at, seen["acts"] + timedelta(minutes=1))
        self.assertGreater(trail.ticket.closed, held.next_result.run_at)  # and the close follows the pass


if __name__ == "__main__":
    unittest.main()
