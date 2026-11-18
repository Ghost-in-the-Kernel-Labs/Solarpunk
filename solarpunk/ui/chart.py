"""The reports window's numbers and geometry (6.3): the period it opens on, a table row's cells, the summary line, the
power axis's top, the hour ticks, and the curve as runs of canvas points, a gap a break in the line, never a zero or a
bridge. No tkinter here, as in glyph.py, so all of it is tested headless by the fast loop's interpreter, which has none
(J-025); reports.py only places what these return."""
from datetime import date, datetime, timedelta

from solarpunk import project
from solarpunk.leaf.clock import SAMPLE_INTERVAL, Period

NO_VALUE = "—"
SUMMARY = "{site}: {energy} kWh over {hours:g} h, peak {peak} kW, {gaps} gaps"
CANVAS_WIDTH = 720
CANVAS_HEIGHT = 260
MARGIN = 44
MAX_TICKS = 8
Point = tuple[float, float]


def default_span(day: date) -> tuple[str, str]:
    """The period the window opens on, as the two entries show it: default_span(date(2026, 6, 1)) is
    ("2026-06-01T00:00:00+00:00", "2026-06-02T00:00:00+00:00")."""
    start = datetime(day.year, day.month, day.day).isoformat() + "+00:00"
    end = (datetime(day.year, day.month, day.day) + timedelta(days=1)).isoformat() + "+00:00"
    return start, end


def table_values(row: project.PowerOutput) -> tuple[str, ...]:
    """One table row's eight cells, an absent peak shown as "—": SOL-13's INV-002 gives ("OAHE-INV-002", "50.0", "9.75",
    "45.0", "0.195", "0.78", "3", "0")."""
    return tuple(NO_VALUE if getattr(row, field) is None else str(getattr(row, field)) for field in project.OUTPUT_FIELDS)


def summary(found: project.PowerReport) -> str:
    """The line under the table: SOL-13's example gives "OAHE-SIT-001: 22.25 kWh over 0.25 h, peak 135.0 kW, 1 gaps"."""
    peak = NO_VALUE if found.site.peak_kw is None else found.site.peak_kw
    return SUMMARY.format(site=found.site.asset_id, energy=found.site.energy_kwh, hours=found.period.hours(), peak=peak,
                          gaps=found.site.gaps)


def axis_top(peak: float | None) -> float:
    """The power axis's top: the peak rounded up to 1, 2 or 5 times a power of ten, 1.0 with no peak: axis_top(187.22) is
    200.0, axis_top(135.0) is 200.0, axis_top(42.0) is 50.0, axis_top(0.0) and axis_top(None) are 1.0."""
    if peak is None or peak <= 0:
        return 1.0
    scale = 1.0
    while scale * 10 <= peak:
        scale *= 10
    while scale > peak:
        scale /= 10
    return next(step * scale for step in (1, 2, 5, 10) if step * scale >= peak)


def tick_hours(period: Period) -> list[datetime]:
    """The time axis's ticks, on whole hours, at most eight, the step the smallest of 1, 2, 3, 6, 12 and 24 hours that
    fits: a day gives 00:00, 03:00 … 21:00; 10:00 to 10:15 gives 10:00 alone."""
    hours = max(period.hours(), 1)
    step = next(s for s in (1, 2, 3, 6, 12, 24) if hours / s <= MAX_TICKS)
    first = period.start.replace(minute=0, second=0, microsecond=0)
    if first < period.start:
        first += timedelta(hours=1)
    ticks = []
    while first < period.end:
        ticks.append(first)
        first += timedelta(hours=step)
    return ticks


def x_of(instant: datetime, period: Period, width: int) -> float:
    """The canvas x of an instant: the period's start at MARGIN, its end at width - MARGIN; the middle of a day on a
    720 px canvas is 360.0."""
    share = (instant - period.start) / (period.end - period.start)
    return MARGIN + share * (width - 2 * MARGIN)


def y_of(power: float, top: float, height: int) -> float:
    """The canvas y of a power: 0 kW at height - MARGIN, top at MARGIN: y_of(100, 200, 260) is 130.0."""
    return height - MARGIN - power / top * (height - 2 * MARGIN)


def segments(curve: tuple[tuple[datetime, float], ...], period: Period, top: float, width: int = CANVAS_WIDTH,
             height: int = CANVAS_HEIGHT) -> list[list[Point]]:
    """The curve as runs of canvas points, a new run wherever an instant is missing, so a gap is a break in the line and
    never a zero or a bridge: 10:00 and 10:05 then 10:15 give two runs, of two points and of one."""
    runs: list[list[Point]] = []
    previous: datetime | None = None
    for instant, power in curve:
        if previous is None or instant - previous > SAMPLE_INTERVAL:
            runs.append([])
        runs[-1].append((x_of(instant, period, width), y_of(power, top, height)))
        previous = instant
    return runs
