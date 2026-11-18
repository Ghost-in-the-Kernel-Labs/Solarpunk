"""The asset maintenance list held to its data (TODO 2.1; test/test_asset_types.py; C-013).

docs/ASSET-MAINTENANCE-LIST.md has one `## KIND` section per `AssetKind`, each with a fields table `| Field | Unit |
Min | Max |` (a max of `—` is null) and a line `Tests: `a`, `b`.`; solarpunk/leaf/asset_types.json is a list of
objects {kind, description, fields: name → {unit, min, max}, tests, passing}. Both must agree: every AssetKind has a
section and an entry and nothing else does; every field row is in the entry with the same unit, min and max and every
entry field has a row; every test named in a section is in the entry's tests and the other way. The files are read
from git's list (scripts/checks/common.py; C-001), so a new file is staged (`git add -N`) before the fast loop.
"""
import json
import re
from pathlib import Path

from scripts.checks.common import matching, tracked_files
from solarpunk.leaf.codes import AssetKind

DOCUMENT = "docs/ASSET-MAINTENANCE-LIST.md"
DATA = "solarpunk/leaf/asset_types.json"
HEADING = "## "
TESTS_LINE = "Tests:"
NO_MAX = "—"
NAMED = re.compile(r"`([^`]+)`")

Range = tuple[str, float, float | None]


def sections(text: str) -> dict[str, list[str]]:
    """Each `## ` heading's name and the lines under it up to the next: sections("# t\\n## SITE\\nx\\n## METER\\n")
    gives {"SITE": ["x"], "METER": []}."""
    found: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith(HEADING):
            current = found.setdefault(line[len(HEADING):].strip(), [])
        elif current is not None:
            current.append(line)
    return found


def field_rows(lines: list[str]) -> dict[str, Range]:
    """A section's field table as name → (unit, min, max), header and rule left out:
    field_rows(["| power_kw | kW | 0 | — |"]) gives {"power_kw": ("kW", 0.0, None)}."""
    found: dict[str, Range] = {}
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(cells) == 4 and cells[0] != "Field" and not cells[0].startswith("---"):
            high = None if cells[3] == NO_MAX else float(cells[3])
            found[cells[0]] = (cells[1], float(cells[2]), high)
    return found


def tests_named(lines: list[str]) -> list[str]:
    """The tests a section's Tests line names in backticks: tests_named(["Tests: `reachable`, `on_grid`."]) gives
    ["reachable", "on_grid"]; "Tests: none." gives []."""
    return [name for line in lines if line.startswith(TESTS_LINE) for name in NAMED.findall(line)]


def json_fields(entry: dict) -> dict[str, Range]:
    """A JSON entry's fields as name → (unit, min, max): {"fields": {"angle_deg": {"unit": "deg", "min": -60, "max":
    60}}} gives {"angle_deg": ("deg", -60.0, 60.0)}."""
    found: dict[str, Range] = {}
    for name, spec in entry["fields"].items():
        found[name] = (spec["unit"], float(spec["min"]), None if spec["max"] is None else float(spec["max"]))
    return found


def entry_problems(kind: str, lines: list[str], entry: dict) -> list[str]:
    """One kind's section against its JSON entry: a row the JSON lacks gives ["TRACKER: field angle_deg is in the
    document and not in the JSON"]; a row whose unit, min or max differs, an entry field with no row, and a test
    named on one side only each give one problem."""
    rows, data = field_rows(lines), json_fields(entry)
    found = [f"{kind}: field {name} is in the document and not in the JSON" for name in rows if name not in data]
    found += [f"{kind}: field {name} is {rows[name]} in the document and {data[name]} in the JSON"
              for name in rows if name in data and rows[name] != data[name]]
    found += [f"{kind}: field {name} is in the JSON and not in the document" for name in data if name not in rows]
    named, listed = tests_named(lines), list(entry["tests"])
    found += [f"{kind}: test {name} is in the document and not in the JSON" for name in named if name not in listed]
    found += [f"{kind}: test {name} is in the JSON and not in the document" for name in listed if name not in named]
    return found


def kind_problems(names: list[str], where: str) -> list[str]:
    """Kinds missing from one side and names there that are no kind: kind_problems(["SITE", "PANEL"], "the JSON")
    gives "INVERTER has no entry in the JSON" (one per missing kind) then "PANEL is in the JSON and is not an asset
    kind"."""
    kinds = [kind.name for kind in AssetKind]
    found = [f"{kind} has no entry in {where}" for kind in kinds if kind not in names]
    return found + [f"{name} is in {where} and is not an asset kind" for name in names if name not in kinds]


def problems(root: Path) -> list[str]:
    """Every way the document and the JSON disagree under root; [] when they hold. A file missing from git's list is
    itself a problem: ["docs/ASSET-MAINTENANCE-LIST.md is not tracked"]."""
    files = tracked_files(root)
    missing = [f"{name} is not tracked" for name in (DOCUMENT, DATA) if not matching(files, root, name)]
    if missing:
        return missing
    document = sections(matching(files, root, DOCUMENT)[0].read_text(encoding="utf-8"))
    entries = {entry["kind"]: entry for entry in json.loads(matching(files, root, DATA)[0].read_text(encoding="utf-8"))}
    found = kind_problems(list(document), DOCUMENT) + kind_problems(list(entries), DATA)
    for kind in document:
        if kind in entries:
            found += entry_problems(kind, document[kind], entries[kind])
    return found
