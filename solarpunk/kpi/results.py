"""The KPI engine's result types: each number beside the counts that explain it, never a number alone (Invariants:
SOL-03, SOL-07, SOL-08, SOL-09, SOL-10). Every float is rounded to the leaf's ROUND_TO places."""
from dataclasses import dataclass

from solarpunk.leaf.kpi_defs import ROUND_TO


def rounded(value: float) -> float:
    """A KPI number at the contract's precision: rounded(11.416666) is 11.4167."""
    return round(value, ROUND_TO)


@dataclass(frozen=True)
class Availability:
    """One inverter's contractual availability over a period (SOL-07): Availability(0.7, 12, 2, 3, 1)."""

    value: float
    expected: int
    excluded: int
    down: int
    gaps: int


@dataclass(frozen=True)
class PerformanceRatio:
    """Yield over reference yield (SOL-08): PerformanceRatio(0.9133, 11.4167, 12.5, 0); value None when reference is 0."""

    value: float | None
    energy_kwh: float
    reference_kwh: float
    unreliable: int


@dataclass(frozen=True)
class EnergyYield:
    """A site's energy and where it came from (SOL-09): EnergyYield(11.2, "meter") or EnergyYield(11.4167, "inverters")."""

    kwh: float
    source: str


@dataclass(frozen=True)
class Reliability:
    """MTBF and MTTR of one asset kind (SOL-10): Reliability(21.0, 3.0, 2, 0); both None when count is 0."""

    mtbf_h: float | None
    mttr_h: float | None
    count: int
    open: int
