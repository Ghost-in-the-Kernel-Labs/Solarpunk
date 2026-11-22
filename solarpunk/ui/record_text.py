"""The Tests window's words (13.7, SP-016, SP-050), with no tkinter so the fast loop tests them: a test's row in the
overview (name, kinds, assets, last run, duration, passes, failures, no data), a logged run's row (asset, instant,
result, reason, duration), a duration, and the window's title and empty lines. record_window.py lays them out over
project.tests_overview and project.test_log. The log's suite is left out: the overview counts only the default suite,
and the log's columns are the five the plan names."""
from solarpunk import project
from solarpunk.ui.asset_text import NEVER_WORD as NEVER, duration_words  # one rule for a duration (13.6)
from solarpunk.ui.cells import instant_text

TITLE = "Tests — record"
OVERVIEW_COLUMNS = ("Test", "Kinds", "Assets", "Last run", "Duration", "Passes", "Failures", "No data", "Clauses")
LOG_COLUMNS = ("Asset", "Instant", "Result", "Reason", "Duration")
PASS = "pass"
FAIL = "FAIL"
NO_DATA = "no data"
NO_TESTS = "no tests"
NO_LOG = "{name} has not run yet"
LOG_HEADING = "Last {limit} runs of {name}"


def overview_row(record: project.TestRecord) -> tuple[str, str, str, str, str, str, str, str, str]:
    """A test's row: reachable run on three assets last at 11:00 UTC in 12 ms with 40 passes, 3 failures and 1 no data
    and the clause 55000-9.1 gives ("reachable", "inverter", "3", "2026-06-01 11:00 UTC", "12 ms", "40", "3", "1",
    "55000-9.1"); a test never run gives "0" assets, "never", "—" and zeros."""
    last = NEVER if record.last_run is None else instant_text(record.last_run)
    return (record.name, ", ".join(kind.name.lower() for kind in record.kinds), str(len(record.assets)), last,
            duration_words(record.last_duration_ms), str(record.passes), str(record.failures), str(record.no_data),
            ", ".join(record.clauses))


def verdict_word(verdict: str) -> str:
    """A stored verdict in the window: "pass", "FAIL", or "no data" (SP-039)."""
    return {"pass": PASS, "fail": FAIL}.get(verdict, NO_DATA)


def log_row(run: project.LoggedRun) -> tuple[str, str, str, str, str]:
    """A logged run's row: ("OAHE-INV-002", "2026-06-01 13:00 UTC", "FAIL", "127.0.0.1:9 is unreachable", "3 ms")."""
    return (run.asset_id, instant_text(run.run_at), verdict_word(run.verdict), run.reason,
            duration_words(run.duration_ms))


def log_heading(name: str | None, limit: int = 100) -> str:
    """The line above the log: "Last 100 runs of reachable"; with no test selected, empty."""
    return "" if name is None else LOG_HEADING.format(limit=limit, name=name)


def empty_log(name: str | None) -> str:
    """What the log says with no row: a test never run "reachable has not run yet"; none selected, empty."""
    return "" if name is None else NO_LOG.format(name=name)
