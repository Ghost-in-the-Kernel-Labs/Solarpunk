"""The field-data commands (12.6, SP-036): `field load PATH` loads one public PV system's export from a local copy
outside the repository (docs/FIELD-DATA.md) into the store, and `field baseline --from DAY --to DAY` runs every remote
test that applies over each loaded asset one UTC day at a time and prints, per test and asset, the days run and the
days alarmed, then each alarmed day with the test's message. Each is one project call (MOD-02); main.py adds them to
its parser."""
import argparse
import sqlite3
from datetime import date
from typing import TextIO

from solarpunk import project
from solarpunk.cli.signin import acting


def field_load(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """field load PATH [--site SITE]: prints "loaded PV1: 5 assets, 24 samples, 8 gaps; skipped 1 off the grid,
    1 duplicate stamps" for test/fixtures/pvdaq/."""
    found = project.load_field(conn, args.path, args.site)
    out.write(f"loaded {found.site}: {found.assets} assets, {found.samples} samples, {found.gaps} gaps;"
              f" skipped {found.off_grid} off the grid, {found.duplicates} duplicate stamps\n")


def field_baseline(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """field baseline --from 2023-02-01 --to 2023-04-30: one line per test and asset, "on_grid  PV1-INV-001  days 89
    alarmed 3", then one per alarmed day, "alarm on_grid  PV1-INV-001  2023-02-01  <the test's message>"."""
    found = project.field_baseline(conn, date.fromisoformat(args.first), date.fromisoformat(args.last))
    for tally in found.tallies:
        out.write(f"{tally.test}  {tally.asset_id}  days {tally.days_run}  alarmed {tally.days_alarmed}\n")
    for alarm in found.alarms():
        out.write(f"alarm {alarm.test}  {alarm.asset_id}  {alarm.day.isoformat()}  {alarm.reason}\n")


def add_field(commands: argparse._SubParsersAction) -> None:
    """The field subcommands: "field load /data/9068 --db f.db" parses to field_load with path "/data/9068" and db
    "f.db" (the --db after the subcommand, as test run takes it)."""
    field = commands.add_parser("field").add_subparsers(required=True)
    load = acting(field.add_parser("load"))
    load.add_argument("path")
    load.add_argument("--site")
    load.add_argument("--db", default=argparse.SUPPRESS)
    load.set_defaults(handler=field_load)
    baseline = field.add_parser("baseline")
    baseline.add_argument("--from", dest="first", required=True)
    baseline.add_argument("--to", dest="last", required=True)
    baseline.add_argument("--db", default=argparse.SUPPRESS)
    baseline.set_defaults(handler=field_baseline)
