"""The clock holds its renderings (SP-006): every cadence to its crontab line and schtasks command by hand, every bad
field refused with its reason, the three demo jobs byte for byte against both goldens, the argument lists install and
remove would run on "linux" and "win32", and the render command. install and remove themselves are never called."""
import io
import tempfile
import unittest
from pathlib import Path

from solarpunk.schedule import jobs
from solarpunk.schedule.__main__ import build_parser, main
from solarpunk.schedule.jobs import BadJob, Job

GOLDENS = Path(__file__).resolve().parent / "goldens"
CRONTAB = GOLDENS / "schedule-crontab.txt"
SCHTASKS = GOLDENS / "schedule-schtasks.txt"


def job(cadence: str, name: str = "ab", command: str = "run it") -> Job:
    """A job for a test: job("hourly").name is "ab"."""
    return Job(name, command, cadence)


def run(argv: list[str]) -> tuple[int, str, str]:
    """Runs the render command: run(["render", "solarpunk-kpi"])[0] is 0."""
    out, err = io.StringIO(), io.StringIO()
    return main(argv, out, err), out.getvalue(), err.getvalue()


class TheCadence(unittest.TestCase):
    def test_parts_by_hand(self) -> None:
        self.assertEqual(jobs.cadence_parts("hourly"), ("hourly", 0, 0))
        self.assertEqual(jobs.cadence_parts("daily@06:30"), ("daily", 6, 30))
        self.assertEqual(jobs.cadence_parts("daily@00:00"), ("daily", 0, 0))
        self.assertEqual(jobs.cadence_parts("daily@23:59"), ("daily", 23, 59))
        self.assertEqual(jobs.cadence_parts("daily@19:09"), ("daily", 19, 9))
        self.assertEqual(jobs.cadence_parts("every:1"), ("every", 1, 0))
        self.assertEqual(jobs.cadence_parts("every:59"), ("every", 59, 0))

    def test_a_bad_form_is_refused_with_the_reason(self) -> None:
        for cadence in ("", "Hourly", "hourly ", "daily@6:00", "daily@24:00", "daily@12:60", "daily@12:00x",
                        "xdaily@12:00", "every:0", "every:05", "every:100", "every:", "every:1x", "weekly"):
            with self.assertRaises(BadJob) as refused:
                jobs.cadence_parts(cadence)
            self.assertEqual(str(refused.exception), f"cadence {cadence!r} must be hourly, daily@HH:MM (00:00 to "
                             "23:59) or every:N (N minutes, 1 to 59)", cadence)

    def test_more_than_59_minutes_is_refused_with_the_reason(self) -> None:
        for cadence in ("every:60", "every:99"):
            with self.assertRaises(BadJob) as refused:
                jobs.cadence_parts(cadence)
            self.assertEqual(str(refused.exception), f"cadence {cadence!r} must run every 1 to 59 minutes")

    def test_a_bad_job_is_a_value_error(self) -> None:
        self.assertTrue(issubclass(BadJob, ValueError))


class TheJob(unittest.TestCase):
    def test_a_good_job_keeps_its_fields_and_is_frozen(self) -> None:
        made = Job("solarpunk-kpi", "run it", "daily@06:00")
        self.assertEqual((made.name, made.command, made.cadence), ("solarpunk-kpi", "run it", "daily@06:00"))
        with self.assertRaises(AttributeError):
            made.name = "other"  # type: ignore[misc]

    def test_names_at_the_edges_are_taken(self) -> None:
        for name in ("ab", "a1", "a-", "a" + "b" * 40, "z9-0"):
            self.assertEqual(job("hourly", name).name, name)

    def test_a_bad_name_is_refused_with_the_reason(self) -> None:
        for name in ("a", "", "Ab", "1a", "-a", "a_b", "a b", "a" + "b" * 41, "ab\n", "aB"):
            with self.assertRaises(BadJob) as refused:
                job("hourly", name)
            self.assertEqual(str(refused.exception), f"job name {name!r} must match [a-z][a-z0-9-]{{1,40}}", name)

    def test_a_bad_command_is_refused_with_the_reason(self) -> None:
        for command in ("", "a\nb", "a\rb", 'say "hi"', "date +%F"):
            with self.assertRaises(BadJob) as refused:
                job("hourly", command=command)
            self.assertEqual(str(refused.exception), f"job command {command!r} must be non-empty and hold no "
                             "newline, double quote or percent sign", command)

    def test_a_bad_cadence_is_refused_when_the_job_is_made(self) -> None:
        with self.assertRaises(BadJob):
            job("every:0")


class TheCrontabLine(unittest.TestCase):
    def test_each_cadence_by_hand(self) -> None:
        self.assertEqual(jobs.crontab_line(job("hourly")), "0 * * * * run it # solarpunk:ab")
        self.assertEqual(jobs.crontab_line(job("daily@06:05")), "05 06 * * * run it # solarpunk:ab")
        self.assertEqual(jobs.crontab_line(job("daily@23:00")), "00 23 * * * run it # solarpunk:ab")
        self.assertEqual(jobs.crontab_line(job("every:15")), "*/15 * * * * run it # solarpunk:ab")
        self.assertEqual(jobs.crontab_line(job("every:7")), "*/7 * * * * run it # solarpunk:ab")


class TheSchtasksCommand(unittest.TestCase):
    def test_each_cadence_by_hand(self) -> None:
        start = 'schtasks /Create /F /TN "Solarpunk\\ab" '
        self.assertEqual(jobs.schtasks_command(job("hourly")), start + '/SC HOURLY /TR "run it"')
        self.assertEqual(jobs.schtasks_command(job("daily@06:05")), start + '/SC DAILY /ST 06:05 /TR "run it"')
        self.assertEqual(jobs.schtasks_command(job("daily@23:00")), start + '/SC DAILY /ST 23:00 /TR "run it"')
        self.assertEqual(jobs.schtasks_command(job("every:7")), start + '/SC MINUTE /MO 7 /TR "run it"')


class TheHostCommands(unittest.TestCase):
    def test_install_on_windows_is_schtasks_create(self) -> None:
        self.assertEqual(jobs.install_command(job("daily@06:05"), "win32"),
                         ["schtasks", "/Create", "/F", "/TN", "Solarpunk\\ab", "/SC", "DAILY", "/ST", "06:05",
                          "/TR", "run it"])
        self.assertEqual(jobs.install_command(job("every:7"), "win32")[5:9], ["/SC", "MINUTE", "/MO", "7"])

    def test_remove_on_windows_is_schtasks_delete(self) -> None:
        self.assertEqual(jobs.remove_command(job("hourly"), "win32"),
                         ["schtasks", "/Delete", "/F", "/TN", "Solarpunk\\ab"])

    def test_install_on_linux_replaces_the_jobs_line(self) -> None:
        self.assertEqual(jobs.install_command(job("hourly"), "linux"),
                         ["sh", "-c", "(crontab -l 2>/dev/null | grep -v ' # solarpunk:ab$'; "
                          "echo '0 * * * * run it # solarpunk:ab') | crontab -"])

    def test_remove_on_linux_drops_the_jobs_line(self) -> None:
        self.assertEqual(jobs.remove_command(job("hourly"), "linux"),
                         ["sh", "-c", "crontab -l 2>/dev/null | grep -v ' # solarpunk:ab$' | crontab -"])

    def test_the_marker_pattern_is_quoted_and_anchored(self) -> None:
        self.assertEqual(jobs.marker_pattern(job("hourly", "solarpunk-kpi")), "' # solarpunk:solarpunk-kpi$'")

    def test_shown_is_one_shell_line(self) -> None:
        self.assertEqual(jobs.shown(["sh", "-c", "crontab -l"]), "sh -c 'crontab -l'")
        self.assertEqual(jobs.shown(jobs.remove_command(job("hourly"), "win32")),
                         "schtasks /Delete /F /TN 'Solarpunk\\ab'")


class TheGoldens(unittest.TestCase):
    def test_the_demo_jobs(self) -> None:
        self.assertEqual([(made.name, made.cadence) for made in jobs.demo_jobs()],
                         [("solarpunk-ping", "every:15"), ("solarpunk-kpi", "daily@06:00"),
                          ("solarpunk-clauses", "hourly")])
        self.assertEqual(jobs.demo_jobs()[0].command, "python -m solarpunk.cli telemetry generate OAHE today --seed 7")

    def test_the_crontab_golden_regenerates_byte_for_byte(self) -> None:
        self.assertEqual(jobs.crontab_golden().encode("utf-8"), CRONTAB.read_bytes())

    def test_the_schtasks_golden_regenerates_byte_for_byte(self) -> None:
        self.assertEqual(jobs.schtasks_golden().encode("utf-8"), SCHTASKS.read_bytes())

    def test_the_goldens_hold_three_lines_by_hand(self) -> None:
        self.assertEqual(CRONTAB.read_text().splitlines()[1],
                         "00 06 * * * python -m solarpunk.cli kpi OAHE yesterday today # solarpunk:solarpunk-kpi")
        self.assertEqual(SCHTASKS.read_text().splitlines()[2],
                         'schtasks /Create /F /TN "Solarpunk\\solarpunk-clauses" /SC HOURLY '
                         '/TR "python -m solarpunk.cli clauses"')
        self.assertEqual(len(CRONTAB.read_text().splitlines()), 3)
        self.assertEqual(len(SCHTASKS.read_text().splitlines()), 3)

    def test_write_goldens_writes_both_identically(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            written = jobs.write_goldens(Path(folder))
            self.assertEqual(written, (Path(folder) / "schedule-crontab.txt", Path(folder) / "schedule-schtasks.txt"))
            self.assertEqual(written[0].read_bytes(), CRONTAB.read_bytes())
            self.assertEqual(written[1].read_bytes(), SCHTASKS.read_bytes())

    def test_the_goldens_folder_is_the_tests(self) -> None:
        self.assertEqual(jobs.GOLDENS, GOLDENS)


class TheRenderCommand(unittest.TestCase):
    def test_render_prints_both_renderings(self) -> None:
        self.assertEqual(run(["render", "solarpunk-clauses"]),
                         (0, "0 * * * * python -m solarpunk.cli clauses # solarpunk:solarpunk-clauses\n"
                          'schtasks /Create /F /TN "Solarpunk\\solarpunk-clauses" /SC HOURLY '
                          '/TR "python -m solarpunk.cli clauses"\n', ""))

    def test_an_unknown_job_is_refused(self) -> None:
        self.assertEqual(run(["render", "solarpunk-nope"]), (2, "", "no demo job named 'solarpunk-nope'\n"))

    def test_render_without_a_target_is_refused(self) -> None:
        self.assertEqual(run(["render"]), (2, "", "render needs a demo job's name or --golden <folder>\n"))

    def test_render_golden_writes_both_and_prints_their_paths(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            code, out, err = run(["render", "--golden", folder])
            self.assertEqual((code, err), (0, ""))
            self.assertEqual(out, f"{Path(folder) / 'schedule-crontab.txt'}\n{Path(folder) / 'schedule-schtasks.txt'}\n")
            self.assertEqual((Path(folder) / "schedule-schtasks.txt").read_bytes(), SCHTASKS.read_bytes())

    def test_the_parser_names_the_subcommand(self) -> None:
        parsed = build_parser().parse_args(["render", "solarpunk-kpi"])
        self.assertEqual((parsed.command, parsed.name, parsed.golden), ("render", "solarpunk-kpi", None))

    def test_no_subcommand_exits(self) -> None:
        with self.assertRaises(SystemExit):
            run([])
