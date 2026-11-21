"""The samples table (SP-004): one row per sample, a gap a row whose values are NULL and whose gap is 1
(Invariant: SOL-06). The module offers its schema; project applies it with solarpunk.leaf.store.apply."""
import sqlite3
from datetime import datetime

from solarpunk.leaf.clock import Period
from solarpunk.leaf.telemetry import Sample

COLUMNS = "asset_id, at, irradiance_w_m2, power_kw, gap"


def schema() -> tuple[str, ...]:
    """The statements that make the samples table: schema()[0] starts with "CREATE TABLE samples"; the primary key is
    (asset_id, at), so a second sample for one asset at one instant is refused."""
    return (
        "CREATE TABLE samples ("
        " asset_id TEXT NOT NULL,"
        " at TEXT NOT NULL,"
        " irradiance_w_m2 REAL NULL,"
        " power_kw REAL NULL,"
        " gap INTEGER NOT NULL,"
        " PRIMARY KEY (asset_id, at))",
    )


def row(sample: Sample) -> tuple[str, str, float | None, float | None, int]:
    """A sample as its table row: row(gap("OAHE-INV-001", 10:20)) is
    ("OAHE-INV-001", "2026-06-01T10:20:00+00:00", None, None, 1)."""
    return (sample.asset_id, sample.moment.isoformat(), sample.irradiance_w_m2, sample.power_kw, int(sample.gap))


def store(connection: sqlite3.Connection, samples: tuple[Sample, ...]) -> None:
    """Inserts every sample, gaps included, and commits: store(c, generate(...)) leaves 288 rows for one inverter's
    day; a duplicate (asset_id, at) raises sqlite3.IntegrityError."""
    # Invariant: SOL-06 (a gap is stored, never dropped)
    rows = [row(sample) for sample in samples]
    connection.executemany(f"INSERT INTO samples ({COLUMNS}) VALUES (?, ?, ?, ?, ?)", rows)
    connection.commit()


def in_period(connection: sqlite3.Connection, asset_id: str, period: Period) -> tuple[Sample, ...]:
    """One asset's stored samples in the half-open period, in time order, as leaf Samples: for [10:00, 11:00) after
    storing a day, twelve samples from 10:00 to 10:55; a stored gap comes back as gap(asset_id, at)."""
    # Invariant: SOL-06 (the half-open period; UTC isoformat strings of one shape sort as their instants)
    found = connection.execute(
        f"SELECT {COLUMNS} FROM samples WHERE asset_id = ? AND at >= ? AND at < ? ORDER BY at",
        (asset_id, period.start.isoformat(), period.end.isoformat()),
    ).fetchall()
    return tuple(Sample(row[0], datetime.fromisoformat(row[1]), row[2], row[3], bool(row[4])) for row in found)


def asset_ids(connection: sqlite3.Connection) -> tuple[str, ...]:
    """The ids of every asset with a stored sample, gaps included, in id order: after storing OAHE-INV-002's and
    OAHE-INV-001's days, ("OAHE-INV-001", "OAHE-INV-002"); an empty table gives ()."""
    found = connection.execute("SELECT DISTINCT asset_id FROM samples ORDER BY asset_id").fetchall()
    return tuple(row[0] for row in found)
