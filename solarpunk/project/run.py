"""The scheduled run (2.7, SP-006): the job the clock runs. It pings every asset with an endpoint and stores the new
samples, records a feed that fails as a failing `reachable` result, runs the remote suite over every asset with an
endpoint with the ledger's open-outage flags, gives an asset with no endpoint (no feed to test) its status from its
faults alone, stamps each status, and mails the engineers of every RED or YELLOW asset when a settings
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
from solarpunk.project.tracker import drain_outbox, local_tracker
from solarpunk.project.suggest import suggest_from_run
from solarpunk.remote import results as result_table
from solarpunk.remote import run as remote
from solarpunk.remote import scaffold
from solarpunk.remote import suggestions as suggestion_table
from solarpunk.remote import registry as test_registry
from solarpunk.remote.registry import RemoteTest, Surveyed, discover, tests_for
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
    tickets_sent: int = 0


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


def fed_only(assets: tuple[Asset, ...]) -> tuple[Asset, ...]:
    """The assets with an endpoint, the ones the remote suite tests, in their order: of the OAHE fixture's site,
    OAHE-INV-001 at 127.0.0.1:5020 and a string, (OAHE-INV-001,); an asset with no port has no feed to test (J-023)."""
    return tuple(asset for asset in assets if asset.port is not None)


def fault_statuses(assets: tuple[Asset, ...], outages: dict[str, Fault]) -> dict[str, AssetStatus]:
    """The status of each asset not run through the suite, from its faults alone: RED with an open OUTAGE, else GREEN:
    a string under an open STR-001 (a derate) is GREEN; a site with an open SIT-001 is RED."""
    # Invariant: SOL-11 (a derate is not an outage)
    return {asset.asset_id: AssetStatus.RED if asset.asset_id in outages else AssetStatus.GREEN for asset in assets}


def suggested_yellow(conn: sqlite3.Connection, statuses: dict[str, AssetStatus]) -> dict[str, AssetStatus]:
    """The statuses with every GREEN asset that has an open suggestion made YELLOW, never RED (SP-015): a tracker with no
    feed and a pushed TRK-001 waiting for an engineer is YELLOW; RED and YELLOW are left as they are."""
    waiting = {found.asset_id for found in suggestion_table.open_suggestions(conn)}
    return {asset_id: AssetStatus.YELLOW if status is AssetStatus.GREEN and asset_id in waiting else status
            for asset_id, status in statuses.items()}


def scheduled_run(conn: sqlite3.Connection, run_at: datetime, settings_path: Path | None = None) -> RunReport:
    """The job the clock runs, over every asset in the fleet: for the OAHE run fixture with a simulator for OAHE-INV-001,
    a closed port for OAHE-INV-002 and an open INV-001 on OAHE-INV-003, statuses GREEN, YELLOW and RED for the three
    and, with a settings path, two mails sent and recorded; bad settings raise BadSettings before any ping."""
    # Decision: SP-006
    settings = None if settings_path is None else transport.load_settings(settings_path)
    assets = fleet_assets(conn, None)
    fed = fed_only(assets)
    pinged = ping_all(conn, fed, run_at)
    span = window(run_at)
    samples = {asset.asset_id: sample_table.in_period(conn, asset.asset_id, span) for asset in fed}
    outages = open_outages(conn)
    flags = {asset_id: True for asset_id in outages}
    statuses = fault_statuses(tuple(asset for asset in assets if asset not in fed), outages)
    statuses.update(stamped(remote.run_suite(conn, fed, samples, flags, run_at), pinged.unreachable))
    suggest_from_run(conn, tuple(asset.asset_id for asset in fed), run_at)
    statuses = suggested_yellow(conn, statuses)
    sent, mail_errors = (0, ()) if settings is None else mail_all(conn, assets, statuses, settings, run_at)
    written = len(pinged.unreachable) + sum(len(tests_for(asset.kind)) for asset in fed)
    # Decision: SP-027 (the run drains the ticket outbox into the tracker; a tracker down is an error line, not a stop)
    drained = drain_outbox(conn, local_tracker(conn), run_at)
    down = () if drained.stopped_by is None else (f"tracker: {drained.stopped_by}; {drained.waiting} changes wait",)
    return RunReport(pinged.pinged, pinged.records, written, statuses, sent, pinged.errors + mail_errors + down,
                     drained.sent)



def remote_tests() -> tuple[RemoteTest, ...]:
    """Every remote test the registry finds, in name order: the names are ("on_grid", "power_under_rated", "reachable")
    while those three are the folder's modules."""
    return tuple(discover().values())


def add_remote_test(name: str, kind_names: tuple[str, ...], clauses: tuple[str, ...],
                    folder: Path | None = None) -> Path:
    """Scaffolds a new remote test beside the others (or in the folder given) and returns its file:
    add_remote_test("tracker_moving", (), ("55000-9.1",)) is solarpunk/remote/tests/tracker_moving.py, its kinds from
    the asset maintenance list; a name already taken, an unknown kind or no clause raises BadRemoteTest, a ValueError."""
    return scaffold.add(name, kind_names, clauses, folder)


def remote_tests_folder() -> Path:
    """The folder of the remote tests, where a script dropped in is a test (9.8): solarpunk/remote/tests/."""
    return test_registry.folder()


def survey_remote_tests(folder: Path | None = None) -> tuple[Surveyed, ...]:
    """Every script in the tests' folder (or the one given), each with its test or the reason it cannot load, in name
    order (9.8): one broken script is listed, never raised, so the window over the folder stands."""
    return test_registry.survey(folder or test_registry.folder())
