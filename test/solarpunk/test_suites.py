"""The suites folder (13.2, SP-019, SP-020): a suite is a module of declarations the registry finds and checks, the
scheduled run runs each suite due at its instant and stores its results carrying the suite, and `suite list|run|add`
manage them. Each hand-made suite lives in a scratch folder the registry is pointed at."""
import gc
import io
import socket
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from unittest import mock

from solarpunk import project
from solarpunk.cli import main as cli
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind
from solarpunk.remote import registry, results, suite_registry
from solarpunk.remote.registry import BadRemoteTest
from solarpunk.remote.suite_registry import Suite, discover_suites, due

SUITE = '''from solarpunk.leaf.codes import AssetKind

TESTS = ("reachable",)
KINDS = (AssetKind.INVERTER,)
SITES = ()
CADENCE = "hourly"
'''
RUN_AT = at(2026, 6, 1, 12)


def dead_port() -> int:
    """A port nothing listens on just now."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class Folder(unittest.TestCase):
    """A scratch suites folder the registry reads in place of the real one."""

    def setUp(self) -> None:
        """self.folder is empty and the registry's folder() points at it for the test."""
        gc.collect()  # an earlier test's unclosed store would warn on stderr
        self.folder = Path(tempfile.mkdtemp(prefix="suites-"))
        patched = mock.patch.object(suite_registry, "folder", return_value=self.folder)
        patched.start()
        self.addCleanup(patched.stop)

    def put(self, name: str, text: str = SUITE) -> None:
        """Writes <name>.py into the folder."""
        (self.folder / f"{name}.py").write_text(text, encoding="utf-8")


class TheRegistry(Folder):
    """The registry finds suites as it finds tests and refuses a bad one by name."""

    def test_with_no_file_the_only_suite_is_all_with_every_test_on_every_run(self) -> None:
        found = discover_suites()
        self.assertEqual(list(found), ["all"])
        self.assertEqual(found["all"].tests, tuple(registry.discover()))
        self.assertEqual(found["all"].cadence, "every run")

    def test_a_suite_file_is_found_after_all(self) -> None:
        self.put("hourly_check")
        found = discover_suites()
        self.assertEqual(found["hourly_check"], Suite("hourly_check", ("reachable",), (AssetKind.INVERTER,), (), "hourly"))
        self.assertEqual(list(found), ["all", "hourly_check"])

    def refused(self, text: str, words: str) -> None:
        """Whether a suite of this text raises BadRemoteTest saying words."""
        self.put("bad", text)
        with self.assertRaisesRegex(BadRemoteTest, words):
            discover_suites()

    def test_a_test_the_registry_lacks_is_refused(self) -> None:
        self.refused(SUITE.replace('"reachable"', '"nope"'), "nope")

    def test_a_kind_none_of_its_tests_runs_on_is_refused(self) -> None:
        self.refused(SUITE.replace("INVERTER", "SITE"), "SITE")

    def test_a_cadence_outside_the_closed_set_is_refused(self) -> None:
        for cadence in ("weekly", "daily at 24", "daily at 6", "Hourly"):
            self.refused(SUITE.replace('"hourly"', f'"{cadence}"'), "CADENCE")

    def test_a_missing_field_is_refused(self) -> None:
        self.refused(SUITE.replace('SITES = ()\n', ""), "bad has no SITES")

    def test_a_function_or_any_name_of_its_own_is_refused(self) -> None:
        self.refused(SUITE + "\n\ndef helper():\n    return 1\n", "helper of its own")
        self.refused(SUITE + "\nEXTRA = 1\n", "EXTRA of its own")

    def test_a_file_named_all_is_refused(self) -> None:
        self.put("all")
        with self.assertRaisesRegex(BadRemoteTest, "default suite"):
            discover_suites()

    def test_a_suite_reaches_its_kinds_and_sites(self) -> None:
        inverter = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", None, "I", 1.0)
        meter = Asset("OAHE-MTR-001", AssetKind.METER, "OAHE", None, "M", None)
        suite = Suite("x", ("reachable",), (AssetKind.INVERTER,), ("OAHE",), "hourly")
        self.assertTrue(suite.reaches(inverter))
        self.assertFalse(suite.reaches(meter))
        self.assertFalse(Suite("x", ("reachable",), (), ("BIGS",), "hourly").reaches(inverter))
        self.assertTrue(Suite("x", ("reachable",), (), (), "hourly").reaches(meter))


class TheCadence(unittest.TestCase):
    """When a suite is due at an instant."""

    def suite(self, cadence: str) -> Suite:
        """A suite of that cadence."""
        return Suite("x", ("reachable",), (), (), cadence)

    def test_every_run_and_a_suite_never_run_are_always_due(self) -> None:
        self.assertTrue(due(self.suite("every run"), RUN_AT, RUN_AT))
        self.assertTrue(due(self.suite("hourly"), None, RUN_AT))

    def test_hourly_is_due_once_the_hour_has_turned(self) -> None:
        self.assertFalse(due(self.suite("hourly"), at(2026, 6, 1, 12, 5), at(2026, 6, 1, 12, 30)))
        self.assertTrue(due(self.suite("hourly"), at(2026, 6, 1, 11, 55), at(2026, 6, 1, 12, 0)))

    def test_daily_is_due_once_since_the_hour_each_day(self) -> None:
        daily = self.suite("daily at 06")
        self.assertFalse(due(daily, at(2026, 6, 1, 6, 5), at(2026, 6, 1, 18)))
        self.assertTrue(due(daily, at(2026, 6, 1, 6, 5), at(2026, 6, 2, 6, 0)))
        self.assertFalse(due(daily, at(2026, 6, 1, 6, 5), at(2026, 6, 2, 5, 55)))
        self.assertTrue(due(daily, at(2026, 6, 1, 5, 0), at(2026, 6, 1, 6, 0)))


class TheStoreRuns(Folder):
    """The scheduled run and `suite run` over a store of one inverter whose port nobody listens on."""

    def setUp(self) -> None:
        """A store with a site and an inverter."""
        super().setUp()
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        site = Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None)
        inverter = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "I1", 100.0, "127.0.0.1",
                         dead_port())
        project.load_fleet(self.conn, (site, inverter))

    def rows(self, suite: str) -> int:
        """The results the suite stored."""
        return self.conn.execute("SELECT count(*) FROM results WHERE suite = ?", (suite,)).fetchone()[0]

    def test_with_only_the_default_suite_the_run_is_as_before(self) -> None:
        report = project.scheduled_run(self.conn, RUN_AT)
        tests = len(registry.tests_for(AssetKind.INVERTER))
        self.assertEqual(report.results, 1 + tests)
        self.assertEqual(self.rows("all"), 1 + tests)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM results WHERE suite != 'all'").fetchone()[0], 0)

    def test_a_suite_due_runs_and_its_results_carry_it_and_it_waits_for_its_cadence(self) -> None:
        self.put("hourly_check")
        project.scheduled_run(self.conn, RUN_AT)
        self.assertEqual(self.rows("hourly_check"), 1)
        project.scheduled_run(self.conn, RUN_AT + timedelta(minutes=10))
        self.assertEqual(self.rows("hourly_check"), 1)
        project.scheduled_run(self.conn, RUN_AT + timedelta(hours=1))
        self.assertEqual(self.rows("hourly_check"), 2)
        self.assertEqual(results.last_run_of(self.conn, "hourly_check"), RUN_AT + timedelta(hours=1))
        self.assertIsNone(results.last_run_of(self.conn, "nobody"))

    def test_suite_run_runs_one_now_and_an_unknown_name_is_refused(self) -> None:
        self.put("hourly_check")
        suite, written = project.run_suite_now(self.conn, "hourly_check", RUN_AT)
        self.assertEqual((suite.name, written, self.rows("hourly_check")), ("hourly_check", 1, 1))
        with self.assertRaisesRegex(BadRemoteTest, "no suite nope"):
            project.run_suite_now(self.conn, "nope", RUN_AT)

    def test_a_results_table_made_before_suites_reads_every_row_as_all(self) -> None:
        old = sqlite3.connect(":memory:")
        self.addCleanup(old.close)
        old.execute("CREATE TABLE results (result_id INTEGER PRIMARY KEY, test_name TEXT NOT NULL, asset_id TEXT NOT NULL,"
                    " run_at TEXT NOT NULL, passed INTEGER NOT NULL, reason TEXT NOT NULL, no_data INTEGER NOT NULL DEFAULT 0)")
        old.execute("INSERT INTO results (test_name, asset_id, run_at, passed, reason) VALUES"
                    " ('reachable', 'A', '2026-06-01T10:00:00+00:00', 1, 'ok')")
        results.upgrade(old)
        self.assertEqual(results.results_of(old, "A")[0].suite, "all")


class TheCommands(Folder):
    """suite list, add and run from the command line."""

    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        """The command's exit code, stdout and stderr."""
        out, err = io.StringIO(), io.StringIO()
        return cli.main(argv, out, err), out.getvalue(), err.getvalue()

    def test_list_prints_each_suite_with_its_tests_and_cadence(self) -> None:
        self.put("hourly_check")
        code, out, _ = self.run_cli(["suite", "list"])
        lines = out.splitlines()
        self.assertEqual(code, 0)
        self.assertTrue(lines[0].startswith("all  irradiance_in_range,") and lines[0].endswith("  every run"))
        self.assertEqual(lines[1], "hourly_check  reachable  hourly")

    def test_add_writes_a_suite_the_registry_then_finds(self) -> None:
        code, out, _ = self.run_cli(["suite", "add", "daily_check", "--test", "reachable", "--test", "on_grid",
                                    "--kind", "INVERTER", "--cadence", "daily at 06"])
        self.assertEqual(code, 0)
        self.assertEqual(out, f"wrote {self.folder / 'daily_check.py'}\n")
        self.assertEqual(discover_suites()["daily_check"],
                         Suite("daily_check", ("reachable", "on_grid"), (AssetKind.INVERTER,), (), "daily at 06"))

    def test_add_refuses_what_the_registry_would_and_writes_nothing(self) -> None:
        for argv in (("bad", "--test", "nope"), ("bad", "--test", "reachable", "--cadence", "weekly"),
                     ("bad", "--test", "reachable", "--kind", "PANEL"), ("all", "--test", "reachable"),
                     ("Bad-Name", "--test", "reachable")):
            code, _, err = self.run_cli(["suite", "add", *argv])
            self.assertEqual((code, err.startswith("error: ")), (2, True), argv)
        self.assertEqual(list(self.folder.iterdir()), [])
        self.put("taken")
        self.assertEqual(self.run_cli(["suite", "add", "taken", "--test", "reachable"])[0], 2)

    def test_run_runs_one_suite_over_the_store(self) -> None:
        self.put("hourly_check")
        store = str(self.folder / "s.db")
        with closing(project.open_or_create(store)) as conn:
            project.load_fleet(conn, (Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", None, "I", 1.0, "127.0.0.1",
                                            dead_port()),))
        code, out, _ = self.run_cli(["suite", "run", "hourly_check", "--at", RUN_AT.isoformat(), "--db", store])
        self.assertEqual((code, out), (0, f"suite hourly_check {RUN_AT.isoformat()}: results 1\n"))
        self.assertEqual(self.run_cli(["suite", "run", "nope", "--db", store])[0], 2)
