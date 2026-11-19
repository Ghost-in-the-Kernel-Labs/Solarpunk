"""The demo's store (3.4): a file store rebuilt each run with the OAHE fixture, one day of seed-7 telemetry, two closed
faults and one open outage, an in-process feed simulator for OAHE-INV-001, and one scheduled run, so the fleet window
opens on green, yellow and red rows and a last-run instant. GREEN is OAHE-INV-001, fed by the simulator; RED is
OAHE-INV-002, carrying an open INV-001 with its port dead (RED wins over YELLOW, SP-007); YELLOW is OAHE-SEN-001, whose
port is dead so its reachable test fails; the trackers, the meter, the strings and the site have no endpoint, so the
suite does not test them and they stay GREEN (J-023). No tkinter here: the window half is in __main__.py, so the store
is built and tested headless (SP-010: this module imports project and the leaf alone)."""
import socketserver
import sqlite3
import threading
from contextlib import closing
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.project.orchestrator import feed_server, simulated_day

SITE = "OAHE"
SITE_ID = "OAHE-SIT-001"
FED = "OAHE-INV-001"
DOWN = "OAHE-INV-002"
SENSOR = "OAHE-SEN-001"
LOOPBACK = "127.0.0.1"
# A port nobody listens on (the discard service, never run on a demo machine): a ping to it is refused at once.
DEAD_PORT = 9
DAY = date(2026, 6, 1)
SEED = 7
RUN_AT = at(2026, 6, 1, 13)
POLL_INTERVAL_S = 0.1
DB_NAME = "demo.db"
SITE_ENGINEER = "site@oahe.example"
INVERTER_ENGINEER = "inverter@oahe.example"
OPERATOR = "operator@oahe.example"
# The faults (SP-015: each names the engineer who assigned it): (asset, code, opened hour, opened minute, closed hour,
# closed minute, engineer, root cause, what was done). Each closed one's ticket (8.2) is closed with its root cause. The open outage on OAHE-INV-002 was called in by INV-001's engineer, covering (INV-002's own
# chain is the site's engineer alone), and entered by the operator: one record showing both.
CLOSED_FAULTS = (
    (SITE_ID, "SIT-002", 12, 0, 13, 0, SITE_ENGINEER, "RC-GRID", "curtailment lifted by the grid operator"),
    (FED, "INV-002", 10, 5, 10, 45, INVERTER_ENGINEER, "RC-WEATHER", "cooled after the midday peak; filters checked"),
)
OPEN_OUTAGE = (DOWN, "INV-001", 11, 30, INVERTER_ENGINEER, OPERATOR)
NO_FEED_KINDS = (AssetKind.TRACKER, AssetKind.METER)


@dataclass(frozen=True)
class DemoState:
    """What building the demo made: DemoState(Path("demo.db"), 50123, <the run's report>), the report's statuses
    holding OAHE-INV-001 GREEN, OAHE-SEN-001 YELLOW and OAHE-INV-002 RED."""

    db_path: Path
    simulator_port: int
    run_report: project.RunReport


def demo_assets(port: int) -> tuple[Asset, ...]:
    """The OAHE fixture with the demo's endpoints: OAHE-INV-001 at 127.0.0.1:<port>, OAHE-INV-002 and OAHE-SEN-001 at
    127.0.0.1:9, the trackers and the meter with no endpoint; demo_assets(5020)[1].port is 5020, eleven assets."""
    return tuple(demo_asset(asset, port) for asset in project.demo_fleet())


def demo_asset(asset: Asset, port: int) -> Asset:
    """One fixture asset with its demo endpoint: OAHE-INV-001 gets 127.0.0.1:<port>; OAHE-INV-002 and OAHE-SEN-001
    127.0.0.1:9; a tracker or the meter no host and no port; the site and the strings are as they were."""
    if asset.asset_id == FED:
        return replace(asset, host=LOOPBACK, port=port)
    if asset.asset_id in (DOWN, SENSOR):
        return replace(asset, host=LOOPBACK, port=DEAD_PORT)
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
    through their tickets (resolved with what was done, then closed with a root cause), then INV-001 on OAHE-INV-002
    from 11:30, open, called in by INV-001's engineer and entered by the operator; afterwards faults_listing(conn, True)
    is that one outage and open_tickets(conn) its one ticket."""
    for asset_id, code, opened_h, opened_m, closed_h, closed_m, engineer, cause, done in CLOSED_FAULTS:
        project.assign_fault(conn, asset_id, code, at(2026, 6, 1, opened_h, opened_m), engineer)
        (order,) = [o for o in project.work_orders_for(conn, asset_id) if o.closed is None]
        closed = at(2026, 6, 1, closed_h, closed_m)
        project.move_ticket(conn, order.wo_id, project.TicketStatus.IN_PROGRESS, closed)
        project.move_ticket(conn, order.wo_id, project.TicketStatus.RESOLVED, closed, done)
        project.close_work_order(conn, order.wo_id, cause, closed)
    asset_id, code, opened_h, opened_m, engineer, operator = OPEN_OUTAGE
    project.assign_fault(conn, asset_id, code, at(2026, 6, 1, opened_h, opened_m), engineer, operator)


def build_demo_store(path: Path, port: int) -> DemoState:
    """Removes the file at path if present and builds the demo there against a simulator on port, then runs the suite
    once at 2026-06-01T13:00Z with no mail: build_demo_store(Path("demo.db"), 50123).run_report.statuses["OAHE-INV-002"]
    is RED; a second call rebuilds the same store rather than raising on a duplicate key."""
    path.unlink(missing_ok=True)
    with closing(project.open_or_create(path)) as conn:
        project.load_fleet(conn, demo_assets(port))
        project.generate_and_store(conn, SITE, project.day_period(DAY), SEED)
        add_faults(conn)
        report = project.scheduled_run(conn, RUN_AT)
        conn.commit()
    return DemoState(path, port, report)
