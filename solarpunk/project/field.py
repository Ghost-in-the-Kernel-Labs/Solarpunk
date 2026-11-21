"""Field data (12.6, SP-036): load one public PV system's export from a local copy outside the repository into the
store (its assets registered as the fleet registers them, no feed port; its samples in the samples table), and the
false-alarm baseline: every registered remote test that applies to an asset's kind run over each day of its stored
samples, one UTC day at a time, the results returned and nothing written to the run record (the results table). The
scheduled run (run.py) is not touched: it still tests only assets with a feed port."""
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from solarpunk.fleet import registry
from solarpunk.project.orchestrator import day_period
from solarpunk.remote.registry import discover
from solarpunk.telemetry import field as field_data
from solarpunk.telemetry import samples as sample_table


@dataclass(frozen=True)
class Loaded:
    """What one load stored: Loaded("PV1", 5, 24, 8, 1, 1) is site PV1, five assets (the site, two stations, two
    inverters), 24 samples of which 8 are gaps, one row off the grid and one duplicate stamp skipped."""

    site: str
    assets: int
    samples: int
    gaps: int
    off_grid: int
    duplicates: int


@dataclass(frozen=True)
class DayResult:
    """One test on one asset over one UTC day: DayResult("power_under_rated", "PV1-INV-001", 2023-02-01, False,
    "2023-02-01T18:05:00+00:00: power 1020.0 kW over rated 1000.0 kW")."""

    test: str
    asset_id: str
    day: date
    passed: bool
    reason: str
    no_data: bool = False

    @property
    def failed(self) -> bool:
        """Whether the day alarmed: neither a pass nor no data (SP-039)."""
        return not self.passed and not self.no_data


@dataclass(frozen=True)
class Tally:
    """One test on one asset over the baseline: Tally("on_grid", "PV1-INV-001", 89, 3) ran 89 days, alarmed on 3."""

    test: str
    asset_id: str
    days_run: int
    days_alarmed: int


@dataclass(frozen=True)
class Baseline:
    """The baseline: each (test, asset) tally in test then asset order, then every day result, failing or not."""

    tallies: tuple[Tally, ...]
    results: tuple[DayResult, ...]

    def alarms(self) -> tuple[DayResult, ...]:
        """The results that failed, in test, asset, day order; a day of no data is no alarm (SP-039)."""
        return tuple(result for result in self.results if result.failed)


def load_field(conn: sqlite3.Connection, folder: str | Path, site: str | None = None) -> Loaded:
    """Reads the system's export in the folder, registers its assets (the site first) and stores every asset's samples,
    gaps included: test/fixtures/pvdaq/ gives Loaded("PV1", 5, 24, 8, 1, 1); a folder that is not one PVDAQ
    system raises FieldError, an asset already registered RegistryError, before any sample is stored."""
    # Decision: SP-036 (field telemetry from a local copy outside the repository; C-033)
    export = field_data.read(Path(folder), site)
    registry.load_fleet(conn, export.assets)
    stored = gaps = 0
    for channel in export.channels:
        made = field_data.samples(export, channel)
        sample_table.store(conn, made)
        stored += len(made)
        gaps += sum(1 for sample in made if sample.gap)
    tables = export.tables.values()
    return Loaded(export.site, len(export.assets), stored, gaps, sum(held.off_grid for held in tables),
                  sum(held.duplicates for held in tables))


def days(first: date, last: date) -> tuple[date, ...]:
    """Every day from first to last, both included: days(2023-02-01, 2023-02-03) is three days; last before first
    raises ValueError."""
    if last < first:
        raise ValueError(f"{last.isoformat()} is before {first.isoformat()}")
    return tuple(first + timedelta(days=offset) for offset in range((last - first).days + 1))


def tallies(results: tuple[DayResult, ...]) -> tuple[Tally, ...]:
    """Days run and days alarmed per (test, asset), in test then asset order: two days of on_grid on INV-001, one
    failed, give (Tally("on_grid", "…-INV-001", 2, 1),)."""
    counts: dict[tuple[str, str], list[int]] = {}
    for result in results:
        held = counts.setdefault((result.test, result.asset_id), [0, 0])
        held[0] += 1
        held[1] += 1 if result.failed else 0
    return tuple(Tally(test, asset_id, run, alarmed) for (test, asset_id), (run, alarmed) in sorted(counts.items()))


def field_baseline(conn: sqlite3.Connection, first: date, last: date) -> Baseline:
    """Every remote test that applies to each asset with stored samples, run over each UTC day from first to last
    (both included) on that day's samples alone, recording nothing: an inverter over three days gives three results for
    each of its kind's tests; an asset with no samples stored is not run. The scheduled run is not changed (SP-036)."""
    # Decision: SP-036 (the false-alarm baseline runs the remote tests a day at a time and writes no run record)
    tests = discover().values()
    found = []
    for asset_id in sample_table.asset_ids(conn):
        asset = registry.known(conn, asset_id)
        applying = [test for test in tests if asset.kind in test.kinds]
        for day in days(first, last):
            held = sample_table.in_period(conn, asset_id, day_period(day))
            for test in applying:
                result = test.run(asset, held)
                found.append(DayResult(test.name, asset_id, day, result.passed, result.reason, result.no_data))
    ordered = tuple(sorted(found, key=lambda result: (result.test, result.asset_id, result.day)))
    return Baseline(tallies(ordered), ordered)
