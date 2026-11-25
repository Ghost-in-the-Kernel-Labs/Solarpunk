"""Every remote test holds the contract in docs/REMOTE-TESTS.md as far as a check can see; the planted breaks are caught
(TODO 13.1, SP-019)."""
import ast
import unittest
from pathlib import Path

from scripts.checks import remote_tests
from scripts.checks.asset_types import sections
from solarpunk.leaf.codes import AssetKind
from solarpunk.remote import scaffold
from test.support import BROKEN, ROOT, scratch

LIST = (ROOT / "docs" / "ASSET-MAINTENANCE-LIST.md").read_text(encoding="utf-8")
GOOD = '''"""Good: says what it checks."""
from solarpunk.leaf.codes import AssetKind
from solarpunk.remote.results import Result, no_data, nothing_to_check

KINDS = (AssetKind.INVERTER,)
CLAUSES = ("9001-9.1.1",)
REACTIONS = {}
# Why: a power over this is a bad reading.
LIMIT = 40.0


def run(asset, samples):
    """Result(True, "1 records") under the limit; Result(False, "at 10:00: 41.0 kW") over it."""
    missing = nothing_to_check(samples)
    return no_data(missing) if missing else Result(True, str(LIMIT))
'''


def tree_with(source: str, name: str = "good") -> Path:
    """A scratch root holding the real maintenance list and one test module with the source given: tree_with(GOOD)."""
    root = scratch()
    (root / "docs" / "ASSET-MAINTENANCE-LIST.md").write_text(LIST, encoding="utf-8")
    folder = root / "solarpunk" / "remote" / "tests"
    folder.mkdir(parents=True)
    (folder / f"{name}.py").write_text(source, encoding="utf-8")
    return root


class TheRepository(unittest.TestCase):
    def test_every_real_test_holds_the_contract(self) -> None:
        self.assertEqual(remote_tests.problems(ROOT), [])

    def test_the_planted_breaks_are_caught(self) -> None:
        self.assertEqual(remote_tests.problems(BROKEN / "remote_tests"), [
            "broken: has no module docstring",
            "broken: imports sqlite3 (a store, a network or a clock reader)",
            "broken: line 8 LIMIT has no comment saying why",
            "broken: line 13 uses the bare number 40.0 (name it)",
            "broken: run's docstring has no passing case (Result(True...)",
            "broken: run's docstring has no failing case (Result(False...)",
            "broken: run never calls nothing_to_check (no records must be no data, never a pass)",
            "broken: has no REACTIONS",
            "broken: INVERTER's Tests line does not name broken",
        ])


class TheContract(unittest.TestCase):
    def test_a_module_that_holds_is_clean_once_listed(self) -> None:
        self.assertEqual(remote_tests.problems(tree_with(GOOD, "records_stored")), [])

    def test_a_clock_call_is_caught(self) -> None:
        source = GOOD.replace("str(LIMIT)", "str(datetime.now())").replace("from solarpunk.leaf", "from datetime import datetime\nfrom solarpunk.leaf", 1)
        self.assertEqual(remote_tests.problems(tree_with(source, "records_stored")), ["records_stored: line 16 calls .now() (reads the clock)"])

    def test_the_leaf_clocks_grid_arithmetic_is_allowed(self) -> None:
        source = GOOD.replace("from solarpunk.leaf.codes", "from solarpunk.leaf.clock import on_grid\nfrom solarpunk.leaf.codes", 1)
        self.assertEqual(remote_tests.problems(tree_with(source, "records_stored")), [])

    def test_reactions_must_be_keyed_by_the_kinds(self) -> None:
        source = GOOD.replace("REACTIONS = {}", "REACTIONS = {AssetKind.METER: ()}")
        self.assertEqual(remote_tests.problems(tree_with(source, "records_stored")),
                         ["records_stored: REACTIONS is not a dict keyed by kinds of KINDS"])

    def test_a_threshold_with_its_comment_at_the_end_of_the_line_holds(self) -> None:
        source = GOOD.replace("# Why: a power over this is a bad reading.\nLIMIT = 40.0", "LIMIT = 40.0  # a bad reading")
        self.assertEqual(remote_tests.problems(tree_with(source, "records_stored")), [])

    def test_a_rounding_digit_is_not_a_threshold(self) -> None:
        source = GOOD.replace("str(LIMIT)", "str(round(LIMIT, 4))")
        self.assertEqual(remote_tests.problems(tree_with(source, "records_stored")), [])

    def test_a_module_that_will_not_load_is_a_problem(self) -> None:
        found = remote_tests.problems(tree_with(GOOD + "\nraise RuntimeError('x')\n", "records_stored"))
        self.assertEqual(found, ["records_stored: will not load: RuntimeError: x"])

    def test_the_real_tests_each_name_their_kinds_in_the_list(self) -> None:
        document = sections(LIST)
        self.assertEqual(remote_tests.list_problems("tracker_moving", (AssetKind.TRACKER,), document), [])
        self.assertEqual(remote_tests.list_problems("tracker_moving", (AssetKind.METER,), document),
                         ["METER's Tests line does not name tracker_moving"])


class TheScaffold(unittest.TestCase):
    def test_a_scaffolded_test_meets_the_contract_but_for_run(self) -> None:
        text = scaffold.source("tracker_moving", (AssetKind.TRACKER,), ("55000-9.1",))
        self.assertEqual(remote_tests.problems(tree_with(text, "tracker_moving")),
                         ["tracker_moving: run never calls nothing_to_check (no records must be no data, never a pass)"])
        self.assertIsInstance(ast.parse(text), ast.Module)
