"""The registry: finds every module under solarpunk/remote/tests/ (SP-010), so a remote test is added by adding a file.
A module must define KINDS (a tuple of AssetKind), CLAUSES (the register clauses it evidences) and run; one missing
any of them is refused by name, never skipped."""
import importlib
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType

from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote import tests
from solarpunk.remote.results import Result

REQUIRED = ("KINDS", "CLAUSES", "run")


class BadRemoteTest(ValueError):
    """Raised for a test module missing a field or with a malformed one, or a test name the registry does not hold:
    BadRemoteTest("solarpunk.remote.tests.broken has no CLAUSES")."""


@dataclass(frozen=True)
class RemoteTest:
    """One discovered test: RemoteTest("reachable", (AssetKind.INVERTER, …), ("55000-9.1",), reachable.run)."""

    name: str
    kinds: tuple[AssetKind, ...]
    clauses: tuple[str, ...]
    run: Callable[[Asset, tuple[Sample, ...]], Result]


def from_module(name: str, module: ModuleType) -> RemoteTest:
    """A module's test, checked: from_module("reachable", reachable).clauses is ("55000-9.1",); a module with no
    CLAUSES raises BadRemoteTest naming the module and CLAUSES; KINDS ["INV"] raises it naming KINDS."""
    for field in REQUIRED:
        if not hasattr(module, field):
            raise BadRemoteTest(f"{module.__name__} has no {field}")
    kinds = module.KINDS
    if not isinstance(kinds, tuple) or not all(isinstance(kind, AssetKind) for kind in kinds):
        raise BadRemoteTest(f"{module.__name__}: KINDS is not a tuple of AssetKind")
    return RemoteTest(name, kinds, module.CLAUSES, module.run)


def load(package: str, paths: list[str]) -> dict[str, RemoteTest]:
    """Every module in the package's folders, imported and checked, by name in name order: load("solarpunk.remote.tests",
    tests.__path__) has the keys "on_grid", "power_under_rated", "reachable"; a broken module raises BadRemoteTest."""
    found: dict[str, RemoteTest] = {}
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
