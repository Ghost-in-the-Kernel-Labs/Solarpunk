"""The remote tests' record (13.5, SP-016): two reads of the results the store holds, one call per view, recomputed when
asked and never kept apart from them. tests_overview is the Tests window's table: each test with its kinds, the assets
it ran on, its last run and duration, its passes, failures and no data; test_log is one test's newest runs across the
fleet. An asset's own runs are asset_runs (10.2, SP-024). Nothing is deleted to show either (SP-016)."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from solarpunk.leaf.codes import AssetKind
from solarpunk.project.runs import SHOWN, verdict_of
from solarpunk.remote import results as result_table
from solarpunk.remote.registry import discover


@dataclass(frozen=True)
class TestRecord:
    """One test's row in the overview (13.5): TestRecord("reachable", (INVERTER, ...), ("OAHE-INV-001", ...), 11:00 UTC,
    12, 40, 3, 1, ("55000-9.1",)); a test never run has no assets, last_run None, last_duration_ms None and counts of 0, and a duration
    never timed is None, never 0."""

    __test__ = False  # not a unittest case, though it begins "Test"

    name: str
    kinds: tuple[AssetKind, ...]
    assets: tuple[str, ...]
    last_run: datetime | None
    last_duration_ms: int | None
    passes: int
    failures: int
    no_data: int
    clauses: tuple[str, ...] = ()  # 13.17: the register clauses the test evidences, from the registry


@dataclass(frozen=True)
class LoggedRun:
    """One stored run of a test on one asset (13.5): LoggedRun("reachable", "OAHE-INV-002", 13:00 UTC, "fail",
    "127.0.0.1:9 is unreachable", "all", 3, 17); verdict is "pass", "fail" or "no data" (SP-039), duration_ms None when
    untimed."""

    test_name: str
    asset_id: str
    run_at: datetime
    verdict: str
    reason: str
    suite: str
    duration_ms: int | None
    result_id: int


def tests_overview(conn: sqlite3.Connection) -> tuple[TestRecord, ...]:
    """Every test with its record, in name order (13.5): the discovered tests and any a stored result names whose module
    is gone (kinds ()); a test never run reads 0 and None. It counts only the default suite "all", the run of every test,
    so a named suite's extra runs do not double what a test did (HANDOFF For Ghost 18); no data is a third count, neither
    a pass nor a failure (SP-039). An empty store gives the discovered tests, all unrun."""
    # Decision: SP-016 (the tests' record is shown at the root, and kept whole)
    found = discover()
    tallies = {tally.test_name: tally for tally in result_table.tally(conn)}
    return tuple(
        TestRecord(name, found[name].kinds if name in found else (), *_counted(tallies.get(name)),
                   found[name].clauses if name in found else ())
        for name in sorted(set(found) | set(tallies)))


def _counted(tally: result_table.Tally | None) -> tuple:
    """A tally as the fields of a TestRecord after its kinds; None, a test never run, as its empty reading."""
    if tally is None:
        return (), None, None, 0, 0, 0
    return tally.assets, tally.last_run, tally.last_duration_ms, tally.passes, tally.failures, tally.no_data


def test_log(conn: sqlite3.Connection, name: str, limit: int = SHOWN) -> tuple[LoggedRun, ...]:
    """The test's newest runs over every asset and suite, newest first, at most limit (13.5): after 120 stored results of
    reachable, limit 100 gives the newest 100 and the other 20 stay stored; a test never run, or a name no module
    provides, gives ()."""
    return tuple(LoggedRun(found.test_name, found.asset_id, found.run_at, verdict_of(found), found.reason, found.suite,
                           found.duration_ms, found.result_id)
                 for found in result_table.of_test(conn, name, limit))
