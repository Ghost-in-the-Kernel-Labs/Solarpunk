"""A ticket's rules (Invariant: SOL-14, SP-022): its five statuses and the moves allowed between them, its priority from
the fault's severity, the acknowledgement and response targets of each priority, the four states a target is in at an
instant, and which side owns each field once a remote tracker is joined. The targets are Claude's proposal until Ghost
sets his own (docs/CONTRACT.md SOL-14). It imports the leaf alone, so every module may read it."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from solarpunk.leaf.clock import utc
from solarpunk.leaf.codes import Severity


class TicketStatus(Enum):
    """Where a ticket stands: TicketStatus.IN_PROGRESS.value is "in progress"; CLOSED is final."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(Enum):
    """How soon a ticket's work is wanted, from its fault's severity: Priority.PRIORITY_P1 for an OUTAGE."""

    PRIORITY_P1 = "P1"
    PRIORITY_P2 = "P2"
    PRIORITY_P3 = "P3"


class TargetState(Enum):
    """A target at an instant (SOL-14): met or late once it happened, pending or overdue while it has not."""

    MET = "met"
    LATE = "late"
    PENDING = "pending"
    OVERDUE = "overdue"


class BadMove(ValueError):
    """Raised for a move SOL-14 does not allow: BadMove("a ticket cannot move from closed to open")."""


@dataclass(frozen=True)
class Targets:
    """A priority's two targets, measured from the ticket's opening: Targets(1 h, 4 h) for P1."""

    acknowledge: timedelta
    respond: timedelta


# Invariant: SOL-14 (the six moves; test/solarpunk/test_tickets_contract.py reads the contract's table against this)
MOVES: frozenset[tuple[TicketStatus, TicketStatus]] = frozenset({
    (TicketStatus.OPEN, TicketStatus.ACKNOWLEDGED),
    (TicketStatus.OPEN, TicketStatus.IN_PROGRESS),
    (TicketStatus.ACKNOWLEDGED, TicketStatus.IN_PROGRESS),
    (TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED),
    (TicketStatus.RESOLVED, TicketStatus.IN_PROGRESS),
    (TicketStatus.RESOLVED, TicketStatus.CLOSED),
})
PRIORITY_OF: dict[Severity, Priority] = {Severity.OUTAGE: Priority.PRIORITY_P1, Severity.DERATE: Priority.PRIORITY_P2,
                                         Severity.INFO: Priority.PRIORITY_P3}
# Claude's proposal, in force until Ghost sets his own (SOL-14): an outage acknowledged within the hour and worked on
# within four; a derate within a working half-day and the next day; information within a day and three.
TARGETS: dict[Priority, Targets] = {
    Priority.PRIORITY_P1: Targets(timedelta(hours=1), timedelta(hours=4)),
    Priority.PRIORITY_P2: Targets(timedelta(hours=4), timedelta(hours=24)),
    Priority.PRIORITY_P3: Targets(timedelta(hours=24), timedelta(hours=72)),
}
# Who owns each field once a remote tracker is joined (SOL-14): Solarpunk keeps what the KPIs and the register read.
SOLARPUNK = "Solarpunk"
TRACKER = "tracker"
OWNERS: dict[str, str] = {
    "fault code": SOLARPUNK, "assigned by": SOLARPUNK, "root cause": SOLARPUNK,
    "opened and closed instants": SOLARPUNK, "status": SOLARPUNK,
    "working assignee": TRACKER, "comments": TRACKER, "scheduling": TRACKER,
}


def check_move(source: TicketStatus, target: TicketStatus) -> TicketStatus:
    """The target status, once the move is one SOL-14 allows: check_move(OPEN, ACKNOWLEDGED) is ACKNOWLEDGED;
    check_move(CLOSED, OPEN) raises BadMove("a ticket cannot move from closed to open")."""
    # Invariant: SOL-14
    if (source, target) not in MOVES:
        raise BadMove(f"a ticket cannot move from {source.value} to {target.value}")
    return target


def priority_of(severity: Severity) -> Priority:
    """A ticket's priority from its fault's severity: priority_of(Severity.OUTAGE) is Priority.PRIORITY_P1."""
    return PRIORITY_OF[severity]


def target_state(opened: datetime, target: timedelta, happened: datetime | None, moment: datetime) -> TargetState:
    """One target's state at an instant (SOL-14): opened 10:00 with a 1 h target, acknowledged 10:40, is MET; responded
    14:30 against 4 h is LATE; not yet responded at 13:00 is PENDING, at 14:15 OVERDUE. Instants are UTC (NotUtc
    otherwise); the due instant itself counts as in time."""
    # Invariant: SOL-14
    due = utc(opened) + target
    if happened is not None:
        return TargetState.MET if utc(happened) <= due else TargetState.LATE
    return TargetState.PENDING if utc(moment) <= due else TargetState.OVERDUE


# The outbox's four kinds of event (11.1, SP-027), one per sink method: a ticket opened, a field of it changed (its
# priority or working assignee), a comment added, a move between statuses.
CREATE = "create"
UPDATE = "update"
COMMENT = "comment"
TRANSITION = "transition"
EVENT_KINDS = (CREATE, UPDATE, COMMENT, TRANSITION)


@dataclass(frozen=True)
class OutboxEvent:
    """One change of a ticket waiting to reach a tracker, written in the change's own transaction (SP-027):
    OutboxEvent(1, 1, "create", 11:30 UTC, "OAHE-INV-002", "Inverter offline: …") is the demo outage's ticket opening.
    detail is the words the kind carries: the note for a create, "assignee crew B" for an update, "<author>: <words>"
    for a comment, the new status for a transition, or "closed" for a close (an
    old store's close carries its root-cause code, "RC-COMPONENT")."""

    event_id: int
    wo_id: int
    kind: str
    moment: datetime
    asset_id: str
    detail: str


@dataclass(frozen=True)
class RemoteChange:
    """A change a person made in a tracker, read back by a source since a cursor: RemoteChange("local:1", 1,
    "comment", 12:05 UTC, "crew B", "on site"). Solarpunk's rules accept or refuse it later (SOL-14); reading it changes
    nothing."""

    ref: str
    wo_id: int
    kind: str
    moment: datetime
    author: str
    detail: str
