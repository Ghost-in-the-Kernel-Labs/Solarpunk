"""The orchestrator joins the lanes over one store (lane 1.6): the OAHE fleet loaded, a day of seed-7 telemetry stored,
a grid curtailment and an inverter outage assigned and closed, and kpis_for's numbers checked by hand against the
contract (SOL-07 to SOL-10); an asset the fleet lacks is refused before the ledger sees it."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from solarpunk import project
from solarpunk.faults import ledger
from solarpunk.fleet import registry
from solarpunk.leaf import store
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import Period, at
from solarpunk.leaf.codes import AssetKind, AssetStatus
from solarpunk.mailer import mail as mail_table
from solarpunk.project import UnknownAsset
from solarpunk.remote import results
from solarpunk.telemetry import samples

ENGINEER = "site@oahe.example"  # SP-015: a fault names the engineer who assigned it; the fixtures' site engineer

SITE_EMAIL = "site@oahe.example"
INVERTER_EMAIL = "inverter@oahe.example"

# The OAHE example fleet, copied from test/solarpunk/test_fleet.py, never imported (MOD-05).
OAHE: tuple[Asset, ...] = (
    Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None, location="Pierre, SD",
          engineer_email=SITE_EMAIL),
    Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 1", 100.0, "10.0.0.1", 5020,
          "Pad A", INVERTER_EMAIL),
    Asset("OAHE-INV-002", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 2", 100.0, "10.0.0.2", 5020, "Pad B"),
    Asset("OAHE-STR-001", AssetKind.STRING, "OAHE", "OAHE-INV-001", "String 1", 50.0),
    Asset("OAHE-STR-002", AssetKind.STRING, "OAHE", "OAHE-INV-001", "String 2", 50.0),
    Asset("OAHE-STR-003", AssetKind.STRING, "OAHE", "OAHE-INV-002", "String 3", 50.0),
    Asset("OAHE-STR-004", AssetKind.STRING, "OAHE", "OAHE-INV-002", "String 4", 50.0),
    Asset("OAHE-TRK-001", AssetKind.TRACKER, "OAHE", "OAHE-SIT-001", "Tracker 1", None, "10.0.0.11", 502),
    Asset("OAHE-TRK-002", AssetKind.TRACKER, "OAHE", "OAHE-SIT-001", "Tracker 2", None, "10.0.0.12", 502),
    Asset("OAHE-MTR-001", AssetKind.METER, "OAHE", "OAHE-SIT-001", "Revenue meter", None, "10.0.0.21", 1),
    Asset("OAHE-SEN-001", AssetKind.SENSOR, "OAHE", None, "Irradiance sensor", None, "10.0.0.31", 65535),
)
# A second site, so a query that forgot to filter by site would be caught.
BIGS: tuple[Asset, ...] = (
    Asset("BIGS-SIT-001", AssetKind.SITE, "BIGS", None, "Big Stone", None),
    Asset("BIGS-INV-001", AssetKind.INVERTER, "BIGS", "BIGS-SIT-001", "Inverter 1", 50.0),
)
DAY = Period(at(2026, 6, 1), at(2026, 6, 2))
INV1 = "OAHE-INV-001"
INV2 = "OAHE-INV-002"


def count(conn: sqlite3.Connection, table: str) -> int:
    """The rows of one table: count(open_store(), "faults") is 0."""
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


class Store(unittest.TestCase):
    """A test case whose stores close when it ends."""

    def fresh(self) -> sqlite3.Connection:
        """An in-memory store with every table and nothing in them: count(self.fresh(), "assets") is 0."""
        conn = project.open_store()
        self.addCleanup(conn.close)
        return conn

    def oahe_day(self) -> sqlite3.Connection:
        """The OAHE and BIGS fleets loaded and 2026-06-01's seed-7 telemetry stored for OAHE: 576 samples."""
        conn = self.fresh()
        project.load_fleet(conn, OAHE + BIGS)
        project.generate_and_store(conn, "OAHE", DAY, 7)
        return conn


class TheStore(Store):
    def test_it_holds_every_modules_table_in_order(self) -> None:
        conn = self.fresh()
        names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid")]
        self.assertEqual(names, ["assets", "faults", "samples", "results", "mails", "work_orders", "ticket_comments", "ticket_outbox", "ticket_moves", "suggestions", "accounts", "failed_sign_ins"])
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_it_opens_a_file_and_keeps_its_rows(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fleet.db"
            conn = project.open_store(path)
            project.load_fleet(conn, OAHE)
            conn.close()
            again = sqlite3.connect(str(path))
            self.assertEqual(count(again, "assets"), 11)
            again.close()

    def test_loading_and_generating_fill_the_tables(self) -> None:
        conn = self.fresh()
        project.load_fleet(conn, OAHE)
        self.assertEqual(count(conn, "assets"), 11)
        self.assertEqual(project.generate_and_store(conn, "OAHE", DAY, 7), 576)
        self.assertEqual(count(conn, "samples"), 576)

    def test_generating_reads_one_site_alone(self) -> None:
        conn = self.fresh()
        project.load_fleet(conn, OAHE + BIGS)
        self.assertEqual(project.generate_and_store(conn, "BIGS", DAY, 7), 288)

    def test_generating_for_a_site_the_fleet_lacks_is_refused_and_stores_nothing(self) -> None:
        conn = self.fresh()
        project.load_fleet(conn, OAHE)
        with self.assertRaises(UnknownAsset) as caught:
            project.generate_and_store(conn, "NOPE", DAY, 7)
        self.assertIn("NOPE-SIT-001", str(caught.exception))
        self.assertEqual(count(conn, "samples"), 0)


class Reopening(unittest.TestCase):
    """open_or_create over a file store: reopened with its rows, an old three-table store gains the later tables."""

    def path(self) -> Path:
        """A store path in a folder removed when the test ends: self.path().name is "fleet.db"."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return Path(folder.name) / "fleet.db"

    def tables(self, conn: sqlite3.Connection) -> list[str]:
        """The store's tables in creation order: ["assets", "faults", "samples", "results", "mails", "work_orders", "ticket_comments", "ticket_outbox", "ticket_moves", "suggestions", "accounts", "failed_sign_ins"] for a new store."""
        return [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid")]

    def test_a_file_store_reopens_with_its_rows(self) -> None:
        path = self.path()
        conn = project.open_or_create(path)
        project.load_fleet(conn, OAHE)
        conn.close()
        again = project.open_or_create(path)
        self.addCleanup(again.close)
        self.assertEqual(count(again, "assets"), 11)
        self.assertEqual(self.tables(again), ["assets", "faults", "samples", "results", "mails", "work_orders", "ticket_comments", "ticket_outbox", "ticket_moves", "suggestions", "accounts", "failed_sign_ins"])

    def test_a_store_made_before_sp015_gains_who_assigned_and_its_faults_read_unrecorded(self) -> None:
        path = self.path()
        conn = project.open_or_create(path)
        project.load_fleet(conn, OAHE)
        conn.execute("ALTER TABLE faults DROP COLUMN recorded_by")
        conn.execute("ALTER TABLE faults DROP COLUMN assigned_by")
        conn.execute("INSERT INTO faults (asset_id, code, opened) VALUES (?, ?, ?)", (INV1, "INV-001", "2026-06-01T12:00:00+00:00"))
        conn.commit()
        conn.close()
        again = project.open_or_create(path)
        self.addCleanup(again.close)
        (old,) = project.faults_listing(again, True)
        self.assertEqual((old.assigned_by, old.recorded_by, project.is_cover(again, old)), ("unrecorded", None, False))

    def test_an_old_store_of_three_tables_gains_results_and_mails_and_keeps_its_rows(self) -> None:
        path = self.path()
        old = store.connect(path)
        for statements in (registry.schema(), ledger.schema(), samples.schema()):
            store.apply(old, statements)
        project.load_fleet(old, OAHE)
        old.close()
        conn = project.open_or_create(path)
        self.addCleanup(conn.close)
        self.assertEqual(self.tables(conn), ["assets", "faults", "samples", "results", "mails", "work_orders", "ticket_comments", "ticket_outbox", "ticket_moves", "suggestions", "accounts", "failed_sign_ins"])
        self.assertEqual(count(conn, "assets"), 11)
        self.assertEqual((count(conn, "results"), count(conn, "mails")), (0, 0))

    def test_a_store_missing_one_later_table_gains_that_one_alone(self) -> None:
        path = self.path()
        old = store.connect(path)
        for statements in (registry.schema(), ledger.schema(), samples.schema(), results.schema()):
            store.apply(old, statements)
        old.close()
        conn = project.open_or_create(path)
        self.addCleanup(conn.close)
        self.assertEqual(self.tables(conn), ["assets", "faults", "samples", "results", "mails", "work_orders", "ticket_comments", "ticket_outbox", "ticket_moves", "suggestions", "accounts", "failed_sign_ins"])

    def test_a_file_holding_some_of_the_first_tables_is_refused(self) -> None:
        path = self.path()
        old = store.connect(path)
        store.apply(old, registry.schema())
        store.apply(old, ledger.schema())
        old.close()
        with self.assertRaisesRegex(sqlite3.OperationalError, "table assets already exists"):
            project.open_or_create(path)


class AssigningAFault(Store):
    def test_an_asset_the_fleet_lacks_is_refused_and_nothing_is_stored(self) -> None:
        conn = self.oahe_day()
        with self.assertRaises(UnknownAsset) as caught:
            project.assign_fault(conn, "OAHE-INV-009", "INV-001", at(2026, 6, 1, 12), ENGINEER)
        self.assertIn("OAHE-INV-009", str(caught.exception))
        self.assertIsInstance(caught.exception, ValueError)
        self.assertEqual(count(conn, "faults"), 0)

    def test_a_known_asset_takes_the_fault_and_closes_it(self) -> None:
        conn = self.oahe_day()
        fault = project.assign_fault(conn, INV1, "INV-001", at(2026, 6, 1, 12), ENGINEER)
        self.assertEqual((fault.asset_id, fault.code, fault.closed), (INV1, "INV-001", None))
        closed = project.close_fault(conn, fault.fault_id, at(2026, 6, 1, 13))
        self.assertEqual(closed.closed, at(2026, 6, 1, 13))
        self.assertEqual(ledger.open_faults(conn), ())


class OnlyAnEngineerAssigns(Store):
    """SP-015: a fault names an engineer the fleet holds, and the operator who entered it when it was called in."""

    def test_an_address_no_asset_names_or_none_is_refused_and_nothing_is_stored(self) -> None:
        conn = self.oahe_day()
        for who, said in (("nobody@x.example", "nobody@x.example"), ("", "nobody")):
            with self.subTest(who=who), self.assertRaises(project.UnknownEngineer) as caught:
                project.assign_fault(conn, INV1, "INV-001", at(2026, 6, 1, 12), who)
            self.assertEqual(str(caught.exception), f"{said} is not an engineer the fleet holds")
        self.assertIsInstance(caught.exception, ValueError)
        self.assertEqual(count(conn, "faults"), 0)

    def test_the_fault_records_the_engineer_and_the_operator_who_entered_it(self) -> None:
        conn = self.oahe_day()
        fault = project.assign_fault(conn, INV1, "INV-001", at(2026, 6, 1, 12), INVERTER_EMAIL, "  ops@oahe.example ")
        self.assertEqual((fault.assigned_by, fault.recorded_by), (INVERTER_EMAIL, "ops@oahe.example"))
        blank = project.assign_fault(conn, INV1, "INV-002", at(2026, 6, 1, 12), INVERTER_EMAIL, "   ")
        self.assertIsNone(blank.recorded_by)
        self.assertEqual(ledger.open_faults(conn), (fault, blank))

    def test_cover_is_an_engineer_outside_the_assets_chain(self) -> None:
        conn = self.oahe_day()
        own = project.assign_fault(conn, INV1, "INV-001", at(2026, 6, 1, 12), INVERTER_EMAIL)
        site = project.assign_fault(conn, "OAHE-INV-002", "INV-001", at(2026, 6, 1, 12), SITE_EMAIL)
        covering = project.assign_fault(conn, "OAHE-SIT-001", "SIT-001", at(2026, 6, 1, 12), INVERTER_EMAIL)
        other_site = project.assign_fault(conn, "BIGS-INV-001", "INV-001", at(2026, 6, 1, 12), SITE_EMAIL)
        self.assertEqual([project.is_cover(conn, f) for f in (own, site, covering, other_site)], [False, False, True, True])

    def test_check_fault_refuses_as_assign_would_and_assigns_nothing(self) -> None:
        conn = self.oahe_day()
        self.assertIsNone(project.check_fault(conn, INV1, "INV-001"))
        with self.assertRaises(UnknownAsset):
            project.check_fault(conn, "OAHE-INV-009", "INV-001")
        with self.assertRaises(ValueError):
            project.check_fault(conn, INV1, "INV-999")
        self.assertEqual(count(conn, "faults"), 0)


class TheStatus(Store):
    def test_an_open_outage_is_red_and_a_closed_one_green(self) -> None:
        conn = self.oahe_day()
        self.assertIs(project.asset_status(conn, INV1), AssetStatus.GREEN)
        fault = project.assign_fault(conn, INV1, "INV-001", at(2026, 6, 1, 12), ENGINEER)
        self.assertIs(project.asset_status(conn, INV1), AssetStatus.RED)
        self.assertIs(project.asset_status(conn, INV2), AssetStatus.GREEN)
        project.close_fault(conn, fault.fault_id, at(2026, 6, 1, 13))
        self.assertIs(project.asset_status(conn, INV1), AssetStatus.GREEN)

    def test_an_open_derate_or_info_is_green(self) -> None:
        conn = self.oahe_day()
        project.assign_fault(conn, INV1, "INV-002", at(2026, 6, 1, 12), ENGINEER)
        project.assign_fault(conn, INV1, "INV-004", at(2026, 6, 1, 12), ENGINEER)
        self.assertIs(project.asset_status(conn, INV1), AssetStatus.GREEN)

    def test_an_open_outage_after_a_closed_one_is_red(self) -> None:
        conn = self.oahe_day()
        first = project.assign_fault(conn, INV1, "INV-001", at(2026, 6, 1, 10), ENGINEER)
        project.close_fault(conn, first.fault_id, at(2026, 6, 1, 11))
        project.assign_fault(conn, INV1, "INV-003", at(2026, 6, 1, 12), ENGINEER)
        self.assertIs(project.asset_status(conn, INV1), AssetStatus.RED)

    def test_a_failing_latest_result_is_yellow_and_a_passing_rerun_green(self) -> None:
        conn = self.oahe_day()
        results.record(conn, "reachable", INV2, at(2026, 6, 1, 10), results.Result(False, "no records"))
        results.record(conn, "on_grid", INV2, at(2026, 6, 1, 10), results.Result(True, "0 records"))
        self.assertIs(project.asset_status(conn, INV2), AssetStatus.YELLOW)
        self.assertIs(project.asset_status(conn, INV1), AssetStatus.GREEN)
        results.record(conn, "reachable", INV2, at(2026, 6, 1, 11), results.Result(True, "3 records"))
        self.assertIs(project.asset_status(conn, INV2), AssetStatus.GREEN)

    def test_an_open_outage_outranks_a_failing_result(self) -> None:
        conn = self.oahe_day()
        results.record(conn, "reachable", INV1, at(2026, 6, 1, 10), results.Result(False, "no records"))
        project.assign_fault(conn, INV1, "INV-001", at(2026, 6, 1, 12), ENGINEER)
        self.assertIs(project.asset_status(conn, INV1), AssetStatus.RED)

    def test_open_outages_holds_each_assets_first_open_outage_alone(self) -> None:
        conn = self.oahe_day()
        closed = project.assign_fault(conn, INV1, "INV-003", at(2026, 6, 1, 9), ENGINEER)
        project.close_fault(conn, closed.fault_id, at(2026, 6, 1, 10))
        first = project.assign_fault(conn, INV2, "INV-001", at(2026, 6, 1, 12), ENGINEER)
        project.assign_fault(conn, INV2, "INV-003", at(2026, 6, 1, 12), ENGINEER)
        project.assign_fault(conn, INV1, "INV-002", at(2026, 6, 1, 12), ENGINEER)
        self.assertEqual(project.open_outages(conn), {INV2: first})

    def test_an_asset_the_fleet_lacks_has_no_status(self) -> None:
        with self.assertRaises(UnknownAsset):
            project.asset_status(self.oahe_day(), "OAHE-INV-009")


class EndToEnd(Store):
    """The OAHE day: SIT-002 over [12:00, 13:00) on the site, INV-001 over [12:30, 14:30) on INV1, both closed. By hand:
    288 expected, 12 excluded (12:00 to 12:55), 24 intervals of INV-001 of which 6 are excluded first, so down 18 and
    INV1's availability (276 − 18) / 276 = 0.9348; INV2 carries only the site's fault: 1.0."""

    def faulted(self) -> tuple[sqlite3.Connection, int]:
        """The OAHE day with both faults assigned, the curtailment closed and the outage still open: (conn, outage id)."""
        conn = self.oahe_day()
        curtail = project.assign_fault(conn, "OAHE-SIT-001", "SIT-002", at(2026, 6, 1, 12), ENGINEER)
        project.close_fault(conn, curtail.fault_id, at(2026, 6, 1, 13))
        outage = project.assign_fault(conn, INV1, "INV-001", at(2026, 6, 1, 12, 30), ENGINEER)
        return conn, outage.fault_id

    def test_while_the_outage_is_open(self) -> None:
        conn, _ = self.faulted()
        kpis = project.kpis_for(conn, "OAHE", DAY)
        inv1 = kpis.availability[INV1]
        self.assertEqual((inv1.expected, inv1.excluded, inv1.gaps), (288, 12, 9))
        self.assertGreater(inv1.down, 0)
        self.assertTrue(0.0 <= inv1.value < 1.0)
        self.assertEqual(kpis.availability[INV2].value, 1.0)
        self.assertEqual((kpis.availability[INV2].excluded, kpis.availability[INV2].down), (12, 0))
        self.assertEqual(kpis.faults_open, 1)
        self.assertIs(kpis.status[INV1], AssetStatus.RED)
        self.assertEqual(kpis.reliability[AssetKind.INVERTER].open, 1)

    def test_after_the_outage_closes(self) -> None:
        conn, outage = self.faulted()
        project.close_fault(conn, outage, at(2026, 6, 1, 14, 30))
        kpis = project.kpis_for(conn, "OAHE", DAY)
        inv1 = kpis.availability[INV1]
        self.assertEqual((inv1.value, inv1.expected, inv1.excluded, inv1.down, inv1.gaps), (0.9348, 288, 12, 18, 9))
        self.assertEqual(kpis.faults_open, 0)
        self.assertEqual(set(kpis.status.values()), {AssetStatus.GREEN})
        inverters = kpis.reliability[AssetKind.INVERTER]
        self.assertEqual((inverters.mtbf_h, inverters.mttr_h, inverters.count, inverters.open), (46.0, 2.0, 1, 0))

    def test_every_asset_has_a_status_and_every_kind_a_reliability(self) -> None:
        kpis = project.kpis_for(self.oahe_day(), "OAHE", DAY)
        self.assertEqual(sorted(kpis.status), sorted(asset.asset_id for asset in OAHE))
        self.assertEqual(list(kpis.reliability), list(AssetKind))
        self.assertEqual(sorted(kpis.availability), [INV1, INV2])

    def test_the_ratio_and_the_yield_come_from_the_stored_samples(self) -> None:
        kpis = project.kpis_for(self.oahe_day(), "OAHE", DAY)
        ratio = kpis.performance_ratio
        self.assertEqual(ratio.unreliable, 17)
        self.assertEqual(ratio.value, round(ratio.energy_kwh / ratio.reference_kwh, 4))
        self.assertGreater(ratio.reference_kwh, ratio.energy_kwh)
        self.assertGreater(ratio.energy_kwh, 0.0)
        self.assertEqual((kpis.energy_yield.kwh, kpis.energy_yield.source), (ratio.energy_kwh, "inverters"))

    def test_the_meter_is_used_when_given_and_not_lost(self) -> None:
        conn = self.oahe_day()
        self.assertEqual(project.kpis_for(conn, "OAHE", DAY, meter_kwh=1500.0).energy_yield.source, "meter")
        self.assertEqual(project.kpis_for(conn, "OAHE", DAY, meter_kwh=1500.0).energy_yield.kwh, 1500.0)
        project.assign_fault(conn, "OAHE-MTR-001", "MTR-001", at(2026, 6, 1, 12), ENGINEER)
        self.assertEqual(project.kpis_for(conn, "OAHE", DAY, meter_kwh=1500.0).energy_yield.source, "inverters")

    def test_a_sensor_fault_marks_the_ratio_unreliable(self) -> None:
        conn = self.oahe_day()
        before = project.kpis_for(conn, "OAHE", DAY).performance_ratio.unreliable
        sensor = project.assign_fault(conn, "OAHE-SEN-001", "SEN-001", at(2026, 6, 1, 12), ENGINEER)
        project.close_fault(conn, sensor.fault_id, at(2026, 6, 1, 13))
        self.assertGreater(project.kpis_for(conn, "OAHE", DAY).performance_ratio.unreliable, before)


class OneSiteAlone(Store):
    def test_another_sites_and_another_inverters_faults_do_not_count(self) -> None:
        conn = self.oahe_day()
        project.assign_fault(conn, "BIGS-SIT-001", "SIT-001", at(2026, 6, 1, 1), ENGINEER)
        project.assign_fault(conn, "BIGS-INV-001", "INV-001", at(2026, 6, 1, 1), ENGINEER)
        project.assign_fault(conn, INV2, "INV-001", at(2026, 6, 1, 20), ENGINEER)
        kpis = project.kpis_for(conn, "OAHE", DAY)
        inv1 = kpis.availability[INV1]
        self.assertEqual((inv1.value, inv1.excluded, inv1.down), (1.0, 0, 0))
        self.assertEqual(kpis.availability[INV2].down, 48)
        self.assertEqual(kpis.faults_open, 1)
        self.assertEqual(kpis.reliability[AssetKind.SITE].open, 0)
        self.assertEqual(kpis.reliability[AssetKind.INVERTER].open, 1)

    def test_a_fault_outside_the_period_does_not_count(self) -> None:
        conn = self.oahe_day()
        early = project.assign_fault(conn, INV1, "INV-001", at(2026, 5, 31, 10), ENGINEER)
        project.close_fault(conn, early.fault_id, at(2026, 5, 31, 11))
        self.assertEqual(project.kpis_for(conn, "OAHE", DAY).availability[INV1].down, 0)

    def test_a_site_the_fleet_lacks_is_refused(self) -> None:
        with self.assertRaises(UnknownAsset):
            project.kpis_for(self.oahe_day(), "NOPE", DAY)


class Phase4Reopening(Reopening):
    def test_a_phase_three_store_gains_work_orders_alone_and_keeps_its_rows(self) -> None:
        path = self.path()
        old = store.connect(path)
        for statements in (registry.schema(), ledger.schema(), samples.schema(), results.schema(), mail_table.schema()):
            store.apply(old, statements)
        project.load_fleet(old, OAHE)
        old.close()
        conn = project.open_or_create(path)
        self.addCleanup(conn.close)
        self.assertEqual(self.tables(conn), ["assets", "faults", "samples", "results", "mails", "work_orders", "ticket_comments", "ticket_outbox", "ticket_moves", "suggestions", "accounts", "failed_sign_ins"])
        self.assertEqual((count(conn, "assets"), count(conn, "work_orders")), (11, 0))

