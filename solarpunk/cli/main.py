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
from solarpunk.cli import signin
from solarpunk.cli.accounts import add_accounts
from solarpunk.cli.field import add_field
from solarpunk.cli.signin import acting, attributed
from solarpunk.cli.suites import add_suites
from solarpunk.cli.tickets import add_tickets

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
  solarpunk --shortcut                         put a Solarpunk shortcut, with its icon, on the desktop
  solarpunk --help                             this list

The remote tests
  test list                                    each remote test, its kinds, clauses and the fault it suggests
  test run [--db PATH] [--at INSTANT]          run every remote test over every asset of the store, once
  test add NAME --clause ID [--kind KIND]      scaffold a new remote test; it fails until its run is written
  suite list                                   each suite with its tests and cadence
  suite run NAME [--db PATH]                   run one suite now
  suite add NAME --test T [--kind K] [--cadence C]  write a suite: every run, hourly, or daily at HH

The fleet and its faults
  fleet load --demo                            register the OAHE example fleet
  fleet list [--site SITE]                     each asset with its kind, name and status
  fault assign ID CODE OPENED [--for ENGINEER] open a fault as the engineer signed in, or on their word
  fault close FAULT_ID CLOSED                  close a fault
  fault list [--open]                          the faults, or the open ones alone
  fault suggestions [--asset ID]               the faults the tests and the devices suggest, waiting
  fault accept ID [--for ENGINEER]             accept a suggestion into a fault, as fault assign does
  fault dismiss ID --reason WHY                dismiss a suggestion, saying why [--for ENGINEER]

The tickets (each takes --at INSTANT, now by default)
  ticket list                                  the open tickets, the nearest target first, a breach marked
  ticket show ID                               a ticket's line and its moves, any status, within your sites
  ticket ack ID                                acknowledge a ticket
  ticket comment ID WORDS                      add a comment, kept as written, by the account signed in
  ticket resolve ID --cause CODE --done WORDS  resolve and close a ticket and its fault with a root cause

The accounts (a password is asked twice, never shown)
  account init                                 make the first admin, on this machine, once: asks name, email, password
  account add EMAIL --name NAME --role ROLE    an admin adds an account [--site SITE ...], all sites for an admin
  account reset EMAIL                          an admin gives an account a new password
  account deactivate EMAIL                     an admin stops an account; its records keep its name
  account list                                 every account: email, name, role, active, sites, created

The numbers
  telemetry generate SITE DAY --seed N         store a day of synthetic telemetry
  kpi SITE START END [--meter-kwh X]           availability, performance ratio, energy yield, MTBF and MTTR
  report SITE START END [--csv]                power output: energy, peak, specific yield, capacity factor
  clauses                                      each ISO 9001 and ISO 55000 clause and the test that holds it
  help                                         this list

Public field data (docs/FIELD-DATA.md; the data stays outside the repository)
  field load PATH [--site SITE]                load one PVDAQ system's export from a local folder
  field baseline --from DAY --to DAY           each remote test over each loaded asset a day at a time: days alarmed

Every command but test run reads solarpunk.db in this folder; for another store,
python -m solarpunk.cli --db PATH <command>. In a store with accounts, a command that acts
(load, assign, close, accept, dismiss, generate, ack, comment, resolve, account add, reset,
deactivate, field load) takes --as EMAIL and asks for its password, and acts as that account: an engineer as
themself, an operator on an engineer's word with --for ENGINEER. test run acts as no person and asks
nothing. A store with no accounts names who acts with --by (an operator's entry: --recorded-by).
"""


def instant(text: str) -> datetime:
    """An ISO instant as written; the leaf refuses a naive one when it is used: instant("2026-06-01T10:00:00+00:00")
    is 10:00 UTC; instant("soon") raises ValueError."""
    return datetime.fromisoformat(text)


def fault_line(fault: project.Fault, cover: bool = False) -> str:
    """One fault as a line, who assigned it last (SP-015): Fault(1, "OAHE-INV-001", "INV-001", 10:10 UTC, None,
    "tech@oahe.example") is "1 OAHE-INV-001 INV-001 2026-06-01T10:10:00+00:00 open by tech@oahe.example"; entered by an
    operator it adds " entered by <operator>", and with cover " (cover)"."""
    closed = "open" if fault.closed is None else fault.closed.isoformat()
    entered = "" if fault.recorded_by is None else f" entered by {fault.recorded_by}"
    covering = " (cover)" if cover else ""
    return (f"{fault.fault_id} {fault.asset_id} {fault.code} {fault.opened.isoformat()} {closed}"
            f" by {fault.assigned_by}{entered}{covering}")


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
    """fault assign OAHE-INV-001 INV-001 2026-06-01T10:10:00+00:00 --as inverter@oahe.example prints "1 OAHE-INV-001
    INV-001 2026-06-01T10:10:00+00:00 open by inverter@oahe.example" (SP-015); an operator adds --for ENGINEER (12.4);
    a store with no accounts takes --by ENGINEER [--recorded-by OPERATOR] instead."""
    fault = project.assign_fault_as(conn, args.account, args.asset_id, args.code, instant(args.opened), args.by,
                                    args.recorded_by, args.for_engineer)
    out.write(fault_line(fault, project.is_cover(conn, fault)) + "\n")


def fault_close(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """fault close 1 2026-06-01T10:30:00+00:00 prints the fault with its close,
    "1 OAHE-INV-001 INV-001 2026-06-01T10:10:00+00:00 2026-06-01T10:30:00+00:00"."""
    fault = project.close_fault(conn, args.fault_id, instant(args.closed))
    out.write(fault_line(fault, project.is_cover(conn, fault)) + "\n")


def fault_list(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """fault list [--open]: one fault_line per fault in fault_id order, the open ones alone with --open."""
    for fault in project.faults_listing(conn, args.open):
        out.write(fault_line(fault, project.is_cover(conn, fault)) + "\n")


def suggestion_line(found: project.Suggestion) -> str:
    """One suggestion as a line (SP-015): "1 OAHE-SEN-001 SEN-001 from reachable at 2026-06-01T13:00:00+00:00:
    127.0.0.1:9 is unreachable"; a pushed one reads "from device"."""
    return (f"{found.suggestion_id} {found.asset_id} {found.code} from {found.source} at {found.raised_at.isoformat()}:"
            f" {found.reason}")


def fault_suggestions(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """fault suggestions [--asset ID]: one suggestion_line per open suggestion, of one asset (a device's first) or all."""
    for found in project.open_suggestions(conn, args.asset):
        out.write(suggestion_line(found) + "\n")


def fault_accept(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """fault accept 1 --as site@oahe.example [--for ENGINEER]: opens the suggested fault as the engineer and prints its
    fault_line, "1 OAHE-SEN-001 SEN-001 2026-06-01T13:00:00+00:00 open by site@oahe.example" (12.4); with no accounts,
    --by ENGINEER [--recorded-by OPERATOR]."""
    fault = project.accept_suggestion_as(conn, args.account, args.suggestion_id, args.by, args.recorded_by,
                                         args.for_engineer)
    out.write(fault_line(fault, project.is_cover(conn, fault)) + "\n")


def fault_dismiss(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """fault dismiss 1 --as site@oahe.example --reason "fibre repaired" prints "dismissed 1 by site@oahe.example:
    fibre repaired" (12.4: an operator adds --for ENGINEER; with no accounts, --by ENGINEER); entered by an operator it
    reads "by site@oahe.example entered by ops@oahe.example: …", as a fault's line does (SP-039)."""
    found = project.dismiss_suggestion_as(conn, args.account, args.suggestion_id, args.reason, args.by,
                                          args.for_engineer)
    entered = "" if found.recorded_by is None else f" entered by {found.recorded_by}"
    out.write(f"dismissed {found.suggestion_id} by {found.decided_by}{entered}: {found.dismissal}\n")


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



def write_report(found: project.PowerReport, as_csv: bool, out: TextIO) -> None:
    """One line per row: the contract's example site starts "output OAHE-SIT-001 rated_kw=150.0 energy_kwh=22.25
    peak_kw=135.0 specific_yield=0.1483 capacity_factor=0.5933 records=5 gaps=1"; with as_csv, project.report_csv."""
    if as_csv:
        out.write(project.report_csv(found))
        return
    for row in project.report_rows(found):
        parts = " ".join(f"{field}={getattr(row, field)}" for field in project.OUTPUT_FIELDS[1:])
        out.write(f"output {row.asset_id} {parts}\n")

def report(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """report OAHE 2026-06-01T00:00:00+00:00 2026-06-02T00:00:00+00:00 [--csv] prints write_report's lines."""
    span = project.period(instant(args.start), instant(args.end))
    write_report(project.power_report(conn, args.site, span), args.csv, out)


def show_help(args: argparse.Namespace, out: TextIO) -> None:
    """help: prints the help list, HELP, whose first line is "Solarpunk: the commands. ..."."""
    out.write(HELP)


def rules_text(test: project.RemoteTest) -> str:
    """A test's rule table in words (SP-015): reachable's is "suggests INV:INV-001,MTR:MTR-001,SEN:SEN-001", a kind with
    no code left out; a test that suggests nothing reads "suggests nothing"."""
    pairs = [f"{kind.value}:{code}" for kind, code in test.suggests.items() if code is not None]
    return "suggests " + (",".join(pairs) if pairs else "nothing")


def test_list(args: argparse.Namespace, out: TextIO) -> None:
    """test list: one line per remote test with its kinds, clauses and rule table,
    "reachable  INV,MTR,SEN,TRK  55000-9.1  suggests INV:INV-001,MTR:MTR-001,SEN:SEN-001"."""
    for test in project.remote_tests():
        kinds = ",".join(kind.value for kind in test.kinds)
        out.write(f"{test.name}  {kinds}  {','.join(test.clauses)}  {rules_text(test)}\n")


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
    load = acting(fleet.add_parser("load"))
    load.add_argument("--demo", action="store_true", required=True)
    load.set_defaults(handler=fleet_load)
    listing = fleet.add_parser("list")
    listing.add_argument("--site")
    listing.set_defaults(handler=fleet_list)
    fault = commands.add_parser("fault").add_subparsers(required=True)
    assign = acting(fault.add_parser("assign"))
    assign.add_argument("asset_id")
    assign.add_argument("code")
    assign.add_argument("opened")
    attributed(assign)
    assign.set_defaults(handler=fault_assign)
    close = acting(fault.add_parser("close"))
    close.add_argument("fault_id", type=int)
    close.add_argument("closed")
    close.set_defaults(handler=fault_close)
    faults = fault.add_parser("list")
    faults.add_argument("--open", action="store_true")
    faults.set_defaults(handler=fault_list)
    add_suggestion_commands(fault)


def add_suggestion_commands(fault: argparse._SubParsersAction) -> None:
    """The suggestion subcommands of fault (7.5): "fault accept 1 --by x@y" parses to fault_accept with suggestion_id 1."""
    suggested = fault.add_parser("suggestions")
    suggested.add_argument("--asset")
    suggested.set_defaults(handler=fault_suggestions)
    accept = acting(fault.add_parser("accept"))
    accept.add_argument("suggestion_id", type=int)
    attributed(accept)
    accept.set_defaults(handler=fault_accept)
    dismiss = acting(fault.add_parser("dismiss"))
    dismiss.add_argument("suggestion_id", type=int)
    attributed(dismiss, operator=False)
    dismiss.add_argument("--reason", required=True)
    dismiss.set_defaults(handler=fault_dismiss)


def add_the_rest(commands: argparse._SubParsersAction) -> None:
    """The telemetry, kpi, report and clauses subcommands: "kpi OAHE <start> <end>" parses to kpi with meter_kwh None."""
    telemetry = commands.add_parser("telemetry").add_subparsers(required=True)
    generate = acting(telemetry.add_parser("generate"))
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
    reports = commands.add_parser("report")
    reports.add_argument("site")
    reports.add_argument("start")
    reports.add_argument("end")
    reports.add_argument("--csv", action="store_true")
    reports.set_defaults(handler=report)
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
    add_suites(commands)  # 13.2
    add_tickets(commands)  # 11.2
    add_accounts(commands)  # 12.5
    add_field(commands)  # 12.6
    return parser


def dispatch(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    """Runs the parsed subcommand: clauses, help, test list and test add without a store, the rest over the store at --db,
    which closes after, a command that acts signed in first (12.3); a handler that returns exits 0."""
    if args.plain is not None:
        args.plain(args, out)
        return 0
    if args.handler is None:
        return run_clauses(out, err)
    with closing(project.open_or_create(args.db)) as conn:
        if signin.acts(args):
            args.account = signin.signed_in(conn, getattr(args, signin.DEST))  # 12.3; 12.4 acts as it
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
