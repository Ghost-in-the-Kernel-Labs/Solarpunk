"""The remote-test commands (13.13, SP-049): `test list`, `test add`, `test results` and `test run [--at INSTANT] [--db
PATH] [--acquire [--shorten N]]`, each one project call (MOD-02); main.py adds them to its parser."""
import argparse
import sqlite3
from datetime import datetime, timezone
from typing import TextIO

from solarpunk import project


def rules_text(test: project.RemoteTest) -> str:
    """A test's reactions in words (13.4, SP-020), each kind its own: reachable's begins "INV: Fault(SIT-004); MTR:
    Fault(MTR-001)", a kind that names none reacting with the generic fault alone."""
    return "; ".join(f"{kind.value}: {', '.join(project.reaction_text(item) for item in test.reactions_for(kind))}"
                     for kind in test.kinds)


def test_list(args: argparse.Namespace, out: TextIO) -> None:
    """test list: one line per remote test with its kinds, clauses and reactions,
    "reachable  INV,MTR,SEN,TRK  55000-9.1  INV: Fault(SIT-004); MTR: Fault(MTR-001); ..."."""
    for test in project.remote_tests():
        kinds = ",".join(kind.value for kind in test.kinds)
        out.write(f"{test.name}  {kinds}  {','.join(test.clauses)}  {rules_text(test)}\n")


def test_results(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """test results --asset ID [--failed]: one line per stored result, newest first, "17  2026-06-01T13:00:00+00:00
    reachable  fail  127.0.0.1:9 is unreachable": id, instant, test, verdict, reason; --failed keeps the failures."""
    for found, verdict in project.asset_results(conn, args.asset, args.failed):
        out.write(f"{found.result_id}  {found.run_at.isoformat()}  {found.test_name}  {verdict}  {found.reason}\n")


def test_add(args: argparse.Namespace, out: TextIO) -> None:
    """test add tracker_moving --clause 55000-9.1 [--kind TRACKER]: scaffolds the test's module and prints
    "wrote <its path>", then a line saying it fails until its run is written."""
    path = project.add_remote_test(args.name, tuple(args.kind), tuple(args.clause))
    out.write(f"wrote {path}\n{args.name} fails on every run until its run function is written\n")


def test_run(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """test run [--at INSTANT] [--db PATH] [--acquire [--shorten N]]: the scheduled run once, now or at the instant
    given, over every asset of the store: "run 2026-06-01T13:00:00+00:00: pinged 3, records 24, results 6", then
    "OAHE-INV-001  green" for each asset and "error OAHE-INV-002: 127.0.0.1:9 is unreachable" for each feed that did not
    answer. A burst test takes its reads only with --acquire, on the real clock (a minute's burst takes a minute),
    --shorten N cutting each burst to N reads (SP-049); without it the burst test records no data."""
    run_at = datetime.now(timezone.utc).replace(microsecond=0) if args.at is None else datetime.fromisoformat(args.at)
    acquirer = project.live_acquirer(args.shorten) if args.acquire else None
    report = project.scheduled_run(conn, run_at, acquirer=acquirer)
    out.write(f"run {run_at.isoformat()}: pinged {report.pinged}, records {report.records},"
              f" results {report.results}\n")
    for asset_id, status in sorted(report.statuses.items()):
        out.write(f"{asset_id}  {status.value}\n")
    for error in report.errors:
        out.write(f"error {error}\n")


def add_tests(commands: argparse._SubParsersAction) -> None:
    """The test subcommands: "test run --db f.db" parses to test_run with db "f.db" (the --db after the
    subcommand, for the one-word launcher); list and add open no store."""
    test = commands.add_parser("test").add_subparsers(required=True)
    test.add_parser("list").set_defaults(plain=test_list)
    add = test.add_parser("add")
    add.add_argument("name")
    add.add_argument("--kind", action="append", default=[])
    add.add_argument("--clause", action="append", required=True)
    add.set_defaults(plain=test_add)
    results = test.add_parser("results")
    results.add_argument("--asset", required=True)
    results.add_argument("--failed", action="store_true")
    results.add_argument("--db", default=argparse.SUPPRESS)
    results.set_defaults(handler=test_results)
    run = test.add_parser("run")
    run.add_argument("--at")
    run.add_argument("--acquire", action="store_true")
    run.add_argument("--shorten", type=int)
    run.add_argument("--db", default=argparse.SUPPRESS)
    run.set_defaults(handler=test_run)
