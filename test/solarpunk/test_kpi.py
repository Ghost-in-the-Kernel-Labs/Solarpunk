"""The KPI engine against the contract: its four worked examples as goldens (SOL-07 to SOL-10), a ten-row table per KPI
a person checks by hand (each row's arithmetic in its comment), and the edges each invariant names.
The day is 2026-06-01, every instant UTC; one sample interval is 5 min, so HOURS_PER_SAMPLE is 1/12."""
import unittest
from datetime import datetime, timedelta

from solarpunk.kpi import (
    Availability,
    EnergyYield,
    PerformanceRatio,
    Reliability,
    availability,
    energy_yield,
    mtbf_mttr,
    performance_ratio,
)
from solarpunk.kpi.results import rounded
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import Period, at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.telemetry import Sample, gap

INV1 = "OAHE-INV-001"
INV2 = "OAHE-INV-002"
DAY = at(2026, 6, 1)

# A fault spec is (code, asset id, opened, closed or None), each instant as minutes after 10:00 (negative is before).
FaultSpec = tuple[str, str, int, int | None]


def ten(minute: int) -> datetime:
    """The instant `minute` minutes after 10:00: ten(5) is 2026-06-01 10:05 UTC, ten(-60) is 09:00."""
    return at(2026, 6, 1, 10) + timedelta(minutes=minute)


def faults_from(specs: list[FaultSpec]) -> list[Fault]:
    """Faults numbered from 1: faults_from([("INV-001", INV1, 10, 30)]) is [Fault(1, INV1, "INV-001", 10:10, 10:30)]."""
    made = []
    for number, (code, asset_id, opened, closed) in enumerate(specs, start=1):
        made.append(Fault(number, asset_id, code, ten(opened), None if closed is None else ten(closed)))
    return made


def inverter(asset_id: str, rated: float) -> Asset:
    """An inverter at its site: inverter("OAHE-INV-001", 100.0).rated_kw is 100.0."""
    return Asset(asset_id, AssetKind.INVERTER, asset_id.split("-")[0], None, asset_id, rated)


def readings(asset_id: str, values: list[tuple[float | None, float | None]]) -> list[Sample]:
    """One sample per (irradiance, power), from 10:00 every 5 min; (None, None) is a gap:
    readings(INV1, [(500.0, 45.0), (None, None)]) is a reading at 10:00 and a gap at 10:05."""
    made = []
    for index, (irradiance, power) in enumerate(values):
        moment = ten(5 * index)
        both_none = irradiance is None and power is None
        made.append(gap(asset_id, moment) if both_none else Sample(asset_id, moment, irradiance, power, False))
    return made


SOL08_SAMPLES = readings(INV1, [(500.0, 45.0), (1000.0, 92.0), (0.0, 0.0)])


class TheGoldens(unittest.TestCase):
    """The contract's four worked examples, the exact numbers it prints."""

    def test_sol07_availability_is_0_7_with_one_gap(self) -> None:
        period = Period(ten(0), ten(60))
        faults = faults_from([("SIT-002", "OAHE-SIT-001", 5, 15), ("INV-001", INV1, 10, 30)])
        samples = [gap(INV1, ten(40)) if m == 40 else Sample(INV1, ten(m), 800.0, 80.0, False) for m in range(0, 60, 5)]
        self.assertEqual(availability(period, faults, samples), Availability(0.7, 12, 2, 3, 1))

    def test_sol08_performance_ratio_is_0_9133(self) -> None:
        result = performance_ratio([inverter(INV1, 100.0)], SOL08_SAMPLES)
        self.assertEqual(result, PerformanceRatio(0.9133, 11.4167, 12.5, 0))

    def test_sol09_yield_has_two_sources(self) -> None:
        self.assertEqual(energy_yield("OAHE", 11.2, SOL08_SAMPLES, []), EnergyYield(11.2, "meter"))
        lost = faults_from([("MTR-001", "OAHE-MTR-001", 0, 15)])
        self.assertEqual(energy_yield("OAHE", 11.2, SOL08_SAMPLES, lost), EnergyYield(11.4167, "inverters"))

    def test_sol10_mttr_3_and_mtbf_21(self) -> None:
        fleet = [inverter(INV1, 100.0), inverter(INV2, 100.0)]
        faults = faults_from([("INV-001", INV1, 0, 120), ("INV-003", INV2, 180, 420)])
        result = mtbf_mttr(AssetKind.INVERTER, fleet, Period(DAY, DAY + timedelta(hours=24)), faults)
        self.assertEqual(result, Reliability(21.0, 3.0, 2, 0))


# Availability, period 10:00 + end minutes; the inverter is INV1, its site OAHE; samples are (gaps, readings).
# Each interval is named by its start minute; a fault covers an interval when it holds that start instant.
AVAILABILITY_TABLE: list[tuple[int, list[FaultSpec], tuple[int, int], Availability]] = [
    # 1. nothing happened: 12 expected, 0 down: 12/12 = 1.0
    (60, [], (0, 12), Availability(1.0, 12, 0, 0, 0)),
    # 2. INV-001 (OUTAGE) 10:00-10:30 covers 0,5,…,25: down 6: (12-6)/12 = 0.5
    (60, [("INV-001", INV1, 0, 30)], (0, 0), Availability(0.5, 12, 0, 6, 0)),
    # 3. INV-002 (DERATE) all hour: a derate is not an outage (SOL-11): 12/12 = 1.0
    (60, [("INV-002", INV1, 0, 60)], (0, 0), Availability(1.0, 12, 0, 0, 0)),
    # 4. half-hour period, SIT-001 grid outage all of it: excluded 6, contractual 0: 1.0 by definition
    (30, [("SIT-001", "OAHE-SIT-001", 0, 30)], (0, 0), Availability(1.0, 6, 6, 0, 0)),
    # 5. SIT-003 10:00-10:30 excluded 6; INV-001 all hour down only in the other 6: (6-6)/6 = 0.0
    (60, [("SIT-003", "OAHE-SIT-001", 0, 30), ("INV-001", INV1, 0, 60)], (0, 0), Availability(0.0, 12, 6, 6, 0)),
    # 6. INV-001 10:02-10:07 holds the start instant 10:05 only: down 1: 11/12 = 0.91666… = 0.9167
    (60, [("INV-001", INV1, 2, 7)], (0, 0), Availability(0.9167, 12, 0, 1, 0)),
    # 7. INV-001 open from 10:45 covers 45,50,55: down 3: 9/12 = 0.75
    (60, [("INV-001", INV1, 45, None)], (0, 0), Availability(0.75, 12, 0, 3, 0)),
    # 8. INV-001 09:00-10:10 covers 0,5; 2 gaps among 3 samples: down 2: 10/12 = 0.8333, gaps 2
    (60, [("INV-001", INV1, -60, 10)], (2, 1), Availability(0.8333, 12, 0, 2, 2)),
    # 9. SIT-002 10:00-10:20 excludes 0..15 (4); INV-003 10:10-10:40 covers 10..35, of which 20..35 not excluded (4):
    #    contractual 8: (8-4)/8 = 0.5
    (60, [("SIT-002", "OAHE-SIT-001", 0, 20), ("INV-003", INV1, 10, 40)], (0, 0), Availability(0.5, 12, 4, 4, 0)),
    # 10. two-hour period (24); INV-001 10:30-10:45 and INV-003 10:35-10:50 overlap: union 30,35,40,45 = 4 down, once each:
    #     20/24 = 0.8333
    (120, [("INV-001", INV1, 30, 45), ("INV-003", INV1, 35, 50)], (0, 0), Availability(0.8333, 24, 0, 4, 0)),
]

# Performance ratio: (ratings of INV1 then INV2, INV1's samples, INV2's samples, SEN-001 faults, expected).
# energy = Σ power / 12; reference = Σ rated × irradiance/1000 / 12; ratio = energy / reference.
PR_TABLE: list[tuple[tuple[float, float], list, list, list[FaultSpec], PerformanceRatio]] = [
    # 1. 1000 W/m², 100 kW: e = 100/12 = 8.3333, ref = 100×1.0/12 = 8.3333: 1.0
    ((100.0, 200.0), [(1000.0, 100.0)], [], [], PerformanceRatio(1.0, 8.3333, 8.3333, 0)),
    # 2. 500 W/m², 40 kW: e = 40/12 = 3.3333, ref = 100×0.5/12 = 4.1667: 40/50 = 0.8
    ((100.0, 200.0), [(500.0, 40.0)], [], [], PerformanceRatio(0.8, 3.3333, 4.1667, 0)),
    # 3. night, 0 W/m² and 0 kW: reference 0: ratio None
    ((100.0, 200.0), [(0.0, 0.0)], [], [], PerformanceRatio(None, 0.0, 0.0, 0)),
    # 4. irradiance None (not a gap): left out of both sums, unreliable 1: ratio None
    ((100.0, 200.0), [(None, 10.0)], [], [], PerformanceRatio(None, 0.0, 0.0, 1)),
    # 5. one gap: no irradiance, left out, unreliable 1: ratio None
    ((100.0, 200.0), [(None, None)], [], [], PerformanceRatio(None, 0.0, 0.0, 1)),
    # 6. (1000, 90) counted, (None, 50) left out: e = 90/12 = 7.5, ref = 8.3333: 90/100 = 0.9, unreliable 1
    ((100.0, 200.0), [(1000.0, 90.0), (None, 50.0)], [], [], PerformanceRatio(0.9, 7.5, 8.3333, 1)),
    # 7. 100 kW and 200 kW at 800 W/m² producing 75 and 150: e = 225/12 = 18.75, ref = 300×0.8/12 = 20: 0.9375
    ((100.0, 200.0), [(800.0, 75.0)], [(800.0, 150.0)], [], PerformanceRatio(0.9375, 18.75, 20.0, 0)),
    # 8. (800, 80), (600, 60) with SEN-001 over 10:05: e = 140/12 = 11.6667, ref = 100×1.4/12 = 11.6667: 1.0, unreliable 1
    ((100.0, 200.0), [(800.0, 80.0), (600.0, 60.0)], [], [("SEN-001", "OAHE-SEN-001", 5, 10)],
     PerformanceRatio(1.0, 11.6667, 11.6667, 1)),
    # 9. 50 kW rated, 200 W/m², 5 kW: e = 5/12 = 0.4167, ref = 50×0.2/12 = 0.8333: 5/10 = 0.5
    ((50.0, 200.0), [(200.0, 5.0)], [], [], PerformanceRatio(0.5, 0.4167, 0.8333, 0)),
    # 10. full sun, nothing produced: e = 0, ref = 8.3333: 0.0
    ((100.0, 200.0), [(1000.0, 0.0)], [], [], PerformanceRatio(0.0, 0.0, 8.3333, 0)),
]

# Energy yield at site OAHE: (meter kWh, samples, faults, expected). S is the SOL-08 example at 10:00, 10:05, 10:10:
# its inverters' energy is (45 + 92 + 0)/12 = 11.4167; its period runs 10:00 to 10:15.
OTHER = readings("BIGS-INV-001", [(1000.0, 60.0)])
YIELD_TABLE: list[tuple[float | None, list[Sample], list[FaultSpec], EnergyYield]] = [
    # 1. meter read, no MTR-001: the meter, rounded: 11.23456 = 11.2346
    (11.23456, SOL08_SAMPLES, [], EnergyYield(11.2346, "meter")),
    # 2. no meter reading: the inverters, 137/12 = 11.4167
    (None, SOL08_SAMPLES, [], EnergyYield(11.4167, "inverters")),
    # 3. MTR-001 at another site (BIGS): OAHE's meter stands: 11.2
    (11.2, SOL08_SAMPLES, [("MTR-001", "BIGS-MTR-001", 0, 15)], EnergyYield(11.2, "meter")),
    # 4. MTR-001 09:00-10:00 closed at the period's start: covers nothing in it: meter 11.2
    (11.2, SOL08_SAMPLES, [("MTR-001", "OAHE-MTR-001", -60, 0)], EnergyYield(11.2, "meter")),
    # 5. MTR-001 opens 10:15, the end of the last interval: covers nothing in [10:00, 10:15): meter 11.2
    (11.2, SOL08_SAMPLES, [("MTR-001", "OAHE-MTR-001", 15, 30)], EnergyYield(11.2, "meter")),
    # 6. MTR-001 10:12-10:13, inside the last interval though off the grid: inverters 11.4167
    (11.2, SOL08_SAMPLES, [("MTR-001", "OAHE-MTR-001", 12, 13)], EnergyYield(11.4167, "inverters")),
    # 7. MTR-001 open since 09:00: inverters 11.4167
    (11.2, SOL08_SAMPLES, [("MTR-001", "OAHE-MTR-001", -60, None)], EnergyYield(11.4167, "inverters")),
    # 8. an inverter OUTAGE is not a meter fault: meter 11.2
    (11.2, SOL08_SAMPLES, [("INV-001", INV1, 0, 15)], EnergyYield(11.2, "meter")),
    # 9. 45 kW, a gap, 92 kW with MTR-001 over 10:05: the gap adds nothing: (45 + 92)/12 = 11.4167
    (11.2, readings(INV1, [(500.0, 45.0), (None, None), (1000.0, 92.0)]), [("MTR-001", "OAHE-MTR-001", 5, 10)],
     EnergyYield(11.4167, "inverters")),
    # 10. BIGS's 60 kW sample beside OAHE's, no meter: OAHE's alone, 11.4167 (not (137 + 60)/12 = 16.4167)
    (None, SOL08_SAMPLES + OTHER, [], EnergyYield(11.4167, "inverters")),
]

# MTBF/MTTR of inverters over 2026-06-01 00:00 to 06-02 00:00 (24 h): (inverter count, faults as
# (code, inverter index or "site", opened h, closed h or None), expected). mttr = Σ repair / n;
# mtbf = (inverters × 24 − Σ repair) / n. The fleet also holds the site OAHE-SIT-001.
MTBF_TABLE: list[tuple[int, list[tuple[str, int | str, float, float | None]], Reliability]] = [
    # 1. one inverter, one 6 h outage: mttr 6, mtbf (24 − 6)/1 = 18
    (1, [("INV-001", 1, 2.0, 8.0)], Reliability(18.0, 6.0, 1, 0)),
    # 2. no faults: count 0: None, None
    (2, [], Reliability(None, None, 0, 0)),
    # 3. a 3 h INV-002 derate (SOL-11): count 0: None, None
    (2, [("INV-002", 1, 1.0, 4.0)], Reliability(None, None, 0, 0)),
    # 4. one INV-001 open since 05:00: excluded, open 1: None, None
    (2, [("INV-001", 1, 5.0, None)], Reliability(None, None, 0, 1)),
    # 5. three inverters, three 1 h outages: mttr 3/3 = 1, mtbf (72 − 3)/3 = 23
    (3, [("INV-001", 1, 1.0, 2.0), ("INV-001", 2, 3.0, 4.0), ("INV-003", 3, 5.0, 6.0)], Reliability(23.0, 1.0, 3, 0)),
    # 6. 23:00 the day before to 02:00 straddles the start (out); a 2 h one inside: mttr 2, mtbf (48 − 2)/1 = 46
    (2, [("INV-001", 1, -1.0, 2.0), ("INV-001", 2, 4.0, 6.0)], Reliability(46.0, 2.0, 1, 0)),
    # 7. 22:00 to 02:00 next day straddles the end (out); a 1.5 h one inside: mttr 1.5, mtbf (48 − 1.5)/1 = 46.5
    (2, [("INV-001", 1, 22.0, 26.0), ("INV-003", 2, 3.0, 4.5)], Reliability(46.5, 1.5, 1, 0)),
    # 8. a 3 h SIT-001 is the site's, not an inverter's; a 0.5 h INV-003: mttr 0.5, mtbf (48 − 0.5)/1 = 47.5
    (2, [("SIT-001", "site", 1.0, 4.0), ("INV-003", 1, 6.0, 6.5)], Reliability(47.5, 0.5, 1, 0)),
    # 9. four inverters, 00:00-24:00 exactly (within) and 20 min: Σ 24.3333 h: mttr 24.3333/2 = 12.1667,
    #    mtbf (96 − 24.3333)/2 = 35.8333
    (4, [("INV-001", 1, 0.0, 24.0), ("INV-003", 2, 10.0, 10.0 + 1 / 3)], Reliability(35.8333, 12.1667, 2, 0)),
    # 10. a closed 4 h outage and one open since 12:00: mttr 4, mtbf (48 − 4)/1 = 44, open 1
    (2, [("INV-001", 1, 0.0, 4.0), ("INV-003", 2, 12.0, None)], Reliability(44.0, 4.0, 1, 1)),
]


def availability_row(end: int, specs: list[FaultSpec], counts: tuple[int, int]) -> Availability:
    """Runs one availability row: availability_row(60, [], (0, 12)) is Availability(1.0, 12, 0, 0, 0)."""
    gaps, kept = counts
    samples = [gap(INV1, ten(5 * i)) for i in range(gaps)]
    samples += [Sample(INV1, ten(5 * (gaps + i)), 800.0, 80.0, False) for i in range(kept)]
    return availability(Period(ten(0), ten(end)), faults_from(specs), samples)


def fleet_of(count: int) -> list[Asset]:
    """The site OAHE and `count` inverters rated 100 kW: fleet_of(2) holds OAHE-SIT-001, OAHE-INV-001, OAHE-INV-002."""
    site = Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None)
    return [site] + [inverter(f"OAHE-INV-{i:03d}", 100.0) for i in range(1, count + 1)]


def hour_faults(specs: list[tuple[str, int | str, float, float | None]]) -> list[Fault]:
    """Faults from hour offsets on 2026-06-01: [("INV-001", 1, 2.0, 8.0)] is INV-001 on OAHE-INV-001, 02:00 to 08:00."""
    made = []
    for number, (code, which, opened, closed) in enumerate(specs, start=1):
        asset_id = "OAHE-SIT-001" if which == "site" else f"OAHE-INV-{which:03d}"
        end = None if closed is None else DAY + timedelta(hours=closed)
        made.append(Fault(number, asset_id, code, DAY + timedelta(hours=opened), end))
    return made


class TheTables(unittest.TestCase):
    """Ten hand-checkable rows per KPI."""

    def test_availability_table(self) -> None:
        self.assertEqual(len(AVAILABILITY_TABLE), 10)
        for row, (end, specs, counts, expected) in enumerate(AVAILABILITY_TABLE, start=1):
            self.assertEqual(availability_row(end, specs, counts), expected, f"row {row}")

    def test_performance_ratio_table(self) -> None:
        self.assertEqual(len(PR_TABLE), 10)
        for row, ((first, second), mine, theirs, specs, expected) in enumerate(PR_TABLE, start=1):
            assets = [inverter(INV1, first), inverter(INV2, second)]
            samples = readings(INV1, mine) + readings(INV2, theirs)
            self.assertEqual(performance_ratio(assets, samples, faults_from(specs)), expected, f"row {row}")

    def test_energy_yield_table(self) -> None:
        self.assertEqual(len(YIELD_TABLE), 10)
        for row, (meter, samples, specs, expected) in enumerate(YIELD_TABLE, start=1):
            self.assertEqual(energy_yield("OAHE", meter, samples, faults_from(specs)), expected, f"row {row}")

    def test_mtbf_mttr_table(self) -> None:
        self.assertEqual(len(MTBF_TABLE), 10)
        period = Period(DAY, DAY + timedelta(hours=24))
        for row, (count, specs, expected) in enumerate(MTBF_TABLE, start=1):
            result = mtbf_mttr(AssetKind.INVERTER, fleet_of(count), period, hour_faults(specs))
            self.assertEqual(result, expected, f"row {row}")


class TheEdges(unittest.TestCase):
    """What each invariant names beyond its example."""

    def test_availability_defaults_to_no_samples(self) -> None:
        self.assertEqual(availability(Period(ten(0), ten(10)), []), Availability(1.0, 2, 0, 0, 0))

    def test_performance_ratio_defaults_to_no_faults(self) -> None:
        self.assertEqual(performance_ratio([inverter(INV1, 100.0)], SOL08_SAMPLES).unreliable, 0)

    def test_a_sensor_fault_counts_each_interval_once_across_inverters(self) -> None:
        samples = readings(INV1, [(800.0, 80.0), (800.0, 80.0)]) + readings(INV2, [(800.0, 80.0), (800.0, 80.0)])
        assets = [inverter(INV1, 100.0), inverter(INV2, 100.0)]
        result = performance_ratio(assets, samples, faults_from([("SEN-001", "OAHE-SEN-001", 0, 60)]))
        self.assertEqual(result, PerformanceRatio(1.0, 26.6667, 26.6667, 2))

    def test_unreliable_adds_up_and_later_samples_still_count(self) -> None:
        # (None, 10), a gap, then (1000, 90) under SEN-001 at 10:10: 1 + 1 left out, plus 1 sensor interval = 3;
        # the reading after them still counts: 90/12 = 7.5 over 100/12 = 8.3333: 0.9
        samples = readings(INV1, [(None, 10.0), (None, None), (1000.0, 90.0)])
        sensor = faults_from([("SEN-001", "OAHE-SEN-001", 10, 15)])
        result = performance_ratio([inverter(INV1, 100.0)], samples, sensor)
        self.assertEqual(result, PerformanceRatio(0.9, 7.5, 8.3333, 3))

    def test_open_faults_add_up(self) -> None:
        period = Period(DAY, DAY + timedelta(hours=24))
        faults = hour_faults([("INV-001", 1, 2.0, None), ("INV-003", 2, 5.0, None), ("INV-001", 1, -2.0, None)])
        self.assertEqual(mtbf_mttr(AssetKind.INVERTER, fleet_of(2), period, faults), Reliability(None, None, 0, 2))

    def test_a_sample_of_an_unrated_or_unknown_asset_is_refused(self) -> None:
        meter = Asset("OAHE-MTR-001", AssetKind.METER, "OAHE", None, "Meter", None)
        for assets in ([], [meter], [inverter(INV2, 100.0)]):
            samples = readings(INV1, [(500.0, 45.0)])
            if assets == [meter]:
                samples = readings("OAHE-MTR-001", [(500.0, 45.0)])
            with self.assertRaises(ValueError) as refused:
                performance_ratio(assets, samples)
            self.assertIn("no rated power among the assets given", str(refused.exception))

    def test_the_rating_found_is_the_samples_own(self) -> None:
        assets = [inverter(INV2, 300.0), inverter(INV1, 100.0)]
        self.assertEqual(performance_ratio(assets, readings(INV1, [(1000.0, 50.0)])).value, 0.5)

    def test_yield_with_no_samples(self) -> None:
        self.assertEqual(energy_yield("OAHE", 3.0, [], []), EnergyYield(3.0, "meter"))
        self.assertEqual(energy_yield("OAHE", None, [], []), EnergyYield(0.0, "inverters"))

    def test_yield_ignores_a_non_gap_sample_without_power(self) -> None:
        samples = SOL08_SAMPLES + [Sample(INV1, ten(15), 900.0, None, False)]
        self.assertEqual(energy_yield("OAHE", None, samples, []), EnergyYield(11.4167, "inverters"))

    def test_open_faults_count_only_when_opened_inside_the_period(self) -> None:
        period = Period(DAY, DAY + timedelta(hours=24))
        for opened, expected_open in ((0.0, 1), (-1.0, 0), (24.0, 0), (23.9, 1)):
            faults = hour_faults([("INV-001", 1, opened, None)])
            self.assertEqual(mtbf_mttr(AssetKind.INVERTER, fleet_of(1), period, faults).open, expected_open, opened)

    def test_a_fault_on_an_asset_outside_the_fleet_is_left_out(self) -> None:
        period = Period(DAY, DAY + timedelta(hours=24))
        faults = hour_faults([("INV-001", 3, 1.0, 2.0), ("INV-001", 1, 1.0, 3.0)])
        self.assertEqual(mtbf_mttr(AssetKind.INVERTER, fleet_of(1), period, faults), Reliability(22.0, 2.0, 1, 0))

    def test_reliability_of_the_site_kind_counts_sites(self) -> None:
        period = Period(DAY, DAY + timedelta(hours=24))
        faults = hour_faults([("SIT-001", "site", 1.0, 4.0), ("INV-001", 1, 1.0, 2.0)])
        self.assertEqual(mtbf_mttr(AssetKind.SITE, fleet_of(2), period, faults), Reliability(21.0, 3.0, 1, 0))

    def test_rounded_keeps_four_places(self) -> None:
        self.assertEqual(rounded(11.416666), 11.4167)
        self.assertEqual(rounded(0.91333), 0.9133)
