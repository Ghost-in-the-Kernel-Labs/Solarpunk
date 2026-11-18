"""The asset maintenance list and its JSON hold together; the planted breaks of each kind are caught (TODO 2.1, C-013)."""
import json
import unittest

from scripts.checks import asset_types
from test.support import BROKEN, ROOT, scratch

KINDS: tuple[str, ...] = ("SITE", "INVERTER", "STRING", "TRACKER", "METER", "SENSOR")
TABLE = "| Field | Unit | Min | Max |\n| --- | --- | --- | --- |\n"
TRACKER_ROW = "| angle_deg | deg | -60 | 60 |\n"
ANGLE = {"angle_deg": {"unit": "deg", "min": -60, "max": 60}}


def section(kind: str, body: str) -> str:
    """One document section: section("SITE", "Tests: none.\\n") is "## SITE\\n\\nTests: none.\\n\\n"."""
    return f"## {kind}\n\n{body}\n"


def tree(tracker_body: str, tracker_entry: dict, kinds: tuple[str, ...] = KINDS) -> list[str]:
    """The check's problems for a scratch tree whose document and JSON hold every kind with no feed but TRACKER, given
    its section body and JSON entry, both sides listing only `kinds`: tree("Tests: none.\\n", {}) gives []."""
    root = scratch()
    document = "# List\n\n" + "".join(section(k, tracker_body if k == "TRACKER" else "Tests: none.\n") for k in kinds)
    (root / "docs" / "ASSET-MAINTENANCE-LIST.md").write_text(document)
    entries = [{"kind": k, "fields": {}, "tests": [], **(tracker_entry if k == "TRACKER" else {})} for k in kinds]
    (root / "solarpunk" / "leaf").mkdir(parents=True)
    (root / "solarpunk" / "leaf" / "asset_types.json").write_text(json.dumps(entries))
    return asset_types.problems(root)


class TheRepository(unittest.TestCase):
    def test_the_real_list_holds(self) -> None:
        self.assertEqual(asset_types.problems(ROOT), [])

    def test_the_real_document_has_a_section_per_kind_in_order(self) -> None:
        found = asset_types.sections((ROOT / "docs" / "ASSET-MAINTENANCE-LIST.md").read_text(encoding="utf-8"))
        self.assertEqual(tuple(found), KINDS)

    def test_the_planted_breaks_are_caught(self) -> None:
        self.assertEqual(asset_types.problems(BROKEN / "asset_types"), [
            "METER has no entry in solarpunk/leaf/asset_types.json",
            "TRACKER: field angle_deg is in the document and not in the JSON",
        ])


class TheCheck(unittest.TestCase):
    def test_a_section_matching_its_entry_holds(self) -> None:
        body = TABLE + TRACKER_ROW + "\nTests: `reachable`, `tracker_moving`.\n"
        self.assertEqual(tree(body, {"fields": ANGLE, "tests": ["reachable", "tracker_moving"]}), [])

    def test_a_null_max_matches_a_dash(self) -> None:
        body = TABLE + "| energy_kwh | kWh | 0 | — |\n"
        self.assertEqual(tree(body, {"fields": {"energy_kwh": {"unit": "kWh", "min": 0, "max": None}}}), [])

    def test_a_kind_missing_from_both_sides_is_caught(self) -> None:
        self.assertEqual(tree("", {}, KINDS[:-1]), [
            "SENSOR has no entry in docs/ASSET-MAINTENANCE-LIST.md",
            "SENSOR has no entry in solarpunk/leaf/asset_types.json",
        ])

    def test_a_name_that_is_no_kind_is_caught(self) -> None:
        self.assertEqual(tree("", {}, KINDS + ("PANEL",)), [
            "PANEL is in docs/ASSET-MAINTENANCE-LIST.md and is not an asset kind",
            "PANEL is in solarpunk/leaf/asset_types.json and is not an asset kind",
        ])

    def test_a_field_absent_from_the_json_is_caught(self) -> None:
        self.assertEqual(tree(TABLE + TRACKER_ROW, {}), ["TRACKER: field angle_deg is in the document and not in the JSON"])

    def test_a_field_absent_from_the_document_is_caught(self) -> None:
        self.assertEqual(tree("", {"fields": ANGLE}), ["TRACKER: field angle_deg is in the JSON and not in the document"])

    def test_a_range_that_differs_is_caught(self) -> None:
        found = tree(TABLE + "| angle_deg | deg | -60 | 45 |\n", {"fields": ANGLE})
        self.assertEqual(found, ["TRACKER: field angle_deg is ('deg', -60.0, 45.0) in the document and "
                                 "('deg', -60.0, 60.0) in the JSON"])

    def test_a_unit_that_differs_is_caught(self) -> None:
        found = tree(TABLE + "| angle_deg | rad | -60 | 60 |\n", {"fields": ANGLE})
        self.assertEqual(len(found), 1)
        self.assertIn("('rad', -60.0, 60.0) in the document", found[0])

    def test_a_test_on_one_side_only_is_caught(self) -> None:
        self.assertEqual(tree("Tests: `reachable`.\n", {"tests": ["tracker_moving"]}), [
            "TRACKER: test reachable is in the document and not in the JSON",
            "TRACKER: test tracker_moving is in the JSON and not in the document",
        ])

    def test_missing_files_are_caught(self) -> None:
        self.assertEqual(asset_types.problems(scratch()), [
            "docs/ASSET-MAINTENANCE-LIST.md is not tracked",
            "solarpunk/leaf/asset_types.json is not tracked",
        ])

    def test_text_before_the_first_heading_is_no_section(self) -> None:
        self.assertEqual(asset_types.sections("Tests: `x`\n## SITE\nTests: none.\n"), {"SITE": ["Tests: none."]})
