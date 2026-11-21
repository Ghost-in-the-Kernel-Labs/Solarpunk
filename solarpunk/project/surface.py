"""The one surface the Phase 3 windows call (2.7, SP-007, MOD-06): rows for the fleet window, a detail for the asset
window with every remote test of the asset's kind and its latest result (6.4), the engineers, the kinds and codes for
the dropdowns, register and ping for the add-asset window. Each function is one call a window makes and a headless test
makes too, so no UI lane edits the orchestrator."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from solarpunk.faults import ledger
from solarpunk.faults.ledger import FaultCause
from solarpunk.feed import client as feed
from solarpunk.fleet import registry
from solarpunk.leaf import asset_types
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind, AssetStatus, FaultCode, Severity, codes_for
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.telemetry import Sample
from solarpunk.project.orchestrator import asset_status, fleet_assets, is_cover, known, open_outages
from solarpunk.remote import results as result_table
from solarpunk.remote.registry import tests_for
from solarpunk.remote import suggestions as suggestion_table
from solarpunk.remote.results import Recorded
from solarpunk.remote.suggestions import Suggestion
from solarpunk.workorders import ledger as work_ledger
from solarpunk.workorders import tickets as ticket_ledger
from solarpunk.workorders.tickets import Ticket
from solarpunk.workorders.ledger import WorkOrder

NO_FAILURE = "—"
IN_MEMORY = "in memory"
FAILED = "fail"
NO_DATA = result_table.NO_DATA
NOT_RUN = "not run"
PASSED = "pass"
# The order the diagnostics are read in: what failed, then what had no data to check (SP-039), then what has never been
# run, then what passed (6.4).
STATE_ORDER = (FAILED, NO_DATA, NOT_RUN, PASSED)
NEVER_RUN_REASON = "no result yet: the scheduled run has not tested this asset"


@dataclass(frozen=True)
class AssetRow:
    """One row of the fleet window: AssetRow("OAHE-INV-002", "Inverter 2", AssetKind.INVERTER, AssetStatus.YELLOW,
    2026-06-01T12:00Z, "reachable"); an asset never run has last_run_at None, one with nothing failing "—"; has_feed
    says whether it has an endpoint (host and port) the scheduled run can reach, so "never run" and "no feed" differ
    (9.1); outage is the open OUTAGE fault that makes it red, suggested the code of its first open suggestion (9.2), so
    a window can say why a row is its colour without a second call."""

    asset_id: str
    name: str
    kind: AssetKind
    status: AssetStatus
    last_run_at: datetime | None
    failing: str
    has_feed: bool = True
    outage: Fault | None = None
    suggested: str | None = None


@dataclass(frozen=True)
class AssetDetail:
    """The asset window's content: the asset, its open faults beside their meanings, its latest results failing first,
    its engineer chain, its status and its open work orders (4.1, last with a default so 3.2's window keeps working):
    for OAHE-INV-003 with an open INV-001 and a work order on it, open_faults is ((that fault, "Inverter offline: …"),),
    status RED and open_orders (that order,); cover lines up with open_faults, True where the fault's engineer is not
    the asset's own chain (SP-015); suggestions are its open suggestions, a device's first, then the newest (7.5); causes line up with open_faults too, each
    fault's latest root cause or None while blank (7.8, SP-046)."""

    asset: Asset
    open_faults: tuple[tuple[Fault, str], ...]
    latest: tuple[Recorded, ...]
    engineers: tuple[str, ...]
    status: AssetStatus
    open_orders: tuple[WorkOrder, ...] = ()
    diagnostics: tuple["Diagnostic", ...] = ()
    cover: tuple[bool, ...] = ()
    suggestions: tuple[Suggestion, ...] = ()
    causes: tuple[FaultCause | None, ...] = ()


@dataclass(frozen=True)
class Diagnostic:
    """One remote test as the asset window reads it (6.4): its name, "fail", "no data" (SP-039), "not run" or "pass",
    the reason, and the run it came from: Diagnostic("on_grid", "fail", "10:05: off the grid", 2026-06-01T12:00Z); a test the registry
    holds for the kind and the store has no result of is Diagnostic(name, "not run", NEVER_RUN_REASON, None)."""

    test_name: str
    state: str
    reason: str
    run_at: datetime | None


def row_of(conn: sqlite3.Connection, asset: Asset) -> AssetRow:
    """One asset's row from its latest results: OAHE-INV-002 after a run at 12:00 whose reachable failed gives
    AssetRow(…, YELLOW, 12:00 UTC, "reachable"); a string never run gives (…, GREEN, None, "—", False), having no
    endpoint."""
    latest = result_table.latest_for(conn, asset.asset_id)
    last_run_at = latest[0].run_at if latest else None
    failing = next((found.test_name for found in latest if found.failed), NO_FAILURE)
    status = asset_status(conn, asset.asset_id)
    has_feed = asset.host is not None and asset.port is not None
    outage = open_outages(conn).get(asset.asset_id)
    suggestions = suggestion_table.open_suggestions(conn, asset.asset_id)
    suggested = suggestions[0].code if suggestions else None
    return AssetRow(asset.asset_id, asset.name, asset.kind, status, last_run_at, failing, has_feed, outage, suggested)


@dataclass(frozen=True)
class Attention:
    """What waits on a person (9.3, SP-023), each a listing whose length is its count: the open OUTAGE faults, the open
    suggestions awaiting an engineer, the open work orders' tickets. The demo gives one of each: OAHE-INV-002's INV-001,
    OAHE-SEN-001's SEN-001, and the outage's ticket."""

    outages: tuple[Fault, ...]
    suggestions: tuple[Suggestion, ...]
    orders: tuple[Ticket, ...]


def attention(conn: sqlite3.Connection) -> Attention:
    """The three listings the fleet window counts at its top, each read once: nothing in them changes a status."""
    # Invariant: SOL-11 (a derate is not an outage)
    outages = tuple(f for f in ledger.open_faults(conn) if f.catalogue_row().severity is Severity.OUTAGE)
    return Attention(outages, suggestion_table.open_suggestions(conn), ticket_ledger.open_tickets(conn))


def store_name(conn: sqlite3.Connection) -> str:
    """The store's file name, for the status bar (9.5): "demo.db" for the demo's store, "in memory" for one in memory."""
    path = next((row[2] for row in conn.execute("PRAGMA database_list") if row[1] == "main"), "")
    return Path(path).name if path else IN_MEMORY


def fleet_last_run(conn: sqlite3.Connection) -> datetime | None:
    """The instant of the fleet's latest run, or None before any: 2026-06-01 13:00 UTC in the demo."""
    return result_table.last_run_at(conn)


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
        cover=tuple(is_cover(conn, fault) for fault, _ in faults),
        suggestions=suggestion_table.open_suggestions(conn, asset_id),
        causes=tuple(ledger.cause_of(conn, fault.fault_id) for fault, _ in faults),
    )


def diagnostics_of(conn: sqlite3.Connection, asset: Asset) -> tuple[Diagnostic, ...]:
    """Every remote test the registry holds for the asset's kind, with its result from the asset's latest run, failing
    first, then no data, then never run, then passing, each group by name; a stored result of a test the folder no longer holds is
    kept, so nothing the run recorded is hidden: an inverter whose last run failed on_grid and passed reachable gives
    on_grid "fail", the five other inverter tests "not run", reachable "pass"; a string, which no test runs on, ()."""
    latest: dict[str, Recorded] = {}
    # latest_for orders failing first, and one run can store two results of a test (a ping that failed beside the suite
    # run over stored samples): the first kept is the failure, so a failure is never hidden by a pass (J-050).
    for found in result_table.latest_for(conn, asset.asset_id):
        latest.setdefault(found.test_name, found)
    names = sorted({test.name for test in tests_for(asset.kind)} | set(latest))
    found = []
    for name in names:
        result = latest.get(name)
        if result is None:
            found.append(Diagnostic(name, NOT_RUN, NEVER_RUN_REASON, None))
        else:
            found.append(Diagnostic(name, state_of(result), result.reason, result.run_at))
    return tuple(sorted(found, key=lambda diagnostic: STATE_ORDER.index(diagnostic.state)))


def state_of(result: Recorded) -> str:
    """A stored result's diagnostic state: "pass", "fail", or "no data" for a test that had nothing to check (SP-039)."""
    if result.no_data:
        return NO_DATA
    return PASSED if result.passed else FAILED


def open_faults_of(conn: sqlite3.Connection, asset_id: str) -> tuple[Fault, ...]:
    """The asset's open faults of every severity, in fault_id order: an open INV-001 and an open INV-004 on OAHE-INV-003
    give both; a closed one is left out."""
    return tuple(fault for fault in ledger.by_asset(conn, asset_id) if fault.closed is None)


def register_asset(conn: sqlite3.Connection, asset: Asset) -> None:
    """Registers one asset as the fleet does, refusing as it does: a second OAHE-SIT-001 raises RegistryError."""
    # Invariant: SOL-05
    registry.register(conn, asset)


def assign_engineer(conn: sqlite3.Connection, asset_id: str, email: str, read_at: int | None = None) -> None:
    """Sets an asset's engineer as the fleet does: assign_engineer(conn, "OAHE-INV-002", "b@x.org") makes it its
    engineer; an unregistered id raises RegistryError, a malformed address ValueError, an asset read at an older
    version StaleWrite (12.2)."""
    registry.assign_engineer(conn, asset_id, email, read_at)


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

