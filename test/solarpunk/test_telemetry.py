"""Synthetic SCADA holds its shape: the clear-sky bell, the power formula, every expected instant present with gaps as
gap() samples (SOL-06), the same seed giving the byte-identical one-day golden (SOL-02), and the samples table."""
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path

from solarpunk.leaf import store as leaf_store
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import Period, at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample, gap
from solarpunk.telemetry import generate as gen
from solarpunk.telemetry import samples

GOLDEN = Path(__file__).resolve().parent / "goldens" / "telemetry-seed7.txt"
DAY = Period(at(2026, 6, 1), at(2026, 6, 2))


def inverter(asset_id: str, rated_kw: float | None = 100.0) -> Asset:
    """An inverter for a test: inverter("OAHE-INV-002").rated_kw is 100.0."""
    return Asset(asset_id, AssetKind.INVERTER, "OAHE", None, asset_id, rated_kw)


def database() -> sqlite3.Connection:
    """An in-memory store with the samples table: database().execute("SELECT count(*) FROM samples") gives 0."""
    connection = leaf_store.connect()
    leaf_store.apply(connection, samples.schema())
    return connection


class TheBell(unittest.TestCase):
    def test_irradiance_is_zero_at_night(self) -> None:
        for hour, minute in ((0, 0), (5, 55), (6, 0), (20, 0), (20, 5), (23, 55)):
            self.assertEqual(gen.irradiance(at(2026, 6, 1, hour, minute)), 0.0, (hour, minute))

    def test_irradiance_peaks_at_1000_at_13_00(self) -> None:
        self.assertEqual(gen.irradiance(at(2026, 6, 1, 13, 0)), 1000.0)
        self.assertLess(gen.irradiance(at(2026, 6, 1, 12, 55)), 1000.0)
        self.assertLess(gen.irradiance(at(2026, 6, 1, 13, 5)), 1000.0)

    def test_irradiance_by_hand(self) -> None:
        # sin(π/4) = 0.70711 at 09:30 and 16:30; sin(π × (1/12) / 14) = 0.018699 at 06:05
        self.assertEqual(gen.irradiance(at(2026, 6, 1, 9, 30)), 707.1)
        self.assertEqual(gen.irradiance(at(2026, 6, 1, 16, 30)), 707.1)
        self.assertEqual(gen.irradiance(at(2026, 6, 1, 6, 5)), 18.7)
        self.assertEqual(gen.irradiance(at(2026, 6, 1, 19, 55)), 18.7)


class ThePower(unittest.TestCase):
    def test_power_by_hand(self) -> None:
        self.assertEqual(gen.power(100.0, 1000.0, 1.0), 92.0)
        self.assertEqual(gen.power(100.0, 707.1, 1.0), 65.05)
        self.assertEqual(gen.power(250.0, 500.0, 0.97), 111.55)
        self.assertEqual(gen.power(100.0, 0.0, 1.03), 0.0)

    def test_an_inverter_without_a_rating_is_refused(self) -> None:
        with self.assertRaises(ValueError) as refused:
            gen.generate((inverter("OAHE-INV-009", None),), DAY, 7)
        self.assertEqual(str(refused.exception), "OAHE-INV-009: an inverter with no rated_kw cannot be simulated")
        self.assertEqual(gen.rating(inverter("OAHE-INV-009", 42.5)), 42.5)


class TheGenerator(unittest.TestCase):
    def test_every_expected_instant_is_present_in_asset_then_time_order(self) -> None:
        sensor = Asset("OAHE-SEN-001", AssetKind.SENSOR, "OAHE", None, "Pyranometer", None)
        made = gen.generate((inverter("OAHE-INV-002"), sensor, inverter("OAHE-INV-001")), DAY, 7)
        self.assertEqual(len(made), 2 * 288)
        self.assertEqual([s.asset_id for s in made], ["OAHE-INV-001"] * 288 + ["OAHE-INV-002"] * 288)
        self.assertEqual([s.at for s in made], DAY.instants() * 2)

    def test_gaps_are_gap_samples_at_about_two_percent(self) -> None:
        fleet = tuple(inverter(f"OAHE-INV-{n:03d}") for n in range(1, 21))
        made = gen.generate(fleet, DAY, 7)
        gaps = [s for s in made if s.gap]
        self.assertTrue(all(s == gap(s.asset_id, s.at) for s in gaps))
        self.assertGreater(len(gaps) / len(made), 0.01)
        self.assertLess(len(gaps) / len(made), 0.03)

    def test_readings_follow_the_bell_with_jitter_within_three_percent(self) -> None:
        made = [s for s in gen.generate((inverter("OAHE-INV-001"),), DAY, 7) if not s.gap]
        for sample in made:
            self.assertEqual(sample.irradiance_w_m2, gen.irradiance(sample.at))
            plain = 100.0 * (sample.irradiance_w_m2 or 0.0) / 1000 * 0.92
            self.assertLessEqual(abs((sample.power_kw or 0.0) - plain), plain * 0.03 + 0.005, sample)
        self.assertGreater(len({s.power_kw for s in made if s.irradiance_w_m2 == 707.1}), 1)

    def test_the_draws_are_gap_then_jitter_at_every_instant(self) -> None:
        rng = random.Random(7)
        expected = []
        for moment in DAY.instants():
            missing = rng.random() < 0.02
            jitter = 1 + rng.uniform(-0.03, 0.03)
            light = gen.irradiance(moment)
            reading = Sample("OAHE-INV-001", moment, light, gen.power(100.0, light, jitter), False)
            expected.append(gap("OAHE-INV-001", moment) if missing else reading)
        self.assertEqual(gen.generate((inverter("OAHE-INV-001"),), DAY, 7), tuple(expected))

    def test_the_same_seed_gives_the_same_samples_and_another_seed_others(self) -> None:
        fleet = (inverter("OAHE-INV-001"),)
        self.assertEqual(gen.generate(fleet, DAY, 7), gen.generate(fleet, DAY, 7))
        self.assertNotEqual(gen.generate(fleet, DAY, 7), gen.generate(fleet, DAY, 8))
        self.assertEqual(gen.asset_key(inverter("OAHE-INV-004")), "OAHE-INV-004")


class TheGolden(unittest.TestCase):
    def test_the_golden_regenerates_byte_for_byte(self) -> None:
        self.assertEqual(gen.golden_text(7).encode("utf-8"), GOLDEN.read_bytes())

    def test_the_golden_is_one_day_of_one_inverter_with_its_peak_and_gaps(self) -> None:
        lines = GOLDEN.read_text().splitlines()
        self.assertEqual(len(lines), 288)
        self.assertEqual(lines[156], "OAHE-INV-001\t2026-06-01T13:00:00+00:00\t1000.0\t91.62\tFalse")
        self.assertEqual(lines[0], "OAHE-INV-001\t2026-06-01T00:00:00+00:00\t0.0\t0.0\tFalse")
        self.assertIn("OAHE-INV-001\t2026-06-01T10:40:00+00:00\tNone\tNone\tTrue", lines)

    def test_the_command_writes_the_golden_identically_twice(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            first = gen.main(["--seed", "7"], Path(folder)).read_bytes()
            target = gen.main(["--seed", "7"], Path(folder))
            self.assertEqual(target, Path(folder) / "telemetry-seed7.txt")
            self.assertEqual(target.read_bytes(), first)
            self.assertEqual(first, GOLDEN.read_bytes())

    def test_the_command_requires_a_seed(self) -> None:
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(SystemExit):
            gen.main([], Path(folder))

    def test_the_command_writes_to_the_test_goldens_folder(self) -> None:
        self.assertEqual(gen.GOLDENS, GOLDEN.parent)


class TheTable(unittest.TestCase):
    def test_a_day_round_trips_gaps_included(self) -> None:
        connection = database()
        made = gen.generate((inverter("OAHE-INV-001"), inverter("OAHE-INV-002")), DAY, 7)
        samples.store(connection, made)
        self.assertEqual(samples.in_period(connection, "OAHE-INV-001", DAY), made[:288])
        self.assertEqual(samples.in_period(connection, "OAHE-INV-002", DAY), made[288:])

    def test_a_period_is_half_open_and_in_time_order(self) -> None:
        connection = database()
        made = gen.generate((inverter("OAHE-INV-001"),), DAY, 7)
        samples.store(connection, tuple(reversed(made)))
        hour = samples.in_period(connection, "OAHE-INV-001", Period(at(2026, 6, 1, 10), at(2026, 6, 1, 11)))
        self.assertEqual([s.at for s in hour], [at(2026, 6, 1, 10, 5 * n) for n in range(12)])
        self.assertEqual(hour, made[120:132])

    def test_a_gap_comes_back_as_a_gap(self) -> None:
        connection = database()
        samples.store(connection, (gap("OAHE-INV-001", at(2026, 6, 1, 10, 20)),))
        (back,) = samples.in_period(connection, "OAHE-INV-001", DAY)
        self.assertIs(back.gap, True)
        self.assertIsNone(back.irradiance_w_m2)
        self.assertIsNone(back.power_kw)
        self.assertEqual(samples.row(back), ("OAHE-INV-001", "2026-06-01T10:20:00+00:00", None, None, 1))

    def test_a_reading_comes_back_with_its_values(self) -> None:
        connection = database()
        reading = Sample("OAHE-INV-001", at(2026, 6, 1, 13), 1000.0, 91.62, False)
        samples.store(connection, (reading,))
        (back,) = samples.in_period(connection, "OAHE-INV-001", DAY)
        self.assertIs(back.gap, False)
        self.assertEqual(back, reading)

    def test_a_second_sample_at_one_instant_is_refused(self) -> None:
        connection = database()
        samples.store(connection, (gap("OAHE-INV-001", at(2026, 6, 1, 10)),))
        with self.assertRaises(sqlite3.IntegrityError):
            samples.store(connection, (gap("OAHE-INV-001", at(2026, 6, 1, 10)),))
        samples.store(connection, (gap("OAHE-INV-002", at(2026, 6, 1, 10)),))

    def test_the_table_has_its_columns_as_declared(self) -> None:
        connection = database()
        names = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        self.assertEqual(names, ["samples"])
        columns = [tuple(r)[1:] for r in connection.execute("PRAGMA table_info(samples)")]
        self.assertEqual(columns, [
            ("asset_id", "TEXT", 1, None, 1),
            ("at", "TEXT", 1, None, 2),
            ("irradiance_w_m2", "REAL", 0, None, 0),
            ("power_kw", "REAL", 0, None, 0),
            ("gap", "INTEGER", 1, None, 0),
        ])

    def test_a_null_gap_flag_is_refused_by_the_table(self) -> None:
        connection = database()
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO samples VALUES ('OAHE-INV-001', 'x', NULL, NULL, NULL)")

    def test_stored_samples_are_committed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fleet.db"
            writer = leaf_store.connect(path)
            leaf_store.apply(writer, samples.schema())
            samples.store(writer, (gap("OAHE-INV-001", at(2026, 6, 1, 10)),))
            reader = leaf_store.connect(path)
            self.assertEqual(len(samples.in_period(reader, "OAHE-INV-001", DAY)), 1)
            writer.close()
            reader.close()
