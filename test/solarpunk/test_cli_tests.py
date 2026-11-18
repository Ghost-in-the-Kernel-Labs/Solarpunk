"""The CLI's test subcommands (the remote tests' own): test list's lines, test add's call into project and its two
lines, test run's report over a small fleet whose one feed does not answer, at an instant given and at now."""
import argparse
import gc
import io
import socket
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from solarpunk import project
from solarpunk.cli import main as cli
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind

RUN_AT = "2026-06-01T13:00:00+00:00"
LOCAL = "127.0.0.1"
SITE = Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None)
TEST_LIST = [
    "on_grid  INV,TRK,MTR,SEN  55000-7.5,9001-9.1.3",
    "power_under_rated  INV  9001-9.1.1",
    "reachable  INV,MTR,SEN,TRK  55000-9.1",
]


def leaves(parser: argparse.ArgumentParser, path: tuple[str, ...]) -> list[str]:
    """Every command a parser reaches, as typed: leaves(cli.build_parser(), ()) holds "fleet list", "test add" and
    "clauses"; a parser with no subcommands is its own path."""
    nested = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]
    if not nested:
        return [" ".join(path)]
    found: list[str] = []
    for name, child in nested[0].choices.items():
        found.extend(leaves(child, (*path, name)))
    return found


def free_port() -> int:
    """A local port nothing listens on, found by binding and closing: free_port() is, say, 49213."""
    with socket.socket() as probe:
        probe.bind((LOCAL, 0))
        return probe.getsockname()[1]


class TestCommands(unittest.TestCase):
    """A test case with a store path of its own, self.db, in a folder removed when it ends."""

    def setUp(self) -> None:
        """A fresh folder; self.db is a store path in it that does not exist yet. Garbage is collected first: a store
        an earlier test file left unclosed warns when it is collected, and the CLI's redirected stderr would hold it."""
        gc.collect()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "fleet.db")

    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        """main as typed: self.run_cli(["test", "list"])[0] is 0."""
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(argv, out, err)
        return code, out.getvalue(), err.getvalue()

    def load(self) -> int:
        """Stores the site and one inverter whose feed is a closed local port, and returns that port."""
        port = free_port()
        inverter = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 1", 100.0, LOCAL, port)
        conn = project.open_or_create(self.db)
        project.load_fleet(conn, (SITE, inverter))
        conn.close()
        return port

    def report(self, port: int, run_at: str) -> str:
        """What test run prints for load's fleet at an instant: its first line is "run <run_at>: pinged 1, records 0,
        results 4" (the failing reachable and the inverter's three tests)."""
        return (f"run {run_at}: pinged 1, records 0, results 4\nOAHE-INV-001  yellow\nOAHE-SIT-001  green\n"
                f"error OAHE-INV-001: {LOCAL}:{port} is unreachable\n")


class ListAndAdd(TestCommands):
    def test_list_prints_each_test_with_its_kinds_and_clauses(self) -> None:
        code, out, err = self.run_cli(["--db", self.db, "test", "list"])
        self.assertEqual((code, out.splitlines(), err), (0, TEST_LIST, ""))
        self.assertFalse(Path(self.db).exists())

    def test_add_calls_project_and_says_what_it_wrote(self) -> None:
        with mock.patch.object(cli.project, "add_remote_test", return_value=Path("tests/tracker_moving.py")) as add:
            code, out, err = self.run_cli(["--db", self.db, "test", "add", "tracker_moving", "--clause", "55000-9.1",
                                           "--clause", "9001-9.1.1", "--kind", "TRACKER", "--kind", "METER"])
        add.assert_called_once_with("tracker_moving", ("TRACKER", "METER"), ("55000-9.1", "9001-9.1.1"))
        wrote = f"wrote {Path('tests/tracker_moving.py')}\n"
        self.assertEqual((code, out, err),
                         (0, wrote + "tracker_moving fails on every run until its run function is written\n", ""))
        self.assertFalse(Path(self.db).exists())

    def test_add_with_no_kind_named_passes_none(self) -> None:
        with mock.patch.object(cli.project, "add_remote_test", return_value=Path("x")) as add:
            self.run_cli(["test", "add", "tracker_moving", "--clause", "55000-9.1"])
        add.assert_called_once_with("tracker_moving", (), ("55000-9.1",))

    def test_a_refused_add_is_an_error(self) -> None:
        code, out, err = self.run_cli(["test", "add", "reachable", "--clause", "55000-9.1"])
        self.assertEqual((code, out, err), (2, "", "error: reachable already exists\n"))

    def test_add_needs_a_clause_and_test_needs_a_subcommand(self) -> None:
        for argv in (["test", "add", "tracker_moving"], ["test"]):
            with self.subTest(argv=argv):
                code, out, err = self.run_cli(argv)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("error: the following arguments are required", err)


class Run(TestCommands):
    def test_run_at_an_instant_prints_the_report(self) -> None:
        port = self.load()
        self.assertEqual(self.run_cli(["test", "run", "--db", self.db, "--at", RUN_AT]),
                         (0, self.report(port, RUN_AT), ""))

    def test_the_store_may_be_named_before_the_subcommand(self) -> None:
        port = self.load()
        self.assertEqual(self.run_cli(["--db", self.db, "test", "run", "--at", RUN_AT]),
                         (0, self.report(port, RUN_AT), ""))

    def test_run_with_no_instant_runs_now_in_utc_to_the_second(self) -> None:
        port = self.load()
        before = datetime.now(timezone.utc)
        code, out, err = self.run_cli(["test", "run", "--db", self.db])
        stamp = out.split()[1].rstrip(":")
        ran = datetime.fromisoformat(stamp)
        self.assertEqual((code, out, err), (0, self.report(port, stamp), ""))
        self.assertEqual((ran.utcoffset(), ran.microsecond), (timedelta(0), 0))
        self.assertLessEqual(before - timedelta(seconds=1), ran)
        self.assertLessEqual(ran, datetime.now(timezone.utc))

    def test_the_run_is_recorded_in_the_store(self) -> None:
        self.load()
        self.run_cli(["test", "run", "--db", self.db, "--at", RUN_AT])
        code, out, err = self.run_cli(["--db", self.db, "fleet", "list"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines(), ["OAHE-INV-001  INV  Inverter 1  yellow", "OAHE-SIT-001  SIT  Oahe  green"])

    def test_a_naive_instant_is_refused(self) -> None:
        self.load()
        code, out, err = self.run_cli(["test", "run", "--db", self.db, "--at", "2026-06-01T13:00:00"])
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("error: "))


class Help(TestCommands):
    def test_help_prints_the_list_and_opens_no_store(self) -> None:
        code, out, err = self.run_cli(["--db", self.db, "help"])
        self.assertEqual((code, out, err), (0, cli.HELP, ""))
        self.assertFalse(Path(self.db).exists())

    def test_the_list_names_the_window_and_starts_plainly(self) -> None:
        lines = cli.HELP.splitlines()
        self.assertTrue(lines[0].startswith("Solarpunk: the commands."))
        for typed in ("solarpunk", "solarpunk --demo", "solarpunk --db PATH", "solarpunk --help"):
            with self.subTest(typed=typed):
                self.assertEqual(len([line for line in lines if line.startswith(f"  {typed}  ")]), 1)

    def test_every_command_of_the_parser_has_exactly_one_line(self) -> None:
        commands = leaves(cli.build_parser(), ())
        self.assertEqual(len(commands), 12)
        lines = cli.HELP.splitlines()
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(len([line for line in lines if line.startswith(f"  {command} ")]), 1)

    def test_no_line_names_a_command_the_parser_lacks(self) -> None:
        commands = leaves(cli.build_parser(), ())
        listed = [line for line in cli.HELP.splitlines() if line.startswith("  ") and not line.startswith("  solarpunk")]
        self.assertEqual(len(listed), len(commands))
