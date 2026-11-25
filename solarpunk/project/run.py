"""The scheduled run (2.7, SP-006): the job the clock runs. It pings every asset with an endpoint and stores the new
samples, records each ping as a `reachable` result (a pass naming what answered, or the failure), runs the remote suite over every asset with an
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
from solarpunk.project.reactions import carry_out
from solarpunk.project.suggest import faults_from_run
from solarpunk.project.suites import run_due_suites
from solarpunk.remote import results as result_table
from solarpunk.remote import run as remote
from solarpunk.remote import scaffold
from solarpunk.remote import suggestions as suggestion_table
from solarpunk.remote import registry as test_registry
from solarpunk.remote import suite_registry
from solarpunk.remote.acquire import Acquirer, Burst, Clock, ReadFailed, take, wall_clock
from solarpunk.remote.registry import PING, RemoteTest, Surveyed, discover, tests_for
from solarpunk.remote.suite_registry import Suite
from solarpunk.telemetry import samples as sample_table

REACHABLE = PING
WINDOW = timedelta(days=1)
ALERTING = (AssetStatus.RED, AssetStatus.YELLOW)
ANSWERED = "answered: {count} new records"
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
    """The pings' outcome: Pinged(3, 24, ("OAHE-INV-002",), ("OAHE-INV-002: 127.0.0.1:9 is unreachable",), 3); stored is
    the reachable results the pings wrote, one per asset pinged (SP-055)."""

    pinged: int
    records: int
    unreachable: tuple[str, ...]
    errors: tuple[str, ...]
    stored: int = 0  # the ping results stored: a pass for each asset that answered, a failure for each that did not


def feed_acquirer(clock: Clock, shorten_to_s: float | None = None) -> Acquirer:
    """What the runner takes a test's ACQUIRE reads with (13.3, SP-020): every read one live request to the asset's
    feed, at the instant the clock gives, so a clock that never waits drives a minute's burst at once (a simulator
    answers from its day); shorten_to_s cuts a burst's duration. A feed that fails a read gives that read no value."""
    def reader(asset: Asset, field: str, moment: datetime) -> float | None:
        """One live read through the feed; a FeedError, or a connection reset mid-read, is the read's failure."""
        try:
            return feed.read_now(asset, field, moment)
        except (feed.FeedError, ConnectionError) as error:
            raise ReadFailed(str(error)) from error

    def acquire(asset: Asset, burst: Burst) -> tuple:
        """The burst's reads of the asset, each with its instant."""
        return take(asset, burst, reader, clock, shorten_to_s)
    return acquire


def live_acquirer(reads: int | None = None) -> Acquirer:
    """What the command line's `test run --acquire` takes reads with (13.13, SP-049): feed_acquirer on the real clock,
    which waits between reads; reads cuts each burst to that many reads (its own period times reads), None leaves it
    whole: Burst("power_kw", 1, 60) with reads 5 takes 5 reads over four seconds, with None sixty over a minute."""
    def acquire(asset: Asset, burst: Burst) -> tuple:
        """The burst's reads of the asset, at most reads of them."""
        return feed_acquirer(wall_clock, None if reads is None else reads * burst.every_s)(asset, burst)
    return acquire


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
    span = Period(min(sample.moment for sample in samples), max(sample.moment for sample in samples) + SAMPLE_INTERVAL)
    held = {sample.moment for sample in sample_table.in_period(conn, samples[0].asset_id, span)}
    return tuple(sample for sample in samples if sample.moment not in held)


def ping_all(conn: sqlite3.Connection, assets: tuple[Asset, ...], run_at: datetime) -> Pinged:
    """Pings every asset with an endpoint and stores its new samples; a FeedError is recorded at run_at as a failing
    reachable result whose reason is the error's message, and an answer as a passing one, "answered: N new records"
    (SP-055), both untimed: a simulator for one inverter serving 24 records and a closed port for another give
    Pinged(2, 24, (the other,), ("<the other>: 127.0.0.1:<port> is unreachable",), 2) with the pass and the failure stored."""
    # Decision: SP-055 (a ping that answers records its own reachable pass, beside the failure it records)
    pinged, records, stored = 0, 0, 0
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
            stored += 1
            unreachable.append(asset.asset_id)
            errors.append(ERROR_LINE.format(asset_id=asset.asset_id, error=error))
            continue
        sample_table.store(conn, fresh)
        result_table.record(conn, REACHABLE, asset.asset_id, run_at,
                            result_table.Result(True, ANSWERED.format(count=len(fresh))))
        stored += 1
        records += len(fresh)
    return Pinged(pinged, records, tuple(unreachable), tuple(errors), stored)


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
    an open INV-001 gives that Fault; a failing records_stored "no records" gives RemoteFailure("records_stored", "no records")."""
    if asset_id in outages:
        return outages[asset_id]
    failing = next(found for found in result_table.latest_for(conn, asset_id) if found.failed)  # never no data
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


def scheduled_run(conn: sqlite3.Connection, run_at: datetime, settings_path: Path | None = None,
                  acquirer: Acquirer | None = None) -> RunReport:
    """The job the clock runs, over every asset in the fleet: for the OAHE run fixture with a simulator for OAHE-INV-001,
    a closed port for OAHE-INV-002 and an open INV-001 on OAHE-INV-003, statuses GREEN, YELLOW and RED for the three
    and, with a settings path, two mails sent and recorded; bad settings raise BadSettings before any ping. A test with
    ACQUIRE is judged on the reads the acquirer takes through the feed (feed_acquirer); with none given it says no data."""
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
    statuses.update(stamped(remote.run_suite(conn, fed, samples, flags, run_at, acquirer), pinged.unreachable))
    # Decision: SP-046 (a failing test of the run raises its fault itself, at the run's instant)
    faults_from_run(conn, tuple(asset.asset_id for asset in fed), run_at)
    outages = open_outages(conn)  # the run's own faults count: an OUTAGE a test raised makes the asset RED at once
    statuses = {asset_id: AssetStatus.RED if asset_id in outages else status for asset_id, status in statuses.items()}
    # Decision: SP-019 (the run runs each named suite due at its instant; the default suite is the run above)
    named_written = run_due_suites(conn, fed, samples, run_at)
    # Decision: SP-020 (a failing test does what it declared: raise its fault, mail, run a suite, open a preventive order)
    reaction_mails = carry_out(conn, fed, samples, run_at, settings, acquirer)
    outages = open_outages(conn)  # a fault a reaction's suite raised counts too
    statuses = {asset_id: AssetStatus.RED if asset_id in outages else status for asset_id, status in statuses.items()}
    statuses = suggested_yellow(conn, statuses)
    sent, mail_errors = (0, ()) if settings is None else mail_all(conn, assets, statuses, settings, run_at)
    sent += reaction_mails
    written = pinged.stored + sum(len(tests_for(asset.kind)) for asset in fed) + named_written
    # Decision: SP-027 (the run drains the ticket outbox into the tracker; a tracker down is an error line, not a stop)
    drained = drain_outbox(conn, local_tracker(conn), run_at)
    down = () if drained.stopped_by is None else (f"tracker: {drained.stopped_by}; {drained.waiting} changes wait",)
    return RunReport(pinged.pinged, pinged.records, written, statuses, sent, pinged.errors + mail_errors + down,
                     drained.sent)



def remote_tests() -> tuple[RemoteTest, ...]:
    """Every remote test the registry finds, in name order: the names are ("on_grid", "power_under_rated", "records_stored")
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


def run_suite_now(conn: sqlite3.Connection, name: str, run_at: datetime,
                  where: Path | None = None, acquirer: Acquirer | None = None) -> tuple[Suite, int]:
    """Runs the suite by name at run_at over every asset with an endpoint and its stored samples of the day up to it, and
    returns it with the results written: run_suite_now(conn, "all", at) writes every test's result; an unknown name
    raises BadRemoteTest."""
    suite = suite_registry.named(name, where)
    fed = fed_only(fleet_assets(conn, None))
    span = window(run_at)
    samples = {asset.asset_id: sample_table.in_period(conn, asset.asset_id, span) for asset in fed}
    return suite, remote.run_named(conn, suite, fed, samples, run_at, acquirer)
