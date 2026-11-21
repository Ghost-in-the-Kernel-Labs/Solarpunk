"""Scaffolding a remote test: writes solarpunk/remote/tests/<name>.py with KINDS, CLAUSES and a run that fails until
it is written, so the registry finds the new test at once and no asset is green on a test nobody wrote. The kinds
default to the ones whose entry in the asset maintenance list names the test (SOL-03); a refusal is BadRemoteTest."""
import keyword
from pathlib import Path

from solarpunk.leaf.asset_types import KIND_BY_NAME, TYPES
from solarpunk.leaf.codes import AssetKind
from solarpunk.remote import tests
from solarpunk.remote.registry import BadRemoteTest

TEMPLATE = '''"""{title}: say here, in a sentence, what the test checks and the clause it evidences.
Scaffolded by `python3 -m solarpunk.cli test add {name}`; it fails on every run until run below is written."""
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result

KINDS = ({kinds},)
CLAUSES = ({clauses},)
# SP-020's reactions: for each kind, what a failure does (Fault("<code>"), Mail(), RunSuite("<name>"), OpenPreventive("<note>"));
# a kind left out raises the generic SIT-004 fault alone; say here why.
REACTIONS = {{}}


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Fails until it is written: run(asset, ()) is Result(False, "{name} is not written yet"); write here the passing
    case too, as in Result(True, "3 records"), and the failing one that names the first offending record's instant."""
    return Result(False, "{name} is not written yet")
'''


def listed_kinds(name: str) -> tuple[AssetKind, ...]:
    """The kinds whose maintenance-list entry names the test, in the list's order: listed_kinds("tracker_moving") is
    (AssetKind.TRACKER,); listed_kinds("irradiance_in_range") is (AssetKind.INVERTER, AssetKind.SENSOR); a name no
    entry holds gives ()."""
    return tuple(kind for kind, entry in TYPES.items() if name in entry.tests)


def named_kinds(names: tuple[str, ...]) -> tuple[AssetKind, ...]:
    """Kind names as kinds, in the order given: named_kinds(("METER", "INVERTER")) is (AssetKind.METER,
    AssetKind.INVERTER); a name that is no kind raises BadRemoteTest("PANEL is not an asset kind")."""
    for name in names:
        if name not in KIND_BY_NAME:
            raise BadRemoteTest(f"{name} is not an asset kind")
    return tuple(KIND_BY_NAME[name] for name in names)


def source(name: str, kinds: tuple[AssetKind, ...], clauses: tuple[str, ...]) -> str:
    """The new module's text: source("energy_monotonic", (AssetKind.METER,), ("9001-9.1.1",)) opens with
    '\"\"\"Energy monotonic: ' and holds the lines 'KINDS = (AssetKind.METER,)' and 'CLAUSES = ("9001-9.1.1",)'."""
    title = name.replace("_", " ").capitalize()
    kind_text = ", ".join(f"AssetKind.{kind.name}" for kind in kinds)
    clause_text = ", ".join(f'"{clause}"' for clause in clauses)
    return TEMPLATE.format(title=title, name=name, kinds=kind_text, clauses=clause_text)


def check(folder: Path, name: str, kinds: tuple[AssetKind, ...], clauses: tuple[str, ...]) -> None:
    """Refuses what cannot become a test, each with its reason: a name that is not a lower-case module name ("Bad-Name"
    is not a lower-case Python module name), one a file already holds (reachable already exists), no kind, no clause."""
    if not name.isidentifier() or keyword.iskeyword(name) or name != name.lower():
        raise BadRemoteTest(f"{name} is not a lower-case Python module name")
    if (folder / f"{name}.py").exists():
        raise BadRemoteTest(f"{name} already exists")
    if not kinds:
        raise BadRemoteTest(f"{name} is in no kind's maintenance list: name its kinds")
    if not clauses:
        raise BadRemoteTest(f"{name} names no clause")
    for clause in clauses:
        if '"' in clause or "\\" in clause or "\n" in clause:
            raise BadRemoteTest(f"{clause!r} is not a clause id")


def write(folder: Path, name: str, kinds: tuple[AssetKind, ...], clauses: tuple[str, ...]) -> Path:
    """Writes folder/<name>.py and returns its path: write(d, "energy_monotonic", (AssetKind.METER,), ("9001-9.1.1",))
    is d/energy_monotonic.py; whatever check refuses raises BadRemoteTest and writes nothing."""
    check(folder, name, kinds, clauses)
    path = folder / f"{name}.py"
    path.write_text(source(name, kinds, clauses), encoding="utf-8")
    return path


def add(name: str, kind_names: tuple[str, ...], clauses: tuple[str, ...], folder: Path | None = None) -> Path:
    """Scaffolds the test beside the others (or in the folder given), its kinds the ones named or, with none named, the
    maintenance list's: add("tracker_moving", (), ("55000-9.1",)) writes solarpunk/remote/tests/tracker_moving.py for
    the tracker."""
    kinds = named_kinds(kind_names) if kind_names else listed_kinds(name)
    return write(folder or Path(tests.__path__[0]), name, kinds, clauses)
