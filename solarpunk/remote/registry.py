"""The registry: finds every module under solarpunk/remote/tests/ (SP-010), so a remote test is added by adding a file.
A module must define KINDS (a tuple of AssetKind), CLAUSES (the register clauses it evidences), SUGGESTS (its rule table,
SP-015: for each of its KINDS the catalogue code a failure suggests, or None) and run; one missing any of them, or a
rule naming a kind it does not run on or a code not of that kind, is refused by name, never skipped. survey() reads a
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

from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind, codes_for
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote import tests
from solarpunk.remote.results import Result

REQUIRED = ("KINDS", "CLAUSES", "SUGGESTS", "run")
SURVEY_PACKAGE = "solarpunk_survey"


class BadRemoteTest(ValueError):
    """Raised for a test module missing a field or with a malformed one, or a test name the registry does not hold:
    BadRemoteTest("solarpunk.remote.tests.broken has no CLAUSES")."""


@dataclass(frozen=True)
class RemoteTest:
    """One discovered test: RemoteTest("reachable", (AssetKind.INVERTER, …), ("55000-9.1",), reachable.run,
    {AssetKind.INVERTER: "INV-001", …}); suggests maps each kind to the code a failure suggests, or None (SP-015)."""

    name: str
    kinds: tuple[AssetKind, ...]
    clauses: tuple[str, ...]
    run: Callable[[Asset, tuple[Sample, ...]], Result]
    suggests: dict[AssetKind, str | None] = dataclasses.field(default_factory=dict)

    def suggestion(self, kind: AssetKind) -> str | None:
        """The code a failure on an asset of this kind suggests: reachable.suggestion(AssetKind.INVERTER) is "INV-001";
        on_grid's is None for every kind."""
        return self.suggests.get(kind)


def from_module(name: str, module: ModuleType) -> RemoteTest:
    """A module's test, checked: from_module("reachable", reachable).clauses is ("55000-9.1",); a module with no
    CLAUSES raises BadRemoteTest naming the module and CLAUSES; KINDS ["INV"] raises it naming KINDS."""
    for field in REQUIRED:
        if not hasattr(module, field):
            raise BadRemoteTest(f"{module.__name__} has no {field}")
    kinds = module.KINDS
    if not isinstance(kinds, tuple) or not all(isinstance(kind, AssetKind) for kind in kinds):
        raise BadRemoteTest(f"{module.__name__}: KINDS is not a tuple of AssetKind")
    return RemoteTest(name, kinds, module.CLAUSES, module.run, checked_rules(module.__name__, kinds, module.SUGGESTS))


def checked_rules(module: str, kinds: tuple[AssetKind, ...], rules: object) -> dict[AssetKind, str | None]:
    """A module's SUGGESTS, held to its KINDS and the catalogue (SP-015): {INVERTER: "INV-001"} for KINDS (INVERTER,)
    passes; a rule for a kind it does not run on, a kind with no rule, or a code not of the kind's raises BadRemoteTest:
    {INVERTER: "SEN-001"} names SEN-001 as no INVERTER code."""
    if not isinstance(rules, dict) or set(rules) != set(kinds):
        raise BadRemoteTest(f"{module}: SUGGESTS must give one rule for each of its KINDS")
    for kind, code in rules.items():
        if code is not None and code not in {row.code for row in codes_for(kind)}:
            raise BadRemoteTest(f"{module}: SUGGESTS names {code}, which is no {kind.name} code")
    return dict(rules)


def load(package: str, paths: list[str]) -> dict[str, RemoteTest]:
    """Every module in the package's folders, imported and checked, by name in name order: load("solarpunk.remote.tests",
    tests.__path__) has the keys "on_grid", "power_under_rated", "reachable"; a broken module raises BadRemoteTest."""
    found: dict[str, RemoteTest] = {}
    importlib.invalidate_caches()  # a script added since the last look is found
    # pkgutil lists a folder's modules in sorted file-name order, so the dict is in name order.
    for info in pkgutil.iter_modules(paths):
        module = importlib.import_module(f"{package}.{info.name}")
        found[info.name] = from_module(info.name, module)
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
