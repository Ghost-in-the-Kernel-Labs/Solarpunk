"""The fleet list's words that need no tkinter (9.2), so the fast loop's Python, which has none, tests them: an instant
as the windows write it, and a row's cause: why a red or yellow row is that colour. The fleet window (app.py) places
them; test_demo.py holds the demo's causes as goldens."""
from datetime import datetime

from solarpunk.leaf.accounts import Account
from solarpunk.leaf.codes import AssetStatus
from solarpunk.project.surface import AssetRow, Attention

INSTANT_FORMAT = "%Y-%m-%d %H:%M UTC"
# The attention band's counts (9.3), in the order they stand: a key, and the words before the count.
BAND = (("outages", "Open outages"), ("suggestions", "Awaiting an engineer"), ("orders", "Open work orders"))
BAND_TEXT = "{label}: {count}"
SHOWING = "; showing {label} alone"
STORE_LINE = "{store}, last run {instant}"
NO_CAUSE = "—"
NEVER_RUN = "never run"
NO_FEED = "no feed"
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


def band_counts(found: Attention) -> tuple[tuple[str, str], ...]:
    """Each count's key and words, zero shown, never hidden: the demo gives (("outages", "Open outages: 1"),
    ("suggestions", "Awaiting an engineer: 1"), ("orders", "Open work orders: 1"))."""
    return tuple((key, BAND_TEXT.format(label=label, count=len(getattr(found, key)))) for key, label in BAND)


def band_assets(found: Attention, key: str) -> frozenset[str]:
    """The assets one count names, for the list's filter: band_assets(demo, "outages") is {"OAHE-INV-002"}."""
    return frozenset(item.asset_id for item in getattr(found, key))


def filtered(rows: tuple[AssetRow, ...], assets: frozenset[str] | None) -> tuple[AssetRow, ...]:
    """The rows a filter keeps, in their order; None keeps them all."""
    return rows if assets is None else tuple(row for row in rows if row.asset_id in assets)


def showing(key: str | None) -> str:
    """The status line's note on a filter: showing("outages") is "; showing open outages alone"; None gives ""."""
    return "" if key is None else SHOWING.format(label=dict(BAND)[key].lower())


def never_text(row: AssetRow) -> str:
    """Why a row has no run: "never run" for an asset with an endpoint, "no feed" for one the run cannot reach."""
    return NEVER_RUN if row.has_feed else NO_FEED


def row_text(row: AssetRow) -> tuple[str, str, str, str, str, str, str]:
    """A row's seven words: AssetRow("OAHE-INV-002", "Inverter 2", INVERTER, YELLOW, 12:00 UTC, "reachable") gives
    ("OAHE-INV-002", "Inverter 2", "inverter", "yellow", "reachable", "2026-06-01 12:00 UTC", "reachable"), its cause
    fifth (9.2, cells.cause_text); never run gives "never run" in the sixth place, or "no feed" for an asset with no
    endpoint."""
    last_run = never_text(row) if row.last_run_at is None else instant_text(row.last_run_at)
    return (row.asset_id, row.name, row.kind.name.lower(), row.status.value, cause_text(row), last_run, row.failing)


def store_line(store: str, last_run: datetime | None) -> str:
    """The status bar's left side (9.5): "demo.db, last run 2026-06-01 13:00 UTC"; a store never run "fleet.db, never
    run"."""
    return f"{store}, {NEVER_RUN}" if last_run is None else STORE_LINE.format(store=store, instant=instant_text(last_run))


NO_ACCOUNTS = "no accounts yet: anyone at this machine acts"
NO_MATCH = "that email and password do not match an active account"


def who_text(account: Account | None) -> str:
    """The status bar's word on who is at the window (12.3): "signed in as site@oahe.example (engineer)"; with no
    account in the store, "no accounts yet: anyone at this machine acts"."""
    if account is None:
        return NO_ACCOUNTS
    return f"signed in as {account.email} ({account.role.value})"
