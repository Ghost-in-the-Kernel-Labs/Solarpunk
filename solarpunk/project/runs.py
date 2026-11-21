"""The runs' surface (10.2, SOL-15, SP-024): what the Runs window reads, one call per view, each a reading of the
results, the faults, the suggestions and the samples the store holds, recomputed when asked and never kept apart
from them. A run is every result stored for an asset at one instant; an error count is faults and suggestions by code,
counted apart; a power series is the samples with their gaps named. The newest 100 runs are shown where more are
kept: nothing is deleted (SP-016)."""
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from solarpunk.faults import ledger
from solarpunk.leaf.clock import Period
from solarpunk.leaf.codes import lookup
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.telemetry import Sample
from solarpunk.project.orchestrator import fleet_assets, known
from solarpunk.remote import results as result_table
from solarpunk.remote import suggestions as suggestion_table
from solarpunk.remote.results import Recorded
from solarpunk.telemetry import samples as sample_table

SHOWN = 100
PASS = "pass"
FAIL = "fail"
NO_DATA = result_table.NO_DATA


@dataclass(frozen=True)
class Run:
    """Every result stored for an asset at one instant, failures first, then no data, then by test name (SOL-15): OAHE-INV-002's run
    at 13:00 in the demo holds 8 results, its first the ping's failed reachable; failed is True."""

    asset_id: str
    run_at: datetime
    results: tuple[Recorded, ...]

    @property
    def failed(self) -> bool:
        """Whether any of the run's results failed; no data is no failure (SP-039)."""
        return any(result.failed for result in self.results)


@dataclass(frozen=True)
class PowerSeries:
    """An asset's samples in a period, in time order, a gap named and never filled (SOL-15, SOL-13): OAHE-INV-001's
    demo day is 288 samples, records 279, gaps 9."""

    asset_id: str
    period: Period
    samples: tuple[Sample, ...]

    @property
    def records(self) -> int:
        """The samples that carry a power."""
        return sum(1 for sample in self.samples if sample.power_kw is not None)

    @property
    def gaps(self) -> int:
        """The gap samples."""
        return sum(1 for sample in self.samples if sample.gap)


@dataclass(frozen=True)
class CodeCount:
    """One code's faults and suggestions, counted apart (SOL-15): CodeCount("SEN-001", 0, 1) on the demo's sensor."""

    code: str
    faults: int
    suggestions: int


@dataclass(frozen=True)
class AssetCount:
    """One asset's faults and suggestions of one code (SOL-15): AssetCount("OAHE-INV-002", 1, 0) for INV-001 in the
    demo."""

    asset_id: str
    faults: int
    suggestions: int


def verdict_of(result: Recorded) -> str:
    """A result's word: "pass", "fail" or "no data" (SP-039)."""
    if result.no_data:
        return NO_DATA
    return PASS if result.passed else FAIL


def matches(result: Recorded, words: str) -> bool:
    """Whether a result answers a search: its test's name, "pass", "fail" or "no data", or words in its reason, any
    case: matches(the ping's failed reachable, "unreachable") and matches(it, "fail") are True, matches(it, "pass")
    False."""
    needle = words.strip().casefold()
    verdict = verdict_of(result)
    return needle in result.test_name.casefold() or needle == verdict or needle in result.reason.casefold()


def asset_runs(conn: sqlite3.Connection, asset_id: str, limit: int = SHOWN, search: str | None = None) -> tuple[Run, ...]:
    """The asset's newest runs, at most limit, newest first, each with every result it holds (SOL-15); with a search,
    the runs holding a result that matches it (matches). An asset the fleet lacks raises UnknownAsset; one never run
    gives ()."""
    known(conn, asset_id)
    by_instant: dict[datetime, list[Recorded]] = {}
    for result in result_table.results_of(conn, asset_id):
        by_instant.setdefault(result.run_at, []).append(result)
    runs = []
    for run_at, found in by_instant.items():
        if search and search.strip() and not any(matches(result, search) for result in found):
            continue
        ordered = tuple(sorted(found, key=lambda r: (r.passed, r.no_data, r.test_name)))
        runs.append(Run(asset_id, run_at, ordered))
        if len(runs) == limit:
            break
    return tuple(runs)


def asset_power(conn: sqlite3.Connection, asset_id: str, period: Period) -> PowerSeries:
    """The asset's samples in the period with their gaps named (SOL-15): OAHE-INV-001's demo day gives records 279 and
    gaps 9 of 288 samples; an asset with none gives an empty series. An asset the fleet lacks raises UnknownAsset."""
    known(conn, asset_id)
    return PowerSeries(asset_id, period, sample_table.in_period(conn, asset_id, period))


def _opened_in(faults: tuple[Fault, ...], period: Period) -> list[Fault]:
    """The faults opened inside the half-open period (SOL-15 counts a fault by its opening)."""
    return [fault for fault in faults if period.start <= fault.opened < period.end]


def asset_code_counts(conn: sqlite3.Connection, asset_id: str, period: Period) -> tuple[CodeCount, ...]:
    """The asset's faults and suggestions in the period by code, counted apart, every suggestion's state counted, in
    code order (SOL-15): the demo's sensor over its day gives (CodeCount("SEN-001", 0, 1),). UnknownAsset as above."""
    known(conn, asset_id)
    faults = Counter(fault.code for fault in _opened_in(ledger.by_asset(conn, asset_id), period))
    suggestions = Counter(s.code for s in suggestion_table.raised_in(conn, period) if s.asset_id == asset_id)
    return tuple(CodeCount(code, faults[code], suggestions[code]) for code in sorted(set(faults) | set(suggestions)))


def code_counts_by_asset(conn: sqlite3.Connection, code: str, period: Period) -> tuple[AssetCount, ...]:
    """Each asset's faults and suggestions of one code in the period, worst first (faults, then suggestions, then by
    id), the assets with none left out (SOL-15): INV-001 over the demo day gives (AssetCount("OAHE-INV-002", 1, 0),).
    A code the catalogue lacks raises UnknownFaultCode."""
    # Invariant: SOL-04
    lookup(code)
    faults = Counter(fault.asset_id for fault in _opened_in(ledger.by_code(conn, code), period))
    suggestions = Counter(s.asset_id for s in suggestion_table.raised_in(conn, period) if s.code == code)
    fleet = {asset.asset_id for asset in fleet_assets(conn, None)}
    counts = [AssetCount(a, faults[a], suggestions[a]) for a in (set(faults) | set(suggestions)) & fleet]
    return tuple(sorted(counts, key=lambda c: (-c.faults, -c.suggestions, c.asset_id)))
