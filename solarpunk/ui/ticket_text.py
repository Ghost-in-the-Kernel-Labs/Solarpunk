"""The tickets' words in the windows (11.2, SOL-14), with no tkinter so the fast loop tests them: a ticket's line in the
Tickets window (its targets' states and due instants, a breach marked), the asset window's ticket line and its history
(one line per move: when, status, who, SP-035). tickets_window.py and
ticket_panel.py lay them out over project.tickets_by_target."""
from datetime import datetime

from solarpunk.leaf.tickets import TargetState
from solarpunk.project import Move, Recorded, ResultTicket, TicketView
from solarpunk.ui.cells import instant_text

COLUMNS = ("ticket", "asset", "priority", "status", "acknowledge", "respond", "opened")
HEADINGS = ("Ticket", "Asset", "Priority", "Status", "Acknowledge", "Respond", "Opened")
NO_TARGET = "—"
NO_TICKET = "No open ticket"
TICKET_LINE = "Ticket {wo_id} · {priority} · {status} · acknowledge {acknowledge} · respond {respond}"
WAITING = "{state}, due {due}"
MOVE_LINE = "{at} · {status} · {who}"
NOBODY_SIGNED_IN = "nobody signed in"
NO_MOVES = "No move yet"


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


def move_line(found: Move) -> str:
    """One move of a ticket's history: "2026-06-01 11:40 UTC · acknowledged · ops@oahe.example"; a move made where
    nobody was signed in names "nobody signed in" (SP-035)."""
    return MOVE_LINE.format(at=instant_text(found.at), status=found.status.value, who=found.actor or NOBODY_SIGNED_IN)


def history_text(moves: tuple[Move, ...]) -> str:
    """The ticket's history in the panel, oldest first, one line per move; a ticket never moved says "No move yet"."""
    # Decision: SP-035 (a ticket's every move is on record with who made it)
    return "\n".join(move_line(found) for found in moves) or NO_MOVES


# A ticket from a failed result (7.9, SP-046): the words of the "Open a ticket" control and of the failed results a
# ticket holds, one row each (test, run, reason).
OPEN_TICKET = "Open a ticket"
CHOOSE_FAILED = "Choose a failed result to open a ticket on."
RESULT_COLUMNS = ("test", "run", "reason")
RESULT_HEADINGS = ("Test", "Run", "Reason")
RESULTS_TITLE = "Failed results in the selected ticket"
RESULTS_LINE = "Failed results: {count}"
NO_RESULTS = "No failed result: this ticket was opened from a fault"
OPENED_LINE = "Ticket {wo_id} opened on the failed result: {count} failed result{plural} in it"
SHOWN_LINE = "Ticket {wo_id} already holds this result: {count} failed result{plural} in it"


def result_row(found: Recorded) -> tuple[str, str, str]:
    """A failed result as a row: ("reachable", "2026-06-01 13:00 UTC", "127.0.0.1:9 is unreachable")."""
    return (found.test_name, instant_text(found.run_at), found.reason)


def results_text(found: tuple[Recorded, ...]) -> str:
    """The ticket panel's line of the failed results the ticket holds: "Failed results: 2"; a ticket opened from a fault
    says it holds none."""
    return RESULTS_LINE.format(count=len(found)) if found else NO_RESULTS


def opened_text(found: ResultTicket) -> str:
    """What the control says after it ran: "Ticket 3 opened on the failed result: 1 failed result in it"; a result
    already in a ticket gives "Ticket 3 already holds this result: 2 failed results in it"."""
    words = OPENED_LINE if found.opened else SHOWN_LINE
    return words.format(wo_id=found.ticket.wo_id, count=len(found.results), plural="" if len(found.results) == 1 else "s")
