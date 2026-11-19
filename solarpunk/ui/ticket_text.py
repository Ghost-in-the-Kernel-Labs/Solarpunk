"""The tickets' words in the windows (11.2, SOL-14), with no tkinter so the fast loop tests them: a ticket's line in the
Tickets window (its targets' states and due instants, a breach marked), the asset window's ticket line, and the root
cause choices Resolve offers. tickets_window.py and ticket_panel.py lay them out over project.tickets_by_target."""
from datetime import datetime

from solarpunk.leaf.root_causes import MEANINGS, RootCause
from solarpunk.leaf.tickets import TargetState
from solarpunk.project import TicketView
from solarpunk.ui.cells import instant_text

COLUMNS = ("ticket", "asset", "priority", "status", "acknowledge", "respond", "opened")
HEADINGS = ("Ticket", "Asset", "Priority", "Status", "Acknowledge", "Respond", "Opened")
NO_TARGET = "—"
NO_TICKET = "No open ticket"
TICKET_LINE = "Ticket {wo_id} · {priority} · {status} · acknowledge {acknowledge} · respond {respond}"
WAITING = "{state}, due {due}"


def target_cell(state: TargetState | None, due: datetime | None) -> str:
    """A target in words: "met" or "late" once it happened; "pending, due 2026-06-01 15:30 UTC" or "OVERDUE, due …"
    while it has not (overdue in capitals, to be seen); "—" with no target."""
    if state is None or due is None:
        return NO_TARGET
    if state in (TargetState.MET, TargetState.LATE):
        return state.value
    word = state.value.upper() if state is TargetState.OVERDUE else state.value
    return WAITING.format(state=word, due=instant_text(due))


def ticket_line(view: TicketView) -> tuple[str, ...]:
    """A ticket's row in the Tickets window: the demo's outage at 13:00 gives ("1", "OAHE-INV-002", "P1", "open",
    "OVERDUE, due 2026-06-01 12:30 UTC", "pending, due 2026-06-01 15:30 UTC", "2026-06-01 11:30 UTC")."""
    found = view.ticket
    priority = NO_TARGET if found.priority is None else found.priority.value
    return (str(found.wo_id), found.asset_id, priority, found.status.value,
            target_cell(view.acknowledge, view.acknowledge_due), target_cell(view.respond, view.respond_due),
            instant_text(found.opened))


def panel_line(view: TicketView | None) -> str:
    """The asset window's ticket line: "Ticket 1 · P1 · open · acknowledge OVERDUE, due … · respond pending, due …";
    an asset with no open ticket "No open ticket"."""
    if view is None:
        return NO_TICKET
    found = view.ticket
    return TICKET_LINE.format(wo_id=found.wo_id, priority=NO_TARGET if found.priority is None else found.priority.value,
                              status=found.status.value, acknowledge=target_cell(view.acknowledge, view.acknowledge_due),
                              respond=target_cell(view.respond, view.respond_due))


def cause_choices() -> tuple[str, ...]:
    """Resolve's root cause choices, the closed list with each meaning: "RC-COMPONENT A component failed …"."""
    return tuple(f"{cause.value} {MEANINGS[cause]}" for cause in RootCause)


def cause_of(choice: str) -> str:
    """The code a choice names: cause_of("RC-GRID The grid …") is "RC-GRID"; an empty choice is ""."""
    return choice.split(" ", 1)[0] if choice else ""
