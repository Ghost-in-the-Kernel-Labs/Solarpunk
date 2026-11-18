"""The orchestrator (lane 1.6): opens the store with every module's tables and joins the lanes over it, in
solarpunk/project/orchestrator.py; the only module that imports fleet, faults, telemetry and kpi together (MOD-02).
The scheduled run is in run.py (2.7, SP-006); the one surface the Phase 3 windows call is in surface.py (SP-007). The
errors a surface catches are re-exported here, so receiver and ui catch them exactly without importing a lane (MOD-06)."""
from solarpunk.faults.ledger import LedgerError
from solarpunk.feed.client import FeedError
from solarpunk.fleet.registry import RegistryError
from solarpunk.project.orchestrator import (
    Fault,
    SiteKpis,
    UnknownAsset,
    asset_status,
    assign_fault,
    close_fault,
    day_period,
    demo_fleet,
    faults_listing,
    fleet_assets,
    fleet_listing,
    generate_and_store,
    kpis_for,
    load_fleet,
    open_or_create,
    open_outages,
    open_store,
    period,
)
from solarpunk.project.run import RunReport, scheduled_run
from solarpunk.project.surface import (
    AssetDetail,
    AssetRow,
    asset_detail,
    asset_rows,
    assign_engineer,
    codes_for_kind,
    kinds,
    known_engineers,
    ping_asset,
    register_asset,
)

__all__ = [
    "AssetDetail",
    "AssetRow",
    "Fault",
    "FeedError",
    "LedgerError",
    "RegistryError",
    "RunReport",
    "SiteKpis",
    "UnknownAsset",
    "asset_detail",
    "asset_rows",
    "asset_status",
    "assign_engineer",
    "assign_fault",
    "close_fault",
    "codes_for_kind",
    "day_period",
    "demo_fleet",
    "faults_listing",
    "fleet_assets",
    "fleet_listing",
    "generate_and_store",
    "kinds",
    "known_engineers",
    "kpis_for",
    "load_fleet",
    "open_or_create",
    "open_outages",
    "open_store",
    "period",
    "ping_asset",
    "register_asset",
    "scheduled_run",
]
