"""The scheduled run and the windows' surface (2.7): the OAHE run fixture with a feed simulator for OAHE-INV-001 on an
ephemeral port, a port nobody listens on for OAHE-INV-002 (a failing reachable: YELLOW) and an open INV-001 on
OAHE-INV-003 (RED), mailed through a minimal fake SMTP server copied from test_mailer.py's pattern, never imported."""
import json
import socket
import socketserver
import sqlite3
import tempfile
import threading
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from solarpunk import project
from solarpunk.faults import ledger
from solarpunk.feed import client, simulate
from solarpunk.fleet import registry
from solarpunk.leaf import asset_types, codes
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import NotUtc, Period, at
from solarpunk.leaf.codes import AssetKind, AssetStatus
from solarpunk.leaf.telemetry import Sample
from solarpunk.mailer import mail as mailer
from solarpunk.mailer.transport import BadSettings
from solarpunk.project import run, surface
from solarpunk.remote import registry as remote_registry
from solarpunk.remote import results
from solarpunk.telemetry import generate as generator
from solarpunk.telemetry import samples as sample_table

ENGINEER = "site@oahe.example"  # SP-015: a fault names the engineer who assigned it; the fixtures' site engineer

SITE_EMAIL = "site@oahe.example"
INVERTER_EMAIL = "inverter@oahe.example"
SENDER = "ops@oahe.example"
INV1 = "OAHE-INV-001"
INV2 = "OAHE-INV-002"
INV3 = "OAHE-INV-003"
LOCAL = "127.0.0.1"
# The OAHE fixture's site, inverters and strings, copied from test_fleet.py, with a third inverter for the outage; the
# trackers, meter and sensor are left out, since each would need a feed of its own to pass reachable.
SITE = Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None, location="Pierre, SD", engineer_email=SITE_EMAIL)
INVERTER_1 = Asset(INV1, AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 1", 100.0, LOCAL, 1, "Pad A",
                   INVERTER_EMAIL)
INVERTER_2 = Asset(INV2, AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 2", 100.0, LOCAL, 1, "Pad B")
INVERTER_3 = Asset(INV3, AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 3", 100.0, LOCAL, 1, "Pad C")
STRINGS = (
    Asset("OAHE-STR-001", AssetKind.STRING, "OAHE", INV1, "String 1", 50.0),
    Asset("OAHE-STR-002", AssetKind.STRING, "OAHE", INV1, "String 2", 50.0),
    Asset("OAHE-STR-003", AssetKind.STRING, "OAHE", INV2, "String 3", 50.0),
)
# A site with no engineer anywhere, so a mail to it has nobody to go to.
BIGS = (
    Asset("BIGS-SIT-001", AssetKind.SITE, "BIGS", None, "Big Stone", None),
    Asset("BIGS-INV-001", AssetKind.INVERTER, "BIGS", "BIGS-SIT-001", "Inverter 1", 50.0),
)
FED = Period(at(2026, 6, 1, 10), at(2026, 6, 1, 12))
RUN_AT = at(2026, 6, 1, 12)
GREEN_ONES = ("OAHE-SIT-001", INV1, "OAHE-STR-001", "OAHE-STR-002", "OAHE-STR-003")


def free_port() -> int:
    """A port nothing listens on just now: free_port() is some int from 1 to 65535."""
    with socket.socket() as probe:
        probe.bind((LOCAL, 0))
        return probe.getsockname()[1]


def count(conn: sqlite3.Connection, table: str) -> int:
    """The rows of one table: count(project.open_store(), "mails") is 0."""
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


class FakeSmtp(socketserver.TCPServer):
    """A one-thread SMTP fake on 127.0.0.1 and an ephemeral port that keeps each DATA payload: FakeSmtp().data is []."""

    def __init__(self) -> None:
        """Binds 127.0.0.1 port 0: FakeSmtp().server_address[1] is the port."""
        self.data: list[str] = []
        super().__init__((LOCAL, 0), FakeSmtpHandler)


class FakeSmtpHandler(socketserver.StreamRequestHandler):
    """Speaks enough SMTP for a plain mail: 220, then 250 to every verb, 354 for DATA, 221 for QUIT."""

    def say(self, reply: str) -> None:
        """Writes one reply with CRLF: say("250 OK") sends b"250 OK\\r\\n"."""
        self.wfile.write(reply.encode() + b"\r\n")

    def handle(self) -> None:
        """Answers one session until QUIT: a DATA payload up to the lone dot is appended to the server's data."""
        server: FakeSmtp = self.server  # type: ignore[assignment]
        self.say("220 fake")
        for raw in self.rfile:
            verb = raw.decode().split(" ", 1)[0].strip().upper()
            if verb == "QUIT":
                self.say("221 bye")
                return
            if verb == "DATA":
                self.say("354 go")
                server.data.append("".join(line.decode() for line in iter(self.rfile.readline, b".\r\n")))
            self.say("250 OK")


class RunFixture(unittest.TestCase):
    """The run fixture: a simulator serving FED's generated samples for OAHE-INV-001, a closed port for OAHE-INV-002
    and OAHE-INV-003, an open INV-001 on OAHE-INV-003, and the stores and servers closed when a test ends."""

    def setUp(self) -> None:
        """The simulator running and the fleet loaded: self.fed is the 24 samples the simulator serves."""
        self.fed = generator.generate((INVERTER_1,), FED, 7)
        self.feed = simulate.make_server(self.fed, LOCAL, 0)
        threading.Thread(target=self.feed.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
        self.addCleanup(self.feed.server_close)
        self.addCleanup(self.feed.shutdown)
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        dead = free_port()
        fleet = (
            SITE,
            replace(INVERTER_1, port=self.feed.server_address[1]),
            replace(INVERTER_2, port=dead),
            replace(INVERTER_3, port=dead),
        ) + STRINGS
        project.load_fleet(self.conn, fleet)
        self.outage = project.assign_fault(self.conn, INV3, "INV-001", at(2026, 6, 1, 9), ENGINEER)

    def smtp(self) -> FakeSmtp:
        """A running fake SMTP server, stopped when the test ends: self.smtp().data is []."""
        server = FakeSmtp()
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def settings(self, port: int) -> Path:
        """A settings file reaching 127.0.0.1 on a port, no login: self.settings(25).name is "mail.json"."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "mail.json"
        values = {"host": LOCAL, "port": port, "sender": SENDER, "starttls": False, "password_variable": None,
                  "username": None}
        path.write_text(json.dumps(values))
        return path


# 3 inverters' tests, and a ping's reachable for each of the 3 fed assets: 2 failures (SP-017), 1 pass (SP-055)
RESULTS_PER_RUN = 3 * len(remote_registry.tests_for(AssetKind.INVERTER)) + 3


class TheScheduledRun(RunFixture):
    def test_one_green_one_yellow_one_red_and_the_counts(self) -> None:
        report = project.scheduled_run(self.conn, RUN_AT)
        self.assertEqual(len(self.fed), 24)
        self.assertEqual((report.pinged, report.records, report.results, report.mails), (3, 24, RESULTS_PER_RUN, 0))
        self.assertIs(report.statuses[INV2], AssetStatus.YELLOW)  # SP-047: its failing reachable raised SIT-004, INFO
        self.assertIs(report.statuses[INV3], AssetStatus.RED)
        self.assertEqual({report.statuses[asset_id] for asset_id in GREEN_ONES}, {AssetStatus.GREEN})
        self.assertEqual(sorted(report.statuses), sorted(GREEN_ONES + (INV2, INV3)))
        port = INVERTER_2.host, registry.get(self.conn, INV2).port
        self.assertEqual(report.errors, tuple(f"{a}: {port[0]}:{port[1]} is unreachable" for a in (INV2, INV3)))
        self.assertEqual(count(self.conn, "samples"), 24)
        self.assertEqual(count(self.conn, "results"), report.results)
        self.assertEqual(count(self.conn, "mails"), 0)

    def test_the_statuses_read_back_agree_with_the_report(self) -> None:
        report = project.scheduled_run(self.conn, RUN_AT)
        self.assertEqual({a: project.asset_status(self.conn, a) for a in report.statuses}, report.statuses)

    def test_a_failed_ping_is_a_failing_reachable_result_with_the_feeds_message(self) -> None:
        project.scheduled_run(self.conn, RUN_AT)
        port = registry.get(self.conn, INV2).port
        reasons = [(r.test_name, r.reason) for r in results.latest_for(self.conn, INV2) if not r.passed]
        self.assertIn(("reachable", f"{LOCAL}:{port} is unreachable"), reasons)
        self.assertEqual({r.run_at for r in results.latest_for(self.conn, INV2)}, {RUN_AT})
        self.assertTrue(all(r.passed for r in results.latest_for(self.conn, INV1) if r.test_name != "power_ripple"))

    def test_a_second_run_stores_no_sample_twice(self) -> None:
        project.scheduled_run(self.conn, RUN_AT)
        again = project.scheduled_run(self.conn, RUN_AT + timedelta(minutes=5))
        self.assertEqual((again.pinged, again.records), (3, 0))
        self.assertEqual(count(self.conn, "samples"), 24)
        self.assertIs(again.statuses[INV1], AssetStatus.GREEN)

    def test_samples_outside_the_last_day_are_not_tested(self) -> None:
        report = project.scheduled_run(self.conn, RUN_AT + timedelta(days=1, minutes=5))
        self.assertEqual(report.records, 24)
        self.assertIs(report.statuses[INV1], AssetStatus.YELLOW)  # SP-047: reachable failed, so SIT-004 opened

    def test_an_unreachable_asset_with_samples_stored_earlier_is_yellow_by_its_tests_fault(self) -> None:
        sample_table.store(self.conn, generator.generate((INVERTER_2,), FED, 7))
        report = project.scheduled_run(self.conn, RUN_AT)
        self.assertIs(report.statuses[INV2], AssetStatus.YELLOW)  # SP-047: a lost link raises the generic SIT-004, no outage
        self.assertIs(project.asset_status(self.conn, INV2), AssetStatus.YELLOW)

    def test_a_closed_outage_is_not_raised_again_by_a_lost_link(self) -> None:
        project.close_fault(self.conn, self.outage.fault_id, at(2026, 6, 1, 10))
        self.assertIs(project.scheduled_run(self.conn, RUN_AT).statuses[INV3], AssetStatus.YELLOW)  # SP-047: SIT-004, INFO

    def test_an_asset_with_no_endpoint_is_not_tested_and_takes_its_status_from_its_faults(self) -> None:
        tracker = Asset("OAHE-TRK-001", AssetKind.TRACKER, "OAHE", "OAHE-SIT-001", "Tracker 1", None)
        silent = Asset("OAHE-INV-004", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 4", 100.0)
        project.load_fleet(self.conn, (tracker, silent))
        project.assign_fault(self.conn, "OAHE-STR-001", "STR-001", at(2026, 6, 1, 9), ENGINEER)
        project.assign_fault(self.conn, silent.asset_id, "INV-001", at(2026, 6, 1, 9), ENGINEER)
        report = project.scheduled_run(self.conn, RUN_AT)
        self.assertEqual((report.pinged, report.results), (3, RESULTS_PER_RUN))
        self.assertIs(report.statuses[tracker.asset_id], AssetStatus.GREEN)
        self.assertIs(report.statuses["OAHE-STR-001"], AssetStatus.GREEN)
        self.assertIs(report.statuses[silent.asset_id], AssetStatus.RED)
        self.assertEqual((results.latest_for(self.conn, tracker.asset_id), results.latest_for(self.conn, silent.asset_id)),
                         ((), ()))
        self.assertEqual({a: project.asset_status(self.conn, a) for a in report.statuses}, report.statuses)
        self.assertEqual(count(self.conn, "results"), report.results)

    def test_a_naive_run_at_is_refused(self) -> None:
        with self.assertRaises(NotUtc):
            project.scheduled_run(self.conn, RUN_AT.replace(tzinfo=None))


class TheMails(RunFixture):
    def test_the_red_and_the_yellow_asset_are_mailed_and_recorded(self) -> None:
        server = self.smtp()
        report = project.scheduled_run(self.conn, RUN_AT, self.settings(server.server_address[1]))
        self.assertEqual(report.mails, 2)
        self.assertEqual(len(server.data), 2)
        self.assertEqual(count(self.conn, "mails"), 2)
        red = mailer.sent_for(self.conn, INV3)
        self.assertEqual([(m.recipients, m.subject) for m in red], [((SITE_EMAIL,), "Solarpunk: OAHE-INV-003 INV-001")])
        self.assertIn("Cause: fault INV-001, Inverter offline", red[0].body)
        yellow = mailer.sent_for(self.conn, INV2)
        self.assertEqual([(m.recipients, m.subject) for m in yellow], [((SITE_EMAIL,), "Solarpunk: OAHE-INV-002 reachable")])
        self.assertIn("Cause: remote test reachable failed: ", yellow[0].body)  # SP-047: a lost link is no outage, the test is the cause
        self.assertIn("Instant: 2026-06-01T12:00:00+00:00", yellow[0].body)
        self.assertIn("Subject: Solarpunk: OAHE-INV-002 reachable", server.data[0])
        self.assertEqual(mailer.sent_for(self.conn, INV1), ())
        sent_at = {row[0] for row in self.conn.execute("SELECT sent_at FROM mails")}
        self.assertEqual(sent_at, {"2026-06-01T12:00:00+00:00"})

    def test_a_mail_that_cannot_go_is_an_error_and_the_run_goes_on(self) -> None:
        dead = free_port()
        report = project.scheduled_run(self.conn, RUN_AT, self.settings(dead))
        self.assertEqual(report.mails, 0)
        self.assertEqual(count(self.conn, "mails"), 0)
        self.assertEqual(report.errors[2:], tuple(f"{a}: mail to {LOCAL}:{dead} was not sent" for a in (INV2, INV3)))
        self.assertIs(report.statuses[INV1], AssetStatus.GREEN)

    def test_an_asset_with_nobody_to_mail_is_an_error_and_the_others_are_mailed(self) -> None:
        project.load_fleet(self.conn, BIGS)
        # BIGS-INV-001 has no endpoint, so the suite does not test it: an open outage is what makes it alert.
        project.assign_fault(self.conn, "BIGS-INV-001", "INV-001", at(2026, 6, 1, 9), ENGINEER)
        server = self.smtp()
        report = project.scheduled_run(self.conn, RUN_AT, self.settings(server.server_address[1]))
        self.assertEqual((report.mails, len(report.errors)), (2, 3))
        self.assertEqual(report.errors[2], "BIGS-INV-001: BIGS-INV-001: no engineer to mail")
        self.assertEqual(mailer.sent_for(self.conn, "BIGS-INV-001"), ())

    def test_bad_settings_are_refused_before_any_ping(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        with self.assertRaises(BadSettings):
            project.scheduled_run(self.conn, RUN_AT, Path(folder.name) / "missing.json")
        self.assertEqual((count(self.conn, "samples"), count(self.conn, "results")), (0, 0))


class TheHelpers(unittest.TestCase):
    def test_the_window_is_the_day_before_run_at_floored_to_the_grid(self) -> None:
        day = Period(at(2026, 6, 1), at(2026, 6, 2))
        self.assertEqual(run.window(at(2026, 6, 2)), day)
        self.assertEqual(run.window(at(2026, 6, 2) + timedelta(minutes=3, seconds=20, microseconds=5)), day)
        self.assertEqual(run.window(at(2026, 6, 2, 0, 5)).end, at(2026, 6, 2, 0, 5))

    def test_new_samples_leaves_out_the_stored_instants(self) -> None:
        conn = project.open_store()
        self.addCleanup(conn.close)
        made = generator.generate((INVERTER_1,), Period(at(2026, 6, 1, 10), at(2026, 6, 1, 10, 15)), 7)
        self.assertEqual(run.new_samples(conn, ()), ())
        self.assertEqual(run.new_samples(conn, made[:1]), made[:1])
        self.assertEqual(run.new_samples(conn, made), made)
        sample_table.store(conn, made[-1:])
        self.assertEqual(run.new_samples(conn, made), made[:-1])
        sample_table.store(conn, made[:1])
        self.assertEqual(run.new_samples(conn, made), made[1:2])

    def test_the_cause_is_the_outage_else_the_first_failing_latest_result(self) -> None:
        conn = project.open_store()
        self.addCleanup(conn.close)
        project.load_fleet(conn, (SITE, INVERTER_1))
        results.record(conn, "reachable", INV1, RUN_AT, results.Result(True, "3 records"))
        results.record(conn, "on_grid", INV1, RUN_AT, results.Result(False, "10:05: off the grid"))
        self.assertEqual(run.cause_of(conn, INV1, {}), mailer.RemoteFailure("on_grid", "10:05: off the grid"))
        outage = project.assign_fault(conn, INV1, "INV-001", RUN_AT, ENGINEER)
        self.assertEqual(run.cause_of(conn, INV1, project.open_outages(conn)), outage)

    def test_ping_all_adds_up_every_feeds_new_records(self) -> None:
        conn = project.open_store()
        self.addCleanup(conn.close)
        fleet = []
        for inverter in (INVERTER_1, INVERTER_2):
            server = simulate.make_server(generator.generate((inverter,), FED, 7), LOCAL, 0)
            threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            fleet.append(replace(inverter, port=server.server_address[1]))
        found = run.ping_all(conn, (SITE, *fleet, STRINGS[0]), RUN_AT)
        self.assertEqual(found, run.Pinged(2, 48, (), (), 2))
        self.assertEqual(count(conn, "samples"), 48)

    def test_stamped_never_leaves_an_unreachable_asset_green(self) -> None:
        found = run.stamped({"A": AssetStatus.GREEN, "B": AssetStatus.GREEN, "C": AssetStatus.RED}, ("A", "C"))
        self.assertEqual(found, {"A": AssetStatus.YELLOW, "B": AssetStatus.GREEN, "C": AssetStatus.RED})


class TheSurface(RunFixture):
    def test_rows_in_id_order_with_status_last_run_and_failing_test(self) -> None:
        project.scheduled_run(self.conn, RUN_AT)
        rows = {row.asset_id: row for row in project.asset_rows(self.conn)}
        ids = [row.asset_id for row in project.asset_rows(self.conn)]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual((rows[INV2].status, rows[INV2].suggested, rows[INV2].outage), (AssetStatus.YELLOW, None, None))  # SP-047
        self.assertEqual(rows[INV1], project.AssetRow(INV1, "Inverter 1", AssetKind.INVERTER, AssetStatus.GREEN,
                                                      RUN_AT, "—"))
        self.assertIs(rows[INV3].status, AssetStatus.RED)
        self.assertEqual((rows["OAHE-STR-001"].last_run_at, rows["OAHE-STR-001"].failing), (None, "—"))

    def test_rows_before_any_run(self) -> None:
        rows = project.asset_rows(self.conn)
        self.assertEqual(len(rows), 7)
        self.assertEqual({row.last_run_at for row in rows}, {None})

    def test_a_row_with_one_latest_result(self) -> None:
        results.record(self.conn, "on_grid", "OAHE-STR-001", RUN_AT, results.Result(False, "bad"))
        row = surface.row_of(self.conn, registry.get(self.conn, "OAHE-STR-001"))
        self.assertEqual((row.status, row.last_run_at, row.failing), (AssetStatus.YELLOW, RUN_AT, "on_grid"))

    def test_the_detail_holds_open_faults_latest_failing_first_engineers_and_status(self) -> None:
        project.scheduled_run(self.conn, RUN_AT)
        closed = project.assign_fault(self.conn, INV3, "INV-002", at(2026, 6, 1, 9), ENGINEER)
        project.close_fault(self.conn, closed.fault_id, at(2026, 6, 1, 10))
        info = project.assign_fault(self.conn, INV3, "INV-004", at(2026, 6, 1, 9), ENGINEER)
        detail = project.asset_detail(self.conn, INV3)
        (lost_link,) = (f for f in project.faults_listing(self.conn, True) if (f.asset_id, f.code) == (INV3, "SIT-004"))
        self.assertEqual(detail.asset, registry.get(self.conn, INV3))
        self.assertEqual(detail.open_faults, ((self.outage, codes.lookup("INV-001").meaning),  # SP-047: SIT-004, the lost link
                                              (lost_link, codes.lookup("SIT-004").meaning), (info, codes.lookup("INV-004").meaning)))
        self.assertEqual(detail.latest, results.latest_for(self.conn, INV3))
        self.assertEqual([r.passed for r in detail.latest], sorted(r.passed for r in detail.latest))
        self.assertFalse(detail.latest[0].passed)
        self.assertEqual(detail.engineers, (SITE_EMAIL,))
        self.assertIs(detail.status, AssetStatus.RED)
        self.assertEqual(project.asset_detail(self.conn, INV1).engineers, (INVERTER_EMAIL, SITE_EMAIL))

    def test_an_unknown_asset_has_no_detail_and_no_ping(self) -> None:
        with self.assertRaises(project.UnknownAsset):
            project.asset_detail(self.conn, "OAHE-INV-009")
        with self.assertRaises(project.UnknownAsset):
            project.ping_asset(self.conn, "OAHE-INV-009")

    def test_known_engineers_are_distinct_and_sorted(self) -> None:
        self.assertEqual(project.known_engineers(self.conn), (INVERTER_EMAIL, SITE_EMAIL))
        project.assign_engineer(self.conn, INV2, "a@oahe.example")
        project.assign_engineer(self.conn, INV3, INVERTER_EMAIL)
        self.assertEqual(project.known_engineers(self.conn), ("a@oahe.example", INVERTER_EMAIL, SITE_EMAIL))

    def test_register_asset_delegates_and_refuses_as_the_fleet_does(self) -> None:
        added = Asset("OAHE-STR-004", AssetKind.STRING, "OAHE", INV2, "String 4", 50.0)
        project.register_asset(self.conn, added)
        self.assertEqual(registry.get(self.conn, "OAHE-STR-004"), added)
        with self.assertRaises(project.RegistryError):
            project.register_asset(self.conn, added)

    def test_assign_engineer_refuses_an_unregistered_asset(self) -> None:
        with self.assertRaises(project.RegistryError):
            project.assign_engineer(self.conn, "OAHE-INV-009", "a@oahe.example")

    def test_the_dropdowns(self) -> None:
        self.assertEqual(project.codes_for_kind(AssetKind.TRACKER), codes.codes_for(AssetKind.TRACKER))
        self.assertEqual([c.code for c in project.codes_for_kind(AssetKind.TRACKER)], ["TRK-001", "TRK-002"])
        self.assertEqual(project.kinds(), asset_types.kinds())
        self.assertIs(project.kinds()[0], AssetKind.SITE)

    def test_ping_reads_the_feed_and_stores_nothing(self) -> None:
        found = project.ping_asset(self.conn, INV1)
        self.assertEqual(found, self.fed)
        self.assertTrue(all(isinstance(sample, Sample) for sample in found))
        self.assertEqual(count(self.conn, "samples"), 0)
        with self.assertRaises(project.FeedError):
            project.ping_asset(self.conn, INV2)
        with self.assertRaises(project.FeedError):
            project.ping_asset(self.conn, "OAHE-STR-001")

    def test_the_errors_are_re_exported_exactly(self) -> None:
        self.assertIs(project.LedgerError, ledger.LedgerError)
        self.assertIs(project.RegistryError, registry.RegistryError)
        self.assertIs(project.FeedError, client.FeedError)
        self.assertIs(surface.AssetRow, project.AssetRow)
        with self.assertRaises(project.LedgerError):
            project.assign_fault(self.conn, INV3, "INV-001", at(2026, 6, 1, 11), ENGINEER)
