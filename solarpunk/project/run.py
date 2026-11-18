"""The scheduled run (2.7, SP-006): the job the clock runs. It pings every asset with an endpoint and stores the new
samples, records a feed that fails as a failing `reachable` result, runs the remote suite over every asset with the
ledger's open-outage flags, stamps each status, and mails the engineers of every RED or YELLOW asset when a settings
path is given, recording each mail sent. Project's own reads go through the owning lanes' modules (fleet, ledger,
samples, results, mails); remote's stored_samples and stored_asset stay remote's, for its command line (J-022)."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from solarpunk.feed import client as feed
from solarpunk.fleet import registry
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import SAMPLE_INTERVAL, SAMPLE_INTERVAL_S, Period, utc
from solarpunk.leaf.codes import AssetStatus
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.telemetry import Sample
from solarpunk.mailer import mail as mailer
from solarpunk.mailer import transport
from solarpunk.project.orchestrator import fleet_assets, open_outages
from solarpunk.remote import results as result_table
from solarpunk.remote import run as remote
from solarpunk.remote.registry import tests_for
from solarpunk.telemetry import samples as sample_table

REACHABLE = "reachable"
WINDOW = timedelta(days=1)
ALERTING = (AssetStatus.RED, AssetStatus.YELLOW)
ERROR_LINE = "{asset_id}: {error}"


@dataclass(frozen=True)
class RunReport:
    """What one scheduled run did: RunReport(3, 24, 10, {"OAHE-INV-001": GREEN, …}, 2, ("OAHE-INV-002: 127.0.0.1:9 is
    unreachable",)); pinged counts every asset with an endpoint, reached or not; errors names each failed ping and
    each mail not sent."""

    pinged: int
    records: int
    results: int
    statuses: dict[str, AssetStatus]
    mails: int
    errors: tuple[str, ...]


@dataclass(frozen=True)
class Pinged:
    """The pings' outcome: Pinged(3, 24, ("OAHE-INV-002",), ("OAHE-INV-002: 127.0.0.1:9 is unreachable",))."""

    pinged: int
    records: int
    unreachable: tuple[str, ...]
    errors: tuple[str, ...]


def window(run_at: datetime) -> Period:
    """The 24 h of samples a run tests, up to run_at floored to the sample grid: window(2026-06-02T00:03:20Z) is
    Period(2026-06-01T00:00Z, 2026-06-02T00:00Z); a naive run_at raises NotUtc."""
    seconds = utc(run_at).timestamp() // SAMPLE_INTERVAL_S * SAMPLE_INTERVAL_S
    end = datetime.fromtimestamp(seconds, timezone.utc)
    return Period(end - WINDOW, end)


def new_samples(conn: sqlite3.Connection, samples: tuple[Sample, ...]) -> tuple[Sample, ...]:
    """The samples of one asset's feed whose instants the store does not yet hold, so a second ping of the same day
    stores nothing rather than raising on the duplicate key: with 10:00 stored, (10:00, 10:05) gives (10:05,); () is ()."""
    if not samples:
        return ()
    span = Period(min(s.at for s in samples), max(s.at for s in samples) + SAMPLE_INTERVAL)
    held = {s.at for s in sample_table.in_period(conn, samples[0].asset_id, span)}
    return tuple(s for s in samples if s.at not in held)


def ping_all(conn: sqlite3.Connection, assets: tuple[Asset, ...], run_at: datetime) -> Pinged:
    """Pings every asset with an endpoint and stores its new samples; a FeedError is recorded at run_at as a failing
    reachable result whose reason is the error's message: a simulator for one inverter serving 24 records and a closed
    port for another give Pinged(2, 24, (the other,), ("<the other>: 127.0.0.1:<port> is unreachable",))."""
    pinged, records = 0, 0
    unreachable: list[str] = []
    errors: list[str] = []
    for asset in assets:
        if asset.port is None:
            continue
        pinged += 1
        try:
            fresh = new_samples(conn, feed.ping(asset))
        except feed.FeedError as error:
            result_table.record(conn, REACHABLE, asset.asset_id, run_at, result_table.Result(False, str(error)))
            unreachable.append(asset.asset_id)
            errors.append(ERROR_LINE.format(asset_id=asset.asset_id, error=error))
            continue
        sample_table.store(conn, fresh)
        records += len(fresh)
    return Pinged(pinged, records, tuple(unreachable), tuple(errors))


def stamped(statuses: dict[str, AssetStatus], unreachable: tuple[str, ...]) -> dict[str, AssetStatus]:
    """The suite's statuses with an unreachable asset never GREEN: its failing reachable result is among its latest even
    when samples stored earlier passed the suite: ({"A": GREEN, "B": GREEN, "C": RED}, ("A", "C")) gives
    {"A": YELLOW, "B": GREEN, "C": RED}."""
    return {
        asset_id: AssetStatus.YELLOW if asset_id in unreachable and status is AssetStatus.GREEN else status
        for asset_id, status in statuses.items()
    }


def cause_of(conn: sqlite3.Connection, asset_id: str, outages: dict[str, Fault]) -> Fault | mailer.RemoteFailure:
    """What a degradation mail is about: the asset's open outage when it has one, else its first failing latest result:
    an open INV-001 gives that Fault; a failing reachable "no records" gives RemoteFailure("reachable", "no records")."""
    if asset_id in outages:
        return outages[asset_id]
    failing = next(found for found in result_table.latest_for(conn, asset_id) if not found.passed)
    return mailer.RemoteFailure(failing.test_name, failing.reason)


def mail_one(conn: sqlite3.Connection, asset: Asset, cause: Fault | mailer.RemoteFailure,
             settings: transport.Settings, run_at: datetime) -> None:
    """Composes, sends and records one degradation mail to the asset's engineer chain: for OAHE-INV-003 with an open
    INV-001, one mail to ("site@oahe.example",) and one mails row; nobody to mail raises NoEngineer, a failed send
    MailError, and neither records a row."""
    mail = mailer.compose_degradation(asset, cause, registry.engineers_for(conn, asset.asset_id), run_at)
    transport.send(mail, settings)
    mailer.record(conn, mail, asset.asset_id, run_at)


def mail_all(conn: sqlite3.Connection, assets: tuple[Asset, ...], statuses: dict[str, AssetStatus],
             settings: transport.Settings, run_at: datetime) -> tuple[int, tuple[str, ...]]:
    """Mails every RED or YELLOW asset, in the assets' order, and returns (mails sent, errors): one RED and one YELLOW
    asset with engineers give (2, ()); a mail that cannot go adds "<asset-id>: <why>" and the run goes on."""
    outages = open_outages(conn)
    sent = 0
    errors: list[str] = []
    for asset in assets:
        if statuses[asset.asset_id] not in ALERTING:
            continue
        try:
            mail_one(conn, asset, cause_of(conn, asset.asset_id, outages), settings, run_at)
        except (mailer.NoEngineer, transport.MailError) as refused:
            errors.append(ERROR_LINE.format(asset_id=asset.asset_id, error=refused))
            continue
        sent += 1
    return sent, tuple(errors)


def scheduled_run(conn: sqlite3.Connection, run_at: datetime, settings_path: Path | None = None) -> RunReport:
    """The job the clock runs, over every asset in the fleet: for the OAHE run fixture with a simulator for OAHE-INV-001,
    a closed port for OAHE-INV-002 and an open INV-001 on OAHE-INV-003, statuses GREEN, YELLOW and RED for the three
    and, with a settings path, two mails sent and recorded; bad settings raise BadSettings before any ping."""
    # Decision: SP-006
    settings = None if settings_path is None else transport.load_settings(settings_path)
    assets = fleet_assets(conn, None)
    pinged = ping_all(conn, assets, run_at)
    span = window(run_at)
    samples = {asset.asset_id: sample_table.in_period(conn, asset.asset_id, span) for asset in assets}
    flags = {asset_id: True for asset_id in open_outages(conn)}
    statuses = stamped(remote.run_suite(conn, assets, samples, flags, run_at), pinged.unreachable)
    sent, mail_errors = (0, ()) if settings is None else mail_all(conn, assets, statuses, settings, run_at)
    written = len(pinged.unreachable) + sum(len(tests_for(asset.kind)) for asset in assets)
    return RunReport(pinged.pinged, pinged.records, written, statuses, sent, pinged.errors + mail_errors)

