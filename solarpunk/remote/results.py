"""The results table: one row per (test, asset, run instant) with pass, fail or no data and the reason (2.3, SP-039).
The module offers its schema; project applies it with solarpunk.leaf.store.apply, and upgrade gives a table made before
12.9 its no_data column, every row it held still a pass or a fail. It also reads two tables it does not own, samples and
assets, by name, so `python3 -m solarpunk.remote.run` can run one test against one asset's stored samples without
importing another lane's module (MOD-05)."""
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import utc
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample

# The SQL lives here, at module level, where mutmut does not reach (docs/MUTATION.md, J-008).
SCHEMA = (
    "CREATE TABLE results ("
    " result_id INTEGER PRIMARY KEY,"
    " test_name TEXT NOT NULL,"
    " asset_id TEXT NOT NULL,"
    " run_at TEXT NOT NULL,"
    " passed INTEGER NOT NULL,"
    " reason TEXT NOT NULL,"
    " no_data INTEGER NOT NULL DEFAULT 0,"
    " suite TEXT NOT NULL DEFAULT 'all',"
    " duration_ms INTEGER)",
)
ALL = "all"  # the default suite (SP-019): a result stored before 13.2, or by the run of every test, carries it
SUITE_COLUMN = "suite"
ADD_SUITE = "ALTER TABLE results ADD COLUMN suite TEXT NOT NULL DEFAULT 'all'"
NO_DATA_COLUMN = "no_data"
ADD_NO_DATA = "ALTER TABLE results ADD COLUMN no_data INTEGER NOT NULL DEFAULT 0"
DURATION_COLUMN = "duration_ms"
ADD_DURATION = "ALTER TABLE results ADD COLUMN duration_ms INTEGER"  # 13.5: NULL for a row stored before it
INSERT = (
    "INSERT INTO results (test_name, asset_id, run_at, passed, reason, no_data, suite, duration_ms)"
    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)
RESULT_COLUMNS = "test_name, asset_id, run_at, passed, reason, no_data, suite, duration_ms"
WITH_ID = RESULT_COLUMNS + ", result_id"  # 7.9: a result's id, which a ticket is opened from
# The result just before another of the same test on the same asset, in (run_at, result_id) order (7.9, SP-046).
PREVIOUS = (f"SELECT {WITH_ID} FROM results WHERE asset_id = ? AND test_name = ?"
            " AND (run_at < ? OR (run_at = ? AND result_id < ?)) ORDER BY run_at DESC, result_id DESC LIMIT 1")
# The first result of a test on an asset in one suite strictly after an instant (13.17): the next result read back.
NEXT_AFTER = (f"SELECT {WITH_ID} FROM results WHERE asset_id = ? AND test_name = ? AND suite = ? AND run_at > ?"
              " ORDER BY run_at, result_id LIMIT 1")
# The first passing result of a test on an asset in one suite strictly after an instant (13.21): the proof of a repair.
PASS_AFTER = (f"SELECT {WITH_ID} FROM results WHERE asset_id = ? AND test_name = ? AND suite = ? AND passed = 1"
              " AND run_at > ? ORDER BY run_at, result_id LIMIT 1")
BY_ID = f"SELECT {WITH_ID} FROM results WHERE result_id = ?"
LAST_OF_SUITE = "SELECT max(run_at) FROM results WHERE suite = ?"
# Failures first, then no data, then passes (a no-data row stores passed 0), each by test name, then in the order
# written, so of two results of one test at one instant the first written leads: the ping's `reachable` before the
# suite's (SP-055).
LATEST = (
    f"SELECT {WITH_ID} FROM results"
    " WHERE asset_id = ? AND run_at = (SELECT max(run_at) FROM results WHERE asset_id = ?)"
    " ORDER BY passed, no_data, test_name, result_id"
)
LAST_RUN = "SELECT max(run_at) FROM results"
# 13.5: per test over one suite, the counts; the assets it ran on; its newest result's instant and duration.
COUNTS = ("SELECT test_name, sum(passed), sum(passed = 0 AND no_data = 0), sum(no_data) FROM results"
          " WHERE suite = ? GROUP BY test_name")
RAN_ON = "SELECT DISTINCT test_name, asset_id FROM results WHERE suite = ? ORDER BY test_name, asset_id"
NEWEST = (f"SELECT {WITH_ID} FROM results AS r WHERE suite = ? AND result_id = (SELECT result_id FROM results"
          " WHERE suite = ? AND test_name = r.test_name ORDER BY run_at DESC, result_id DESC LIMIT 1)")
OF_TEST = f"SELECT {WITH_ID} FROM results WHERE test_name = ? ORDER BY run_at DESC, result_id DESC LIMIT ?"
NO_DATA = "no data"
NO_RECORDS = "no records"
SAMPLES = "SELECT asset_id, at, irradiance_w_m2, power_kw, gap FROM samples WHERE asset_id = ? ORDER BY at"
ASSET = (
    "SELECT asset_id, kind, site, parent_id, name, rated_kw, host, port, location, engineer_email"
    " FROM assets WHERE asset_id = ?"
)


class NotStored(LookupError):
    """Raised for an asset the assets table does not hold: NotStored("OAHE-INV-009 is not stored")."""


class NotAVerdict(ValueError):
    """Raised for a result that says both pass and no data: Result(True, "x", no_data=True)."""


@dataclass(frozen=True)
class Result:
    """One remote test's verdict on one asset, one of three (SP-039): a pass, Result(True, "3 records"); a failure,
    Result(False, "no records"); no data, Result(False, "no records", no_data=True), which is neither: never a pass,
    never a failure, shown grey."""

    passed: bool
    reason: str
    no_data: bool = False

    def __post_init__(self) -> None:
        """Refuses a result that says both pass and no data: Result(True, "x", no_data=True) raises NotAVerdict."""
        # Decision: SP-039 (no data is never a pass)
        if self.passed and self.no_data:
            raise NotAVerdict(f"a result cannot pass with no data: {self.reason}")

    @property
    def failed(self) -> bool:
        """Whether the result is a failure: Result(False, "x").failed is True; a pass or no data is not."""
        return not self.passed and not self.no_data


@dataclass(frozen=True)
class Recorded:
    """One stored result: Recorded("reachable", "OAHE-INV-001", 2026-06-01T10:00Z, False, "no records"); a no-data
    result has no_data True and passed False, and a row stored before 12.9 reads as the pass or fail it was; suite names
    the suite that ran it (13.2), "all" for a row stored before suites; result_id is the row's id (7.9), 0 for one not
    read from the store, and takes no part in equality; duration_ms is the milliseconds the test took (13.5), None for a
    row stored before it or one never timed, never 0, and takes no part in equality either."""

    test_name: str
    asset_id: str
    run_at: datetime
    passed: bool
    reason: str
    no_data: bool = False
    suite: str = ALL
    duration_ms: int | None = field(default=None, compare=False)
    result_id: int = field(default=0, compare=False)

    @property
    def failed(self) -> bool:
        """Whether the stored result is a failure: neither a pass nor no data."""
        return not self.passed and not self.no_data


def no_data(reason: str) -> Result:
    """The third result (SP-039): no_data("no records") is Result(False, "no records", no_data=True)."""
    return Result(False, reason, no_data=True)


def nothing_to_check(samples: tuple[Sample, ...]) -> str | None:
    """Why the samples hold nothing a test can check, or None when one is not a gap: () gives "no records", three gaps
    "no records: 3 gaps", a gap beside one record None. A record with no field set is still a record (SP-039: a day of
    real records with none of the kind a test needs is judged, not no data)."""
    if any(not sample.gap for sample in samples):
        return None
    return f"{NO_RECORDS}: {len(samples)} gaps" if samples else NO_RECORDS


@dataclass(frozen=True)
class Tally:
    """One test's stored record over one suite (13.5): Tally("reachable", ("OAHE-INV-001",), 2026-06-01T10:00Z, 12, 3, 1,
    0) is its assets, its newest result's instant and duration (None if untimed), then passes, failures, no data."""

    test_name: str
    assets: tuple[str, ...]
    last_run: datetime
    last_duration_ms: int | None
    passes: int
    failures: int
    no_data: int


def schema() -> tuple[str, ...]:
    """The statements that make the results table: schema()[0] starts with "CREATE TABLE results"."""
    return SCHEMA


def upgrade(conn: sqlite3.Connection) -> None:
    """Gives a results table made before 12.9 its no_data column, every row it holds 0, so each reads as the pass or
    fail it was stored as (SP-039), and one made before 13.2 its suite column, every row "all"; a table that has them is
    left as it is; one made before 13.5 its duration_ms column, every row NULL (never 0)."""
    held = {row[1] for row in conn.execute("PRAGMA table_info(results)")}
    if NO_DATA_COLUMN not in held:
        conn.execute(ADD_NO_DATA)
    if SUITE_COLUMN not in held:
        conn.execute(ADD_SUITE)
    if DURATION_COLUMN not in held:
        conn.execute(ADD_DURATION)
    conn.commit()


def _recorded(row: sqlite3.Row | tuple) -> Recorded:
    """One results row as a Recorded."""
    return Recorded(row[0], row[1], datetime.fromisoformat(row[2]), bool(row[3]), row[4], bool(row[5]), row[6], row[7], row[8])


def record(conn: sqlite3.Connection, test_name: str, asset_id: str, run_at: datetime, result: Result,
           suite: str = ALL, duration_ms: int | None = None) -> None:
    """Stores one result and commits: record(c, "reachable", "OAHE-INV-001", 10:00 UTC, Result(True, "3 records"))
    leaves the row ("reachable", "OAHE-INV-001", "2026-06-01T10:00:00+00:00", 1, "3 records", 0); no data stores
    passed 0 and no_data 1; a result carries the suite that ran it, "all" unless one is named (13.2); a naive run_at
    raises NotUtc; duration_ms is the test's milliseconds (13.5), None when it was not timed."""
    # Invariant: SOL-06 (UTC isoformat text of one shape sorts as its instants)
    conn.execute(INSERT, (test_name, asset_id, utc(run_at).isoformat(), int(result.passed), result.reason,
                          int(result.no_data), suite, duration_ms))
    conn.commit()


def last_run_of(conn: sqlite3.Connection, suite: str) -> datetime | None:
    """The instant of the suite's most recent stored result, or None before any: after the suite "hourly_check" ran at
    10:00 UTC, 10:00; a suite never run gives None."""
    latest = conn.execute(LAST_OF_SUITE, (suite,)).fetchone()[0]
    return None if latest is None else datetime.fromisoformat(latest)


def latest_for(conn: sqlite3.Connection, asset_id: str) -> tuple[Recorded, ...]:
    """The asset's results from its most recent run, failing first, then no data, then passing, each by test name:
    after a run at 10:00 and one at 11:00 where on_grid failed, (on_grid failed, reachable passed) both at 11:00; an
    asset never run gives ()."""
    return tuple(_recorded(row) for row in conn.execute(LATEST, (asset_id, asset_id)).fetchall())


def results_of(conn: sqlite3.Connection, asset_id: str) -> tuple[Recorded, ...]:
    """Every result stored for the asset, newest run first, then in the order stored: after runs at 10:00 and 11:00,
    the 11:00 results come first; an asset never run gives (). Nothing is deleted to make it (SP-016)."""
    rows = conn.execute(f"SELECT {WITH_ID} FROM results WHERE asset_id = ? ORDER BY run_at DESC, result_id",
                        (asset_id,)).fetchall()
    return tuple(_recorded(row) for row in rows)


def get(conn: sqlite3.Connection, result_id: int) -> Recorded | None:
    """One stored result by its id, or None: get(conn, 1) is the first result recorded."""
    row = conn.execute(BY_ID, (result_id,)).fetchone()
    return None if row is None else _recorded(row)


def previous_of(conn: sqlite3.Connection, found: Recorded) -> Recorded | None:
    """The result of the same test on the same asset just before this one, or None for the first (7.9, SP-046): no other
    result of that test on that asset lies between them, ordered by run instant and then by id; after a pass at 10:00
    and a failure at 11:00, the failure's previous is the pass."""
    row = conn.execute(PREVIOUS, (found.asset_id, found.test_name, utc(found.run_at).isoformat(),
                                  utc(found.run_at).isoformat(), found.result_id)).fetchone()
    return None if row is None else _recorded(row)


def next_after(conn: sqlite3.Connection, found: Recorded, suite: str = ALL) -> Recorded | None:
    """The first stored result of the same test on the same asset in the suite, strictly after this one's run instant,
    or None: after a failure at 11:00 and a pass at 12:00, the failure's next is the pass; the newest result has none."""
    row = conn.execute(NEXT_AFTER, (found.asset_id, found.test_name, suite, utc(found.run_at).isoformat())).fetchone()
    return None if row is None else _recorded(row)


def pass_after(conn: sqlite3.Connection, found: Recorded, suite: str = ALL) -> Recorded | None:
    """The first passing result of the same test on the same asset in the suite, strictly after this one's run instant,
    or None: after a failure at 13:00 and a pass at 13:25 it is the 13:25 pass; with only a failure after it, None."""
    row = conn.execute(PASS_AFTER, (found.asset_id, found.test_name, suite, utc(found.run_at).isoformat())).fetchone()
    return None if row is None else _recorded(row)


def last_run_at(conn: sqlite3.Connection) -> datetime | None:
    """The instant of the most recent run over every asset, or None before any: 11:00 UTC after runs at 10:00 and
    11:00; last_run_at of an empty table is None."""
    latest = conn.execute(LAST_RUN).fetchone()[0]
    return None if latest is None else datetime.fromisoformat(latest)


def stored_samples(conn: sqlite3.Connection, asset_id: str) -> tuple[Sample, ...]:
    """One asset's samples from the samples table, in time order, as leaf Samples: a stored gap comes back as
    Sample(asset_id, moment, None, None, True); an asset with no rows gives ()."""
    rows = conn.execute(SAMPLES, (asset_id,)).fetchall()
    return tuple(Sample(row[0], datetime.fromisoformat(row[1]), row[2], row[3], bool(row[4])) for row in rows)


def stored_asset(conn: sqlite3.Connection, asset_id: str) -> Asset:
    """One asset from the assets table as a leaf Asset: stored_asset(c, "OAHE-INV-001").kind is AssetKind.INVERTER
    (the table holds the kind's prefix, "INV"); an id the table lacks raises NotStored."""
    row = conn.execute(ASSET, (asset_id,)).fetchone()
    if row is None:
        raise NotStored(f"{asset_id} is not stored")
    return Asset(row[0], AssetKind(row[1]), row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9])


def tally(conn: sqlite3.Connection, suite: str = ALL) -> tuple[Tally, ...]:
    """Each test's record over one suite, in test name order (13.5): after three results of reachable on OAHE-INV-001, two
    passes and a failure, the last at 11:00 taking 12 ms, Tally("reachable", ("OAHE-INV-001",), 11:00, 12, 2, 1, 0); a
    test with no result in the suite is absent. Nothing is deleted to make it (SP-016)."""
    ran_on: dict[str, list[str]] = {}
    for name, asset_id in conn.execute(RAN_ON, (suite,)):
        ran_on.setdefault(name, []).append(asset_id)
    newest = {row[0]: _recorded(row) for row in conn.execute(NEWEST, (suite, suite))}
    return tuple(Tally(name, tuple(ran_on[name]), newest[name].run_at, newest[name].duration_ms, passes, failures, empty)
                 for name, passes, failures, empty in conn.execute(COUNTS, (suite,)).fetchall())


def of_test(conn: sqlite3.Connection, test_name: str, limit: int) -> tuple[Recorded, ...]:
    """The test's newest results over every asset and suite, newest first and then newest stored first, at most limit:
    after 120 stored results, limit 100 gives the newest 100; a test never run, or a limit below 1, gives ()."""
    return tuple(_recorded(row) for row in conn.execute(OF_TEST, (test_name, max(limit, 0))).fetchall())
