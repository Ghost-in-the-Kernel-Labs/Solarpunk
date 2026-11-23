"""13.20 (SP-055): a ping that answers records its own reachable pass, beside the failure a dead feed records."""
from solarpunk import project
from solarpunk.project import run
from solarpunk.remote import results
from test.solarpunk.test_project_run import INV1, INV2, RUN_AT, RunFixture


def pings_of(fixture: RunFixture, asset_id: str) -> list[results.Recorded]:
    """The reachable results stored for the asset, in the order stored: pings_of(self, INV1) is one pass before any suite."""
    stored = project.asset_results(fixture.conn, asset_id)
    return [found for found, _ in sorted(stored, key=lambda pair: pair[0].result_id) if found.test_name == "reachable"]


class ThePingsOwnResult(RunFixture):
    def test_a_live_feed_stores_answered_with_its_new_records_untimed(self) -> None:
        found = run.ping_all(self.conn, run.fed_only(project.fleet_assets(self.conn, None)), RUN_AT)
        self.assertEqual(found.stored, 3)
        (ping,) = pings_of(self, INV1)
        self.assertEqual((ping.passed, ping.reason, ping.no_data, ping.suite, ping.duration_ms),
                         (True, "answered: 24 new records", False, results.ALL, None))

    def test_a_second_ping_of_the_same_day_answers_with_no_new_records(self) -> None:
        assets = run.fed_only(project.fleet_assets(self.conn, None))
        run.ping_all(self.conn, assets, RUN_AT)
        run.ping_all(self.conn, assets, RUN_AT)
        self.assertEqual([ping.reason for ping in pings_of(self, INV1)],
                         ["answered: 24 new records", "answered: 0 new records"])

    def test_a_dead_feed_stores_its_failure_as_before_and_no_pass(self) -> None:
        run.ping_all(self.conn, run.fed_only(project.fleet_assets(self.conn, None)), RUN_AT)
        (ping,) = pings_of(self, INV2)
        self.assertEqual((ping.passed, ping.failed, ping.duration_ms), (False, True, None))
        self.assertTrue(ping.reason.endswith("is unreachable"))
