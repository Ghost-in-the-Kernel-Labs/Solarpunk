"""The one surface the Phase 3 windows call (2.7, SP-007, MOD-06): rows for the fleet window, a detail for the asset
window with every remote test of the asset's kind and its latest result (6.4), the engineers, the kinds and codes for
the dropdowns, register and ping for the add-asset window. Each function is one call a window makes and a headless test
makes too, so no UI lane edits the orchestrator."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from solarpunk.faults import ledger
from solarpunk.feed import client as feed
from solarpunk.fleet import registry
from solarpunk.leaf import asset_types
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind, AssetStatus, FaultCode, codes_for
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.telemetry import Sample
from solarpunk.project.orchestrator import asset_status, fleet_assets, known
from solarpunk.remote import results as result_table
from solarpunk.remote.registry import tests_for
from solarpunk.remote.results import Recorded
from solarpunk.workorders import ledger as work_ledger
from solarpunk.workorders.ledger import WorkOrder

NO_FAILURE = "—"
FAILED = "fail"
NOT_RUN = "not run"
PASSED = "pass"
# The order the diagnostics are read in: what failed, then what has never been run, then what passed (6.4).
STATE_ORDER = (FAILED, NOT_RUN, PASSED)
NEVER_RUN_REASON = "no result yet: the scheduled run has not tested this asset"


@dataclass(frozen=True)
class AssetRow:
    """One row of the fleet window: AssetRow("OAHE-INV-002", "Inverter 2", AssetKind.INVERTER, AssetStatus.YELLOW,
    2026-06-01T12:00Z, "reachable"); an asset never run has last_run_at None, one with nothing failing "—"."""

    asset_id: str
    name: str
    kind: AssetKind
    status: AssetStatus
    last_run_at: datetime | None
    failing: str


@dataclass(frozen=True)
class AssetDetail:
    """The asset window's content: the asset, its open faults beside their meanings, its latest results failing first,
    its engineer chain, its status and its open work orders (4.1, last with a default so 3.2's window keeps working):
    for OAHE-INV-003 with an open INV-001 and a work order on it, open_faults is ((that fault, "Inverter offline: …"),),
    status RED and open_orders (that order,)."""

    asset: Asset
    open_faults: tuple[tuple[Fault, str], ...]
    latest: tuple[Recorded, ...]
    engineers: tuple[str, ...]
    status: AssetStatus
    open_orders: tuple[WorkOrder, ...] = ()
    diagnostics: tuple["Diagnostic", ...] = ()


@dataclass(frozen=True)
class Diagnostic:
    """One remote test as the asset window reads it (6.4): its name, "fail", "not run" or "pass", the reason, and the
    run it came from: Diagnostic("on_grid", "fail", "10:05: off the grid", 2026-06-01T12:00Z); a test the registry
    holds for the kind and the store has no result of is Diagnostic(name, "not run", NEVER_RUN_REASON, None)."""

    test_name: str
    state: str
    reason: str
    run_at: datetime | None


def row_of(conn: sqlite3.Connection, asset: Asset) -> AssetRow:
    """One asset's row from its latest results: OAHE-INV-002 after a run at 12:00 whose reachable failed gives
    AssetRow(…, YELLOW, 12:00 UTC, "reachable"); a string never run gives (…, GREEN, None, "—")."""
    latest = result_table.latest_for(conn, asset.asset_id)
    last_run_at = latest[0].run_at if latest else None
    failing = next((found.test_name for found in latest if not found.passed), NO_FAILURE)
    status = asset_status(conn, asset.asset_id)
    return AssetRow(asset.asset_id, asset.name, asset.kind, status, last_run_at, failing)


def asset_rows(conn: sqlite3.Connection) -> tuple[AssetRow, ...]:
    """Every asset's row in id order, every site's: for the OAHE fleet, eleven rows, OAHE-INV-001 before OAHE-INV-002."""
    return tuple(row_of(conn, asset) for asset in fleet_assets(conn, None))


def asset_detail(conn: sqlite3.Connection, asset_id: str) -> AssetDetail:
    """The asset window's content for one id: asset_detail(conn, "OAHE-INV-003").engineers is ("site@oahe.example",)
    in the run fixture; an id the fleet lacks raises UnknownAsset."""
    asset = known(conn, asset_id)
    faults = tuple((f, f.catalogue_row().meaning) for f in open_faults_of(conn, asset_id))
    return AssetDetail(
        asset=asset,
        open_faults=faults,
        latest=result_table.latest_for(conn, asset_id),
        engineers=registry.engineers_for(conn, asset_id),
        status=asset_status(conn, asset_id),
        open_orders=tuple(order for order in work_ledger.by_asset(conn, asset_id) if order.closed is None),
        diagnostics=diagnostics_of(conn, asset),
    )


def diagnostics_of(conn: sqlite3.Connection, asset: Asset) -> tuple[Diagnostic, ...]:
    """Every remote test the registry holds for the asset's kind, with its result from the asset's latest run, failing
    first, then never run, then passing, each group by name; a stored result of a test the folder no longer holds is
    kept, so nothing the run recorded is hidden: an inverter whose last run failed on_grid and passed reachable gives
    on_grid "fail", the five other inverter tests "not run", reachable "pass"; a string, which no test runs on, ()."""
    latest = {found.test_name: found for found in result_table.latest_for(conn, asset.asset_id)}
    names = sorted({test.name for test in tests_for(asset.kind)} | set(latest))
    found = []
    for name in names:
        result = latest.get(name)
        if result is None:
            found.append(Diagnostic(name, NOT_RUN, NEVER_RUN_REASON, None))
        else:
            found.append(Diagnostic(name, PASSED if result.passed else FAILED, result.reason, result.run_at))
    return tuple(sorted(found, key=lambda diagnostic: STATE_ORDER.index(diagnostic.state)))


def open_faults_of(conn: sqlite3.Connection, asset_id: str) -> tuple[Fault, ...]:
    """The asset's open faults of every severity, in fault_id order: an open INV-001 and an open INV-004 on OAHE-INV-003
    give both; a closed one is left out."""
    return tuple(fault for fault in ledger.by_asset(conn, asset_id) if fault.closed is None)


def known_engineers(conn: sqlite3.Connection) -> tuple[str, ...]:
    """Every engineer address the fleet holds, distinct and sorted, for the engineer dropdown: the OAHE fleet gives
    ("inverter@oahe.example", "site@oahe.example")."""
    emails = {asset.engineer_email for asset in fleet_assets(conn, None) if asset.engineer_email is not None}
    return tuple(sorted(emails))


def register_asset(conn: sqlite3.Connection, asset: Asset) -> None:
    """Registers one asset as the fleet does, refusing as it does: a second OAHE-SIT-001 raises RegistryError."""
    # Invariant: SOL-05
    registry.register(conn, asset)


def assign_engineer(conn: sqlite3.Connection, asset_id: str, email: str) -> None:
    """Sets an asset's engineer as the fleet does: assign_engineer(conn, "OAHE-INV-002", "b@x.org") makes it its
    engineer; an unregistered id raises RegistryError, a malformed address ValueError."""
    registry.assign_engineer(conn, asset_id, email)


def codes_for_kind(kind: AssetKind) -> tuple[FaultCode, ...]:
    """The catalogue codes an asset of a kind may carry, for the fault dropdown: codes_for_kind(AssetKind.TRACKER) is
    TRK-001 and TRK-002."""
    # Invariant: SOL-04
    return codes_for(kind)


def kinds() -> tuple[AssetKind, ...]:
    """The kinds the asset maintenance list holds, for the type dropdown: kinds()[0] is AssetKind.SITE."""
    return asset_types.kinds()


def ping_asset(conn: sqlite3.Connection, asset_id: str) -> tuple[Sample, ...]:
    """The stored asset's feed read once, storing nothing (the add-asset window's Ping): against a simulator serving 24
    records, those 24; an id the fleet lacks raises UnknownAsset, a feed that fails FeedError."""
    return feed.ping(known(conn, asset_id))

