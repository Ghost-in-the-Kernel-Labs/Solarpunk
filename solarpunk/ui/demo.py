"""The demo's store (3.4): a file store rebuilt each run with the OAHE fixture, one day of seed-7 telemetry, two closed
faults and one open outage, an in-process feed simulator for OAHE-INV-001, and one scheduled run, so the fleet window
opens on green, yellow and red rows and a last-run instant. GREEN is OAHE-INV-001, fed by the simulator; RED is
OAHE-INV-002, carrying an open INV-001 with its port dead (RED wins over YELLOW, SP-007); YELLOW is OAHE-SEN-001, whose
port is dead so its reachable test fails; the trackers, the meter, the strings and the site have no endpoint, so the
suite does not test them and they stay GREEN (J-023). No tkinter here: the window half is in __main__.py, so the store
is built and tested headless (SP-010: this module imports project and the leaf alone)."""
import socket
import socketserver
import sqlite3
import threading
import time
from contextlib import closing
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind, AssetStatus
from solarpunk.leaf.telemetry import Sample
from solarpunk.project.orchestrator import feed_server, simulated_day

SITE = "OAHE"
SITE_ID = "OAHE-SIT-001"
FED = "OAHE-INV-001"
DOWN = "OAHE-INV-002"
SENSOR = "OAHE-SEN-001"
LOOPBACK = "127.0.0.1"
DAY = date(2026, 6, 1)
SEED = 7
RUN_AT = at(2026, 6, 1, 13)
POLL_INTERVAL_S = 0.1
# The demo's bursts (13.13, SP-049): shortened to 5 reads, on a clock that never waits, so the demo opens as fast as ever.
BURST_READS_S = 5
DB_NAME = "demo.db"
SITE_ENGINEER = "site@oahe.example"
INVERTER_ENGINEER = "inverter@oahe.example"
OPERATOR = "operator@oahe.example"
# The faults (SP-015: each names the engineer who assigned it): (asset, code, opened hour, opened minute, closed hour,
# closed minute, engineer, root cause in the engineer's words, what was done). Each closed one's root cause is written by its
# engineer (7.8) before its ticket (8.2) is closed. The open outage on OAHE-INV-002 was called in by INV-001's engineer, covering (INV-002's own
# chain is the site's engineer alone), and entered by the operator: one record showing both.
CLOSED_FAULTS = (
    (SITE_ID, "SIT-002", 12, 0, 13, 0, SITE_ENGINEER, "the grid operator curtailed the site", "curtailment lifted by the grid operator"),
    (FED, "INV-002", 10, 5, 10, 45, INVERTER_ENGINEER, "midday heat derated the inverter", "cooled after the midday peak; filters checked"),
)
OPEN_OUTAGE = (DOWN, "INV-001", 11, 30, INVERTER_ENGINEER, OPERATOR)
NO_FEED_KINDS = (AssetKind.TRACKER, AssetKind.METER)
# The demo's people (13.15, SP-053): two accounts of the OAHE site with fixed, plainly demo-only passwords, printed by the
# demo for the presenter's second terminal; the window signs in as the engineer without asking.
ENGINEER = "engineer@oahe.example"
ENGINEER_PASSWORD = "oahe-demo-engineer"
OPERATOR_PASSWORD = "oahe-demo-operator"
ACCOUNTS = (
    (ENGINEER, "Demo engineer", project.Role.ENGINEER, ENGINEER_PASSWORD),
    (OPERATOR, "Demo operator", project.Role.OPERATOR, OPERATOR_PASSWORD),
)
# 13.15: the dead inverter's stored output is zero from its outage's start to the end of the day (SQL at module level).
ZERO_OUTPUT = "UPDATE samples SET power_kw = 0 WHERE asset_id = ? AND at >= ? AND at < ? AND gap = 0"


@dataclass(frozen=True)
class DemoState:
    """What building the demo made: DemoState(Path("demo.db"), 50123, 50124, <the run's report>), the report's statuses
    holding OAHE-INV-001 GREEN, OAHE-SEN-001 YELLOW and OAHE-INV-002 RED."""

    db_path: Path
    simulator_port: int
    dead_port: int
    run_report: project.RunReport


def reserve_port() -> int:
    """A free loopback port for this run to keep dead (13.16): bound to port 0, read, released, so nothing listens on
    it and a ping is refused at once; reserve_port() is 50124, and a second run's is another, never a fixed number."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((LOOPBACK, 0))
        return probe.getsockname()[1]


def demo_assets(port: int, dead_port: int) -> tuple[Asset, ...]:
    """The OAHE fixture with the demo's endpoints: OAHE-INV-001 at 127.0.0.1:<port>, OAHE-INV-002 and OAHE-SEN-001 at
    127.0.0.1:<dead_port>, the trackers and the meter with no endpoint; demo_assets(5020, 5021)[1].port is 5020,
    eleven assets."""
    return tuple(demo_asset(asset, port, dead_port) for asset in project.demo_fleet())


def demo_asset(asset: Asset, port: int, dead_port: int) -> Asset:
    """One fixture asset with its demo endpoint: OAHE-INV-001 gets 127.0.0.1:<port>; OAHE-INV-002 and OAHE-SEN-001
    127.0.0.1:<dead_port>; a tracker or the meter no host and no port; the site and the strings are as they were."""
    if asset.asset_id == FED:
        return replace(asset, host=LOOPBACK, port=port)
    if asset.asset_id in (DOWN, SENSOR):
        return replace(asset, host=LOOPBACK, port=dead_port)
    if asset.kind in NO_FEED_KINDS:
        return replace(asset, host=None, port=None)
    return asset


def simulator_samples() -> tuple[Sample, ...]:
    """The day the simulator serves: OAHE-INV-001's 288 seed-7 samples of 2026-06-01."""
    inverter = next(asset for asset in project.demo_fleet() if asset.asset_id == FED)
    return simulated_day(inverter, project.day_period(DAY), SEED)


def start_simulator(samples: tuple[Sample, ...]) -> tuple[socketserver.TCPServer, int]:
    """Binds a feed simulator on 127.0.0.1 and a free port and serves it from a daemon thread, which ends with the
    process: start_simulator(simulator_samples()) is (the server, 50123); the caller may shutdown() and server_close()."""
    server = feed_server(samples)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": POLL_INTERVAL_S}, daemon=True).start()
    return server, server.server_address[1]


def add_faults(conn: sqlite3.Connection) -> None:
    """The demo's ledger: SIT-002 on the site 12:00 to 13:00 and INV-002 on OAHE-INV-001 10:05 to 10:45, both closed
    through their tickets (its root cause written, then resolved with what was done and closed), then INV-001 on OAHE-INV-002
    from 11:30, open, called in by INV-001's engineer and entered by the operator; afterwards faults_listing(conn, True)
    is that one outage and open_tickets(conn) its one ticket."""
    for asset_id, code, opened_h, opened_m, closed_h, closed_m, engineer, cause, done in CLOSED_FAULTS:
        project.assign_fault(conn, asset_id, code, at(2026, 6, 1, opened_h, opened_m), engineer)
        (order,) = [work_order for work_order in project.work_orders_for(conn, asset_id) if work_order.closed is None]
        closed = at(2026, 6, 1, closed_h, closed_m)
        project.move_ticket(conn, order.wo_id, project.TicketStatus.IN_PROGRESS, closed)
        project.move_ticket(conn, order.wo_id, project.TicketStatus.RESOLVED, closed, done)
        project.write_fault_cause(conn, order.fault_id, cause, engineer, closed)
        project.close_work_order(conn, order.wo_id, closed)
    asset_id, code, opened_h, opened_m, engineer, operator = OPEN_OUTAGE
    project.assign_fault(conn, asset_id, code, at(2026, 6, 1, opened_h, opened_m), engineer, operator)


def add_accounts(conn: sqlite3.Connection) -> None:
    """The demo's two accounts, engineer@oahe.example (an engineer) and operator@oahe.example (an operator), both of the
    OAHE site, made at the run's instant: afterwards project.accounts(conn) holds both and the store asks for a sign-in."""
    for email, name, role, password in ACCOUNTS:
        project.create_account(conn, email, name, role, password, (SITE,), RUN_AT)


def zero_output(conn: sqlite3.Connection) -> None:
    """OAHE-INV-002's stored power is 0 from its INV-001 outage's start (11:30) to the end of the day, its gaps staying
    gaps: afterwards its 11:30 sample reads 0.0 kW where the generator gave about 90."""
    # Decision: SP-053 (an inverter with an open outage delivers nothing, so the store agrees with its fault)
    _, _, opened_h, opened_m, _, _ = OPEN_OUTAGE
    start = at(2026, 6, 1, opened_h, opened_m)
    conn.execute(ZERO_OUTPUT, (DOWN, start.isoformat(), project.day_period(DAY).end.isoformat()))


def demo_clock(wall: Callable[[], float] = time.monotonic) -> Callable[[], datetime]:
    """The demo's day (13.15): a callable giving the run's instant, 2026-06-01T13:00:00Z, plus the whole seconds of wall
    time elapsed since this call; with a wall clock that says 0 then 90, demo_clock(wall)() is 13:00:00 and then 13:01:30."""
    started = wall()

    def now() -> datetime:
        """The demo's instant: RUN_AT plus the wall seconds since the demo started."""
        return RUN_AT + timedelta(seconds=int(wall() - started))
    return now


def instant_clock(start: datetime = RUN_AT) -> Callable[[float], datetime]:
    """A clock that never waits: each call moves the instant on by the wait it is asked for and says it; from the run's
    instant, instant_clock()(0) is 13:00:00 and the next call with 1 is 13:00:01."""
    now = [start]

    def clock(wait_s: float) -> datetime:
        """The instant after waiting wait_s, without waiting."""
        now[0] += timedelta(seconds=wait_s)
        return now[0]
    return clock


def build_demo_store(path: Path, port: int, dead_port: int | None = None) -> DemoState:
    """Removes the file at path if present and builds the demo there against a simulator on port, the dead assets on
    dead_port (a port nothing serves, 13.16; one reserved for the call when None), then runs the suite
    once at 2026-06-01T13:00Z with no mail, its bursts shortened to 5 reads (13.13), so OAHE-INV-001's power_ripple passes: build_demo_store(Path("demo.db"), 50123, 50124).run_report.statuses["OAHE-INV-002"]
    is RED; a second call rebuilds the same store rather than raising on a duplicate key."""
    dead_port = reserve_port() if dead_port is None else dead_port
    path.unlink(missing_ok=True)
    with closing(project.open_or_create(path)) as conn:
        project.load_fleet(conn, demo_assets(port, dead_port))
        project.generate_and_store(conn, SITE, project.day_period(DAY), SEED)
        zero_output(conn)
        add_faults(conn)
        report = project.scheduled_run(conn, RUN_AT, acquirer=project.feed_acquirer(instant_clock(), BURST_READS_S))
        add_accounts(conn)  # last: the build's own acts name their engineers before accounts exist
        conn.commit()
    return DemoState(path, port, dead_port, report)


class Revival:
    """The demo's one control (13.16, SP-053), handed to the windows by run_demo and by nothing else: Revival(5021) offers
    its button for OAHE-INV-002 and not for OAHE-SEN-001, which the simulator cannot serve, and bring_back starts the
    inverter's feed on 5021 once and runs its tests again."""

    def __init__(self, dead_port: int, now: Callable[[], datetime] | None = None) -> None:
        """A revival of the feed on dead_port, none started yet: Revival(5021).server is None; now is the demo's clock
        (demo_clock, 13.15), which stamps each run so none precedes an act the window stamped; with none, a run is five
        minutes after the last press's."""
        self.dead_port = dead_port
        self.now = now
        self.last_run = RUN_AT
        self.server: socketserver.TCPServer | None = None
        self.runs = 0

    def offers(self, asset: Asset) -> bool:
        """Whether the asset is a dead inverter of the demo: offers(OAHE-INV-002 at 127.0.0.1:5021) is True, offers of
        OAHE-SEN-001 at the same port False (a sensor), and of OAHE-INV-001 on its own port False."""
        return asset.kind is AssetKind.INVERTER and asset.host == LOOPBACK and asset.port == self.dead_port

    def bring_back(self, conn: sqlite3.Connection, asset_id: str) -> AssetStatus:
        """Serves the asset's day on its port (the first press only) and runs its tests once, five minutes after the last
        press's run: the first press of OAHE-INV-002 records reachable as a pass at 13:05 and returns its status."""
        asset = project.asset_detail(conn, asset_id).asset
        if self.server is None:
            samples = simulated_day(asset, project.day_period(DAY), SEED)
            self.server = project.feed_server_on(samples, LOOPBACK, self.dead_port)
            threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": POLL_INTERVAL_S}, daemon=True).start()
        self.runs += 1
        run_at = self.run_instant(project.last_ticket_act(conn, asset_id))
        acquirer = project.feed_acquirer(instant_clock(run_at), BURST_READS_S)
        status = project.run_asset_tests(conn, asset_id, run_at, acquirer)
        conn.commit()
        return status

    def run_instant(self, last_act: datetime | None = None) -> datetime:
        """The instant of this press's run: the demo's clock, never at or before the last press's run (the scheduled run's,
        13:00, before the first) and, once last_act is given, never less than a minute after it (SP-055: the proof follows
        the action); with no clock, RUN_AT plus five minutes per press (the first press gives 13:05): with the last act at
        13:55 the run is stamped 13:56 at the earliest."""
        # Decision: SP-055 (the revival is never stamped before the asset's last ticket act)
        found = RUN_AT + timedelta(minutes=5 * self.runs) if self.now is None else self.now()
        if last_act is not None:
            found = max(found, last_act + project.AFTER_THE_LAST_ACT)
        if self.now is not None and found <= self.last_run:
            found = self.last_run + timedelta(seconds=1)
        self.last_run = found
        return found

    def close(self) -> None:
        """Stops the feed if one was started: after close(), the port answers nothing; a second close does nothing."""
        server, self.server = self.server, None
        if server is not None:
            server.shutdown()
            server.server_close()
