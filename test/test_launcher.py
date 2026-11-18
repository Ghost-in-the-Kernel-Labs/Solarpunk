"""solarpunk.cmd, the one-word launcher on Windows: the first words it sends to the command line are exactly the
command line's own subcommands, so a subcommand added to solarpunk/cli is added here or this fails; every other first
word, and none, opens the window. No Windows shell runs here: the file is read, its routing line held to the parser."""
import io
import re
import unittest
from pathlib import Path

from solarpunk.cli import main as cli

LAUNCHER = Path(__file__).resolve().parents[1] / "solarpunk.cmd"
ROUTE = re.compile(r'^for %%c in \(([a-z ]+)\) do if "%~1"=="%%c" set "SOLARPUNK_MODULE=solarpunk\.cli"$', re.MULTILINE)


def subcommands() -> list[str]:
    """The command line's top-level subcommands, sorted: ["clauses", "fault", "fleet", "help", "kpi", "telemetry",
    "test"]."""
    actions = cli.build_parser()._subparsers._group_actions
    return sorted(actions[0].choices)


class TheLauncher(unittest.TestCase):
    def test_it_routes_exactly_the_command_lines_subcommands(self) -> None:
        routed = ROUTE.findall(LAUNCHER.read_text(encoding="utf-8"))
        self.assertEqual(len(routed), 1)
        self.assertEqual(sorted(routed[0].split()), subcommands())

    def test_the_window_is_the_default_and_every_argument_is_passed(self) -> None:
        lines = LAUNCHER.read_text(encoding="utf-8").splitlines()
        self.assertIn('set "SOLARPUNK_MODULE=solarpunk.ui"', lines)
        run = "if defined SOLARPUNK_HELP (py -m solarpunk.cli help) else (py -m %SOLARPUNK_MODULE% %*)"
        self.assertIn(run, lines)
        self.assertLess(lines.index('set "SOLARPUNK_MODULE=solarpunk.ui"'), lines.index(run))

    def test_the_help_flags_ask_the_command_line_for_its_list(self) -> None:
        lines = LAUNCHER.read_text(encoding="utf-8").splitlines()
        flags = 'for %%h in (--help -h) do if "%~1"=="%%h" set "SOLARPUNK_HELP=yes"'
        self.assertIn(flags, lines)
        self.assertEqual(lines.index(flags), lines.index('set "SOLARPUNK_HELP="') + 1)
        self.assertEqual(cli.main(["help"], io.StringIO(), io.StringIO()), 0)

    def test_it_has_no_label_to_lose_under_unix_line_endings(self) -> None:
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertNotIn("goto", text.lower())
        self.assertIsNone(re.search(r"^:", text, re.MULTILINE))
