"""The asset maintenance list as data: per asset kind, what it is, the fields its feed answers with and each field's
range, the remote tests that apply and what a passing response is (docs/ASSET-MAINTENANCE-LIST.md says the same in
words; scripts/checks/asset_types.py holds the two together). The UI's type dropdown, the feed reader and the remote
tests read it from here. The list is the leaf's own file beside this module, read once at import."""
import json
from dataclasses import dataclass
from pathlib import Path

from solarpunk.leaf.codes import AssetKind

LIST_FILE = Path(__file__).with_name("asset_types.json")
KIND_BY_NAME: dict[str, AssetKind] = {kind.name: kind for kind in AssetKind}


class UnknownAssetType(ValueError):
    """Raised for a kind the list does not hold, or a list entry naming no AssetKind: UnknownAssetType("PANEL")."""


class UnknownField(ValueError):
    """Raised for a field the kind's feed does not answer with: UnknownField("TRACKER has no field power_kw")."""


@dataclass(frozen=True)
class FieldRange:
    """One feed field's unit and range: FieldRange("W/m2", 0.0, 1500.0). maximum None means the list sets no fixed
    ceiling (an inverter's power_kw is bounded by its own rated_kw, a meter's energy_kwh only grows)."""

    unit: str
    minimum: float
    maximum: float | None

    def holds(self, value: float) -> bool:
        """The value lies in the range, both ends included, None above unbounded: FieldRange("deg", -60, 60).holds(60)
        is True, .holds(60.5) is False; FieldRange("kWh", 0, None).holds(1e9) is True."""
        if value < self.minimum:
            return False
        return self.maximum is None or value <= self.maximum


@dataclass(frozen=True)
class AssetType:
    """One entry of the list: AssetType(AssetKind.TRACKER, "A single-axis tracker…", {"angle_deg": FieldRange("deg",
    -60, 60)}, ("reachable", "tracker_moving"), "The endpoint answers…")."""

    kind: AssetKind
    description: str
    fields: dict[str, FieldRange]
    tests: tuple[str, ...]
    passing: str


def entry(raw: dict) -> AssetType:
    """One JSON object as an AssetType: entry({"kind": "METER", "description": "d", "fields": {"energy_kwh": {"unit":
    "kWh", "min": 0, "max": None}}, "tests": ["reachable"], "passing": "p"}).fields["energy_kwh"].maximum is None;
    a kind that is no AssetKind name ("PANEL") raises UnknownAssetType."""
    # Invariant: SOL-03
    if raw["kind"] not in KIND_BY_NAME:
        raise UnknownAssetType(f"{raw['kind']!r} is not an asset kind")
    fields = {name: FieldRange(spec["unit"], spec["min"], spec["max"]) for name, spec in raw["fields"].items()}
    return AssetType(KIND_BY_NAME[raw["kind"]], raw["description"], fields, tuple(raw["tests"]), raw["passing"])


def load(text: str) -> dict[AssetKind, AssetType]:
    """The list's JSON text as entries by kind, in the file's order: load('[]') is {}; a kind listed twice raises
    UnknownAssetType, since the list holds one entry per kind."""
    found: dict[AssetKind, AssetType] = {}
    for raw in json.loads(text):
        parsed = entry(raw)
        if parsed.kind in found:
            raise UnknownAssetType(f"{parsed.kind.name} is listed twice")
        found[parsed.kind] = parsed
    return found


TYPES: dict[AssetKind, AssetType] = load(LIST_FILE.read_text(encoding="utf-8"))


def asset_type(kind: AssetKind) -> AssetType:
    """The list's entry for a kind: asset_type(AssetKind.TRACKER).tests is ("reachable", "tracker_moving"); a kind the
    list lacks raises UnknownAssetType."""
    # Invariant: SOL-03
    if kind not in TYPES:
        raise UnknownAssetType(f"{kind!r} is not in the asset maintenance list")
    return TYPES[kind]


def kinds() -> tuple[AssetKind, ...]:
    """The kinds the list holds, in the file's order: kinds()[0] is AssetKind.SITE, kinds()[1] AssetKind.INVERTER."""
    return tuple(TYPES)


def fields_of(kind: AssetKind) -> dict[str, FieldRange]:
    """A copy of the fields a kind's feed answers with: fields_of(AssetKind.TRACKER) is {"angle_deg": FieldRange("deg",
    -60, 60)}; fields_of(AssetKind.SITE) is {}."""
    return dict(asset_type(kind).fields)


def in_range(kind: AssetKind, field: str, value: float) -> bool:
    """A feed value against its field's range: in_range(AssetKind.TRACKER, "angle_deg", -60) is True, -61 is False;
    a field the kind does not answer with raises UnknownField."""
    fields = fields_of(kind)
    # Invariant: SOL-03
    if field not in fields:
        raise UnknownField(f"{kind.name} has no field {field}")
    return fields[field].holds(value)
