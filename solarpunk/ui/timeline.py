"""The Runs window's "By test" timeline (10.4, SP-024): one row per test, one mark per run, green a pass and red a
failure, the time axis in UTC. Its geometry is pure, with no tkinter, as chart.py's is, so the fast loop tests it;
runs_window.py only draws what these return. A test with two results in one run (the ping's reachable beside the
test's own, SOL-15) has one mark there, red when either failed."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from solarpunk.project import Run

WIDTH = 760
LABEL_WIDTH = 190
LABEL_GAP = 24
RIGHT = 24
TOP = 12
ROW_HEIGHT = 22
AXIS_HEIGHT = 34
MARK_WIDTH = 6
MARK_HEIGHT = 12
MAX_TICKS = 8
STEPS_H = (1, 2, 3, 6, 12, 24, 48, 168)
PASS_COLOUR = "#2e8b57"
FAIL_COLOUR = "#c0392b"


@dataclass(frozen=True)
class Mark:
    """One run of one test on the timeline: Mark(x=401.0, row=0, passed=False) is a red mark on the first test's row."""

    x: float
    row: int
    passed: bool


def tests_of(runs: tuple[Run, ...]) -> tuple[str, ...]:
    """The timeline's rows: every test the runs hold, by name: OAHE-INV-002's demo run gives its seven tests."""
    return tuple(sorted({result.test_name for run in runs for result in run.results}))


def span(runs: tuple[Run, ...]) -> tuple[datetime, datetime]:
    """The axis's ends: from the hour at or before the first run to the hour after the last, so no mark sits on an
    edge; one run at 13:00 gives (13:00, 14:00); runs at 13:00 and 15:30 give (13:00, 16:00)."""
    instants = [run.run_at for run in runs]
    start = min(instants).replace(minute=0, second=0, microsecond=0)
    end = max(instants).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return start, end


def left_of(label_widths: list[int]) -> int:
    """Where the time axis starts: past the widest test name and a 24 px gap, never before 190: names up to 166 px wide
    give 190, a 200 px name 224."""
    return max([LABEL_WIDTH, *(width + LABEL_GAP for width in label_widths)])


def x_of(moment: datetime, start: datetime, end: datetime, width: int = WIDTH, left: int = LABEL_WIDTH) -> float:
    """The x of an instant: the span's start at left, its end at width - RIGHT: the middle of 13:00 to 14:00 on the
    760 px canvas is 463.0."""
    share = (moment - start) / (end - start)
    return left + share * (width - left - RIGHT)


def y_of(row: int) -> float:
    """The middle of a test's row: y_of(0) is 23.0, each next row 22 px lower."""
    return TOP + row * ROW_HEIGHT + ROW_HEIGHT / 2


def height_of(rows: int) -> int:
    """The canvas's height for so many rows and the axis below them: height_of(7) is 200."""
    return TOP + rows * ROW_HEIGHT + AXIS_HEIGHT


def marks(runs: tuple[Run, ...], width: int = WIDTH, left: int = LABEL_WIDTH) -> tuple[Mark, ...]:
    """One mark per run per test it ran, passed only when every result of that test in that run passed; none for no
    runs."""
    if not runs:
        return ()
    rows = {name: index for index, name in enumerate(tests_of(runs))}
    start, end = span(runs)
    found = []
    for run in runs:
        verdicts: dict[str, bool] = {}
        for result in run.results:
            verdicts[result.test_name] = verdicts.get(result.test_name, True) and result.passed
        x = x_of(run.run_at, start, end, width, left)
        found.extend(Mark(x, rows[name], passed) for name, passed in sorted(verdicts.items()))
    return tuple(found)


def ticks(start: datetime, end: datetime) -> tuple[datetime, ...]:
    """The axis's ticks on whole hours, at most eight, the step the smallest of 1, 2, 3, 6, 12, 24, 48 and 168 hours
    that fits: 13:00 to 14:00 gives (13:00, 14:00); a day gives every third hour."""
    hours = (end - start) / timedelta(hours=1)
    step = next((s for s in STEPS_H if hours / s <= MAX_TICKS), STEPS_H[-1])
    found, moment = [], start
    while moment <= end:
        found.append(moment)
        moment += timedelta(hours=step)
    return tuple(found)


def tick_text(moment: datetime, start: datetime, end: datetime) -> str:
    """A tick's label: "13:00" within one day, "06-01 13:00" when the span crosses a day."""
    return moment.strftime("%H:%M" if start.date() == (end - timedelta(seconds=1)).date() else "%m-%d %H:%M")
