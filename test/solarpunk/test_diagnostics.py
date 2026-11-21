"""The inverter diagnostics (6.2): irradiance_in_range, night_power_near_zero, performance_above_floor and
power_not_frozen, each passing and failing as its docstring says, each at its threshold's edge, and each passing on a
synthetic day the generator makes, so a healthy simulated inverter stays green."""
import unittest
from datetime import datetime, timedelta

from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import Period, at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample, gap
from solarpunk.remote.results import Result
from solarpunk.remote.tests import irradiance_in_range, night_power_near_zero, performance_above_floor, power_not_frozen
from solarpunk.telemetry import generate

INV = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 1", 100.0)
SEN = Asset("OAHE-SEN-001", AssetKind.SENSOR, "OAHE", None, "Weather station", None)
UNRATED = Asset("OAHE-INV-009", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 9", None)
T0 = at(2026, 6, 1, 10, 0)
T1 = at(2026, 6, 1, 10, 5)
NIGHT = at(2026, 6, 1, 2, 0)


def reading(asset: Asset, moment: datetime, irradiance: float | None, power: float | None) -> Sample:
    """A non-gap sample: reading(INV, T0, 800.0, 60.0).power_kw is 60.0."""
    return Sample(asset.asset_id, moment, irradiance, power, False)


def steady(power: float, count: int) -> tuple[Sample, ...]:
    """count records from 10:00 five minutes apart, all at one power: steady(50.0, 6)[-1].at is 10:25."""
    return tuple(reading(INV, T0 + timedelta(minutes=5 * i), 800.0, power) for i in range(count))


class IrradianceInRange(unittest.TestCase):
    def test_the_docstrings_cases(self) -> None:
        good = (reading(INV, T0, 0.0, 0.0), reading(INV, T1, 980.0, 80.0), gap(INV.asset_id, at(2026, 6, 1, 10, 10)))
        self.assertEqual(irradiance_in_range.run(INV, good), Result(True, "2 irradiance readings in range"))
        self.assertEqual(irradiance_in_range.run(SEN, (reading(SEN, T1, 1600.0, None),)),
                         Result(False, "2026-06-01T10:05:00+00:00: irradiance 1600.0 W/m2 out of range"))

    def test_the_edges_of_the_list(self) -> None:
        self.assertTrue(irradiance_in_range.run(SEN, (reading(SEN, T0, 1500.0, None),)).passed)
        self.assertTrue(irradiance_in_range.run(SEN, (reading(SEN, T0, -5.0, None),)).passed)  # SP-039, J-101
        self.assertFalse(irradiance_in_range.run(SEN, (reading(SEN, T0, -5.1, None),)).passed)


class NightPowerNearZero(unittest.TestCase):
    def test_the_docstrings_cases(self) -> None:
        self.assertEqual(night_power_near_zero.run(INV, (reading(INV, NIGHT, 0.0, 0.4),)),
                         Result(True, "1 night records near zero"))
        self.assertEqual(night_power_near_zero.run(INV, (reading(INV, NIGHT, 0.0, 3.0),)),
                         Result(False, "2026-06-01T02:00:00+00:00: 3.0 kW at night, over 1.0 kW"))
        self.assertEqual(night_power_near_zero.run(UNRATED, ()), Result(False, "no rating"))

    def test_the_edges(self) -> None:
        self.assertTrue(night_power_near_zero.run(INV, (reading(INV, NIGHT, 5.0, 1.0),)).passed)
        self.assertEqual(night_power_near_zero.run(INV, (reading(INV, T0, 5.1, 50.0),)),
                         Result(True, "0 night records near zero"))


class PerformanceAboveFloor(unittest.TestCase):
    def test_the_docstrings_cases(self) -> None:
        self.assertEqual(performance_above_floor.run(INV, (reading(INV, T0, 800.0, 72.0),)),
                         Result(True, "ratio 0.9 over 1 daylight records"))
        self.assertEqual(performance_above_floor.run(INV, (reading(INV, T0, 800.0, 40.0),)),
                         Result(False, "ratio 0.5 under the floor 0.75 over 1 daylight records"))
        self.assertEqual(performance_above_floor.run(INV, (reading(INV, T0, 100.0, 1.0),)),
                         Result(True, "no daylight records"))
        self.assertEqual(performance_above_floor.run(UNRATED, ()), Result(False, "no rating"))

    def test_the_floor_itself_passes_and_dusk_does_not_decide(self) -> None:
        self.assertTrue(performance_above_floor.run(INV, (reading(INV, T0, 800.0, 60.0),)).passed)
        dusk = (reading(INV, T0, 800.0, 72.0), reading(INV, T1, 150.0, 0.0))
        self.assertEqual(performance_above_floor.run(INV, dusk), Result(True, "ratio 0.9 over 1 daylight records"))


class PowerNotFrozen(unittest.TestCase):
    def test_the_docstrings_cases(self) -> None:
        moving = (reading(INV, T0, 800.0, 50.0), reading(INV, T1, 810.0, 51.2),
                  reading(INV, at(2026, 6, 1, 10, 10), 790.0, 49.8))
        self.assertEqual(power_not_frozen.run(INV, moving), Result(True, "3 power records, none frozen"))
        self.assertEqual(power_not_frozen.run(INV, steady(50.0, 6)),
                         Result(False, "power 50.0 kW unchanged on 6 records from 2026-06-01T10:00:00+00:00"))

    def test_five_in_a_row_and_zero_at_night_pass(self) -> None:
        self.assertTrue(power_not_frozen.run(INV, steady(50.0, 5)).passed)
        self.assertTrue(power_not_frozen.run(INV, steady(0.0, 12)).passed)

    def test_a_frozen_run_after_a_moving_one_and_out_of_order(self) -> None:
        records = (reading(INV, at(2026, 6, 1, 9, 55), 800.0, 48.0), *steady(50.0, 6))
        self.assertFalse(power_not_frozen.run(INV, tuple(reversed(records))).passed)


class AHealthyDay(unittest.TestCase):
    def test_every_diagnostic_passes_on_the_generators_day(self) -> None:
        day = Period(at(2026, 6, 1), at(2026, 6, 2))
        samples = tuple(generate.generate((INV,), day, 7))
        for module in (irradiance_in_range, night_power_near_zero, performance_above_floor, power_not_frozen):
            with self.subTest(test=module.__name__):
                self.assertTrue(module.run(INV, samples).passed, module.run(INV, samples).reason)


if __name__ == "__main__":
    unittest.main()
