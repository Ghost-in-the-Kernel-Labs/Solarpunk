"""A dead feed brought back, and its tests re-run (13.16, SP-053): the two calls the demo's window makes through
project: a feed server for samples on a chosen port, and one asset's pass of the scheduled run's own steps."""
import sqlite3
from datetime import datetime

from solarpunk.feed import simulate
from solarpunk.leaf.codes import AssetStatus
from solarpunk.leaf.telemetry import Sample
from solarpunk.project.orchestrator import fleet_assets, open_outages
from solarpunk.project.run import Acquirer, fed_only, ping_all, remote, stamped, window
from solarpunk.project.suggest import faults_from_run
from solarpunk.telemetry import samples as sample_table


def feed_server_on(samples: tuple[Sample, ...], host: str, port: int) -> simulate.FeedServer:
    """A bound feed simulator on host and the port given, answering a ping and live reads from the samples, not yet
    serving: feed_server_on(day, "127.0.0.1", 50123).server_address is ("127.0.0.1", 50123); a port in use raises OSError."""
    return simulate.make_server(samples, host, port, live=True)


def run_asset_tests(conn: sqlite3.Connection, asset_id: str, run_at: datetime,
                    acquirer: Acquirer | None = None) -> AssetStatus:
    """One asset's tests once at run_at, by the steps scheduled_run takes for every fed asset (the ping, the stored
    day's samples, the suite, the faults a failure raises): run_asset_tests(conn, "OAHE-INV-002", at) with its feed up
    records reachable as a pass at that instant and returns the asset's status; an asset with no endpoint runs nothing
    and gets the status it has by its faults."""
    # Decision: SP-053 (the window's one-asset run is scheduled_run's steps over one asset, not a second runner)
    assets = fed_only(tuple(asset for asset in fleet_assets(conn, None) if asset.asset_id == asset_id))
    pinged = ping_all(conn, assets, run_at)
    span = window(run_at)
    samples = {asset.asset_id: sample_table.in_period(conn, asset.asset_id, span) for asset in assets}
    flags = {found: True for found in open_outages(conn)}
    statuses = stamped(remote.run_suite(conn, assets, samples, flags, run_at, acquirer), pinged.unreachable)
    faults_from_run(conn, tuple(asset.asset_id for asset in assets), run_at)
    return AssetStatus.RED if asset_id in open_outages(conn) else statuses.get(asset_id, AssetStatus.GREEN)
