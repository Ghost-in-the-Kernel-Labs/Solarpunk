"""The test suites over the store (13.2, SP-019): the suites the registry finds, each run when its cadence is due in the
scheduled run, or now by name, and one written by `suite add`. The default suite `all` is run by the scheduled run's own
suite pass; the named suites here run beside it and store their results carrying their name."""
import sqlite3
from datetime import datetime
from pathlib import Path

from solarpunk.leaf.assets import Asset
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote import results as result_table
from solarpunk.remote import run as remote
from solarpunk.remote import suite_registry, suite_writer
from solarpunk.remote.results import ALL
from solarpunk.remote.suite_registry import Suite


def test_suites() -> tuple[Suite, ...]:
    """Every suite the registry finds, `all` first: with no file in the suites folder, (the default,)."""
    return tuple(suite_registry.discover_suites().values())


def add_suite(name: str, tests: tuple[str, ...], kind_names: tuple[str, ...], cadence: str,
              folder: Path | None = None) -> Path:
    """Writes a new suite beside the others (or in the folder given) and returns its file: add_suite("hourly_check",
    ("records_stored",), ("INVERTER",), "hourly") is solarpunk/remote/suites/hourly_check.py; a refusal raises BadRemoteTest."""
    return suite_writer.write(name, tests, kind_names, cadence, folder)


def run_due_suites(conn: sqlite3.Connection, fed: tuple[Asset, ...], samples: dict[str, tuple[Sample, ...]],
                   run_at: datetime) -> int:
    """Runs each named suite whose cadence is due at run_at, over the assets given, and returns the results written:
    with only the default suite, 0 (the default is the scheduled run's own); an hourly suite last run an hour ago is run
    and one run ten minutes ago is not."""
    written = 0
    for suite in test_suites():
        if suite.name != ALL and suite_registry.due(suite, result_table.last_run_of(conn, suite.name), run_at):
            written += remote.run_named(conn, suite, fed, samples, run_at)
    return written
