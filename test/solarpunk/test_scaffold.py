"""The remote-test scaffold: the module it writes, pinned whole and loaded through the registry's own loader; the kinds
it takes from the asset maintenance list; every refusal by its message; and project's two calls over it."""
import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from solarpunk import project
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.remote import registry, scaffold
from solarpunk.remote.registry import BadRemoteTest
from solarpunk.remote.results import Result

PACKAGE = "scaffold_fixture_pkg"
METER = Asset("OAHE-MTR-001", AssetKind.METER, "OAHE", None, "Revenue meter", None)
ENERGY_MONOTONIC = '''"""Energy monotonic: say here, in a sentence, what the test checks and the clause it evidences.
Scaffolded by `python3 -m solarpunk.cli test add energy_monotonic`; it fails on every run until run below is written."""
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result

KINDS = (AssetKind.METER, AssetKind.INVERTER,)
CLAUSES = ("9001-9.1.1", "55000-9.1",)
# SP-020's reactions: for each kind, what a failure does (Fault("<code>"), Mail(), RunSuite("<name>"), OpenPreventive("<note>"));
# a kind left out raises the generic SIT-004 fault alone; say here why.
REACTIONS = {}


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Fails until it is written: run(asset, ()) is Result(False, "energy_monotonic is not written yet"); write here the passing
    case too, as in Result(True, "3 records"), and the failing one that names the first offending record's instant."""
    return Result(False, "energy_monotonic is not written yet")
'''


class Scaffold(unittest.TestCase):
    """A test case with an empty package folder of its own, self.folder, removed when it ends."""

    def setUp(self) -> None:
        """A fresh root holding the package PACKAGE with an empty init module: self.folder is the package's folder."""
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = root.name
        self.folder = Path(root.name) / PACKAGE
        self.folder.mkdir()
        (self.folder / "__init__.py").write_text("", encoding="utf-8")

    def load(self) -> dict[str, registry.RemoteTest]:
        """The folder's modules through the registry's loader, then forgotten by the import machinery: after a write of
        "energy_monotonic", list(self.load()) is ["energy_monotonic"]."""
        sys.path.insert(0, self.root)
        try:
            importlib.invalidate_caches()
            return registry.load(PACKAGE, [str(self.folder)])
        finally:
            sys.path.remove(self.root)
            for name in [name for name in sys.modules if name.startswith(PACKAGE)]:
                del sys.modules[name]

    def refused(self, name: str, kinds: tuple[AssetKind, ...], clauses: tuple[str, ...], message: str) -> None:
        """Asserts write refuses with the message and leaves the folder as it was."""
        before = sorted(path.name for path in self.folder.iterdir())
        with self.assertRaises(BadRemoteTest) as caught:
            scaffold.write(self.folder, name, kinds, clauses)
        self.assertEqual(str(caught.exception), message)
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), before)


class TheSource(Scaffold):
    def test_the_module_text_is_pinned(self) -> None:
        kinds = (AssetKind.METER, AssetKind.INVERTER)
        self.assertEqual(scaffold.source("energy_monotonic", kinds, ("9001-9.1.1", "55000-9.1")), ENERGY_MONOTONIC)

    def test_write_returns_the_file_it_wrote(self) -> None:
        path = scaffold.write(self.folder, "energy_monotonic", (AssetKind.METER, AssetKind.INVERTER),
                              ("9001-9.1.1", "55000-9.1"))
        self.assertEqual(path, self.folder / "energy_monotonic.py")
        self.assertEqual(path.read_text(encoding="utf-8"), ENERGY_MONOTONIC)

    def test_the_file_is_written_as_utf8_whatever_the_platforms_default(self) -> None:
        with mock.patch.object(Path, "write_text") as write_text:
            scaffold.write(self.folder, "energy_monotonic", (AssetKind.METER, AssetKind.INVERTER),
                           ("9001-9.1.1", "55000-9.1"))
        write_text.assert_called_once_with(ENERGY_MONOTONIC, encoding="utf-8")

    def test_the_registry_loads_it_and_it_fails_until_written(self) -> None:
        scaffold.write(self.folder, "tracker_moving", (AssetKind.TRACKER,), ("55000-9.1",))
        found = self.load()
        self.assertEqual(list(found), ["tracker_moving"])
        self.assertEqual(found["tracker_moving"].kinds, (AssetKind.TRACKER,))
        self.assertEqual(found["tracker_moving"].clauses, ("55000-9.1",))
        self.assertEqual(found["tracker_moving"].run(METER, ()), Result(False, "tracker_moving is not written yet"))


class TheKinds(unittest.TestCase):
    def test_the_maintenance_list_names_a_tests_kinds(self) -> None:
        self.assertEqual(scaffold.listed_kinds("tracker_moving"), (AssetKind.TRACKER,))
        self.assertEqual(scaffold.listed_kinds("irradiance_in_range"), (AssetKind.INVERTER, AssetKind.SENSOR))
        self.assertEqual(scaffold.listed_kinds("no_such_test"), ())

    def test_named_kinds_keep_their_order(self) -> None:
        self.assertEqual(scaffold.named_kinds(("METER", "INVERTER")), (AssetKind.METER, AssetKind.INVERTER))
        self.assertEqual(scaffold.named_kinds(()), ())

    def test_a_name_that_is_no_kind_is_refused(self) -> None:
        for name in ("PANEL", "INV", "meter"):
            with self.subTest(name=name), self.assertRaises(BadRemoteTest) as caught:
                scaffold.named_kinds(("METER", name))
            self.assertEqual(str(caught.exception), f"{name} is not an asset kind")


class TheRefusals(Scaffold):
    def test_a_name_that_is_no_lower_case_module_name(self) -> None:
        for name in ("Bad-Name", "2fast", "class", "Reachable", ""):
            with self.subTest(name=name):
                self.refused(name, (AssetKind.METER,), ("x",), f"{name} is not a lower-case Python module name")

    def test_a_name_a_file_already_holds(self) -> None:
        scaffold.write(self.folder, "taken", (AssetKind.METER,), ("x",))
        self.refused("taken", (AssetKind.METER,), ("x",), "taken already exists")

    def test_no_kind_and_no_clause(self) -> None:
        self.refused("fresh", (), ("x",), "fresh is in no kind's maintenance list: name its kinds")
        self.refused("fresh", (AssetKind.METER,), (), "fresh names no clause")

    def test_a_clause_that_would_break_the_module(self) -> None:
        for clause in ('a"b', "a\\b", "a\nb"):
            with self.subTest(clause=clause):
                self.refused("fresh", (AssetKind.METER,), ("9001-9.1.1", clause), f"{clause!r} is not a clause id")


class AddAndProject(Scaffold):
    def add(self, name: str, kind_names: tuple[str, ...]) -> dict[str, registry.RemoteTest]:
        """project.add_remote_test with self.folder standing in for solarpunk/remote/tests/, then the folder loaded:
        self.add("tracker_moving", ())["tracker_moving"].kinds is (AssetKind.TRACKER,)."""
        with mock.patch.object(scaffold.tests, "__path__", [str(self.folder)]):
            path = project.add_remote_test(name, kind_names, ("55000-9.1",))
        self.assertEqual(path, self.folder / f"{name}.py")
        return self.load()

    def test_the_kinds_default_to_the_maintenance_lists(self) -> None:
        self.assertEqual(self.add("irradiance_in_range", ())["irradiance_in_range"].kinds,
                         (AssetKind.INVERTER, AssetKind.SENSOR))

    def test_named_kinds_win_over_the_list(self) -> None:
        self.assertEqual(self.add("irradiance_in_range", ("METER",))["irradiance_in_range"].kinds, (AssetKind.METER,))

    def test_a_test_in_no_list_needs_its_kinds_named(self) -> None:
        with mock.patch.object(scaffold.tests, "__path__", [str(self.folder)]), self.assertRaises(ValueError) as caught:
            project.add_remote_test("no_such_test", (), ("55000-9.1",))
        self.assertEqual(str(caught.exception), "no_such_test is in no kind's maintenance list: name its kinds")

    def test_the_real_folder_is_where_the_tests_live(self) -> None:
        with mock.patch.object(scaffold, "write", return_value=Path("x")) as write:
            self.assertEqual(scaffold.add("tracker_moving", (), ("55000-9.1",)), Path("x"))
        write.assert_called_once_with(Path(registry.tests.__path__[0]), "tracker_moving", (AssetKind.TRACKER,),
                                      ("55000-9.1",))

    def test_remote_tests_are_the_registrys_in_name_order(self) -> None:
        self.assertEqual(project.remote_tests(), tuple(registry.discover().values()))
        self.assertEqual([test.name for test in project.remote_tests()], sorted(registry.discover()))
