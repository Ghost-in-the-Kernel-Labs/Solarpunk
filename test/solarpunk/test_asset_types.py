"""The asset maintenance list as the leaf loads it: every kind present, ranges exact at their ends, outsiders refused."""
import json
import unittest

from solarpunk.leaf import asset_types
from solarpunk.leaf.asset_types import AssetType, FieldRange, UnknownAssetType, UnknownField
from solarpunk.leaf.codes import AssetKind

METER = {"kind": "METER", "description": "d", "fields": {"energy_kwh": {"unit": "kWh", "min": 0, "max": None}},
         "tests": ["records_stored"], "passing": "p"}


class TheList(unittest.TestCase):
    def test_every_kind_loads_in_the_files_order(self) -> None:
        self.assertEqual(asset_types.kinds(), tuple(AssetKind))
        for kind in AssetKind:
            entry = asset_types.asset_type(kind)
            self.assertIs(entry.kind, kind)
            self.assertTrue(entry.description.strip() and entry.passing.strip(), kind)

    def test_the_json_names_only_asset_kinds_once_each(self) -> None:
        names = [raw["kind"] for raw in json.loads(asset_types.LIST_FILE.read_text(encoding="utf-8"))]
        self.assertEqual(sorted(names), sorted(kind.name for kind in AssetKind))

    def test_kinds_with_no_feed_have_no_fields_and_no_tests(self) -> None:
        for kind in (AssetKind.SITE, AssetKind.STRING):
            self.assertEqual(asset_types.fields_of(kind), {})
            self.assertEqual(asset_types.asset_type(kind).tests, ())

    def test_the_fields_each_kind_answers_with(self) -> None:
        self.assertEqual(sorted(asset_types.fields_of(AssetKind.INVERTER)), ["irradiance_w_m2", "power_kw", "temperature_c"])
        self.assertEqual(asset_types.fields_of(AssetKind.TRACKER), {"angle_deg": FieldRange("deg", -60, 60)})
        self.assertEqual(asset_types.fields_of(AssetKind.METER), {"energy_kwh": FieldRange("kWh", 0, None)})
        self.assertEqual(sorted(asset_types.fields_of(AssetKind.SENSOR)), ["irradiance_w_m2", "temperature_c"])

    def test_the_tests_each_kind_runs(self) -> None:
        self.assertEqual(asset_types.asset_type(AssetKind.TRACKER).tests, ("records_stored", "on_grid", "tracker_moving"))
        self.assertEqual(asset_types.asset_type(AssetKind.METER).tests, ("records_stored", "on_grid", "energy_monotonic"))
        self.assertIn("power_under_rated", asset_types.asset_type(AssetKind.INVERTER).tests)

    def test_fields_of_is_a_copy(self) -> None:
        asset_types.fields_of(AssetKind.TRACKER).clear()
        self.assertEqual(len(asset_types.fields_of(AssetKind.TRACKER)), 1)


class TheRanges(unittest.TestCase):
    def test_both_ends_are_included(self) -> None:
        self.assertTrue(asset_types.in_range(AssetKind.TRACKER, "angle_deg", -60))
        self.assertTrue(asset_types.in_range(AssetKind.TRACKER, "angle_deg", 60))
        self.assertFalse(asset_types.in_range(AssetKind.TRACKER, "angle_deg", -60.5))
        self.assertFalse(asset_types.in_range(AssetKind.TRACKER, "angle_deg", 60.5))

    def test_irradiance_bounds(self) -> None:
        self.assertTrue(asset_types.in_range(AssetKind.SENSOR, "irradiance_w_m2", 1500))
        self.assertFalse(asset_types.in_range(AssetKind.SENSOR, "irradiance_w_m2", 1501))
        for kind in (AssetKind.INVERTER, AssetKind.SENSOR):  # SP-039: J-101's night offsets, to -4.39 W/m2, hold
            self.assertTrue(asset_types.in_range(kind, "irradiance_w_m2", -5))
            self.assertFalse(asset_types.in_range(kind, "irradiance_w_m2", -5.01))

    def test_a_null_max_is_unbounded_above(self) -> None:
        self.assertTrue(asset_types.in_range(AssetKind.METER, "energy_kwh", 1e12))
        self.assertTrue(asset_types.in_range(AssetKind.METER, "energy_kwh", 0))
        self.assertFalse(asset_types.in_range(AssetKind.METER, "energy_kwh", -0.001))

    def test_holds_at_the_ends(self) -> None:
        self.assertTrue(FieldRange("°C", -40, 90).holds(-40))
        self.assertTrue(FieldRange("°C", -40, 90).holds(90))
        self.assertFalse(FieldRange("°C", -40, 90).holds(-41))
        self.assertFalse(FieldRange("°C", -40, 90).holds(91))


class TheRefusals(unittest.TestCase):
    def test_a_kind_the_list_lacks_is_refused(self) -> None:
        with self.assertRaisesRegex(UnknownAssetType, "'PANEL' is not in the asset maintenance list"):
            asset_types.asset_type("PANEL")  # type: ignore[arg-type]

    def test_a_field_the_kind_lacks_is_refused(self) -> None:
        with self.assertRaisesRegex(UnknownField, "^TRACKER has no field power_kw$"):
            asset_types.in_range(AssetKind.TRACKER, "power_kw", 1)

    def test_a_list_entry_naming_no_kind_is_refused(self) -> None:
        with self.assertRaisesRegex(UnknownAssetType, "^'PANEL' is not an asset kind$"):
            asset_types.load(json.dumps([dict(METER, kind="PANEL")]))

    def test_a_kind_listed_twice_is_refused(self) -> None:
        with self.assertRaisesRegex(UnknownAssetType, "^METER is listed twice$"):
            asset_types.load(json.dumps([METER, METER]))

    def test_both_refusals_are_value_errors(self) -> None:
        self.assertTrue(issubclass(UnknownAssetType, ValueError))
        self.assertTrue(issubclass(UnknownField, ValueError))


class TheLoader(unittest.TestCase):
    def test_an_entry_loads_whole(self) -> None:
        loaded = asset_types.load(json.dumps([METER]))
        self.assertEqual(loaded, {AssetKind.METER: AssetType(
            AssetKind.METER, "d", {"energy_kwh": FieldRange("kWh", 0, None)}, ("records_stored",), "p")})

    def test_a_bounded_field_keeps_its_max(self) -> None:
        tracker = dict(METER, kind="TRACKER", fields={"angle_deg": {"unit": "deg", "min": -60, "max": 60}})
        loaded = asset_types.load(json.dumps([tracker]))[AssetKind.TRACKER]
        self.assertEqual(loaded.fields, {"angle_deg": FieldRange("deg", -60, 60)})

    def test_an_empty_list_loads_empty(self) -> None:
        self.assertEqual(asset_types.load("[]"), {})
