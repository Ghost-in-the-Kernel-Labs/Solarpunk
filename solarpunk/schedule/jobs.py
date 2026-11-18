"""One Job rendered for the platform's scheduler (SP-006): `crontab_line` for cron, `schtasks_command` for Windows Task
Scheduler, each held against a golden; `install_command` and `remove_command` build the argument list `install` and
`remove` run. Only `install` and `remove` touch the host, and no test calls them (F-03)."""
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

GOLDENS = Path(__file__).resolve().parents[2] / "test" / "solarpunk" / "goldens"
CRONTAB_GOLDEN = "schedule-crontab.txt"
SCHTASKS_GOLDEN = "schedule-schtasks.txt"

NAME_PATTERN = r"[a-z][a-z0-9-]{1,40}"
DAILY_PATTERN = r"daily@([01][0-9]|2[0-3]):([0-5][0-9])"
EVERY_PATTERN = r"every:([1-9][0-9]?)"
HOURLY = "hourly"
DAILY = "daily"
EVERY = "every"
FORBIDDEN_IN_COMMAND = ("\n", "\r", '"', "%")

BAD_NAME = "job name {!r} must match {}"
BAD_COMMAND = "job command {!r} must be non-empty and hold no newline, double quote or percent sign"
BAD_CADENCE = "cadence {!r} must be hourly, daily@HH:MM (00:00 to 23:59) or every:N (N minutes, 1 to 59)"
BAD_MINUTES = "cadence {!r} must run every 1 to 59 minutes"

MARKER = " # solarpunk:{}"
TASK_NAME = "Solarpunk\\{}"
SCHTASKS = "schtasks"
WINDOWS = "win32"
CRONTAB_INSTALL = "(crontab -l 2>/dev/null | grep -v {}; echo {}) | crontab -"
CRONTAB_REMOVE = "crontab -l 2>/dev/null | grep -v {} | crontab -"

PING_COMMAND = "python -m solarpunk.cli telemetry generate OAHE today --seed 7"
KPI_COMMAND = "python -m solarpunk.cli kpi OAHE yesterday today"
CLAUSES_COMMAND = "python -m solarpunk.cli clauses"


class BadJob(ValueError):
    """A job the schedulers cannot take: Job("Ping", "x", "hourly") raises BadJob naming the name rule."""


def cadence_parts(cadence: str) -> tuple[str, int, int]:
    """The cadence as (kind, first, second): "hourly" gives ("hourly", 0, 0), "daily@06:30" gives ("daily", 6, 30),
    "every:15" gives ("every", 15, 0); anything else raises BadJob with the reason."""
    if cadence == HOURLY:
        return HOURLY, 0, 0
    daily = re.fullmatch(DAILY_PATTERN, cadence)
    if daily:
        return DAILY, int(daily.group(1)), int(daily.group(2))
    every = re.fullmatch(EVERY_PATTERN, cadence)
    if not every:
        raise BadJob(BAD_CADENCE.format(cadence))
    minutes = int(every.group(1))
    if minutes > 59:
        raise BadJob(BAD_MINUTES.format(cadence))
    return EVERY, minutes, 0


@dataclass(frozen=True)
class Job:
    """One scheduled job: Job("solarpunk-kpi", "python -m solarpunk.cli kpi OAHE", "daily@06:00") renders to
    "00 06 * * * python -m solarpunk.cli kpi OAHE # solarpunk:solarpunk-kpi"; a bad field raises BadJob."""

    name: str
    command: str
    cadence: str

    def __post_init__(self) -> None:
        """Refuses a bad field: Job("x", "y", "hourly") raises BadJob, since a name needs two characters."""
        if not re.fullmatch(NAME_PATTERN, self.name):
            raise BadJob(BAD_NAME.format(self.name, NAME_PATTERN))
        if not self.command or any(mark in self.command for mark in FORBIDDEN_IN_COMMAND):
            raise BadJob(BAD_COMMAND.format(self.command))
        cadence_parts(self.cadence)


def crontab_line(job: Job) -> str:
    """The job's crontab line: every:15 gives "*/15 * * * * <command> # solarpunk:<name>", hourly "0 * * * * ...",
    daily@06:00 "00 06 * * * ..."."""
    kind, first, second = cadence_parts(job.cadence)
    when = {HOURLY: "0 * * * *", DAILY: f"{second:02d} {first:02d} * * *", EVERY: f"*/{first} * * * *"}[kind]
    return f"{when} {job.command}{MARKER.format(job.name)}"


def schedule_arguments(job: Job) -> list[str]:
    """The schtasks /SC part as arguments: hourly gives ["/SC", "HOURLY"], daily@06:00 ["/SC", "DAILY", "/ST", "06:00"],
    every:15 ["/SC", "MINUTE", "/MO", "15"]."""
    kind, first, second = cadence_parts(job.cadence)
    if kind == HOURLY:
        return ["/SC", "HOURLY"]
    if kind == DAILY:
        return ["/SC", "DAILY", "/ST", f"{first:02d}:{second:02d}"]
    return ["/SC", "MINUTE", "/MO", str(first)]


def schtasks_command(job: Job) -> str:
    """The job's schtasks command: hourly gives
    'schtasks /Create /F /TN "Solarpunk\\<name>" /SC HOURLY /TR "<command>"'."""
    schedule = " ".join(schedule_arguments(job))
    return f'{SCHTASKS} /Create /F /TN "{TASK_NAME.format(job.name)}" {schedule} /TR "{job.command}"'


def marker_pattern(job: Job) -> str:
    """The grep pattern for the job's crontab lines: solarpunk-kpi gives "' # solarpunk:solarpunk-kpi$'" (quoted)."""
    return shlex.quote(MARKER.format(job.name) + "$")


def install_command(job: Job, platform: str) -> list[str]:
    """What install runs: on "win32" ["schtasks", "/Create", "/F", "/TN", "Solarpunk\\<name>", "/SC", ..., "/TR",
    "<command>"]; elsewhere ["sh", "-c", <the crontab without the job's old line, plus its new line, piped to crontab ->]."""
    if platform == WINDOWS:
        task = [SCHTASKS, "/Create", "/F", "/TN", TASK_NAME.format(job.name)]
        return task + schedule_arguments(job) + ["/TR", job.command]
    return ["sh", "-c", CRONTAB_INSTALL.format(marker_pattern(job), shlex.quote(crontab_line(job)))]


def remove_command(job: Job, platform: str) -> list[str]:
    """What remove runs: on "win32" ["schtasks", "/Delete", "/F", "/TN", "Solarpunk\\<name>"]; elsewhere
    ["sh", "-c", <the crontab without the job's line, piped to crontab ->]."""
    if platform == WINDOWS:
        return [SCHTASKS, "/Delete", "/F", "/TN", TASK_NAME.format(job.name)]
    return ["sh", "-c", CRONTAB_REMOVE.format(marker_pattern(job))]


def shown(command: list[str]) -> str:
    """The command as one shell line: shown(["sh", "-c", "crontab -l"]) gives "sh -c 'crontab -l'"."""
    return shlex.join(command)


def install(job: Job) -> str:
    """Host-touching: schedules the job with this platform's tool and returns shown(install_command(...)). No test calls
    it (SP-006)."""
    command = install_command(job, sys.platform)
    subprocess.run(command, check=True)
    return shown(command)


def remove(job: Job) -> str:
    """Host-touching: unschedules the job with this platform's tool and returns shown(remove_command(...)). No test
    calls it (SP-006)."""
    command = remove_command(job, sys.platform)
    subprocess.run(command, check=True)
    return shown(command)


def demo_jobs() -> tuple[Job, ...]:
    """The fleet's three jobs: [job.name for job in demo_jobs()] gives
    ["solarpunk-ping", "solarpunk-kpi", "solarpunk-clauses"]."""
    return (
        Job("solarpunk-ping", PING_COMMAND, "every:15"),
        Job("solarpunk-kpi", KPI_COMMAND, "daily@06:00"),
        Job("solarpunk-clauses", CLAUSES_COMMAND, HOURLY),
    )


def crontab_golden() -> str:
    """The crontab golden: one crontab_line per demo job, each ending in a newline; its first line starts "*/15 "."""
    return "".join(crontab_line(job) + "\n" for job in demo_jobs())


def schtasks_golden() -> str:
    """The schtasks golden: one schtasks_command per demo job, each ending in a newline; its last has "/SC HOURLY"."""
    return "".join(schtasks_command(job) + "\n" for job in demo_jobs())


def write_goldens(folder: Path) -> tuple[Path, Path]:
    """Writes both goldens as UTF-8 bytes to folder and returns their paths: write_goldens(GOLDENS) gives
    (GOLDENS / "schedule-crontab.txt", GOLDENS / "schedule-schtasks.txt")."""
    crontab = folder / CRONTAB_GOLDEN
    schtasks = folder / SCHTASKS_GOLDEN
    crontab.write_bytes(crontab_golden().encode())
    schtasks.write_bytes(schtasks_golden().encode())
    return crontab, schtasks
