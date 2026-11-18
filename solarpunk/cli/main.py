"""The thin CLI: each subcommand parses its arguments, makes one call into project and prints plain text; a refusal
(any ValueError project raises: UnknownAsset, RegistryError, LedgerError, UnknownFaultCode, NotUtc) prints
"error: <message>" to stderr and exits 2 (MOD-02: logic cannot hide in argument parsing)."""
import argparse
import sqlite3
import subprocess
import sys
from contextlib import closing, redirect_stderr, redirect_stdout
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TextIO

from solarpunk import project

ROOT = Path(__file__).resolve().parents[2]
CLAUSES_SCRIPT = "scripts/clauses.py"
DEFAULT_DB = "solarpunk.db"
DESCRIPTION = "Instants are UTC: 2026-06-01T10:00:00+00:00."
# The help list: every command, the window's first. test/solarpunk/test_cli_tests.py holds it to the parser, so a
# subcommand added below without its line here fails.
HELP = """Solarpunk: the commands. On Windows type them after "solarpunk"; anywhere, the window is
"python -m solarpunk.ui" and the rest "python -m solarpunk.cli <command>". Instants are UTC: 2026-06-01T10:00:00+00:00.

The window
  solarpunk                                    open the fleet window on solarpunk.db in this folder, made if missing
  solarpunk --demo                             rebuild demo.db and open the demo
  solarpunk --db PATH                          open the window on another store
  solarpunk --help                             this list

The remote tests
  test list                                    each remote test with its asset kinds and clauses
  test run [--db PATH] [--at INSTANT]          run every remote test over every asset of the store, once
  test add NAME --clause ID [--kind KIND]      scaffold a new remote test; it fails until its run is written

The fleet and its faults
  fleet load --demo                            register the OAHE example fleet
  fleet list [--site SITE]                     each asset with its kind, name and status
  fault assign ASSET_ID CODE OPENED            open a fault from the catalogue on an asset
  fault close FAULT_ID CLOSED                  close a fault
  fault list [--open]                          the faults, or the open ones alone

The numbers
  telemetry generate SITE DAY --seed N         store a day of synthetic telemetry
  kpi SITE START END [--meter-kwh X]           availability, performance ratio, energy yield, MTBF and MTTR
  clauses                                      each ISO 9001 and ISO 55000 clause and the test that holds it
  help                                         this list

Every command but test run reads solarpunk.db in this folder; for another store,
python -m solarpunk.cli --db PATH <command>.
"""


def instant(text: str) -> datetime:
    """An ISO instant as written; the leaf refuses a naive one when it is used: instant("2026-06-01T10:00:00+00:00")
    is 10:00 UTC; instant("soon") raises ValueError."""
    return datetime.fromisoformat(text)


def fault_line(fault: project.Fault) -> str:
    """One fault as a line: Fault(1, "OAHE-INV-001", "INV-001", 10:10 UTC, None) is
    "1 OAHE-INV-001 INV-001 2026-06-01T10:10:00+00:00 open"."""
    closed = "open" if fault.closed is None else fault.closed.isoformat()
    return f"{fault.fault_id} {fault.asset_id} {fault.code} {fault.opened.isoformat()} {closed}"


def fleet_load(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """fleet load --demo: registers the OAHE example fleet and prints "loaded 11 assets"."""
    demo = project.demo_fleet()
    project.load_fleet(conn, demo)
    out.write(f"loaded {len(demo)} assets\n")


def fleet_list(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """fleet list [--site SITE]: one line per asset, "OAHE-INV-001  INV  Inverter 1  green"."""
    for asset, status in project.fleet_listing(conn, args.site):
        out.write(f"{asset.asset_id}  {asset.kind.value}  {asset.name}  {status.value}\n")


def fault_assign(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """fault assign OAHE-INV-001 INV-001 2026-06-01T10:10:00+00:00 prints
    "1 OAHE-INV-001 INV-001 2026-06-01T10:10:00+00:00 open"."""
    out.write(fault_line(project.assign_fault(conn, args.asset_id, args.code, instant(args.opened))) + "\n")


def fault_close(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """fault close 1 2026-06-01T10:30:00+00:00 prints the fault with its close,
    "1 OAHE-INV-001 INV-001 2026-06-01T10:10:00+00:00 2026-06-01T10:30:00+00:00"."""
    out.write(fault_line(project.close_fault(conn, args.fault_id, instant(args.closed))) + "\n")


def fault_list(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """fault list [--open]: one fault_line per fault in fault_id order, the open ones alone with --open."""
    for fault in project.faults_listing(conn, args.open):
        out.write(fault_line(fault) + "\n")


def telemetry_generate(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """telemetry generate OAHE 2026-06-01 --seed 7 stores the day's samples and prints "stored 576 samples"."""
    day = project.day_period(date.fromisoformat(args.day))
    out.write(f"stored {project.generate_and_store(conn, args.site, day, args.seed)} samples\n")


def write_kpis(found: project.SiteKpis, out: TextIO) -> None:
    """Each KPI on its own line with its parts: J-012's OAHE day (SIT-002 12:00-13:00, INV-001 12:30-14:30, seed 7)
    starts "availability OAHE-INV-001 0.9348 expected=288 excluded=12 down=18 gaps=9" and ends
    "status OAHE-TRK-002 green"."""
    for asset_id, avail in found.availability.items():
        out.write(f"availability {asset_id} {avail.value} expected={avail.expected} excluded={avail.excluded}"
                  f" down={avail.down} gaps={avail.gaps}\n")
    ratio = found.performance_ratio
    out.write(f"performance_ratio {ratio.value} energy_kwh={ratio.energy_kwh} reference_kwh={ratio.reference_kwh}"
              f" unreliable={ratio.unreliable}\n")
    out.write(f"energy_yield {found.energy_yield.kwh} source={found.energy_yield.source}\n")
    for kind, rel in found.reliability.items():
        out.write(f"reliability {kind.value} mtbf_h={rel.mtbf_h} mttr_h={rel.mttr_h} count={rel.count}"
                  f" open={rel.open}\n")
    out.write(f"faults_open {found.faults_open}\n")
    for asset_id, status in found.status.items():
        out.write(f"status {asset_id} {status.value}\n")


def kpi(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """kpi OAHE 2026-06-01T00:00:00+00:00 2026-06-02T00:00:00+00:00 [--meter-kwh X] prints write_kpis' lines."""
    span = project.period(instant(args.start), instant(args.end))
    write_kpis(project.kpis_for(conn, args.site, span, args.meter_kwh), out)


def show_help(args: argparse.Namespace, out: TextIO) -> None:
    """help: prints the help list, HELP, whose first line is "Solarpunk: the commands. ..."."""
    out.write(HELP)


def test_list(args: argparse.Namespace, out: TextIO) -> None:
    """test list: one line per remote test with its kinds and clauses, "reachable  INV,MTR,SEN,TRK  55000-9.1"."""
    for test in project.remote_tests():
        kinds = ",".join(kind.value for kind in test.kinds)
        out.write(f"{test.name}  {kinds}  {','.join(test.clauses)}\n")


def test_add(args: argparse.Namespace, out: TextIO) -> None:
    """test add tracker_moving --clause 55000-9.1 [--kind TRACKER]: scaffolds the test's module and prints
    "wrote <its path>", then a line saying it fails until its run is written."""
    path = project.add_remote_test(args.name, tuple(args.kind), tuple(args.clause))
    out.write(f"wrote {path}\n{args.name} fails on every run until its run function is written\n")


def test_run(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """test run [--at INSTANT] [--db PATH]: the scheduled run once, now or at the instant given, over every asset of
    the store: "run 2026-06-01T13:00:00+00:00: pinged 3, records 24, results 6", then "OAHE-INV-001  green" for each
    asset and "error OAHE-INV-002: 127.0.0.1:9 is unreachable" for each feed that did not answer."""
    run_at = datetime.now(timezone.utc).replace(microsecond=0) if args.at is None else instant(args.at)
    report = project.scheduled_run(conn, run_at)
    out.write(f"run {run_at.isoformat()}: pinged {report.pinged}, records {report.records},"
              f" results {report.results}\n")
    for asset_id, status in sorted(report.statuses.items()):
        out.write(f"{asset_id}  {status.value}\n")
    for error in report.errors:
        out.write(f"error {error}\n")


def run_clauses(out: TextIO, err: TextIO) -> int:
    """clauses: the one subcommand that is not a project call; it runs scripts/clauses.py isolated from the repository
    root and passes its output and exit code through: "9001: 7 held, 0 failing, 1 open" among its lines, exit 0."""
    done = subprocess.run([sys.executable, "-I", CLAUSES_SCRIPT], cwd=ROOT, capture_output=True, text=True, check=False)
    out.write(done.stdout)
    err.write(done.stderr)
    return done.returncode


def add_fleet_and_faults(commands: argparse._SubParsersAction) -> None:
    """The fleet and fault subcommands, each pointing at its handler: "fleet list --site OAHE" parses to fleet_list."""
    fleet = commands.add_parser("fleet").add_subparsers(required=True)
    load = fleet.add_parser("load")
    load.add_argument("--demo", action="store_true", required=True)
    load.set_defaults(handler=fleet_load)
    listing = fleet.add_parser("list")
    listing.add_argument("--site")
    listing.set_defaults(handler=fleet_list)
    fault = commands.add_parser("fault").add_subparsers(required=True)
    assign = fault.add_parser("assign")
    assign.add_argument("asset_id")
    assign.add_argument("code")
    assign.add_argument("opened")
    assign.set_defaults(handler=fault_assign)
    close = fault.add_parser("close")
    close.add_argument("fault_id", type=int)
    close.add_argument("closed")
    close.set_defaults(handler=fault_close)
    faults = fault.add_parser("list")
    faults.add_argument("--open", action="store_true")
    faults.set_defaults(handler=fault_list)


def add_the_rest(commands: argparse._SubParsersAction) -> None:
    """The telemetry, kpi and clauses subcommands: "kpi OAHE <start> <end>" parses to kpi with meter_kwh None."""
    telemetry = commands.add_parser("telemetry").add_subparsers(required=True)
    generate = telemetry.add_parser("generate")
    generate.add_argument("site")
    generate.add_argument("day")
    generate.add_argument("--seed", type=int, required=True)
    generate.set_defaults(handler=telemetry_generate)
    kpis = commands.add_parser("kpi")
    kpis.add_argument("site")
    kpis.add_argument("start")
    kpis.add_argument("end")
    kpis.add_argument("--meter-kwh", type=float)
    kpis.set_defaults(handler=kpi)
    commands.add_parser("clauses").set_defaults(handler=None)


def add_tests(commands: argparse._SubParsersAction) -> None:
    """The test subcommands, the remote tests' own, and help: "test run --db f.db" parses to test_run with db "f.db"
    (the --db after the subcommand, for the one-word launcher, which passes its arguments as typed); list, add and help
    open no store."""
    test = commands.add_parser("test").add_subparsers(required=True)
    test.add_parser("list").set_defaults(plain=test_list)
    add = test.add_parser("add")
    add.add_argument("name")
    add.add_argument("--kind", action="append", default=[])
    add.add_argument("--clause", action="append", required=True)
    add.set_defaults(plain=test_add)
    run = test.add_parser("run")
    run.add_argument("--at")
    run.add_argument("--db", default=argparse.SUPPRESS)
    run.set_defaults(handler=test_run)
    commands.add_parser("help").set_defaults(plain=show_help)


def build_parser() -> argparse.ArgumentParser:
    """The whole parser: build_parser().parse_args(["fleet", "list"]).db is "solarpunk.db"."""
    parser = argparse.ArgumentParser(prog="python3 -m solarpunk.cli", description=DESCRIPTION)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.set_defaults(plain=None)
    commands = parser.add_subparsers(required=True)
    add_fleet_and_faults(commands)
    add_the_rest(commands)
    add_tests(commands)
    return parser


def dispatch(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    """Runs the parsed subcommand: clauses, help, test list and test add without a store, the rest over the store at --db,
    which closes after; a handler that returns exits 0."""
    if args.plain is not None:
        args.plain(args, out)
        return 0
    if args.handler is None:
        return run_clauses(out, err)
    with closing(project.open_or_create(args.db)) as conn:
        args.handler(conn, args, out)
    return 0


def main(argv: list[str], out: TextIO, err: TextIO) -> int:
    """Parses argv and runs it, printing to out and err: main(["--db", "x.db", "fleet", "load", "--demo"], out, err) is
    0 with "loaded 11 assets"; a usage error is 2 with argparse's message on err, a refusal 2 with "error: ..."."""
    try:
        with redirect_stdout(out), redirect_stderr(err):
            args = build_parser().parse_args(argv)
    except SystemExit as stop:
        return int(stop.code or 0)
    try:
        return dispatch(args, out, err)
    except ValueError as refusal:
        err.write(f"error: {refusal}\n")
        return 2
