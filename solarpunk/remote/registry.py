"""The registry: finds every module under solarpunk/remote/tests/ (SP-010), so a remote test is added by adding a file.
A module may define ACQUIRE (13.3, SP-020: what the runner reads for it, a value of acquire.ACQUISITIONS) and must define
KINDS (a tuple of AssetKind), CLAUSES (the register clauses it evidences), REACTIONS (13.4, SP-020: for each kind what a
failure does, a tuple of reactions.REACTIONS_SET, the generic SIT-004 fault where a kind names none) and run; one
missing any of them, or a reaction outside the set, naming a kind it does not run on, a code not of that kind, a suite
the folder lacks or a chain of started suites that loops or runs too deep, is refused by name, never skipped. survey() reads a
folder for the Manage tests window (9.8): there a script that cannot load is listed with its reason, not raised."""
import importlib
import importlib.util
import pkgutil
import sys
from collections.abc import Callable
import dataclasses
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from solarpunk.leaf import asset_types
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote import reactions as reaction_set
from solarpunk.remote import suites, tests
from solarpunk.remote.acquire import ACQUISITIONS, reads_only
from solarpunk.remote.results import ALL, Result

REQUIRED = ("KINDS", "CLAUSES", "REACTIONS", "run")
SURVEY_PACKAGE = "solarpunk_survey"


class BadRemoteTest(ValueError):
    """Raised for a test module missing a field or with a malformed one, or a test name the registry does not hold:
    BadRemoteTest("solarpunk.remote.tests.broken has no CLAUSES")."""


@dataclass(frozen=True)
class RemoteTest:
    """One discovered test: RemoteTest("reachable", (AssetKind.INVERTER, …), ("55000-9.1",), reachable.run,
    {AssetKind.INVERTER: (Fault("INV-001"),), …}); reactions maps each kind to what a failure does (13.4)."""

    name: str
    kinds: tuple[AssetKind, ...]
    clauses: tuple[str, ...]
    run: Callable[[Asset, tuple[Sample, ...]], Result]
    reactions: dict[AssetKind, tuple] = dataclasses.field(default_factory=dict)
    acquire: object | None = None  # a value of acquire.ACQUISITIONS: what the runner reads for this test (13.3)

    def reactions_for(self, kind: AssetKind) -> tuple:
        """What a failure on an asset of this kind does, a Fault always among it: reachable's for a METER is
        (Fault("MTR-001"),); a kind the test names none for is (Fault("SIT-004"),)."""
        return reaction_set.with_fault(self.reactions.get(kind, ()))

    def fault_code(self, kind: AssetKind) -> str:
        """The code a failure on this kind raises: reachable's for a METER is "MTR-001", for an INVERTER the generic
        "SIT-004" (SP-047: a lost link is no OUTAGE or DERATE)."""
        return reaction_set.fault_code_of(self.reactions_for(kind))


def from_module(name: str, module: ModuleType) -> RemoteTest:
    """A module's test, checked: from_module("reachable", reachable).clauses is ("55000-9.1",); a module with no
    CLAUSES raises BadRemoteTest naming the module and CLAUSES; KINDS ["INV"] raises it naming KINDS."""
    for field in REQUIRED:
        if not hasattr(module, field):
            raise BadRemoteTest(f"{module.__name__} has no {field}")
    kinds = module.KINDS
    if not isinstance(kinds, tuple) or not all(isinstance(kind, AssetKind) for kind in kinds):
        raise BadRemoteTest(f"{module.__name__}: KINDS is not a tuple of AssetKind")
    acquire = checked_acquire(module.__name__, kinds, getattr(module, "ACQUIRE", None))
    run = module.run if acquire is None else reads_only(module.run)
    return RemoteTest(name, kinds, module.CLAUSES, run, checked_reactions(module.__name__, kinds, module.REACTIONS), acquire)


def checked_acquire(module: str, kinds: tuple[AssetKind, ...], declared: object) -> object | None:
    """A module's ACQUIRE, held to the closed set and to its kinds' fields (SP-020): None (no ACQUIRE) and
    Burst("power_kw", 1, 60) for INVERTER pass; "burst", or a Burst of a field the kind does not hold, raises BadRemoteTest."""
    if declared is None:
        return None
    if not isinstance(declared, ACQUISITIONS):
        raise BadRemoteTest(f"{module}: ACQUIRE is none of {', '.join(kind.__name__ for kind in ACQUISITIONS)}")
    for kind in kinds:
        try:
            asset_types.in_range(kind, declared.field, 0)
        except asset_types.UnknownField as error:
            raise BadRemoteTest(f"{module}: ACQUIRE reads {declared.field}, which {kind.name} does not hold") from error
    return declared


def suites_folder() -> Path:
    """The suites' folder, solarpunk/remote/suites/, read here by name only: the suite registry imports this one."""
    return Path(suites.__path__[0])


def suite_names() -> frozenset[str]:
    """The suites a RunSuite may name, `all` and each file of the folder: with an empty folder, {"all"}."""
    return frozenset({ALL} | {path.stem for path in suites_folder().glob("*.py") if path.stem != "__init__"})


def checked_reactions(module: str, kinds: tuple[AssetKind, ...], declared: object) -> dict[AssetKind, tuple]:
    """A module's REACTIONS, held to the closed set, its KINDS, the catalogue and the folder's suites (SP-020): {INVERTER:
    (Fault("INV-001"),)} for KINDS (INVERTER,) passes; {INVERTER: (Fault("SEN-001"),)} raises BadRemoteTest naming
    SEN-001 as no INVERTER code."""
    try:
        return reaction_set.checked_reactions(module, kinds, suite_names(), declared)
    except ValueError as error:
        raise BadRemoteTest(str(error)) from error


def checked_chains(found: dict[str, RemoteTest]) -> None:
    """Refuses a folder where a suite a reaction starts starts itself, directly or through another, or runs deeper than
    MAX_CHAIN suites (SP-020): reads each suite's TESTS from its file, so a suite that will not load is the suite
    registry's to refuse, not this check's."""
    started = {name: tuple(item.name for items in test.reactions.values() for item in items
                           if isinstance(item, reaction_set.RunSuite)) for name, test in found.items()}
    if not any(started.values()):
        return
    contents = {ALL: tuple(found)}
    for path in sorted(suites_folder().glob("*.py")):
        try:
            contents[path.stem] = tuple(load_file(path).TESTS)
        except (Exception, SystemExit):  # the suite registry names what is wrong with it
            contents[path.stem] = ()
    problem = reaction_set.chain_problem(started, contents)
    if problem is not None:
        raise BadRemoteTest(f"REACTIONS: {problem}")


def load(package: str, paths: list[str]) -> dict[str, RemoteTest]:
    """Every module in the package's folders, imported and checked, by name in name order: load("solarpunk.remote.tests",
    tests.__path__) has the keys "on_grid", "power_under_rated", "reachable"; a broken module raises BadRemoteTest."""
    found: dict[str, RemoteTest] = {}
    importlib.invalidate_caches()  # a script added since the last look is found
    # pkgutil lists a folder's modules in sorted file-name order, so the dict is in name order.
    for info in pkgutil.iter_modules(paths):
        module = importlib.import_module(f"{package}.{info.name}")
        found[info.name] = from_module(info.name, module)
    checked_chains(found)
    return found


def discover() -> dict[str, RemoteTest]:
    """Every test under solarpunk/remote/tests/ by name: sorted(discover()) is ["on_grid", "power_under_rated",
    "reachable"] while those three are the folder's modules."""
    return load(tests.__name__, list(tests.__path__))


def tests_for(kind: AssetKind) -> tuple[RemoteTest, ...]:
    """The discovered tests that run against a kind, in name order: tests_for(AssetKind.INVERTER) names on_grid,
    power_under_rated, reachable; tests_for(AssetKind.SITE) is ()."""
    return tuple(test for test in discover().values() if kind in test.kinds)


@dataclass(frozen=True)
class Surveyed:
    """One script in the tests' folder as the Manage tests window lists it (9.8): Surveyed("reachable", <its test>,
    None) loads; Surveyed("broken", None, "broken has no CLAUSES") does not, and says why."""

    name: str
    test: RemoteTest | None
    problem: str | None


def load_file(path: Path) -> ModuleType:
    """A script loaded fresh from its file, under its own name in a package of the survey's (never the scheduled run's
    module, which it leaves as it is): load_file(d / "on_grid.py").KINDS is on_grid's KINDS."""
    name = f"{SURVEY_PACKAGE}.{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BadRemoteTest(f"{path.name} is not a Python module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # a dataclass in the script finds its module while it runs
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def surveyed(path: Path) -> Surveyed:
    """One script, loaded and checked, or its reason: a script missing CLAUSES gives problem "x has no CLAUSES", one
    that does not parse "SyntaxError: invalid syntax (x.py, line 3)", one that raises at import its error's name and
    words. A script is anyone's code, so whatever it raises, sys.exit included, is its problem, listed."""
    try:
        return Surveyed(path.stem, from_module(path.stem, load_file(path)), None)
    except BadRemoteTest as error:
        return Surveyed(path.stem, None, str(error).replace(f"{SURVEY_PACKAGE}.{path.stem}", path.stem))
    except (Exception, SystemExit) as error:
        return Surveyed(path.stem, None, f"{type(error).__name__}: {error}")


def survey(folder: Path) -> tuple[Surveyed, ...]:
    """Every script in a folder, in name order, each loaded afresh so an edit or a new file shows at once:
    survey(the tests' folder) lists reachable among the seven, each with its test and no problem."""
    return tuple(surveyed(path) for path in sorted(folder.glob("*.py")) if path.stem != "__init__")


def folder() -> Path:
    """The folder of the remote tests, solarpunk/remote/tests/, where a new test is a new script."""
    return Path(tests.__path__[0])
