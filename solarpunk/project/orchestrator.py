"""The orchestrator: one store holding every module's tables, and the joins no lane may make (MOD-05). It checks an
asset against the fleet before the ledger takes a fault, and reads the fleet, the faults and the samples to hand the
KPI engine leaf types (Invariants: SOL-04, SOL-05, SOL-07 to SOL-10); an asset's status is the three-colour rule over
the ledger and the remote results (SP-006, SP-007). The scheduled run is in run.py, the windows' surface in surface.py.
The demo (3.4) reaches the generator and the feed simulator through simulated_day and feed_server, since ui imports
project and the leaf alone (SP-010). A work order (4.1, SP-011) is opened from a fault the ledger holds open, and closing
a corrective one closes its fault in the same call."""
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from solarpunk import kpi
from solarpunk.faults import ledger
from solarpunk.feed import simulate
from solarpunk.fleet import registry
from solarpunk.leaf import store
from solarpunk.leaf.assets import Asset, site_id
from solarpunk.leaf.clock import Period, at
from solarpunk.leaf.codes import AssetKind, AssetStatus, Severity, lookup
from solarpunk.leaf.faults import UNRECORDED, Fault
from solarpunk.leaf.telemetry import Sample
from solarpunk.mailer import mail as mail_table
from solarpunk.remote import results as result_table
from solarpunk.telemetry import generate as generator
from solarpunk.telemetry import samples as sample_table
from solarpunk.workorders import ledger as work_ledger
from solarpunk.workorders.ledger import WorkOrder, WorkOrderError


SITE_EMAIL = "site@oahe.example"
LOOPBACK = "127.0.0.1"
INVERTER_EMAIL = "inverter@oahe.example"
STORE_TABLES = ("assets", "faults", "samples")
# The tables Phases 2 and 4 added, by name, each with its schema: a store made before them gains them on reopening.
LATER_TABLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("results", result_table.schema()),
    ("mails", mail_table.schema()),
    ("work_orders", work_ledger.schema()),
)
TABLE_NAMES = "SELECT name FROM sqlite_master WHERE type = 'table'"


class UnknownAsset(ValueError):
    """Raised for an asset id the fleet does not hold: UnknownAsset("OAHE-INV-009 is not in the fleet")."""


class UnknownEngineer(ValueError):
    """Raised for a fault assigned by an address the fleet holds for no asset, or by nobody (SP-015):
    UnknownEngineer("nobody@example.com is not an engineer the fleet holds")."""


@dataclass(frozen=True)
class SiteKpis:
    """A site's KPIs over one period, each beside its counts: availability and status keyed by asset id, reliability by
    kind; for the OAHE fleet, availability has the keys OAHE-INV-001 and OAHE-INV-002 and status eleven keys."""

    availability: dict[str, kpi.Availability]
    performance_ratio: kpi.PerformanceRatio
    energy_yield: kpi.EnergyYield
    reliability: dict[AssetKind, kpi.Reliability]
    faults_open: int
    status: dict[str, AssetStatus]


def open_store(path: str | Path = store.MEMORY) -> sqlite3.Connection:
    """A store holding the fleet's, the ledger's, the samples', the remote results', the mails' and the work orders'
    tables, applied in that order: open_store() is an in-memory store where "SELECT count(*) FROM faults" gives 0."""
    conn = store.connect(path)
    store.apply(conn, registry.schema())
    store.apply(conn, ledger.schema())
    store.apply(conn, sample_table.schema())
    for _name, statements in LATER_TABLES:
        store.apply(conn, statements)
    return conn


def open_or_create(path: str | Path) -> sqlite3.Connection:
    """The store at a path, its tables made only when it has none (the CLI's store, which outlives one call):
    open_or_create("fleet.db") on a new file is open_store("fleet.db"); on a file holding the three first tables it
    opens it again with its rows, adding results, mails and work_orders where it lacks them, where open_store would raise
    "table assets already exists"; a file holding some of the three first is handed to open_store, which refuses it."""
    conn = store.connect(path)
    present = {row[0] for row in conn.execute(TABLE_NAMES)}
    if not set(STORE_TABLES) <= present:
        conn.close()
        return open_store(path)
    for name, statements in LATER_TABLES:
        if name not in present:
            store.apply(conn, statements)
    ledger.upgrade(conn)
    return conn


def demo_fleet() -> tuple[Asset, ...]:
    """The OAHE example fleet, copied from test/solarpunk/test_fleet.py (ROADMAP 1.1): eleven assets, the site first,
    a parent before its children; demo_fleet()[1].asset_id is "OAHE-INV-001"."""
    return (
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


def load_fleet(conn: sqlite3.Connection, assets: tuple[Asset, ...]) -> None:
    """Registers the assets, a parent before its children, refusing as the registry does: load_fleet(conn, OAHE) stores
    eleven assets."""
    # Invariant: SOL-05
    registry.load_fleet(conn, assets)


def known(conn: sqlite3.Connection, asset_id: str) -> Asset:
    """The fleet's asset of one id, or UnknownAsset: known(conn, "OAHE-INV-001") is the inverter; known(conn,
    "OAHE-INV-009") raises UnknownAsset."""
    asset = registry.get(conn, asset_id)
    if asset is None:
        raise UnknownAsset(f"{asset_id} is not in the fleet")
    return asset


def known_engineers(conn: sqlite3.Connection) -> tuple[str, ...]:
    """Every engineer address the fleet holds, distinct and sorted: the OAHE fleet gives ("inverter@oahe.example",
    "site@oahe.example"); a fleet with no engineer gives ()."""
    emails = {asset.engineer_email for asset in fleet_assets(conn, None) if asset.engineer_email is not None}
    return tuple(sorted(emails))


def assign_fault(conn: sqlite3.Connection, asset_id: str, code: str, opened: datetime, assigned_by: str,
                 recorded_by: str | None = None) -> Fault:
    """Opens a fault on an asset the fleet holds, assigned by an engineer the fleet holds and, when it was called in,
    entered by the operator named in recorded_by (SP-015): assign_fault(conn, "OAHE-INV-001", "INV-001", 10:10 UTC,
    "inverter@oahe.example") is Fault(1, "OAHE-INV-001", "INV-001", 10:10, None, "inverter@oahe.example", None);
    "OAHE-INV-009" raises UnknownAsset and an address no asset names raises UnknownEngineer, each storing nothing. Any
    engineer the fleet holds may assign; is_cover says when it is not the asset's own."""
    # Decision: SP-015 (only an engineer assigns a fault, and the record says which)
    # Invariant: SOL-04 (the ledger refuses an unknown code); SOL-05 (no fault on an asset the fleet lacks)
    known(conn, asset_id)
    if assigned_by not in known_engineers(conn):
        raise UnknownEngineer(f"{assigned_by or 'nobody'} is not an engineer the fleet holds")
    entered = recorded_by.strip() if recorded_by is not None else None
    return ledger.assign(conn, asset_id, code, opened, assigned_by, entered or None)


def check_fault(conn: sqlite3.Connection, asset_id: str, code: str) -> None:
    """Refuses as assign_fault would, without assigning: an asset the fleet lacks raises UnknownAsset (SOL-05), a code
    the catalogue lacks UnknownFaultCode (SOL-04); check_fault(conn, "OAHE-INV-001", "INV-001") returns None."""
    known(conn, asset_id)
    lookup(code)


def is_cover(conn: sqlite3.Connection, fault: Fault) -> bool:
    """Whether the engineer who assigned the fault is not the asset's own chain of asset, parent and site (SP-015): an
    OAHE-INV-001 fault assigned by site@oahe.example is not cover (the site's engineer is in the chain); one assigned by
    an engineer of another site is; a fault stored before SP-015 ("unrecorded") is not called cover."""
    # Decision: SP-015 (cover is allowed, and visible)
    if fault.assigned_by == UNRECORDED:
        return False
    return fault.assigned_by not in registry.engineers_for(conn, fault.asset_id)


def close_fault(conn: sqlite3.Connection, fault_id: int, closed: datetime) -> Fault:
    """Closes an open fault as the ledger does: close_fault(conn, 1, 10:30 UTC).closed is 10:30 UTC."""
    return ledger.close(conn, fault_id, closed)


def open_work_order_from_fault(conn: sqlite3.Connection, fault_id: int, opened: datetime, note: str) -> WorkOrder:
    """Opens a corrective work order for a fault the ledger holds open, on that fault's asset: for open fault 1 on
    OAHE-INV-001 opened 10:10, open_work_order_from_fault(conn, 1, 10:20 UTC, "fuse") is WorkOrder(1, "OAHE-INV-001", 1,
    "corrective", 10:20, None, None, "fuse"); a fault not open in the ledger raises LedgerError, an order opened before
    its fault WorkOrderError, and neither stores anything."""
    fault = next((found for found in ledger.open_faults(conn) if found.fault_id == fault_id), None)
    if fault is None:
        raise ledger.LedgerError(f"fault {fault_id} is not open in the ledger")
    if opened < fault.opened:
        raise WorkOrderError(f"a work order for fault {fault_id} cannot open before the fault did")
    return work_ledger.open_corrective(conn, fault.asset_id, fault_id, opened, note)


def open_preventive_work_order(conn: sqlite3.Connection, asset_id: str, opened: datetime, note: str) -> WorkOrder:
    """Opens a preventive work order on an asset the fleet holds: open_preventive_work_order(conn, "OAHE-TRK-001",
    10:10 UTC, "grease").kind is "preventive"; "OAHE-INV-009" raises UnknownAsset, stores nothing."""
    # Invariant: SOL-05 (no record on an asset the fleet lacks)
    known(conn, asset_id)
    return work_ledger.open_preventive(conn, asset_id, opened, note)


def close_work_order(conn: sqlite3.Connection, wo_id: int, root_cause: str, closed: datetime) -> WorkOrder:
    """Closes a work order with its root-cause code and, for a corrective order whose fault is still open, that fault
    at the same instant, in one call: close_work_order(conn, 1, "RC-COMPONENT", 10:30 UTC) leaves order 1 and its
    fault both closed at 10:30; an unknown code raises UnknownRootCause and closes neither."""
    # Decision: SP-011 (closing a corrective order closes its fault, in project, in one call)
    order = work_ledger.close(conn, wo_id, root_cause, closed)
    if order.fault_id is not None and any(f.fault_id == order.fault_id for f in ledger.open_faults(conn)):
        ledger.close(conn, order.fault_id, closed)
    return order


def work_orders_for(conn: sqlite3.Connection, asset_id: str) -> tuple[WorkOrder, ...]:
    """Every work order an asset the fleet holds had or has, in wo_id order: work_orders_for(conn, "OAHE-INV-001") holds
    its orders alone; "OAHE-INV-009" raises UnknownAsset."""
    known(conn, asset_id)
    return work_ledger.by_asset(conn, asset_id)


def fleet_assets(conn: sqlite3.Connection, site: str | None) -> tuple[Asset, ...]:
    """The fleet's assets in id order, one site's when a site is given: fleet_assets(conn, "OAHE") is OAHE's eleven;
    fleet_assets(conn, None) adds every other site's, BIGS-INV-001 before OAHE-INV-001."""
    if site is not None:
        return registry.by_site(conn, site)
    found = [asset for kind in AssetKind for asset in registry.by_kind(conn, kind)]
    return tuple(sorted(found, key=lambda asset: asset.asset_id))


def fleet_listing(conn: sqlite3.Connection, site: str | None) -> tuple[tuple[Asset, AssetStatus], ...]:
    """Each of fleet_assets' assets beside its status: with an open INV-001 on OAHE-INV-001, fleet_listing(conn,
    "OAHE")[1] is (OAHE-INV-001, AssetStatus.RED) and every other pair's status GREEN."""
    return tuple((asset, asset_status(conn, asset.asset_id)) for asset in fleet_assets(conn, site))


def faults_listing(conn: sqlite3.Connection, open_only: bool) -> tuple[Fault, ...]:
    """Every fault the ledger holds in fault_id order, or the open ones alone: with fault 1 closed and fault 2 open,
    faults_listing(conn, False) is (fault 1, fault 2) and faults_listing(conn, True) is (fault 2,)."""
    if open_only:
        return ledger.open_faults(conn)
    found = [fault for asset in fleet_assets(conn, None) for fault in ledger.by_asset(conn, asset.asset_id)]
    return tuple(sorted(found, key=lambda fault: fault.fault_id))


def period(start: datetime, end: datetime) -> Period:
    """The leaf's half-open period, refusing as it does: period(10:00 UTC, 11:00 UTC).expected() is 12; a naive end
    raises NotUtc, a reversed pair ValueError."""
    return Period(start, end)


def day_period(day: date) -> Period:
    """One UTC day as a period, midnight to midnight: day_period(date(2026, 6, 1)) is Period(at(2026, 6, 1),
    at(2026, 6, 2)), 288 instants."""
    start = at(day.year, day.month, day.day)
    return Period(start, start + timedelta(days=1))


def generate_and_store(conn: sqlite3.Connection, site: str, period: Period, seed: int) -> int:
    """Generates the site's inverters' samples over the period from the seed, stores them, and returns how many:
    generate_and_store(conn, "OAHE", 2026-06-01's day, 7) is 576 for OAHE's two inverters, gaps included; a site the
    fleet lacks raises UnknownAsset and stores nothing (J-014)."""
    # Invariant: SOL-02 (one seed, the same samples); SOL-06 (gaps stored, never dropped)
    known(conn, site_id(site))
    made = generator.generate(registry.by_site(conn, site), period, seed)
    sample_table.store(conn, made)
    return len(made)


def simulated_day(asset: Asset, period: Period, seed: int) -> tuple[Sample, ...]:
    """One inverter's generated samples over a period, stored nowhere, for a simulator to serve: simulated_day(OAHE-INV-001,
    2026-06-01's day, 7) is 288 samples, the same each call."""
    # Invariant: SOL-02 (one seed, the same samples)
    return generator.generate((asset,), period, seed)


def feed_server(samples: tuple[Sample, ...]) -> simulate.FeedServer:
    """A bound feed simulator on 127.0.0.1 and a free port answering each connection with the samples' records, not yet
    serving: feed_server(day).server_address is ("127.0.0.1", <the port>); the caller runs serve_forever."""
    return simulate.make_server(samples, LOOPBACK, 0)


def open_outages(conn: sqlite3.Connection) -> dict[str, Fault]:
    """Each asset carrying an open fault whose catalogue severity is OUTAGE, with its first such fault: with an open
    INV-001 (fault 2) and INV-003 (fault 3) on OAHE-INV-003 and an open INV-002 on OAHE-INV-001, {"OAHE-INV-003": fault 2}."""
    # Invariant: SOL-11 (a derate is not an outage)
    found: dict[str, Fault] = {}
    for fault in ledger.open_faults(conn):
        if fault.catalogue_row().severity is Severity.OUTAGE:
            found.setdefault(fault.asset_id, fault)
    return found


def asset_status(conn: sqlite3.Connection, asset_id: str) -> AssetStatus:
    """The three-colour rule (SP-007): RED while the asset carries an open OUTAGE fault, else YELLOW when its latest
    remote results hold a failure, else GREEN: with an open INV-001 on OAHE-INV-001 its status is RED, with only an open
    INV-002 (a derate) GREEN, with a failing latest reachable YELLOW; an id the fleet lacks raises UnknownAsset."""
    # Invariant: SOL-11 (a derate is not an outage)
    known(conn, asset_id)
    if asset_id in open_outages(conn):
        return AssetStatus.RED
    if any(not result.passed for result in result_table.latest_for(conn, asset_id)):
        return AssetStatus.YELLOW
    return AssetStatus.GREEN


def inverters_of(assets: tuple[Asset, ...]) -> tuple[Asset, ...]:
    """The inverters among some assets, in their order: inverters_of(OAHE) is (OAHE-INV-001, OAHE-INV-002)."""
    return tuple(asset for asset in assets if asset.kind is AssetKind.INVERTER)


def availability_of(conn: sqlite3.Connection, site: str, period: Period, faults: tuple[Fault, ...]) -> dict[str, kpi.Availability]:
    """Each inverter's availability from its own faults and its site's and its own samples: with no faults and a
    stored day, availability_of(conn, "OAHE", day, ())["OAHE-INV-001"].value is 1.0."""
    # Invariant: SOL-07 (the inverter's faults plus the site's)
    found = {}
    for inverter in inverters_of(registry.by_site(conn, site)):
        carried = tuple(f for f in faults if f.asset_id in (inverter.asset_id, site_id(site)))
        stored = sample_table.in_period(conn, inverter.asset_id, period)
        found[inverter.asset_id] = kpi.availability(period, carried, stored)
    return found


def site_samples(conn: sqlite3.Connection, inverters: tuple[Asset, ...], period: Period) -> tuple[Sample, ...]:
    """Every inverter's stored samples in the period, inverter by inverter: 576 for OAHE's two over a stored day."""
    found: list[Sample] = []
    for inverter in inverters:
        found.extend(sample_table.in_period(conn, inverter.asset_id, period))
    return tuple(found)


def reliability_of(assets: tuple[Asset, ...], period: Period, faults: tuple[Fault, ...]) -> dict[AssetKind, kpi.Reliability]:
    """MTBF and MTTR for every kind present among the assets, in AssetKind order: for OAHE with no faults, six kinds,
    reliability_of(OAHE, day, ())[AssetKind.INVERTER].count is 0."""
    # Invariant: SOL-10
    present = {asset.kind for asset in assets}
    return {kind: kpi.mtbf_mttr(kind, assets, period, faults) for kind in AssetKind if kind in present}


def kpis_for(conn: sqlite3.Connection, site: str, period: Period, meter_kwh: float | None = None) -> SiteKpis:
    """The site's KPIs over the period from the fleet, the ledger and the stored samples; energy_yield uses meter_kwh
    when given and the meter carried no MTR-001, else the inverters' energy: kpis_for(conn, "OAHE", day) for a clean
    stored day has availability 1.0 per inverter, faults_open 0 and every status GREEN; a site the fleet lacks raises
    UnknownAsset."""
    # Invariant: SOL-07, SOL-08, SOL-09, SOL-10 (the engine's numbers over the site's own assets and faults)
    known(conn, site_id(site))
    assets = registry.by_site(conn, site)
    ids = {asset.asset_id for asset in assets}
    faults = tuple(f for f in ledger.in_period(conn, period) if f.asset_id in ids)
    samples = site_samples(conn, inverters_of(assets), period)
    return SiteKpis(
        availability=availability_of(conn, site, period, faults),
        performance_ratio=kpi.performance_ratio(inverters_of(assets), samples, faults),
        energy_yield=kpi.energy_yield(site, meter_kwh, samples, faults),
        reliability=reliability_of(assets, period, faults),
        faults_open=len([f for f in ledger.open_faults(conn) if f.asset_id in ids]),
        status={asset.asset_id: asset_status(conn, asset.asset_id) for asset in assets},
    )
