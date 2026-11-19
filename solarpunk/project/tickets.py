"""The tickets' surface (8.2, SOL-14, SP-022): what the windows and the command line call to read and move a ticket.
A ticket opens with its fault (orchestrator.assign_fault) and closes with a root cause (orchestrator.close_work_order,
4.1); in between, these calls acknowledge, start, resolve and reopen it, set who works it, comment on it, and report
the tickets past a target. Each is one call into the ticket ledger, so the rules are written once (MOD-02)."""
import sqlite3
from datetime import datetime

from solarpunk.leaf.tickets import TicketStatus
from solarpunk.workorders import tickets as ticket_ledger
from solarpunk.workorders.tickets import Breach, Comment, Ticket


def ticket_of(conn: sqlite3.Connection, wo_id: int) -> Ticket:
    """A work order's ticket: ticket_of(conn, 1).status is TicketStatus.OPEN for one just opened."""
    return ticket_ledger.ticket(conn, wo_id)


def open_tickets(conn: sqlite3.Connection) -> tuple[Ticket, ...]:
    """Every ticket not closed, in wo_id order: the demo store gives its one outage's ticket."""
    return ticket_ledger.open_tickets(conn)


def move_ticket(conn: sqlite3.Connection, wo_id: int, status: TicketStatus, moment: datetime,
                evidence: str | None = None) -> Ticket:
    """Moves a ticket as SOL-14 allows: move_ticket(conn, 1, ACKNOWLEDGED, 10:40 UTC).acknowledged is 10:40; resolving
    needs evidence; a forbidden move raises BadMove and a move to closed WorkOrderError (close_work_order closes)."""
    return ticket_ledger.move(conn, wo_id, status, moment, evidence)


def set_ticket_assignee(conn: sqlite3.Connection, wo_id: int, assignee: str | None,
                        moment: datetime | None = None) -> Ticket:
    """Sets or clears who works a ticket, at an instant (now when not given; the outbox's event carries it):
    set_ticket_assignee(conn, 1, "crew B").assignee is "crew B"."""
    return ticket_ledger.set_assignee(conn, wo_id, assignee, moment)


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
