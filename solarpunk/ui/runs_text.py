"""The Runs window's words (10.3, SOL-15, SP-024), with no tkinter so the fast loop tests them: a run's line in the list
(its instant, its count of results, its verdict), a result's line, the window's title, and what an asset with no runs
says, and the Power tab's curve and its line of counts (10.5). runs_window.py lays them out over project.asset_runs
and project.asset_power."""
from datetime import date, datetime

from solarpunk.leaf.codes import CATALOGUE
from solarpunk.project import AssetCount, CodeCount, PowerSeries, Recorded, Run
from solarpunk.ui.cells import NO_FEED, instant_text

TITLE = "Runs — {asset_id} {name}"
RESULTS = "{count} results"
ONE_RESULT = "1 result"
FAILED = "{count} failed"
ALL_PASSED = "all passed"
NO_DATA_COUNT = "{count} no data"
NO_RUNS = "no runs yet"
NO_MATCH = "no run matches “{words}”"
PASS = "pass"
FAIL = "FAIL"
NO_DATA = "no data"
POWER_LINE = "{samples} samples: records {records}, gaps {gaps}; peak {peak} kW"
NO_POWER = "no power samples on {day}"
BAD_DAY = "a day reads like 2026-06-01"
BAD_DAYS = "days read like 2026-06-01, the first not after the last"
NO_ERRORS = "no faults or suggestions from {first} to {last}"
NO_ASSET_ERRORS = "no asset raised {code} from {first} to {last}"


def title(asset_id: str, name: str) -> str:
    """The window's title: title("OAHE-INV-002", "Inverter 2") is "Runs — OAHE-INV-002 Inverter 2"."""
    return TITLE.format(asset_id=asset_id, name=name)


def run_line(run: Run) -> tuple[str, str, str]:
    """A run in the list: OAHE-INV-002's demo run gives ("2026-06-01 13:00 UTC", "8 results", "1 failed"); a run with
    no failure but results with no data says "2 no data" (SP-039: never "all passed"); one that passed whole says
    "all passed"."""
    count = len(run.results)
    failures = sum(1 for result in run.results if result.failed)
    empty = sum(1 for result in run.results if result.no_data)
    results = ONE_RESULT if count == 1 else RESULTS.format(count=count)
    if failures:
        return (instant_text(run.run_at), results, FAILED.format(count=failures))
    return (instant_text(run.run_at), results, NO_DATA_COUNT.format(count=empty) if empty else ALL_PASSED)


def verdict_word(result: Recorded) -> str:
    """A result's word in the window: "pass", "FAIL", or "no data" for a test with nothing to check (SP-039)."""
    if result.no_data:
        return NO_DATA
    return PASS if result.passed else FAIL


def result_line(result: Recorded) -> tuple[str, str, str]:
    """A result of the chosen run: the ping's failure gives ("reachable", "FAIL", "127.0.0.1:9 is unreachable"); the
    sensor's on_grid ("on_grid", "no data", "no records")."""
    return (result.test_name, verdict_word(result), result.reason)


def empty_text(has_feed: bool, search: str) -> str:
    """What the list says when it holds no run: a search that found none names its words; else an asset with an
    endpoint "no runs yet", one without "no feed" (SOL-15: a run needs a feed to answer, or the ping to fail)."""
    if search.strip():
        return NO_MATCH.format(words=search.strip())
    return NO_RUNS if has_feed else NO_FEED


def power_curve(series: PowerSeries) -> tuple[tuple[datetime, float], ...]:
    """The samples that carry a power, as (instant, kW), in time order: a gap is left out, so the drawn line breaks
    there (chart.segments) and never shows it as zero (SOL-15)."""
    return tuple((s.at, s.power_kw) for s in series.samples if s.power_kw is not None)


def peak_of(series: PowerSeries) -> float | None:
    """The largest power the series carries, None with none."""
    return max((power for _, power in power_curve(series)), default=None)


def power_line(series: PowerSeries) -> str:
    """The words beside the chart: OAHE-INV-001's demo day gives "288 samples: records 279, gaps 9; peak 94.35 kW" (its
    peak as stored); a series with no samples "no power samples on 2026-06-01"."""
    if not series.samples:
        return NO_POWER.format(day=series.period.start.date().isoformat())
    return POWER_LINE.format(samples=len(series.samples), records=series.records, gaps=series.gaps, peak=peak_of(series))


def day_of(text: str) -> date | None:
    """The day a box holds, or None when it is not one: day_of(" 2026-06-01 ") is date(2026, 6, 1); "June" is None."""
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


def days_of(first: str, last: str) -> tuple[date, date] | None:
    """The two days a From and a To box hold, the last counted whole: ("2026-06-01", "2026-06-01") is one day; a box
    that holds no day, or a last before the first, is None."""
    start, end = day_of(first), day_of(last)
    if start is None or end is None or end < start:
        return None
    return start, end


def no_errors(first: date, last: date) -> str:
    """What the Errors tab says with nothing counted: "no faults or suggestions from 2026-06-01 to 2026-06-01"."""
    return NO_ERRORS.format(first=first.isoformat(), last=last.isoformat())


def code_counts(found: tuple[CodeCount, ...]) -> tuple[tuple[str, int, int], ...]:
    """The bars' (label, faults, suggestions), in code order: the demo's sensor gives (("SEN-001", 0, 1),)."""
    return tuple((count.code, count.faults, count.suggestions) for count in found)


def code_choices() -> tuple[str, ...]:
    """The code box's choices, the whole catalogue, each its code and meaning: the first is "SIT-001 Site offline"…"""
    return tuple(f"{row.code} {row.meaning}" for row in CATALOGUE)


def code_of(choice: str) -> str:
    """The code a choice names: code_of("INV-001 Inverter offline: …") is "INV-001"."""
    return choice.split(" ", 1)[0]


def asset_counts(found: tuple[AssetCount, ...]) -> tuple[tuple[str, int, int], ...]:
    """The bars' (label, faults, suggestions), worst first as found: INV-001 over the demo day gives
    (("OAHE-INV-002", 1, 0),)."""
    return tuple((count.asset_id, count.faults, count.suggestions) for count in found)


def no_asset_errors(code: str, first: date, last: date) -> str:
    """The fleet's Errors window with nothing counted: "no asset raised INV-005 from 2026-06-01 to 2026-06-01"."""
    return NO_ASSET_ERRORS.format(code=code, first=first.isoformat(), last=last.isoformat())


def row_of(tags: tuple[str, ...], tag: str = "bar") -> str | None:
    """The row a clicked item belongs to, from its tags (bars.draw_bars tags each "bar:<label>"): ("bar",
    "bar:OAHE-INV-002", "current") gives "OAHE-INV-002"; an item of no row gives None."""
    prefix = f"{tag}:"
    return next((found[len(prefix):] for found in tags if found.startswith(prefix)), None)
