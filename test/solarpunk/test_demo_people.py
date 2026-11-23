"""The demo's people, day and outage (13.15, SP-053), headless: the store holds an engineer's and an operator's account,
OAHE-INV-002's stored power is 0 from its INV-001 outage's start (11:30), the demo's clock is the run instant plus the
wall seconds since it started, and the revival runs on it. What the dead inverter's tests show at the run and after the
revival is read here. The window half is in test_demo.py (the status bar's account, an act stamped on 2026-06-01)."""
import unittest
from datetime import timedelta

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.telemetry import samples as sample_table
from solarpunk.ui import demo
from test.solarpunk import test_demo

INV2 = test_demo.INV2
RUN_AT = test_demo.RUN_AT


class ThePeopleAndTheDay(test_demo.DemoFixture):
    """13.15: the demo store holds an engineer and an operator, its dead inverter delivers nothing from its outage's
    start, and the demo has a day of its own."""

    def test_the_store_holds_both_accounts_and_the_passwords_sign_in(self) -> None:
        demo.build_demo_store(self.path, self.port, self.dead)
        conn = self.opened()
        self.assertEqual([(a.email, a.role.value, a.sites) for a in project.accounts(conn)],
                         [("engineer@oahe.example", "engineer", ("OAHE",)), ("operator@oahe.example", "operator", ("OAHE",))])
        self.assertTrue(project.needs_sign_in(conn))
        for email, _name, _role, password in demo.ACCOUNTS:
            self.assertEqual(project.sign_in(conn, email, password, RUN_AT).email, email)
        self.assertGreaterEqual(min(len(password) for *_rest, password in demo.ACCOUNTS), 12)

    def test_the_dead_inverters_stored_power_is_zero_from_its_outage_to_the_days_end(self) -> None:
        demo.build_demo_store(self.path, self.port, self.dead)
        stored = sample_table.in_period(self.opened(), INV2, project.day_period(demo.DAY))
        after = [s for s in stored if s.moment >= at(2026, 6, 1, 11, 30) and not s.gap]
        self.assertEqual((len(after), {s.power_kw for s in after}), (len(after), {0.0}))
        self.assertGreater(len(after), 100)
        self.assertGreater(max(s.power_kw for s in stored if s.moment < at(2026, 6, 1, 11, 30) and not s.gap), 50)

    def test_the_demos_clock_is_the_run_instant_plus_the_wall_seconds_since_it_started(self) -> None:
        wall = iter((100.0, 100.0, 190.7))
        now = demo.demo_clock(lambda: next(wall))
        self.assertEqual((now(), now()), (RUN_AT, RUN_AT + timedelta(seconds=90)))

    def test_the_revival_runs_on_the_demos_clock_and_never_before_an_earlier_run(self) -> None:
        demo.build_demo_store(self.path, self.port, self.dead)
        conn = self.opened()
        revival = demo.Revival(self.dead, lambda: at(2026, 6, 1, 13, 2))
        self.addCleanup(revival.close)
        revival.bring_back(conn, INV2)
        revival.bring_back(conn, INV2)
        instants = [row[0] for row in conn.execute("SELECT DISTINCT run_at FROM results WHERE asset_id = ? ORDER BY run_at", (INV2,))]
        self.assertEqual(instants, [at(2026, 6, 1, 13).isoformat(), at(2026, 6, 1, 13, 2).isoformat(),
                                    (at(2026, 6, 1, 13, 2) + timedelta(seconds=1)).isoformat()])

    def test_the_inverters_tests_at_the_run_and_after_the_revival(self) -> None:
        demo.build_demo_store(self.path, self.port, self.dead)
        conn = self.opened()
        self.assertEqual({d.test_name: d.state for d in project.asset_detail(conn, INV2).diagnostics},
                         {"performance_above_floor": "fail", "reachable": "fail", "power_ripple": "no data", "irradiance_in_range": "pass",
                          "night_power_near_zero": "pass", "on_grid": "pass", "power_not_frozen": "pass", "power_under_rated": "pass"})
        revival = demo.Revival(self.dead, lambda: at(2026, 6, 1, 13, 2))
        self.addCleanup(revival.close)
        revival.bring_back(conn, INV2)
        after = {d.test_name: d.state for d in project.asset_detail(conn, INV2).diagnostics}
        self.assertEqual((after["reachable"], after["power_ripple"], after["performance_above_floor"]), ("pass", "pass", "fail"))

    def test_the_floor_and_the_lost_link_are_each_their_own_fault_through_the_revivals(self) -> None:
        """13.18, SP-054: the run raises INV-005 (test:performance_above_floor) and SIT-004 (test:reachable) beside the
        outage; a revival closes nothing; SIT-004's ticket closes it; INV-005 stays, and a second revival raises no new SIT-004."""
        demo.build_demo_store(self.path, self.port, self.dead)
        conn = self.opened()

        def open_faults() -> list[tuple[str, str]]:
            """OAHE-INV-002's open faults as (code, assigned_by): [("INV-001", "inverter@oahe.example"), ...]."""
            return [(f.code, f.assigned_by) for f in project.faults_listing(conn, True) if f.asset_id == INV2]
        floor, lost = ("INV-005", "test:performance_above_floor"), ("SIT-004", "test:reachable")
        self.assertEqual(open_faults(), [("INV-001", demo.INVERTER_ENGINEER), floor, lost])
        revival = demo.Revival(self.dead, lambda: at(2026, 6, 1, 13, 2))
        self.addCleanup(revival.close)
        revival.bring_back(conn, INV2)
        self.assertEqual(open_faults(), [("INV-001", demo.INVERTER_ENGINEER), floor, lost])  # a passing test closes no fault
        link = next(f for f in project.faults_listing(conn, True) if f.code == "SIT-004")
        order = project.open_work_order_from_fault(conn, link.fault_id, at(2026, 6, 1, 13, 10), "feed restored")
        project.write_fault_cause(conn, link.fault_id, "feed process stopped", demo.ACCOUNTS[0][0], at(2026, 6, 1, 13, 11))
        project.resolve_ticket(conn, order.wo_id, "feed restarted", at(2026, 6, 1, 13, 12))
        self.assertEqual(open_faults(), [("INV-001", demo.INVERTER_ENGINEER), floor])
        revival.bring_back(conn, INV2)
        self.assertEqual(open_faults(), [("INV-001", demo.INVERTER_ENGINEER), floor])


if __name__ == "__main__":
    unittest.main()
