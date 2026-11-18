"""The orchestrator: one store holding every module's tables, and the joins no lane may make (MOD-05). It checks an
asset against the fleet before the ledger takes a fault, and reads the fleet, the faults and the samples to hand the
KPI engine leaf types (Invariants: SOL-04, SOL-05, SOL-07 to SOL-10)."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from solarpunk import kpi
from solarpunk.faults import ledger
from solarpunk.fleet import registry
from solarpunk.leaf import store
from solarpunk.leaf.assets import Asset, site_id
from solarpunk.leaf.clock import Period
from solarpunk.leaf.codes import AssetKind, AssetStatus, Severity
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.telemetry import Sample
from solarpunk.telemetry import generate as generator
from solarpunk.telemetry import samples as sample_table


class UnknownAsset(ValueError):
    """Raised for an asset id the fleet does not hold: UnknownAsset("OAHE-INV-009 is not in the fleet")."""


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
    """A store holding the fleet's, the ledger's and the samples' tables, applied in that order: open_store() is an
    in-memory store where "SELECT count(*) FROM faults" gives 0."""
    conn = store.connect(path)
    store.apply(conn, registry.schema())
    store.apply(conn, ledger.schema())
    store.apply(conn, sample_table.schema())
    return conn


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


def assign_fault(conn: sqlite3.Connection, asset_id: str, code: str, opened: datetime) -> Fault:
    """Opens a fault on an asset the fleet holds, then as the ledger does: assign_fault(conn, "OAHE-INV-001", "INV-001",
    10:10 UTC) is Fault(1, "OAHE-INV-001", "INV-001", 10:10, None); "OAHE-INV-009" raises UnknownAsset, stores nothing."""
    # Invariant: SOL-04 (the ledger refuses an unknown code); SOL-05 (no fault on an asset the fleet lacks)
    known(conn, asset_id)
    return ledger.assign(conn, asset_id, code, opened)


def close_fault(conn: sqlite3.Connection, fault_id: int, closed: datetime) -> Fault:
    """Closes an open fault as the ledger does: close_fault(conn, 1, 10:30 UTC).closed is 10:30 UTC."""
    return ledger.close(conn, fault_id, closed)


def generate_and_store(conn: sqlite3.Connection, site: str, period: Period, seed: int) -> int:
    """Generates the site's inverters' samples over the period from the seed, stores them, and returns how many:
    generate_and_store(conn, "OAHE", 2026-06-01's day, 7) is 576 for OAHE's two inverters, gaps included."""
    # Invariant: SOL-02 (one seed, the same samples); SOL-06 (gaps stored, never dropped)
    made = generator.generate(registry.by_site(conn, site), period, seed)
    sample_table.store(conn, made)
    return len(made)


def asset_status(conn: sqlite3.Connection, asset_id: str) -> AssetStatus:
    """RED while the asset carries an open fault whose catalogue severity is OUTAGE, else GREEN; YELLOW (a failing remote
    test) comes with the remote tests in Phase 2: with an open INV-001 on OAHE-INV-001 its status is RED, with only an
    open INV-002 (a derate) GREEN; an id the fleet lacks raises UnknownAsset."""
    # Invariant: SOL-11 (a derate is not an outage)
    known(conn, asset_id)
    for fault in ledger.by_asset(conn, asset_id):
        if fault.closed is None and fault.catalogue_row().severity is Severity.OUTAGE:
            return AssetStatus.RED
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
