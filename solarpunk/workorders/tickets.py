"""The ticket ledger (8.2, SOL-14, SP-022): every work order is a ticket. Its status moves only as the leaf's MOVES allow,
each move stamping its instant (acknowledged, responded, resolved) and logged with who made it, a history only ever
added to (SP-035); resolving needs closeout evidence; the working assignee is free text a person sets; comments carry
their author and instant and are never edited or deleted; a query reports the tickets past a target. Closing is the
ledger's `close` (4.1; the fault's root cause is written first, SP-046). It imports the leaf and its own module's ledger alone (MOD-05): project sets
a ticket's priority from its fault and opens it with the fault, and hands each move its actor as a plain email."""
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from solarpunk.leaf.clock import utc
from solarpunk.leaf.tickets import COMMENT, TRANSITION, UPDATE, TARGETS, Priority, TargetState, TicketStatus, check_move, target_state
from solarpunk.leaf.versions import BUMP
from solarpunk.workorders.ledger import (CREATE_COMMENTS, CREATE_MOVES, CREATE_OUTBOX, TICKET_COLUMNS, WorkOrderError,
                                         check_read, get, last_stamp, outbox_add, record_move)

SELECT_TICKET = (
    "SELECT wo_id, asset_id, kind, status, priority, assignee, opened, acknowledged, responded, resolved, closed,"
    " evidence, version FROM work_orders"
)
SELECT_COMMENTS = "SELECT comment_id, wo_id, author, at, body FROM ticket_comments WHERE wo_id = ? ORDER BY comment_id"
SELECT_MOVES = "SELECT move_id, wo_id, status, at, actor FROM ticket_moves WHERE wo_id = ? ORDER BY move_id"
INSERT_COMMENT = "INSERT INTO ticket_comments (wo_id, author, at, body) VALUES (?, ?, ?, ?)"
LATE = (TargetState.LATE, TargetState.OVERDUE)
ASSIGNEE = "assignee {name}"
NOBODY = "nobody"
ACKNOWLEDGE = "acknowledge"
RESPOND = "respond"


@dataclass(frozen=True)
class Ticket:
    """A work order seen as a ticket: Ticket(1, "OAHE-INV-002", "corrective", TicketStatus.OPEN, Priority.PRIORITY_P1, None,
    11:30 UTC, None, None, None, None, None) is an outage's ticket nobody has taken yet."""

    wo_id: int
    asset_id: str
    kind: str
    status: TicketStatus
    priority: Priority | None
    assignee: str | None
    opened: datetime
    acknowledged: datetime | None
    responded: datetime | None
    resolved: datetime | None
    closed: datetime | None
    evidence: str | None
    version: int = 1  # 12.2: raised by one with every change to the ticket


@dataclass(frozen=True)
class Comment:
    """One comment, never edited or deleted: Comment(1, 1, "site@oahe.example", 11:40 UTC, "on my way")."""

    comment_id: int
    wo_id: int
    author: str
    moment: datetime
    body: str


@dataclass(frozen=True)
class Move:
    """One move in a ticket's history, never updated or deleted (SP-035): Move(1, 1, TicketStatus.ACKNOWLEDGED, 11:40
    UTC, "ops@oahe.example"); actor is None where nobody was signed in."""

    move_id: int
    wo_id: int
    status: TicketStatus
    moment: datetime
    actor: str | None


@dataclass(frozen=True)
class Breach:
    """A ticket past one of its targets at an instant: Breach(ticket, "acknowledge", TargetState.OVERDUE)."""

    ticket: Ticket
    target: str
    state: TargetState


def upgrade(conn: sqlite3.Connection) -> None:
    """Gives a work_orders table made before 8.2 the ticket's columns, a closed order's status "closed", and the comments,
    outbox and moves tables (the moves' empty: a history begins when the store gains it, SP-035); a store that has them
    is left as it is: upgrade(conn) twice changes nothing the second time."""
    present = {row[1] for row in conn.execute("PRAGMA table_info(work_orders)")}
    added = [name for name, _column in TICKET_COLUMNS if name not in present]
    for name, column in TICKET_COLUMNS:
        if name in added:
            conn.execute(f"ALTER TABLE work_orders ADD COLUMN {column}")
    if "status" in added:
        conn.execute("UPDATE work_orders SET status = 'closed' WHERE closed IS NOT NULL")
    conn.execute(CREATE_COMMENTS)
    conn.execute(CREATE_OUTBOX)
    conn.execute(CREATE_MOVES)
    conn.commit()


def _instant(text: str | None) -> datetime | None:
    """The aware instant stored text names, or None: _instant("2026-06-01T10:10:00+00:00") is at(2026, 6, 1, 10, 10)."""
    return None if text is None else datetime.fromisoformat(text)


def _ticket(row: tuple) -> Ticket:
    """One stored row as a Ticket, its instants aware and its status and priority the leaf's."""
    wo_id, asset_id, kind, status, priority, assignee, opened, acked, responded, resolved, closed, evidence, version = row
    return Ticket(wo_id, asset_id, kind, TicketStatus(status), None if priority is None else Priority(priority), assignee,
                  datetime.fromisoformat(opened), _instant(acked), _instant(responded), _instant(resolved),
                  _instant(closed), evidence, version)


def ticket(conn: sqlite3.Connection, wo_id: int) -> Ticket:
    """The ticket of a work order: ticket(conn, 1).status is TicketStatus.OPEN for a new one; an unknown id raises
    WorkOrderError("work order 9 is not in the ledger")."""
    get(conn, wo_id)
    return _ticket(conn.execute(SELECT_TICKET + " WHERE wo_id = ?", (wo_id,)).fetchone())


def open_tickets(conn: sqlite3.Connection) -> tuple[Ticket, ...]:
    """Every ticket not closed, in wo_id order."""
    return tuple(_ticket(row) for row in conn.execute(SELECT_TICKET + " WHERE status != 'closed' ORDER BY wo_id"))


def all_tickets(conn: sqlite3.Connection) -> tuple[Ticket, ...]:
    """Every ticket, closed ones too, in wo_id order: after one of two is closed, both."""
    return tuple(_ticket(row) for row in conn.execute(SELECT_TICKET + " ORDER BY wo_id"))


def _checked(conn: sqlite3.Connection, wo_id: int, target: TicketStatus, moment: datetime,
             read_at: int | None) -> Ticket:
    """The ticket, once it was read at its current version (12.2), the move to target is one SOL-14 allows by this call
    and the instant is not before its last stamp: a move to closed raises WorkOrderError (closing takes a root cause:
    the ledger's close, once the fault's root cause is written)."""
    check_read(conn, wo_id, read_at)
    found = ticket(conn, wo_id)
    if target is TicketStatus.CLOSED:
        raise WorkOrderError(f"work order {wo_id} closes by close, once its fault's root cause is written")
    # Invariant: SOL-14 (only the six moves)
    check_move(found.status, target)
    if utc(moment) < last_stamp(conn, wo_id):
        raise WorkOrderError(f"work order {wo_id} cannot move at {utc(moment).isoformat()}, before its last move")
    return found


def move(conn: sqlite3.Connection, wo_id: int, target: TicketStatus, moment: datetime, evidence: str | None = None,
         read_at: int | None = None, actor: str | None = None) -> Ticket:
    """Moves a ticket as SOL-14 allows and stamps the move: move(conn, 1, ACKNOWLEDGED, 10:40 UTC).acknowledged is 10:40;
    to IN_PROGRESS stamps responded (and acknowledged) if not yet stamped, and from RESOLVED clears resolved and the
    evidence; to RESOLVED needs evidence. A forbidden move raises BadMove, a move to CLOSED, an instant before the last
    move, or resolving without evidence WorkOrderError, a ticket read at an older version StaleWrite (12.2); a refused
    move writes nothing, and every move raises the version and is logged as actor's, None where nobody is signed in
    (SP-035)."""
    found = _checked(conn, wo_id, target, moment, read_at)
    stamp = utc(moment).isoformat()
    if target is TicketStatus.RESOLVED:
        if evidence is None or not evidence.strip():
            raise WorkOrderError(f"work order {wo_id} resolves with evidence of what was done")
        conn.execute(f"UPDATE work_orders SET status = ?, resolved = ?, evidence = ?, {BUMP} WHERE wo_id = ?",
                     (target.value, stamp, evidence.strip(), wo_id))
    elif found.status is TicketStatus.RESOLVED:
        conn.execute(f"UPDATE work_orders SET status = ?, resolved = NULL, evidence = NULL, {BUMP} WHERE wo_id = ?",
                     (target.value, wo_id))
    else:
        responded = "coalesce(responded, :stamp)" if target is TicketStatus.IN_PROGRESS else "responded"
        conn.execute(f"UPDATE work_orders SET status = :status, acknowledged = coalesce(acknowledged, :stamp),"
                     f" responded = {responded}, {BUMP} WHERE wo_id = :wo_id",
                     {"status": target.value, "stamp": stamp, "wo_id": wo_id})
    outbox_add(conn, wo_id, TRANSITION, stamp, target.value)
    record_move(conn, wo_id, target.value, stamp, actor)
    conn.commit()
    return ticket(conn, wo_id)


def without_priority(conn: sqlite3.Connection) -> tuple[int, ...]:
    """The ids of the tickets with no priority yet (those stored before 8.2), in order."""
    return tuple(row[0] for row in conn.execute("SELECT wo_id FROM work_orders WHERE priority IS NULL ORDER BY wo_id"))


def set_priority(conn: sqlite3.Connection, wo_id: int, priority: Priority) -> Ticket:
    """Sets a ticket's priority (project does, from its fault's severity): set_priority(conn, 1, P1).priority is P1."""
    get(conn, wo_id)
    conn.execute(f"UPDATE work_orders SET priority = ?, {BUMP} WHERE wo_id = ?", (priority.value, wo_id))
    conn.commit()
    return ticket(conn, wo_id)


def set_assignee(conn: sqlite3.Connection, wo_id: int, assignee: str | None, moment: datetime | None = None,
                 read_at: int | None = None) -> Ticket:
    """Sets the person working the ticket (a tracker's field, SOL-14), or clears it with None or blank, at an instant
    (now when not given, for the outbox's event), raising its version: set_assignee(conn, 1, "crew B").assignee is
    "crew B"; read at an older version, StaleWrite and nothing written (12.2)."""
    check_read(conn, wo_id, read_at)
    name = None if assignee is None or not assignee.strip() else assignee.strip()
    conn.execute(f"UPDATE work_orders SET assignee = ?, {BUMP} WHERE wo_id = ?", (name, wo_id))
    stamp = utc(moment).isoformat() if moment is not None else datetime.now(timezone.utc).isoformat()
    outbox_add(conn, wo_id, UPDATE, stamp, ASSIGNEE.format(name=name or NOBODY))
    conn.commit()
    return ticket(conn, wo_id)


def comment(conn: sqlite3.Connection, wo_id: int, author: str, moment: datetime, body: str) -> Comment:
    """Adds a comment, never edited or deleted after: comment(conn, 1, "site@oahe.example", 11:40 UTC, "on my way") is
    Comment(1, 1, …). An unknown order, a blank author or body, or an instant before the ticket opened raises
    WorkOrderError; a naive instant NotUtc."""
    order = get(conn, wo_id)
    if not author.strip() or not body.strip():
        raise WorkOrderError(f"a comment on work order {wo_id} needs an author and words")
    if utc(moment) < order.opened:
        raise WorkOrderError(f"a comment on work order {wo_id} cannot come before it opened")
    cursor = conn.execute(INSERT_COMMENT, (wo_id, author.strip(), utc(moment).isoformat(), body.strip()))
    outbox_add(conn, wo_id, COMMENT, utc(moment).isoformat(), f"{author.strip()}: {body.strip()}")
    conn.commit()
    return next(found for found in comments(conn, wo_id) if found.comment_id == cursor.lastrowid)


def comments(conn: sqlite3.Connection, wo_id: int) -> tuple[Comment, ...]:
    """A ticket's comments, oldest first."""
    return tuple(Comment(cid, wid, author, datetime.fromisoformat(stamp), body)
                 for cid, wid, author, stamp, body in conn.execute(SELECT_COMMENTS, (wo_id,)))


def moves(conn: sqlite3.Connection, wo_id: int) -> tuple[Move, ...]:
    """A ticket's moves, oldest first (SP-035): after ops@oahe.example acknowledges ticket 1 at 11:40, moves(conn, 1) is
    (Move(1, 1, ACKNOWLEDGED, 11:40 UTC, "ops@oahe.example"),); a ticket nobody has moved, or moved before the store
    gained the table, has ()."""
    return tuple(Move(mid, wid, TicketStatus(status), datetime.fromisoformat(stamp), actor)
                 for mid, wid, status, stamp, actor in conn.execute(SELECT_MOVES, (wo_id,)))


def breaches(found: Ticket, moment: datetime, start: datetime | None = None) -> tuple[Breach, ...]:
    """A ticket's targets that are late or overdue at an instant (SOL-14), counted from start (the ticket's opened
    instant when not given; project gives a result's instant for a ticket opened from a failed result, 13.15); none for
    a ticket with no priority: the worked example's P1 at 15:00 gives (Breach(t, "respond", LATE),)."""
    if found.priority is None:
        return ()
    targets = TARGETS[found.priority]
    start = found.opened if start is None else start
    states = ((ACKNOWLEDGE, target_state(start, targets.acknowledge, found.acknowledged, moment)),
              (RESPOND, target_state(start, targets.respond, found.responded, moment)))
    return tuple(Breach(found, name, state) for name, state in states if state in LATE)


def past_target(conn: sqlite3.Connection, moment: datetime,
                start_of: Callable[[Ticket], datetime] | None = None) -> tuple[Breach, ...]:
    """Every open ticket's late or overdue targets at an instant, in wo_id order, acknowledgement before response: a
    query, not a stored flag, so it is true at whatever instant it is asked (SOL-14). start_of gives the instant a
    ticket's targets are counted from (its opened instant when not given)."""
    return tuple(breach for found in open_tickets(conn)
                 for breach in breaches(found, utc(moment), None if start_of is None else start_of(found)))
