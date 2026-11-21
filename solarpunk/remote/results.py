"""The results table: one row per (test, asset, run instant) with pass, fail or no data and the reason (2.3, SP-039).
The module offers its schema; project applies it with solarpunk.leaf.store.apply, and upgrade gives a table made before
12.9 its no_data column, every row it held still a pass or a fail. It also reads two tables it does not own, samples and
assets, by name, so `python3 -m solarpunk.remote.run` can run one test against one asset's stored samples without
importing another lane's module (MOD-05)."""
import sqlite3
from dataclasses import dataclass
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
    " no_data INTEGER NOT NULL DEFAULT 0)",
)
NO_DATA_COLUMN = "no_data"
ADD_NO_DATA = "ALTER TABLE results ADD COLUMN no_data INTEGER NOT NULL DEFAULT 0"
INSERT = "INSERT INTO results (test_name, asset_id, run_at, passed, reason, no_data) VALUES (?, ?, ?, ?, ?, ?)"
RESULT_COLUMNS = "test_name, asset_id, run_at, passed, reason, no_data"
# Failures first, then no data, then passes (a no-data row stores passed 0), each by test name.
LATEST = (
    f"SELECT {RESULT_COLUMNS} FROM results"
    " WHERE asset_id = ? AND run_at = (SELECT max(run_at) FROM results WHERE asset_id = ?)"
    " ORDER BY passed, no_data, test_name"
)
LAST_RUN = "SELECT max(run_at) FROM results"
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
    result has no_data True and passed False, and a row stored before 12.9 reads as the pass or fail it was."""

    test_name: str
    asset_id: str
    run_at: datetime
    passed: bool
    reason: str
    no_data: bool = False

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


def schema() -> tuple[str, ...]:
    """The statements that make the results table: schema()[0] starts with "CREATE TABLE results"."""
    return SCHEMA


def upgrade(conn: sqlite3.Connection) -> None:
    """Gives a results table made before 12.9 its no_data column, every row it holds 0, so each reads as the pass or
    fail it was stored as (SP-039); a table that has it is left as it is."""
    if NO_DATA_COLUMN not in {row[1] for row in conn.execute("PRAGMA table_info(results)")}:
        conn.execute(ADD_NO_DATA)
        conn.commit()


def _recorded(row: sqlite3.Row | tuple) -> Recorded:
    """One results row as a Recorded."""
    return Recorded(row[0], row[1], datetime.fromisoformat(row[2]), bool(row[3]), row[4], bool(row[5]))


def record(conn: sqlite3.Connection, test_name: str, asset_id: str, run_at: datetime, result: Result) -> None:
    """Stores one result and commits: record(c, "reachable", "OAHE-INV-001", 10:00 UTC, Result(True, "3 records"))
    leaves the row ("reachable", "OAHE-INV-001", "2026-06-01T10:00:00+00:00", 1, "3 records", 0); no data stores
    passed 0 and no_data 1; a naive run_at raises NotUtc."""
    # Invariant: SOL-06 (UTC isoformat text of one shape sorts as its instants)
    conn.execute(INSERT, (test_name, asset_id, utc(run_at).isoformat(), int(result.passed), result.reason,
                          int(result.no_data)))
    conn.commit()


def latest_for(conn: sqlite3.Connection, asset_id: str) -> tuple[Recorded, ...]:
    """The asset's results from its most recent run, failing first, then no data, then passing, each by test name:
    after a run at 10:00 and one at 11:00 where on_grid failed, (on_grid failed, reachable passed) both at 11:00; an
    asset never run gives ()."""
    return tuple(_recorded(row) for row in conn.execute(LATEST, (asset_id, asset_id)).fetchall())


def results_of(conn: sqlite3.Connection, asset_id: str) -> tuple[Recorded, ...]:
    """Every result stored for the asset, newest run first, then in the order stored: after runs at 10:00 and 11:00,
    the 11:00 results come first; an asset never run gives (). Nothing is deleted to make it (SP-016)."""
    rows = conn.execute(f"SELECT {RESULT_COLUMNS} FROM results WHERE asset_id = ? ORDER BY run_at DESC, result_id",
                        (asset_id,)).fetchall()
    return tuple(_recorded(row) for row in rows)


def last_run_at(conn: sqlite3.Connection) -> datetime | None:
    """The instant of the most recent run over every asset, or None before any: 11:00 UTC after runs at 10:00 and
    11:00; last_run_at of an empty table is None."""
    latest = conn.execute(LAST_RUN).fetchone()[0]
    return None if latest is None else datetime.fromisoformat(latest)


def stored_samples(conn: sqlite3.Connection, asset_id: str) -> tuple[Sample, ...]:
    """One asset's samples from the samples table, in time order, as leaf Samples: a stored gap comes back as
    Sample(asset_id, at, None, None, True); an asset with no rows gives ()."""
    rows = conn.execute(SAMPLES, (asset_id,)).fetchall()
    return tuple(Sample(r[0], datetime.fromisoformat(r[1]), r[2], r[3], bool(r[4])) for r in rows)


def stored_asset(conn: sqlite3.Connection, asset_id: str) -> Asset:
    """One asset from the assets table as a leaf Asset: stored_asset(c, "OAHE-INV-001").kind is AssetKind.INVERTER
    (the table holds the kind's prefix, "INV"); an id the table lacks raises NotStored."""
    row = conn.execute(ASSET, (asset_id,)).fetchone()
    if row is None:
        raise NotStored(f"{asset_id} is not stored")
    return Asset(row[0], AssetKind(row[1]), row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9])
