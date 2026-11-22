"""The tickets' surface (8.2, SOL-14, SP-022): what the windows and the command line call to read and move a ticket.
A ticket opens with its fault (orchestrator.assign_fault) and closes once its fault's root cause is written (orchestrator.close_work_order,
4.1, SP-046); in between, these calls acknowledge, start, resolve and reopen it, set who works it, comment on it, and report
the tickets past a target. Each move is logged with the actor project hands down, the account's email or None where
nobody is signed in (SP-035), and its history read back oldest first. Each is one call into the ticket ledger, so the rules are written once (MOD-02)."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from solarpunk.leaf.tickets import TARGETS, TargetState, TicketStatus, target_state
from solarpunk.project.causes import require_cause
from solarpunk.project.orchestrator import close_work_order
from solarpunk.workorders import ledger as work_ledger
from solarpunk.workorders.ledger import WorkOrderError
from solarpunk.workorders import tickets as ticket_ledger
from solarpunk.workorders.tickets import Breach, Comment, Move, Ticket

LATE_STATES = (TargetState.LATE, TargetState.OVERDUE)
WAITING_STATES = (TargetState.PENDING, TargetState.OVERDUE)


def ticket_of(conn: sqlite3.Connection, wo_id: int) -> Ticket:
    """A work order's ticket: ticket_of(conn, 1).status is TicketStatus.OPEN for one just opened."""
    return ticket_ledger.ticket(conn, wo_id)


def open_tickets(conn: sqlite3.Connection) -> tuple[Ticket, ...]:
    """Every ticket not closed, in wo_id order: the demo store gives its one outage's ticket."""
    return ticket_ledger.open_tickets(conn)


def move_ticket(conn: sqlite3.Connection, wo_id: int, status: TicketStatus, moment: datetime,
                evidence: str | None = None, read_at: int | None = None, actor: str | None = None) -> Ticket:
    """Moves a ticket as SOL-14 allows, the move logged as actor's (SP-035): move_ticket(conn, 1, ACKNOWLEDGED, 10:40
    UTC).acknowledged is 10:40; resolving needs evidence; a forbidden move raises BadMove, a move to closed
    WorkOrderError (close_work_order closes), a ticket read at an older version StaleWrite (12.2)."""
    return ticket_ledger.move(conn, wo_id, status, moment, evidence, read_at, actor)


def ticket_moves(conn: sqlite3.Connection, wo_id: int) -> tuple[Move, ...]:
    """A ticket's moves, oldest first, each with its status, instant and actor (None: nobody signed in), SP-035."""
    return ticket_ledger.moves(conn, wo_id)


def set_ticket_assignee(conn: sqlite3.Connection, wo_id: int, assignee: str | None,
                        moment: datetime | None = None, read_at: int | None = None) -> Ticket:
    """Sets or clears who works a ticket, at an instant (now when not given; the outbox's event carries it):
    set_ticket_assignee(conn, 1, "crew B").assignee is "crew B"; read at an older version, StaleWrite (12.2)."""
    return ticket_ledger.set_assignee(conn, wo_id, assignee, moment, read_at)


def comment_on_ticket(conn: sqlite3.Connection, wo_id: int, author: str, moment: datetime, body: str) -> Comment:
    """Adds a comment, kept as written: comment_on_ticket(conn, 1, "site@oahe.example", 11:40 UTC, "on my way")."""
    return ticket_ledger.comment(conn, wo_id, author, moment, body)


def ticket_comments(conn: sqlite3.Connection, wo_id: int) -> tuple[Comment, ...]:
    """A ticket's comments, oldest first."""
    return ticket_ledger.comments(conn, wo_id)


def tickets_past_target(conn: sqlite3.Connection, moment: datetime) -> tuple[Breach, ...]:
    """The open tickets' late or overdue targets at an instant: the demo's outage, opened 11:30 and not acknowledged,
    is overdue on acknowledgement at 13:00 (P1, due 12:30)."""
    return ticket_ledger.past_target(conn, moment)


@dataclass(frozen=True)
class TicketView:
    """An open ticket with its two targets' states and due instants at an instant (SOL-14), for the Tickets window and
    `solarpunk ticket list`: the demo's outage at 13:00 has its acknowledgement OVERDUE (due 12:30) and its response
    PENDING (due 15:30); next_due is the sooner of the two not yet met, and breached says whether either is late or
    overdue."""

    ticket: Ticket
    acknowledge: TargetState | None
    acknowledge_due: datetime | None
    respond: TargetState | None
    respond_due: datetime | None

    @property
    def breached(self) -> bool:
        """Whether a target is late or overdue."""
        return self.acknowledge in LATE_STATES or self.respond in LATE_STATES

    @property
    def next_due(self) -> datetime | None:
        """The sooner due instant of the targets not yet met, None when both happened or the ticket has no priority."""
        open_targets = [due for state, due in ((self.acknowledge, self.acknowledge_due), (self.respond, self.respond_due))
                        if state in WAITING_STATES and due is not None]
        return min(open_targets, default=None)


def view_of(found: Ticket, moment: datetime) -> TicketView:
    """One ticket's view at an instant; a ticket with no priority has no targets."""
    if found.priority is None:
        return TicketView(found, None, None, None, None)
    targets = TARGETS[found.priority]
    ack_due, respond_due = found.opened + targets.acknowledge, found.opened + targets.respond
    return TicketView(found, target_state(found.opened, targets.acknowledge, found.acknowledged, moment), ack_due,
                      target_state(found.opened, targets.respond, found.responded, moment), respond_due)


def tickets_by_target(conn: sqlite3.Connection, moment: datetime) -> tuple[TicketView, ...]:
    """The open tickets at an instant, the nearest target first (an overdue one before a pending one, as its due is
    earlier), those with no target waiting last, ties by work order: SOL-14's order for the Tickets window (11.2)."""
    views = [view_of(found, moment) for found in ticket_ledger.open_tickets(conn)]
    far = datetime.max.replace(tzinfo=timezone.utc)
    return tuple(sorted(views, key=lambda view: (view.next_due or far, view.ticket.wo_id)))


def all_ticket_views(conn: sqlite3.Connection, moment: datetime) -> tuple[TicketView, ...]:
    """Every ticket, closed too, at an instant (13.17's Show closed): the open ones in tickets_by_target's order, then
    the closed ones by work order; after one of two tickets closes, the open one then the closed one."""
    closed = tuple(view_of(found, moment) for found in ticket_ledger.all_tickets(conn) if found.status is TicketStatus.CLOSED)
    return tickets_by_target(conn, moment) + closed


def resolve_ticket(conn: sqlite3.Connection, wo_id: int, done: str, moment: datetime,
                   read_at: int | None = None, actor: str | None = None) -> Ticket:
    """Resolves a ticket with what was done and closes it, in one act at an instant (11.2's Resolve): a ticket not yet
    in progress moves there first, then to resolved with the words, then to closed, which closes its fault (4.1). A
    ticket on a fault whose root cause is not written (NoRootCause, SP-046), no words (WorkOrderError) or a ticket read at an older version (StaleWrite, 12.2) writes nothing: read_at is checked by the
    act's first move, and the moves after it carry on from the version that move made. Each move is logged as actor's
    (SP-035)."""
    # Decision: SP-028 (a write from a screen names the version it read)
    # Decision: SP-046 (a ticket on a fault closes only once the fault's root cause is written)
    require_cause(conn, work_ledger.get(conn, wo_id))
    if not done.strip():
        raise WorkOrderError(f"work order {wo_id} resolves with evidence of what was done")
    if ticket_ledger.ticket(conn, wo_id).status in (TicketStatus.OPEN, TicketStatus.ACKNOWLEDGED):
        ticket_ledger.move(conn, wo_id, TicketStatus.IN_PROGRESS, moment, None, read_at, actor)
        read_at = None
    ticket_ledger.move(conn, wo_id, TicketStatus.RESOLVED, moment, done, read_at, actor)
    close_work_order(conn, wo_id, moment, actor=actor)
    return ticket_ledger.ticket(conn, wo_id)
