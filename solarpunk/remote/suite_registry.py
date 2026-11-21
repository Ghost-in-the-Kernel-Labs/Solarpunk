"""The suite registry (13.2, SP-019, SP-020): finds every module under solarpunk/remote/suites/ as the registry finds
every test, and holds it to its declarations. A suite module has TESTS (names the test registry holds), KINDS and SITES
(its reach, () for every kind or every site) and CADENCE (one of the closed forms below) and nothing else of its own: a
test, kind or cadence it lacks, or a function or any other name of its own, is refused by name on load, so a typo fails
at once. The default suite `all` is the registry's own, every test on every run, and is no file; a file named all is
refused. due() says whether a suite's cadence has come at an instant."""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType

from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.remote import suites
from solarpunk.remote.registry import BadRemoteTest, discover, load_file
from solarpunk.remote.results import ALL

EVERY_RUN = "every run"
HOURLY = "hourly"
DAILY = re.compile(r"daily at ([01]\d|2[0-3])")
# The cadence's closed set, three forms and no other (TODO 13.2): a free-form schedule could not be checked on load, so a
# typo would run a suite never or always. A daily cadence names its UTC hour in two digits.
CADENCE_FORMS = (EVERY_RUN, HOURLY, "daily at HH")
FIELDS = ("TESTS", "KINDS", "SITES", "CADENCE")
IMPORTED = ("AssetKind",)  # the one name a suite may import, to write its KINDS


@dataclass(frozen=True)
class Suite:
    """One suite: Suite("hourly_check", ("reachable",), (AssetKind.INVERTER,), (), "hourly"); KINDS and SITES empty
    reach every kind and every site."""

    name: str
    tests: tuple[str, ...]
    kinds: tuple[AssetKind, ...]
    sites: tuple[str, ...]
    cadence: str

    def reaches(self, asset: Asset) -> bool:
        """Whether the asset is in the suite's reach: a suite of INVERTER at "OAHE" reaches OAHE-INV-001 and not a meter
        or an inverter of another site; empty KINDS and SITES reach every asset."""
        return (not self.kinds or asset.kind in self.kinds) and (not self.sites or asset.site in self.sites)


def default_suite() -> Suite:
    """The suite every store has: every test the registry holds, every kind and site, on every run (SP-019)."""
    return Suite(ALL, tuple(discover()), (), (), EVERY_RUN)


def checked_cadence(where: str, cadence: object) -> str:
    """A cadence of the closed set: "hourly" and "daily at 06" pass; "weekly" raises BadRemoteTest naming it."""
    if isinstance(cadence, str) and (cadence in (EVERY_RUN, HOURLY) or DAILY.fullmatch(cadence)):
        return cadence
    raise BadRemoteTest(f"{where}: CADENCE {cadence!r} is none of {', '.join(CADENCE_FORMS)}")


def checked_suite(name: str, tests: object, kinds: object, sites: object, cadence: object) -> Suite:
    """A suite from its declarations, checked: an unknown test, a kind no test of the suite runs on, a malformed field or
    a cadence outside the closed set raises BadRemoteTest naming the suite; the name `all` is the default's."""
    if name == ALL:
        raise BadRemoteTest(f"{name} is the default suite and cannot be declared")
    if not isinstance(tests, tuple) or not tests or not all(isinstance(test, str) for test in tests):
        raise BadRemoteTest(f"{name}: TESTS is not a tuple of test names")
    held = discover()
    for test in tests:
        if test not in held:
            raise BadRemoteTest(f"{name}: TESTS names {test}, which the registry does not hold")
    if not isinstance(kinds, tuple) or not all(isinstance(kind, AssetKind) for kind in kinds):
        raise BadRemoteTest(f"{name}: KINDS is not a tuple of AssetKind")
    for kind in kinds:
        if not any(kind in held[test].kinds for test in tests):
            raise BadRemoteTest(f"{name}: KINDS names {kind.name}, which none of its tests runs on")
    if not isinstance(sites, tuple) or not all(isinstance(site, str) for site in sites):
        raise BadRemoteTest(f"{name}: SITES is not a tuple of site names")
    return Suite(name, tests, kinds, sites, checked_cadence(name, cadence))


def from_module(name: str, module: ModuleType) -> Suite:
    """A suite module's suite, checked: a module missing a field raises BadRemoteTest "<name> has no TESTS"; one with a
    function or any name of its own beyond the four fields raises "<name> has <thing> of its own"."""
    for field in FIELDS:
        if not hasattr(module, field):
            raise BadRemoteTest(f"{name} has no {field}")
    for held in vars(module):
        if not held.startswith("_") and held not in FIELDS + IMPORTED:
            raise BadRemoteTest(f"{name} has {held} of its own: a suite declares and nothing else")
    return checked_suite(name, module.TESTS, module.KINDS, module.SITES, module.CADENCE)


def folder() -> Path:
    """The suites' folder, solarpunk/remote/suites/, where a new suite is a new module."""
    return Path(suites.__path__[0])


def discover_suites(where: Path | None = None) -> dict[str, Suite]:
    """Every suite by name, `all` first and then the folder's modules in name order: with no module in the folder,
    {"all": the default}; a broken module raises BadRemoteTest."""
    found = {ALL: default_suite()}
    for path in sorted((where or folder()).glob("*.py")):
        if path.stem == "__init__":
            continue
        found[path.stem] = from_module(path.stem, load_file(path))
    return found


def named(name: str, where: Path | None = None) -> Suite:
    """One suite: named("all").cadence is "every run"; a name the folder does not hold raises BadRemoteTest."""
    found = discover_suites(where)
    if name not in found:
        raise BadRemoteTest(f"no suite {name}")
    return found[name]


def due(suite: Suite, last_run: datetime | None, moment: datetime) -> bool:
    """Whether the suite's cadence has come at the instant, given its last stored run: every run is always due; hourly
    when it has not run since the start of the moment's hour; daily at 06 when it has not run since the latest 06:00 not
    after the moment (at 05:00, yesterday's): hourly with last run 10:05 is due at 11:00 and not at 10:30; never run is always due."""
    if suite.cadence == EVERY_RUN or last_run is None:
        return True
    if suite.cadence == HOURLY:
        since = moment.replace(minute=0, second=0, microsecond=0)
    else:
        since = moment.replace(hour=int(suite.cadence[-2:]), minute=0, second=0, microsecond=0)
        if since > moment:
            since -= timedelta(days=1)
    return last_run < since
