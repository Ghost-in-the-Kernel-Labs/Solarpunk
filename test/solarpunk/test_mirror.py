"""The blind mirror (stacks/python/README.md): the contract's four worked examples (SOL-07 to SOL-10) recomputed by small
plain functions written from docs/CONTRACT.md's text alone, by a worker who never read the KPI engine's bodies, and
compared with what solarpunk.kpi returns on the same leaf inputs. A disagreement is a finding for the contract to settle,
never a reason to change either side."""
import unittest
from datetime import datetime, timedelta

from solarpunk import kpi
from solarpunk.leaf.assets import Asset, parse_asset_id
from solarpunk.leaf.clock import SAMPLE_INTERVAL_S, Period, at
from solarpunk.leaf.codes import AssetKind, Severity, lookup
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.kpi_defs import EXCLUDED_CODES, METER_LOST_CODE, ROUND_TO, STC_IRRADIANCE_W_M2
from solarpunk.leaf.telemetry import Sample, gap

SITE = "OAHE-SIT-001"
INV1 = "OAHE-INV-001"
INV2 = "OAHE-INV-002"
METER = "OAHE-MTR-001"
HOUR = Period(at(2026, 6, 1, 10), at(2026, 6, 1, 11))
DAY = Period(at(2026, 6, 1), at(2026, 6, 2))
INVERTER_1 = Asset(INV1, AssetKind.INVERTER, "OAHE", SITE, "Inverter 1", 100.0)
INVERTER_2 = Asset(INV2, AssetKind.INVERTER, "OAHE", SITE, "Inverter 2", 100.0)


# The mirror: each function below is the contract's formula, read from its text.


def covers(fault: Fault, instant: datetime) -> bool:
    """SOL-07: a fault's [opened, closed) covers an interval's start instant; an open fault covers all after opening:
    covers(Fault(1, INV1, "INV-001", 10:10, 10:30), 10:25) is True, at 10:30 it is False."""
    if instant < fault.opened:
        return False
    return fault.closed is None or instant < fault.closed


def mirror_availability(period: Period, faults: list[Fault], samples: list[Sample]) -> tuple[float, int, int, int, int]:
    """SOL-07's (availability, expected, excluded, down, gaps): the worked example gives (0.7, 12, 2, 3, 1); with
    contractual 0 the availability is 1.0."""
    expected = period.expected()
    excluded = 0
    down = 0
    for instant in period.instants():
        if any(f.code in EXCLUDED_CODES and covers(f, instant) for f in faults):
            excluded += 1
        elif any(lookup(f.code).severity is Severity.OUTAGE and covers(f, instant) for f in faults):
            down += 1
    gaps = len([s for s in samples if s.gap and period.start <= s.at < period.end])
    contractual = expected - excluded
    value = 1.0 if contractual == 0 else (contractual - down) / contractual
    return round(value, ROUND_TO), expected, excluded, down, gaps


def mirror_energy(samples: list[Sample]) -> float:
    """SOL-08's energy_kwh, Σ power × interval hours over samples with irradiance that are not gaps, unrounded:
    power 45, 92, 0 kW gives 137 × 5/60 = 11.41666…."""
    hours = SAMPLE_INTERVAL_S / 3600
    usable = [s for s in samples if not s.gap and s.irradiance_w_m2 is not None and s.power_kw is not None]
    return sum(s.power_kw for s in usable if s.power_kw is not None) * hours


def mirror_reference(rated: dict[str, float], samples: list[Sample]) -> float:
    """SOL-08's reference_kwh, Σ rated × irradiance / 1000 × interval hours over the same samples, unrounded:
    100 kW at 500, 1000, 0 W/m² gives 100 × 1.5 × 5/60 = 12.5."""
    hours = SAMPLE_INTERVAL_S / 3600
    total = 0.0
    for s in samples:
        if s.gap or s.irradiance_w_m2 is None or s.power_kw is None:
            continue
        total += rated[s.asset_id] * (s.irradiance_w_m2 / STC_IRRADIANCE_W_M2) * hours
    return total


def mirror_ratio(rated: dict[str, float], samples: list[Sample]) -> tuple[float | None, float, float, int]:
    """SOL-08's (ratio, energy, reference, unreliable) at four decimals: the worked example gives
    (0.9133, 11.4167, 12.5, 0); a sample with irradiance None adds 1 to unreliable and nothing to the sums."""
    energy = mirror_energy(samples)
    reference = mirror_reference(rated, samples)
    unreliable = len([s for s in samples if s.irradiance_w_m2 is None])
    ratio = None if reference == 0 else round(energy / reference, ROUND_TO)
    return ratio, round(energy, ROUND_TO), round(reference, ROUND_TO), unreliable


def mirror_yield(site: str, period: Period, meter_kwh: float, samples: list[Sample], faults: list[Fault]) -> tuple[float, str]:
    """SOL-09's (kwh, source): the meter's energy unless a MTR-001 of the site's meter overlaps the period, then the
    inverters' SOL-08 energy: (11.2, "meter") with no fault, (11.4167, "inverters") with MTR-001 over the period."""
    for fault in faults:
        fault_site, kind, _ = parse_asset_id(fault.asset_id)
        overlaps = fault.opened < period.end and (fault.closed is None or fault.closed > period.start)
        if fault.code == METER_LOST_CODE and kind is AssetKind.METER and fault_site == site and overlaps:
            return round(mirror_energy(samples), ROUND_TO), "inverters"
    return meter_kwh, "meter"


def mirror_reliability(kind: AssetKind, assets: list[Asset], period: Period, faults: list[Fault]) -> tuple[float | None, float | None, int, int]:
    """SOL-10's (mtbf_h, mttr_h, count, open): two inverters, 24 h, closed outages of 2 h and 4 h give
    (21.0, 3.0, 2, 0); an open outage is counted in open alone."""
    ids = {a.asset_id for a in assets if a.kind is kind}
    outages = [f for f in faults if f.asset_id in ids and lookup(f.code).severity is Severity.OUTAGE]
    still_open = len([f for f in outages if f.closed is None and period.start <= f.opened < period.end])
    closed = [f for f in outages if f.closed is not None and period.start <= f.opened and f.closed <= period.end]
    if not closed:
        return None, None, 0, still_open
    repair_h = sum((f.closed - f.opened) / timedelta(hours=1) for f in closed if f.closed is not None)
    mttr = repair_h / len(closed)
    mtbf = (len(ids) * period.hours() - repair_h) / len(closed)
    return round(mtbf, ROUND_TO), round(mttr, ROUND_TO), len(closed), still_open


# The worked examples' inputs, as leaf types.


def hour_samples(gap_at: int | None) -> list[Sample]:
    """Twelve samples of INV1 over HOUR, the one at index gap_at a gap: hour_samples(8)[8].gap is True."""
    found = []
    for index, instant in enumerate(HOUR.instants()):
        found.append(gap(INV1, instant) if index == gap_at else Sample(INV1, instant, 800.0, 70.0, False))
    return found


def sol07_faults() -> list[Fault]:
    """SOL-07's two faults: SIT-002 on the site over [10:05, 10:15), INV-001 on INV1 over [10:10, 10:30)."""
    return [
        Fault(1, SITE, "SIT-002", at(2026, 6, 1, 10, 5), at(2026, 6, 1, 10, 15)),
        Fault(2, INV1, "INV-001", at(2026, 6, 1, 10, 10), at(2026, 6, 1, 10, 30)),
    ]


def sol08_samples() -> list[Sample]:
    """SOL-08's three samples of INV1: (500, 45), (1000, 92), (0, 0) at 10:00, 10:05, 10:10."""
    readings = ((500.0, 45.0), (1000.0, 92.0), (0.0, 0.0))
    return [Sample(INV1, at(2026, 6, 1, 10, 5 * i), irr, kw, False) for i, (irr, kw) in enumerate(readings)]


def sol10_faults() -> list[Fault]:
    """SOL-10's two closed outages, 2 h on INV1 and 4 h on INV2, within DAY."""
    return [
        Fault(1, INV1, "INV-001", at(2026, 6, 1, 2), at(2026, 6, 1, 4)),
        Fault(2, INV2, "INV-003", at(2026, 6, 1, 10), at(2026, 6, 1, 14)),
    ]


class TheMirrorItself(unittest.TestCase):
    """The mirror reproduces the contract's printed numbers before it is compared with anything."""

    def test_the_mirror_gives_the_contracts_numbers(self) -> None:
        self.assertEqual(mirror_availability(HOUR, sol07_faults(), hour_samples(8)), (0.7, 12, 2, 3, 1))
        self.assertEqual(mirror_ratio({INV1: 100.0}, sol08_samples()), (0.9133, 11.4167, 12.5, 0))
        self.assertEqual(mirror_reliability(AssetKind.INVERTER, [INVERTER_1, INVERTER_2], DAY, sol10_faults()),
                         (21.0, 3.0, 2, 0))


class SOL07Availability(unittest.TestCase):
    def test_the_engine_agrees_on_the_worked_example(self) -> None:
        faults, samples = sol07_faults(), hour_samples(8)
        result = kpi.availability(HOUR, faults, samples)
        mirror = mirror_availability(HOUR, faults, samples)
        self.assertEqual((result.value, result.expected, result.excluded, result.down, result.gaps), mirror)
        self.assertEqual(mirror, (0.7, 12, 2, 3, 1))

    def test_the_engine_agrees_with_no_faults_and_with_all_excluded(self) -> None:
        excluded = [Fault(1, SITE, "SIT-001", at(2026, 6, 1, 9), None)]
        for faults in ([], excluded):
            result = kpi.availability(HOUR, faults, hour_samples(None))
            mirror = mirror_availability(HOUR, faults, hour_samples(None))
            self.assertEqual((result.value, result.expected, result.excluded, result.down, result.gaps), mirror)


class SOL08PerformanceRatio(unittest.TestCase):
    def test_the_engine_agrees_on_the_worked_example(self) -> None:
        result = kpi.performance_ratio([INVERTER_1], sol08_samples())
        mirror = mirror_ratio({INV1: 100.0}, sol08_samples())
        self.assertEqual((result.value, result.energy_kwh, result.reference_kwh, result.unreliable), mirror)
        self.assertEqual(mirror, (0.9133, 11.4167, 12.5, 0))

    def test_the_engine_agrees_when_a_gap_joins_the_example(self) -> None:
        samples = [*sol08_samples(), gap(INV1, at(2026, 6, 1, 10, 15))]
        result = kpi.performance_ratio([INVERTER_1], samples)
        mirror = mirror_ratio({INV1: 100.0}, samples)
        self.assertEqual((result.value, result.energy_kwh, result.reference_kwh, result.unreliable), mirror)
        self.assertEqual(mirror, (0.9133, 11.4167, 12.5, 1))


class SOL09EnergyYield(unittest.TestCase):
    def test_the_engine_agrees_when_the_meter_is_present(self) -> None:
        span = Period(at(2026, 6, 1, 10), at(2026, 6, 1, 10, 15))
        result = kpi.energy_yield("OAHE", 11.2, sol08_samples(), [])
        mirror = mirror_yield("OAHE", span, 11.2, sol08_samples(), [])
        self.assertEqual((result.kwh, result.source), mirror)
        self.assertEqual(mirror, (11.2, "meter"))

    def test_the_engine_agrees_when_mtr_001_covers_the_span(self) -> None:
        span = Period(at(2026, 6, 1, 10), at(2026, 6, 1, 10, 15))
        lost = [Fault(1, METER, "MTR-001", at(2026, 6, 1, 10), at(2026, 6, 1, 10, 15))]
        result = kpi.energy_yield("OAHE", 11.2, sol08_samples(), lost)
        mirror = mirror_yield("OAHE", span, 11.2, sol08_samples(), lost)
        self.assertEqual((result.kwh, result.source), mirror)
        self.assertEqual(mirror, (11.4167, "inverters"))


class SOL10Reliability(unittest.TestCase):
    def test_the_engine_agrees_on_the_worked_example(self) -> None:
        assets = [INVERTER_1, INVERTER_2]
        result = kpi.mtbf_mttr(AssetKind.INVERTER, assets, DAY, sol10_faults())
        mirror = mirror_reliability(AssetKind.INVERTER, assets, DAY, sol10_faults())
        self.assertEqual((result.mtbf_h, result.mttr_h, result.count, result.open), mirror)
        self.assertEqual(mirror, (21.0, 3.0, 2, 0))

    def test_the_engine_agrees_with_an_open_outage_and_a_derate_beside_it(self) -> None:
        assets = [INVERTER_1, INVERTER_2]
        faults = [*sol10_faults(), Fault(3, INV1, "INV-001", at(2026, 6, 1, 20), None),
                  Fault(4, INV2, "INV-002", at(2026, 6, 1, 15), at(2026, 6, 1, 16))]
        result = kpi.mtbf_mttr(AssetKind.INVERTER, assets, DAY, faults)
        mirror = mirror_reliability(AssetKind.INVERTER, assets, DAY, faults)
        self.assertEqual((result.mtbf_h, result.mttr_h, result.count, result.open), mirror)
        self.assertEqual(mirror, (21.0, 3.0, 2, 1))

    def test_the_engine_agrees_with_no_outage(self) -> None:
        result = kpi.mtbf_mttr(AssetKind.INVERTER, [INVERTER_1], DAY, [])
        mirror = mirror_reliability(AssetKind.INVERTER, [INVERTER_1], DAY, [])
        self.assertEqual((result.mtbf_h, result.mttr_h, result.count, result.open), mirror)
