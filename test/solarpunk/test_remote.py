"""The remote tests (2.3): the registry finds exactly the folder's modules and refuses a broken one; each test passes and
fails as its docstring says; the results table orders an asset's latest run failing first; the suite stamps GREEN,
YELLOW and RED; the command line runs one test against one stored asset. The store's assets and samples tables are
made by their own lanes' schemas, so the results module's reads by name are held to the real tables."""
import importlib
import io
import sqlite3
import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime
from pathlib import Path

from solarpunk.fleet import registry as fleet
from solarpunk.leaf import store
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import NotUtc, at
from solarpunk.leaf.codes import AssetKind, AssetStatus
from solarpunk.leaf.telemetry import Sample, gap
from solarpunk.remote import registry, results, run
from solarpunk.remote.registry import BadRemoteTest
from solarpunk.remote.results import NotStored, Recorded, Result
from solarpunk.remote.tests import on_grid, power_under_rated, reachable
from solarpunk.telemetry import samples as telemetry

SITE = Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None)
INV1 = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 1", 100.0)
INV2 = Asset("OAHE-INV-002", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 2", 100.0)
SEN = Asset("OAHE-SEN-001", AssetKind.SENSOR, "OAHE", "OAHE-SIT-001", "Weather station", None)
TRK = Asset("OAHE-TRK-001", AssetKind.TRACKER, "OAHE", "OAHE-SIT-001", "Tracker 1", None)
WIRED = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 1", 100.0, "10.0.0.1", 5020,
              "Row 1, east", "tech@example.com")
UNRATED = Asset("OAHE-INV-009", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 9", None)
T0 = at(2026, 6, 1, 10, 0)
T1 = at(2026, 6, 1, 10, 5)
STAMP = "2026-06-01T10:05:00+00:00"
BROKEN_PACKAGE = "remote_fixture_pkg"
# Every module under solarpunk/remote/tests/, in name order, read from the folder rather than the registry, so the list
# follows a file added there (SP-017); the counts below follow from each kind's tests, never pinned.
TESTS_FOLDER = Path(registry.__file__).parent / "tests"
EVERY_TEST = sorted(path.stem for path in TESTS_FOLDER.glob("*.py") if path.stem != "__init__")


def reading(asset: Asset, moment: datetime, irradiance: float | None, power: float | None) -> Sample:
    """A non-gap sample: reading(INV1, T0, 800.0, 60.0).power_kw is 60.0."""
    return Sample(asset.asset_id, moment, irradiance, power, False)


def off_grid(asset: Asset) -> Sample:
    """A sample at 10:02, built past the leaf's own check (which would refuse it) so on_grid's guard can be shown to
    hold: off_grid(INV1).at.minute is 2."""
    built = object.__new__(Sample)
    values = {"asset_id": asset.asset_id, "at": at(2026, 6, 1, 10, 2), "irradiance_w_m2": 1.0, "power_kw": 1.0,
              "gap": False}
    for name, value in values.items():
        object.__setattr__(built, name, value)
    return built


def values(statuses: dict[str, AssetStatus]) -> dict[str, str]:
    """Each status by its value, since the leaf's AssetStatus members compare equal to one another (a dataclass
    decorator on the Enum; see the lane's report): values({"A": AssetStatus.RED}) is {"A": "red"}."""
    return {asset_id: status.value for asset_id, status in statuses.items()}


def fresh() -> sqlite3.Connection:
    """An in-memory store with the assets, samples and results tables:
    fresh().execute("SELECT count(*) FROM results").fetchone()[0] is 0."""
    conn = store.connect()
    store.apply(conn, fleet.schema() + telemetry.schema() + results.schema())
    return conn


def write_broken_package(root: Path, body: str) -> None:
    """A package BROKEN_PACKAGE under root holding one module, broken.py, with the body given:
    write_broken_package(d, "KINDS = ()") leaves d/remote_fixture_pkg/broken.py."""
    folder = root / BROKEN_PACKAGE
    folder.mkdir()
    (folder / "__init__.py").write_text("", encoding="utf-8")
    (folder / "broken.py").write_text(body, encoding="utf-8")


class TheRegistry(unittest.TestCase):
    def test_discover_finds_every_module_in_the_folder(self) -> None:
        found = registry.discover()
        self.assertEqual(list(found), EVERY_TEST)
        self.assertEqual(found["reachable"].kinds, reachable.KINDS)
        self.assertEqual(found["on_grid"].clauses, ("55000-7.5", "9001-9.1.3"))
        self.assertIs(found["power_under_rated"].run, power_under_rated.run)
        self.assertEqual(found["power_under_rated"].name, "power_under_rated")

    def test_tests_for_a_kind_in_name_order(self) -> None:
        names = [test.name for test in registry.tests_for(AssetKind.INVERTER)]
        self.assertEqual(names, [name for name in EVERY_TEST if AssetKind.INVERTER in registry.discover()[name].kinds])
        self.assertIn("reachable", names)
        sensor = [test.name for test in registry.tests_for(AssetKind.SENSOR)]
        self.assertEqual(sensor, [name for name in EVERY_TEST if AssetKind.SENSOR in registry.discover()[name].kinds])
        self.assertLess({"on_grid", "reachable"}, set(sensor))
        self.assertEqual(registry.tests_for(AssetKind.SITE), ())

    def test_each_test_names_register_clauses(self) -> None:
        register = (Path(__file__).resolve().parents[2] / "docs" / "CLAUSE-REGISTER.md").read_text(encoding="utf-8")
        for test in registry.discover().values():
            for clause in test.clauses:
                self.assertIn(f"| {clause} |", register)

    def load_broken(self, body: str) -> dict[str, registry.RemoteTest]:
        """Loads a fixture package through the registry's own loader, then removes it from the import machinery:
        load_broken("KINDS = ()") raises BadRemoteTest naming CLAUSES."""
        with tempfile.TemporaryDirectory() as root:
            write_broken_package(Path(root), body)
            sys.path.insert(0, root)
            try:
                importlib.invalidate_caches()
                return registry.load(BROKEN_PACKAGE, [str(Path(root) / BROKEN_PACKAGE)])
            finally:
                sys.path.remove(root)
                for name in [name for name in sys.modules if name.startswith(BROKEN_PACKAGE)]:
                    del sys.modules[name]

    def test_a_module_missing_a_field_is_refused_by_name(self) -> None:
        cases = {
            "CLAUSES = ()\nSUGGESTS = {}\ndef run(a, s): pass\n": "KINDS",
            "KINDS = ()\nSUGGESTS = {}\ndef run(a, s): pass\n": "CLAUSES",
            "KINDS = ()\nCLAUSES = ()\ndef run(a, s): pass\n": "SUGGESTS",
            "KINDS = ()\nCLAUSES = ()\nSUGGESTS = {}\n": "run",
        }
        for body, field in cases.items():
            with self.subTest(field=field), self.assertRaises(BadRemoteTest) as caught:
                self.load_broken(body)
            self.assertEqual(str(caught.exception), f"{BROKEN_PACKAGE}.broken has no {field}")

    def test_kinds_must_be_a_tuple_of_asset_kinds(self) -> None:
        for kinds in ("['INV']", "('INV',)", "[]"):
            body = (f"from solarpunk.leaf.codes import AssetKind\nKINDS = {kinds}\nCLAUSES = ()\nSUGGESTS = {{}}\n"
                    "def run(a, s): pass\n")
            with self.subTest(kinds=kinds), self.assertRaises(BadRemoteTest) as caught:
                self.load_broken(body)
            self.assertEqual(str(caught.exception), f"{BROKEN_PACKAGE}.broken: KINDS is not a tuple of AssetKind")

    def test_a_good_fixture_module_loads(self) -> None:
        found = self.load_broken("from solarpunk.leaf.codes import AssetKind\n"
                                 "KINDS = (AssetKind.METER,)\nCLAUSES = ('x',)\nSUGGESTS = {AssetKind.METER: 'MTR-001'}\n"
                                 "def run(a, s): pass\n")
        self.assertEqual(list(found), ["broken"])
        self.assertEqual(found["broken"].kinds, (AssetKind.METER,))
        self.assertEqual(found["broken"].suggestion(AssetKind.METER), "MTR-001")

    def test_a_rule_table_is_held_to_the_kinds_and_the_catalogue(self) -> None:
        """SP-015: a rule for every kind and no other, each code one of that kind's."""
        head = "from solarpunk.leaf.codes import AssetKind\nKINDS = (AssetKind.METER,)\nCLAUSES = ()\ndef run(a, s): pass\n"
        cases = {
            "SUGGESTS = {}": "SUGGESTS must give one rule for each of its KINDS",
            "SUGGESTS = {AssetKind.METER: None, AssetKind.SENSOR: None}": "SUGGESTS must give one rule for each of its KINDS",
            "SUGGESTS = {AssetKind.METER: 'INV-001'}": "SUGGESTS names INV-001, which is no METER code",
        }
        for rules, said in cases.items():
            with self.subTest(rules=rules), self.assertRaises(BadRemoteTest) as caught:
                self.load_broken(head + rules + "\n")
            self.assertEqual(str(caught.exception), f"{BROKEN_PACKAGE}.broken: {said}")


class Reachable(unittest.TestCase):
    def test_passes_with_records(self) -> None:
        samples = (reading(INV1, T0, 800.0, 60.0), gap(INV1.asset_id, T1))
        self.assertEqual(reachable.run(INV1, samples), Result(True, "2 records"))

    def test_fails_with_none(self) -> None:
        self.assertEqual(reachable.run(INV1, ()), Result(False, "no records"))

    def test_kinds_and_clauses(self) -> None:
        kinds = (AssetKind.INVERTER, AssetKind.METER, AssetKind.SENSOR, AssetKind.TRACKER)
        self.assertEqual((reachable.KINDS, reachable.CLAUSES), (kinds, ("55000-9.1",)))


class OnGrid(unittest.TestCase):
    def test_passes_on_the_grid_and_in_range(self) -> None:
        samples = (reading(INV1, T0, 1500.0, 0.0), gap(INV1.asset_id, T1))
        self.assertEqual(on_grid.run(INV1, samples), Result(True, "2 records on the grid and in range"))

    def test_an_empty_feed_has_no_data(self) -> None:
        """SP-039 reverses J-045's vacuous pass: nothing to check is no data, never a pass."""
        self.assertEqual(on_grid.run(SEN, ()), Result(False, "no records", no_data=True))

    def test_fails_naming_the_first_value_out_of_range(self) -> None:
        samples = (reading(INV1, T0, 800.0, 60.0), reading(INV1, T1, 1500.5, -1.0))
        expected = Result(False, f"{STAMP}: irradiance_w_m2 1500.5 out of range")
        self.assertEqual(on_grid.run(INV1, samples), expected)

    def test_fails_on_a_power_out_of_range(self) -> None:
        samples = (reading(INV1, T1, None, -1.0),)
        self.assertEqual(on_grid.run(INV1, samples), Result(False, f"{STAMP}: power_kw -1.0 out of range"))

    def test_fails_on_a_field_the_kind_does_not_answer(self) -> None:
        samples = (reading(TRK, T1, None, 5.0),)
        self.assertEqual(on_grid.run(TRK, samples), Result(False, f"{STAMP}: TRACKER has no field power_kw"))

    def test_fails_off_the_grid(self) -> None:
        samples = (reading(INV1, T0, 800.0, 60.0), off_grid(INV1))
        self.assertEqual(on_grid.run(INV1, samples), Result(False, "2026-06-01T10:02:00+00:00: off the grid"))

    def test_kinds_are_every_kind_with_a_feed(self) -> None:
        kinds = (AssetKind.INVERTER, AssetKind.TRACKER, AssetKind.METER, AssetKind.SENSOR)
        self.assertEqual(on_grid.KINDS, kinds)


class PowerUnderRated(unittest.TestCase):
    def test_passes_at_or_under_the_rating(self) -> None:
        samples = (reading(INV1, T0, 800.0, 100.0), gap(INV1.asset_id, T1))
        self.assertEqual(power_under_rated.run(INV1, samples), Result(True, "2 records at or under 100.0 kW"))

    def test_skips_a_record_with_no_power(self) -> None:
        samples = (reading(INV1, T0, 800.0, None),)
        self.assertEqual(power_under_rated.run(INV1, samples), Result(True, "1 records at or under 100.0 kW"))

    def test_fails_naming_the_first_excess(self) -> None:
        samples = (reading(INV1, T0, 800.0, 99.0), reading(INV1, T1, 900.0, 100.5))
        expected = Result(False, f"{STAMP}: power 100.5 kW over rated 100.0 kW")
        self.assertEqual(power_under_rated.run(INV1, samples), expected)

    def test_fails_with_no_rating(self) -> None:
        self.assertEqual(power_under_rated.run(UNRATED, ()), Result(False, "no rating"))

    def test_kinds_and_clauses(self) -> None:
        self.assertEqual((power_under_rated.KINDS, power_under_rated.CLAUSES), ((AssetKind.INVERTER,), ("9001-9.1.1",)))


class TheResultsTable(unittest.TestCase):
    def test_the_table_has_the_settled_columns(self) -> None:
        info = [tuple(row)[1:] for row in fresh().execute("PRAGMA table_info(results)")]
        self.assertEqual(info, [
            ("result_id", "INTEGER", 0, None, 1),
            ("test_name", "TEXT", 1, None, 0),
            ("asset_id", "TEXT", 1, None, 0),
            ("run_at", "TEXT", 1, None, 0),
            ("passed", "INTEGER", 1, None, 0),
            ("reason", "TEXT", 1, None, 0),
            ("no_data", "INTEGER", 1, "0", 0),
        ])

    def test_record_stores_iso_utc_text(self) -> None:
        conn = fresh()
        results.record(conn, "reachable", INV1.asset_id, T1, Result(True, "3 records"))
        rows = [tuple(row) for row in conn.execute("SELECT * FROM results")]
        self.assertEqual(rows, [(1, "reachable", INV1.asset_id, STAMP, 1, "3 records", 0)])

    def test_record_refuses_a_naive_instant(self) -> None:
        with self.assertRaises(NotUtc):
            results.record(fresh(), "reachable", INV1.asset_id, datetime(2026, 6, 1), Result(True, "x"))

    def test_latest_for_is_the_newest_run_failing_first(self) -> None:
        conn = fresh()
        results.record(conn, "reachable", INV1.asset_id, T0, Result(False, "old"))
        results.record(conn, "reachable", INV1.asset_id, T1, Result(True, "1 records"))
        results.record(conn, "power_under_rated", INV1.asset_id, T1, Result(True, "fine"))
        results.record(conn, "on_grid", INV1.asset_id, T1, Result(False, "bad"))
        results.record(conn, "reachable", INV2.asset_id, at(2026, 6, 1, 11, 0), Result(True, "other asset"))
        self.assertEqual(results.latest_for(conn, INV1.asset_id), (
            Recorded("on_grid", INV1.asset_id, T1, False, "bad"),
            Recorded("power_under_rated", INV1.asset_id, T1, True, "fine"),
            Recorded("reachable", INV1.asset_id, T1, True, "1 records"),
        ))
        self.assertEqual(results.latest_for(conn, SEN.asset_id), ())

    def test_last_run_at(self) -> None:
        conn = fresh()
        self.assertIsNone(results.last_run_at(conn))
        results.record(conn, "reachable", INV2.asset_id, T1, Result(True, "x"))
        results.record(conn, "reachable", INV1.asset_id, T0, Result(True, "x"))
        self.assertEqual(results.last_run_at(conn), T1)

    def test_stored_samples_and_asset(self) -> None:
        conn = fresh()
        fleet.load_fleet(conn, (SITE, WIRED))
        telemetry.store(conn, (gap(INV1.asset_id, T1), reading(INV1, T0, 800.0, 60.0)))
        self.assertEqual(results.stored_samples(conn, INV1.asset_id),
                         (reading(INV1, T0, 800.0, 60.0), gap(INV1.asset_id, T1)))
        self.assertEqual(results.stored_samples(conn, INV2.asset_id), ())
        self.assertEqual(results.stored_asset(conn, INV1.asset_id), WIRED)
        with self.assertRaises(NotStored) as caught:
            results.stored_asset(conn, INV2.asset_id)
        self.assertEqual(str(caught.exception), "OAHE-INV-002 is not stored")


class RunningTests(unittest.TestCase):
    def test_run_test_runs_a_discovered_test(self) -> None:
        self.assertEqual(run.run_test("reachable", INV1, ()), Result(False, "no records"))

    def test_run_test_refuses_an_unknown_name(self) -> None:
        with self.assertRaises(BadRemoteTest) as caught:
            run.run_test("no_such_test", INV1, ())
        self.assertEqual(str(caught.exception), "no remote test no_such_test")

    def test_run_test_refuses_an_asset_of_another_kind(self) -> None:
        with self.assertRaises(BadRemoteTest) as caught:
            run.run_test("power_under_rated", SEN, ())
        self.assertEqual(str(caught.exception), "power_under_rated does not run against a SENSOR")

    def test_status_of(self) -> None:
        good, bad = Result(True, "a"), Result(False, "b")
        self.assertIs(run.status_of(True, (good,)), AssetStatus.RED)
        self.assertIs(run.status_of(False, (good, bad)), AssetStatus.YELLOW)
        self.assertIs(run.status_of(False, (good, good)), AssetStatus.GREEN)
        self.assertIs(run.status_of(False, ()), AssetStatus.GREEN)

    def test_run_suite_stamps_each_asset(self) -> None:
        conn = fresh()
        samples = {
            INV1.asset_id: (reading(INV1, T0, 800.0, 60.0), gap(INV1.asset_id, T1)),
            INV2.asset_id: (reading(INV2, T0, 800.0, 101.0),),
        }
        statuses = run.run_suite(conn, (INV1, INV2, SEN), samples, {INV1.asset_id: False, SEN.asset_id: True}, T1)
        self.assertEqual(values(statuses), {INV1.asset_id: "green", INV2.asset_id: "yellow", SEN.asset_id: "red"})
        self.assertEqual(results.latest_for(conn, INV2.asset_id)[0],
                         Recorded("power_under_rated", INV2.asset_id, T1, False,
                                  "2026-06-01T10:00:00+00:00: power 101.0 kW over rated 100.0 kW"))
        latest = results.latest_for(conn, SEN.asset_id)
        self.assertEqual(sorted(r.test_name for r in latest), sorted(t.name for t in registry.tests_for(AssetKind.SENSOR)))
        # failing first, then no data, each by name (SP-039)
        self.assertEqual(latest, tuple(sorted(latest, key=lambda r: (r.passed, r.no_data, r.test_name))))
        self.assertFalse(next(r for r in latest if r.test_name == "reachable").passed)
        per_run = 2 * len(registry.tests_for(AssetKind.INVERTER)) + len(registry.tests_for(AssetKind.SENSOR))
        self.assertEqual(conn.execute("SELECT count(*) FROM results").fetchone()[0], per_run)  # every test of each kind
        self.assertEqual(results.last_run_at(conn), T1)

    def test_run_suite_with_no_flags_is_green(self) -> None:
        samples = {INV1.asset_id: (reading(INV1, T0, 800.0, 60.0),)}
        self.assertEqual(values(run.run_suite(fresh(), (INV1,), samples, {}, T0)), {INV1.asset_id: "green"})


class TheCommandLine(unittest.TestCase):
    def stored(self, root: str) -> str:
        """A store file under root holding the site, two inverters and INV1's samples; returns its path."""
        path = str(Path(root) / "store.db")
        conn = store.connect(path)
        store.apply(conn, fleet.schema() + telemetry.schema() + results.schema())
        fleet.load_fleet(conn, (SITE, INV1, INV2))
        telemetry.store(conn, (reading(INV1, T0, 800.0, 60.0), reading(INV1, T1, 800.0, 101.0)))
        conn.close()
        return path

    def verdict(self, argv: list[str]) -> tuple[int, str]:
        """main's exit code and output for argv."""
        out = io.StringIO()
        code = run.main(argv, out)
        return code, out.getvalue()

    def test_pass_and_fail(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            db = self.stored(root)
            self.assertEqual(self.verdict(["reachable", INV1.asset_id, "--db", db]), (0, "pass\n"))
            self.assertEqual(self.verdict(["reachable", INV2.asset_id, "--db", db]), (1, "fail no records\n"))
            self.assertEqual(self.verdict(["power_under_rated", INV1.asset_id, "--db", db]),
                             (1, f"fail {STAMP}: power 101.0 kW over rated 100.0 kW\n"))

    def test_errors(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            db = self.stored(root)
            self.assertEqual(self.verdict(["nope", INV1.asset_id, "--db", db]), (2, "error no remote test nope\n"))
            self.assertEqual(self.verdict(["reachable", SEN.asset_id, "--db", db]),
                             (2, "error OAHE-SEN-001 is not stored\n"))
            missing = str(Path(root) / "absent.db")
            self.assertEqual(self.verdict(["reachable", INV1.asset_id, "--db", missing]),
                             (2, f"error no store at {missing}\n"))
            self.assertFalse(Path(missing).exists())

    def test_the_store_is_required(self) -> None:
        with self.assertRaises(SystemExit), unittest.mock.patch("sys.stderr", io.StringIO()):
            run.main(["reachable", INV1.asset_id], io.StringIO())
