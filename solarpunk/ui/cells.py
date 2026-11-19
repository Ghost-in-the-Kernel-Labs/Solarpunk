"""The fleet list's words that need no tkinter (9.2), so the fast loop's Python, which has none, tests them: an instant
as the windows write it, and a row's cause: why a red or yellow row is that colour. The fleet window (app.py) places
them; test_demo.py holds the demo's causes as goldens."""
from datetime import datetime

from solarpunk.leaf.codes import AssetStatus
from solarpunk.project.surface import AssetRow

INSTANT_FORMAT = "%Y-%m-%d %H:%M UTC"
NO_CAUSE = "—"
OUTAGE_CAUSE = "{code} since {instant}"
SUGGESTED_CAUSE = "suggested {code}"


def instant_text(moment: datetime) -> str:
    """An instant as the windows write it: at(2026, 6, 1, 12) gives "2026-06-01 12:00 UTC"."""
    return moment.strftime(INSTANT_FORMAT)


def cause_text(row: AssetRow) -> str:
    """Why a row is its colour (SP-007's rule read back): a red row its open outage and since when, "INV-001 since
    2026-06-01 11:30 UTC"; a yellow row its open suggestion, "suggested SEN-001", or else its failing test, "reachable";
    a green row "—"."""
    if row.status is AssetStatus.RED and row.outage is not None:
        return OUTAGE_CAUSE.format(code=row.outage.code, instant=instant_text(row.outage.opened))
    if row.status is AssetStatus.YELLOW:
        return SUGGESTED_CAUSE.format(code=row.suggested) if row.suggested is not None else row.failing
    return NO_CAUSE
