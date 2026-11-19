"""The Runs window's words (10.3, SOL-15, SP-024), with no tkinter so the fast loop tests them: a run's line in the list
(its instant, its count of results, its verdict), a result's line, the window's title, and what an asset with no runs
says. runs_window.py lays them out over one project call, project.asset_runs."""
from solarpunk.project import Recorded, Run
from solarpunk.ui.cells import NO_FEED, instant_text

TITLE = "Runs — {asset_id} {name}"
RESULTS = "{count} results"
ONE_RESULT = "1 result"
FAILED = "{count} failed"
ALL_PASSED = "all passed"
NO_RUNS = "no runs yet"
NO_MATCH = "no run matches “{words}”"
PASS = "pass"
FAIL = "FAIL"


def title(asset_id: str, name: str) -> str:
    """The window's title: title("OAHE-INV-002", "Inverter 2") is "Runs — OAHE-INV-002 Inverter 2"."""
    return TITLE.format(asset_id=asset_id, name=name)


def run_line(run: Run) -> tuple[str, str, str]:
    """A run in the list: OAHE-INV-002's demo run gives ("2026-06-01 13:00 UTC", "8 results", "1 failed"); a run that
    passed whole says "all passed"."""
    count = len(run.results)
    failures = sum(1 for result in run.results if not result.passed)
    results = ONE_RESULT if count == 1 else RESULTS.format(count=count)
    return (instant_text(run.run_at), results, FAILED.format(count=failures) if failures else ALL_PASSED)


def result_line(result: Recorded) -> tuple[str, str, str]:
    """A result of the chosen run: the ping's failure gives ("reachable", "FAIL", "127.0.0.1:9 is unreachable")."""
    return (result.test_name, PASS if result.passed else FAIL, result.reason)


def empty_text(has_feed: bool, search: str) -> str:
    """What the list says when it holds no run: a search that found none names its words; else an asset with an
    endpoint "no runs yet", one without "no feed" (SOL-15: a run needs a feed to answer, or the ping to fail)."""
    if search.strip():
        return NO_MATCH.format(words=search.strip())
    return NO_RUNS if has_feed else NO_FEED
