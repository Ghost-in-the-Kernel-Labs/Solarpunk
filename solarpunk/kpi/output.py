"""Power output over a period: each inverter's energy, peak, specific yield and capacity factor, and the site's beside
them, each number beside the records and gaps it was read from (Invariants: SOL-03, SOL-13)."""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from solarpunk.kpi.results import rounded
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import HOURS_PER_SAMPLE, Period
from solarpunk.leaf.telemetry import Sample


@dataclass(frozen=True)
class PowerOutput:
    """One inverter's, or a site's, output over a period (SOL-13): PowerOutput("OAHE-INV-001", 100.0, 12.5, 90.0,
    0.125, 0.5, 2, 1); peak_kw None when no record carries a power."""

    asset_id: str
    rated_kw: float
    energy_kwh: float
    peak_kw: float | None
    specific_yield: float
    capacity_factor: float
    records: int
    gaps: int


def powered(samples: Sequence[Sample]) -> list[Sample]:
    """The samples that carry a power, gaps left out: powered([60 kW, gap, 30 kW]) is the two readings."""
    return [sample for sample in samples if not sample.gap and sample.power_kw is not None]


def output_of(asset_id: str, rated: float, samples: Sequence[Sample], peak: float | None, period: Period) -> PowerOutput:
    """The numbers SOL-13 derives from a rating, the records and a peak: rated 100, records 60 and 90 kW and one gap over
    15 minutes give PowerOutput(asset_id, 100.0, 12.5, 90.0, 0.125, 0.5, 2, 1). A rating of 0 is refused (SOL-03)."""
    # Invariant: SOL-13
    if rated <= 0:
        raise ValueError(f"{asset_id}: rated power {rated} kW cannot divide a yield")
    read = powered(samples)
    energy = sum(sample.power_kw for sample in read) * HOURS_PER_SAMPLE
    return PowerOutput(asset_id, rated, rounded(energy), peak, rounded(energy / rated),
                       rounded(energy / (rated * period.hours())), len(read), sum(1 for s in samples if s.gap))


def inverter_output(inverter: Asset, samples: Sequence[Sample], period: Period) -> PowerOutput:
    """One inverter's output from its own samples in the period (SOL-13); samples of other assets and outside the period
    are left out, and an inverter with no rated_kw raises ValueError (SOL-03): the contract's example for OAHE-INV-002,
    rated 50 kW with 30, 45, 42 kW over 15 minutes, gives PowerOutput("OAHE-INV-002", 50.0, 9.75, 45.0, 0.195, 0.78, 3,
    0)."""
    # Invariant: SOL-03, SOL-13
    if inverter.rated_kw is None:
        raise ValueError(f"{inverter.asset_id}: no rated power")
    own = [s for s in samples if s.asset_id == inverter.asset_id and period.start <= s.at < period.end]
    powers = [sample.power_kw for sample in powered(own)]
    return output_of(inverter.asset_id, inverter.rated_kw, own, max(powers) if powers else None, period)


def summed_power(samples: Sequence[Sample]) -> tuple[tuple[datetime, float], ...]:
    """The sum of power at each instant that has a record carrying one, in time order (SOL-13): SOL-13's example gives
    ((10:00, 90.0), (10:05, 135.0), (10:10, 42.0)); an instant of gaps alone is left out, never drawn as 0."""
    # Invariant: SOL-13
    by_instant: dict[datetime, float] = {}
    for sample in powered(samples):
        by_instant[sample.at] = by_instant.get(sample.at, 0.0) + sample.power_kw
    return tuple((instant, rounded(by_instant[instant])) for instant in sorted(by_instant))


def coincident_peak(samples: Sequence[Sample]) -> float | None:
    """The largest sum of power at one instant over every inverter (SOL-13): 60+30, 90+45 and 42 kW at three instants
    give 135.0; None when no record carries a power."""
    # Invariant: SOL-13
    curve = summed_power(samples)
    return max(power for _, power in curve) if curve else None


def site_curve(inverters: Sequence[Asset], samples: Sequence[Sample], period: Period) -> tuple[tuple[datetime, float], ...]:
    """The site's summed power over the period at each instant where every inverter has a record carrying a power
    (SOL-13): the curve the reports window draws. An instant where one inverter has a gap is left out, so the line breaks
    there rather than dropping to the other inverters' share: SOL-13's example gives ((10:00, 90.0), (10:05, 135.0)),
    INV-001's gap at 10:10 leaving 10:10 out."""
    # Invariant: SOL-13
    ids = {inverter.asset_id for inverter in inverters}
    own = [s for s in powered(samples) if s.asset_id in ids and period.start <= s.at < period.end]
    reporting: dict[datetime, int] = {}
    for sample in own:
        reporting[sample.at] = reporting.get(sample.at, 0) + 1
    return tuple(point for point in summed_power(own) if reporting[point[0]] == len(ids))


def site_output(site_id: str, inverters: Sequence[Asset], samples: Sequence[Sample], period: Period) -> PowerOutput:
    """The site's output: its inverters' energy and ratings summed, its peak the coincident one (SOL-13). The contract's
    two inverters give PowerOutput("OAHE-SIT-001", 150.0, 22.25, 135.0, 0.1483, 0.5933, 5, 1)."""
    # Invariant: SOL-13
    rows = [inverter_output(inverter, samples, period) for inverter in inverters]
    ids = {inverter.asset_id for inverter in inverters}
    own = [s for s in samples if s.asset_id in ids and period.start <= s.at < period.end]
    return output_of(site_id, sum(row.rated_kw for row in rows), own, coincident_peak(own), period)
