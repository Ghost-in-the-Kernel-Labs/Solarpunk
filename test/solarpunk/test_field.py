"""Field telemetry (12.6, SP-036) on a hand-written sample in PVDAQ's exact CSV format (test/fixtures/pvdaq/: real
column names, invented values, so no file of the dataset enters the repository, C-033): the loader's mapping, its gaps
(a missing row, an empty cell, a word, a sentinel; never a zero, SOL-06), its skipped stamps (off the grid, a second
row for one stamp), the load into the store, the day-at-a-time baseline that records nothing, and the two commands."""
import gc
import io
import json
import shutil
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from solarpunk import project
from solarpunk.cli.main import main
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample, gap
from solarpunk.project.field import DayResult, Tally, days, tallies
from solarpunk.telemetry import field

SAMPLE = Path(__file__).resolve().parents[1] / "fixtures" / "pvdaq"
DAY = date(2023, 2, 1)


def instant(minute: int) -> datetime:
    """The sample's local 10:<minute> on 1 February 2023, in UTC: timezone_code 7 makes it 17:<minute>Z."""
    return at(2023, 2, 1, 17, minute)


class TheMapping(unittest.TestCase):
    def setUp(self) -> None:
        """The sample read: its site PV1, two stations, two inverters."""
        self.export = field.read(SAMPLE)

    def test_the_site_stations_and_inverters_are_named_from_the_export(self) -> None:
        found = {asset.asset_id: asset for asset in self.export.assets}
        self.assertEqual(list(found), ["PV1-SIT-001", "PV1-SEN-001", "PV1-SEN-002", "PV1-INV-001", "PV1-INV-002"])
        self.assertEqual(found["PV1-SIT-001"].name, "hand-written sample (PVDAQ 1)")
        self.assertEqual(found["PV1-SIT-001"].location, "Nowhere, CO")
        self.assertEqual(found["PV1-SEN-001"].kind, AssetKind.SENSOR)
        self.assertEqual(found["PV1-SEN-002"].name, "pyranometer_(class_a)_pad_2_poa_irradiance_(w/m2)_o_149725")
        self.assertEqual(found["PV1-INV-001"].name, "inverter_1_ac_power_(kw)_inv_150143")
        self.assertEqual((found["PV1-INV-001"].rated_kw, found["PV1-INV-002"].rated_kw), (1000.0, None))
        self.assertTrue(all(asset.host is None and asset.port is None for asset in found.values()))
        self.assertTrue(all(asset.parent_id == "PV1-SIT-001" for asset in self.export.assets[1:]))

    def test_another_site_code_can_be_given(self) -> None:
        self.assertEqual(field.read(SAMPLE, "FIELD").assets[0].asset_id, "FIELD-SIT-001")

    def test_local_stamps_become_utc_and_the_span_ends_after_the_last(self) -> None:
        self.assertEqual((self.export.start, self.export.end), (instant(0), instant(30)))

    def test_a_stamp_off_the_grid_and_a_second_row_are_skipped_and_counted(self) -> None:
        power = self.export.tables["1_ac_power_data.csv"]
        self.assertEqual((power.off_grid, power.duplicates), (1, 1))
        self.assertEqual(power.rows[instant(10)]["inverter_1_ac_power_(kw)_inv_150143"], "0.0")

    def test_values_and_gaps(self) -> None:
        self.assertEqual(field.value("812.5"), 812.5)
        self.assertEqual(field.value("0.0"), 0.0)
        for cell in ("", "  ", None, "NaN", "inf", "n/a", "32767", "-32768", "65535"):
            with self.subTest(cell=cell):
                self.assertIsNone(field.value(cell))


class TheSamples(unittest.TestCase):
    def setUp(self) -> None:
        """Each channel's samples by asset id: self.made["PV1-INV-001"] is six samples, 17:00Z to 17:25Z."""
        self.export = field.read(SAMPLE)
        self.made = {channel.asset.asset_id: field.samples(self.export, channel) for channel in self.export.channels}

    def test_every_instant_of_the_span_is_present(self) -> None:
        for asset_id, made in self.made.items():
            with self.subTest(asset_id=asset_id):
                self.assertEqual([sample.moment for sample in made], [instant(minute) for minute in range(0, 30, 5)])

    def test_inverter_1_carries_pad_1s_irradiance_and_its_gaps_are_never_zeros(self) -> None:
        inverter = "PV1-INV-001"
        self.assertEqual(self.made[inverter], (
            Sample(inverter, instant(0), 600.0, 900.0, False),
            gap(inverter, instant(5)),  # an empty cell
            Sample(inverter, instant(10), None, 0.0, False),  # a zero is a reading; the station had no row then
            gap(inverter, instant(15)),  # no row
            Sample(inverter, instant(20), -3.0, 905.0, False),
            Sample(inverter, instant(25), 610.0, 906.0, False),
        ))

    def test_inverter_n_carries_the_irradiance_of_pad_ns_station(self) -> None:
        """SP-039, J-101's cause G: inverter 2 reads pad 2's pyranometer (PV1-SEN-002), not the first station's."""
        inverter = "PV1-INV-002"
        self.assertEqual(self.made[inverter][:3], (
            Sample(inverter, instant(0), 610.0, 880.0, False),
            Sample(inverter, instant(5), 612.0, 881.0, False),
            Sample(inverter, instant(10), None, 883.0, False),  # pad 2's station has no row then
        ))
        self.assertEqual(field.station_for(self.export, self.export.channels[3]).asset.asset_id, "PV1-SEN-002")

    def test_with_no_station_named_for_its_pad_an_inverter_reads_the_first(self) -> None:
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        folder = Path(made.name)
        for name in ("1_system_metadata.json", "1_ac_power_data.csv"):
            shutil.copy(SAMPLE / name, folder)
        text = (SAMPLE / "1_irradiance_data.csv").read_text(encoding="utf-8")
        (folder / "1_irradiance_data.csv").write_text(text.replace("_pad_2_", "_cell_2_"), encoding="utf-8")
        export = field.read(folder)
        inverter = next(channel for channel in export.channels if channel.asset.asset_id == "PV1-INV-002")
        self.assertEqual(field.station_for(export, inverter).asset.asset_id, "PV1-SEN-001")
        self.assertEqual(field.samples(export, inverter)[0], Sample("PV1-INV-002", instant(0), 600.0, 880.0, False))

    def test_a_sentinel_and_a_word_are_gaps(self) -> None:
        self.assertEqual([sample.gap for sample in self.made["PV1-INV-002"]], [False, False, False, True, True, True])

    def test_a_station_carries_its_own_irradiance_and_no_power(self) -> None:
        station = self.made["PV1-SEN-002"]
        self.assertEqual(station[0], Sample("PV1-SEN-002", instant(0), 610.0, None, False))
        self.assertEqual([sample.gap for sample in station], [False, False, True, True, False, False])
        self.assertEqual(station[4].irradiance_w_m2, 1600.0)  # loaded as read; the tests judge it


class TheRefusals(unittest.TestCase):
    def folder(self) -> Path:
        """A new empty folder, removed after the test: folder().iterdir() yields nothing."""
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        return Path(made.name)

    def test_a_folder_without_one_metadata_file_is_refused(self) -> None:
        with self.assertRaisesRegex(field.FieldError, "0 \\*_system_metadata.json files"):
            field.read(self.folder())

    def test_a_csv_without_its_stamp_column_is_refused(self) -> None:
        folder = self.folder()
        shutil.copy(SAMPLE / "1_system_metadata.json", folder)
        (folder / "1_bad.csv").write_text("time,inverter_1_ac_power_(kw)_inv_1\n", encoding="utf-8")
        with self.assertRaisesRegex(field.FieldError, "no measured_on column"):
            field.read(folder)

    def test_metadata_without_its_time_zone_is_refused(self) -> None:
        folder = self.folder()
        shutil.copy(SAMPLE / "1_ac_power_data.csv", folder)
        (folder / "1_system_metadata.json").write_text(json.dumps({"System": {"system_id": 1}}), encoding="utf-8")
        with self.assertRaisesRegex(field.FieldError, "timezone_code"):
            field.read(folder)

    def test_a_folder_with_no_channel_is_refused(self) -> None:
        folder = self.folder()
        shutil.copy(SAMPLE / "1_system_metadata.json", folder)
        (folder / "1_meter.csv").write_text("measured_on,meter_ac_power_(kw)_meter_1\n", encoding="utf-8")
        with self.assertRaisesRegex(field.FieldError, "no inverter power"):
            field.read(folder)


class TheBaseline(unittest.TestCase):
    def setUp(self) -> None:
        """An in-memory store with the sample loaded: five assets, 24 samples."""
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        self.loaded = project.load_field(self.conn, SAMPLE)

    def test_the_load_registers_the_assets_and_stores_every_sample(self) -> None:
        self.assertEqual(self.loaded, project.Loaded("PV1", 5, 24, 8, 1, 1))
        self.assertEqual(len(project.fleet_assets(self.conn, "PV1")), 5)

    def test_loading_twice_is_refused(self) -> None:
        with self.assertRaises(project.RegistryError):
            project.load_field(self.conn, SAMPLE)

    def test_each_test_that_applies_runs_each_day_and_nothing_is_recorded(self) -> None:
        found = project.field_baseline(self.conn, DAY, date(2023, 2, 2))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM results").fetchone()[0], 0)
        per_kind = {"SEN": 3, "INV": 8}  # records_stored, on_grid, irradiance_in_range; and the inverter's eight (power_ripple says no data)
        self.assertEqual(len(found.results), 2 * (2 * per_kind["SEN"] + 2 * per_kind["INV"]))
        tally = {(t.test, t.asset_id): (t.days_run, t.days_alarmed) for t in found.tallies}
        self.assertEqual(tally[("records_stored", "PV1-INV-001")], (2, 1))  # the second day has no samples
        self.assertEqual(tally[("night_power_near_zero", "PV1-INV-001")], (2, 1))  # 905 kW under -3 W/m2
        self.assertEqual(tally[("performance_above_floor", "PV1-INV-001")], (2, 0))
        self.assertEqual(tally[("power_under_rated", "PV1-INV-002")], (2, 2))  # no rating
        self.assertEqual(tally[("irradiance_in_range", "PV1-SEN-002")], (2, 1))

    def test_an_alarm_carries_the_tests_message(self) -> None:
        alarms = project.field_baseline(self.conn, DAY, DAY).alarms()
        self.assertIn(DayResult("irradiance_in_range", "PV1-SEN-002", DAY, False,
                                "2023-02-01T17:20:00+00:00: irradiance 1600.0 W/m2 out of range"), alarms)
        self.assertNotIn("records_stored", {alarm.test for alarm in alarms})


class TheDays(unittest.TestCase):
    def test_both_ends_are_included_and_a_reversed_pair_is_refused(self) -> None:
        self.assertEqual(days(DAY, date(2023, 2, 3)), (DAY, date(2023, 2, 2), date(2023, 2, 3)))
        with self.assertRaises(ValueError):
            days(date(2023, 2, 3), DAY)

    def test_tallies_count_days_run_and_alarmed(self) -> None:
        results = (DayResult("on_grid", "A", DAY, True, "ok"), DayResult("on_grid", "A", date(2023, 2, 2), False, "x"))
        self.assertEqual(tallies(results), (Tally("on_grid", "A", 2, 1),))


class TheCommands(unittest.TestCase):
    def setUp(self) -> None:
        """A path for a new store, field.db, in a folder removed after the test. Garbage is collected first, as in
        test_cli_tests: a store an earlier test file left unclosed warns when collected, into the CLI's captured stderr."""
        gc.collect()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "field.db")

    def run_cli(self, words: list[str]) -> tuple[int, str, str]:
        """One command: (exit code, out, err), e.g. (0, "loaded PV1: …\n", "")."""
        out, err = io.StringIO(), io.StringIO()
        code = main(words, out, err)
        return code, out.getvalue(), err.getvalue()

    def test_load_then_baseline(self) -> None:
        loaded = self.run_cli(["field", "load", str(SAMPLE), "--db", self.db])
        self.assertEqual(loaded, (0, "loaded PV1: 5 assets, 24 samples, 8 gaps; skipped 1 off the grid,"
                                     " 1 duplicate stamps\n", ""))
        code, out, _ = self.run_cli(["field", "baseline", "--from", "2023-02-01", "--to", "2023-02-01", "--db", self.db])
        lines = out.splitlines()
        self.assertEqual(code, 0)
        self.assertIn("irradiance_in_range  PV1-SEN-002  days 1  alarmed 1", lines)
        self.assertIn("alarm irradiance_in_range  PV1-SEN-002  2023-02-01  2023-02-01T17:20:00+00:00: irradiance"
                      " 1600.0 W/m2 out of range", lines)

    def test_a_folder_that_is_no_export_is_an_error(self) -> None:
        code, _, err = self.run_cli(["field", "load", str(SAMPLE.parent / "broken"), "--db", self.db])
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("error: "))
