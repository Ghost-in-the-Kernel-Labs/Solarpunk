"""The suite commands (13.2, SP-019): `suite list` (each suite with its tests and cadence), `suite run NAME [--at
INSTANT] [--db PATH]` (one suite now) and `suite add NAME --test T [--kind K] [--cadence C]` (writes one), each one
project call (MOD-02). main.py adds them to its parser."""
import argparse
import sqlite3
from datetime import datetime, timezone
from typing import TextIO

from solarpunk import project

LINE = "{name}  {tests}  {cadence}"
DEFAULT_CADENCE = "every run"


def suite_list(args: argparse.Namespace, out: TextIO) -> None:
    """suite list: one line per suite, its tests and its cadence: with no suite of its own, "all  <every test, commas>
    every run"; a suite of records_stored, hourly, is "hourly_check  records_stored  hourly"."""
    for suite in project.test_suites():
        out.write(LINE.format(name=suite.name, tests=",".join(suite.tests), cadence=suite.cadence) + "\n")


def suite_run(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """suite run NAME [--at INSTANT] [--db PATH]: the suite now, or at the instant given, over every asset with an
    endpoint: "suite all 2026-06-01T13:00:00+00:00: results 6"; an unknown name is "error: no suite x", exit 2."""
    run_at = datetime.now(timezone.utc).replace(microsecond=0) if args.at is None else datetime.fromisoformat(args.at)
    suite, written = project.run_suite_now(conn, args.name, run_at)
    out.write(f"suite {suite.name} {run_at.isoformat()}: results {written}\n")


def suite_add(args: argparse.Namespace, out: TextIO) -> None:
    """suite add hourly_check --test records_stored [--kind INVERTER] [--cadence hourly]: writes the suite's module and prints
    "wrote <its path>"; an unknown test, kind or cadence, or a name taken, is "error: ...", exit 2."""
    path = project.add_suite(args.name, tuple(args.test), tuple(args.kind), args.cadence)
    out.write(f"wrote {path}\n")


def add_suites(commands: argparse._SubParsersAction) -> None:
    """The suite subcommands: "suite run hourly_check --db f.db" parses to suite_run with db "f.db" (after the subcommand,
    as test run takes it); list and add open no store."""
    suite = commands.add_parser("suite").add_subparsers(required=True)
    suite.add_parser("list").set_defaults(plain=suite_list)
    add = suite.add_parser("add")
    add.add_argument("name")
    add.add_argument("--test", action="append", required=True)
    add.add_argument("--kind", action="append", default=[])
    add.add_argument("--cadence", default=DEFAULT_CADENCE)
    add.set_defaults(plain=suite_add)
    run = suite.add_parser("run")
    run.add_argument("name")
    run.add_argument("--at")
    run.add_argument("--db", default=argparse.SUPPRESS)
    run.set_defaults(handler=suite_run)
