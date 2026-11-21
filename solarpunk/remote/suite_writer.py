"""Writing a suite (13.2): `solarpunk suite add` makes solarpunk/remote/suites/<name>.py of declarations, checked by the
suite registry first so what is written is what loads; a refusal is BadRemoteTest and writes nothing."""
import keyword
from pathlib import Path

from solarpunk.leaf.asset_types import KIND_BY_NAME
from solarpunk.remote.registry import BadRemoteTest
from solarpunk.remote import suite_registry
from solarpunk.remote.suite_registry import EVERY_RUN, checked_suite

TEMPLATE = '''"""{title}: a suite of declarations (SP-020); it holds no logic. Written by `solarpunk suite add {name}`."""
from solarpunk.leaf.codes import AssetKind

TESTS = ({tests},)
KINDS = ({kinds})
SITES = ()
CADENCE = "{cadence}"
'''


def write(name: str, tests: tuple[str, ...], kind_names: tuple[str, ...], cadence: str = EVERY_RUN,
          where: Path | None = None) -> Path:
    """Writes the suite beside the others (or in the folder given) and returns its path: write("hourly_check",
    ("reachable",), ("INVERTER",), "hourly") is solarpunk/remote/suites/hourly_check.py; a name that is not a lower-case
    module name or is taken, an unknown test, kind or cadence raises BadRemoteTest and writes nothing."""
    where = where or suite_registry.folder()
    if not name.isidentifier() or keyword.iskeyword(name) or name != name.lower():
        raise BadRemoteTest(f"{name} is not a lower-case Python module name")
    if (where / f"{name}.py").exists():
        raise BadRemoteTest(f"{name} already exists")
    for kind_name in kind_names:
        if kind_name not in KIND_BY_NAME:
            raise BadRemoteTest(f"{kind_name} is not an asset kind")
    checked_suite(name, tests, tuple(KIND_BY_NAME[kind] for kind in kind_names), (), cadence)
    kinds = "".join(f"AssetKind.{kind}, " for kind in kind_names).rstrip()
    text = TEMPLATE.format(title=name.replace("_", " ").capitalize(), name=name,
                           tests=", ".join(f'"{test}"' for test in tests), kinds=kinds, cadence=cadence)
    path = where / f"{name}.py"
    path.write_text(text, encoding="utf-8")
    return path
