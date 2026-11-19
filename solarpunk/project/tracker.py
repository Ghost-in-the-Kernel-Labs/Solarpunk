"""The outbox's drain (11.1, SP-022, SP-027): the ticket changes the ledger wrote to its outbox, handed to a tracker's
sink oldest first and stamped as each is taken. A tracker that cannot be reached stops the drain where it is, the rest
waiting for the next one, and nothing in the ledger waits on it; a ticket the tracker was never sent (one made before
the outbox) is opened there first from its work order. The scheduled run drains into the local tracker."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from solarpunk.leaf.tickets import CREATE, OutboxEvent
from solarpunk.tickets.adapter import TicketSink, Unreachable, UnknownTicket, deliver
from solarpunk.tickets.local import LocalTracker
from solarpunk.workorders import ledger as work_ledger
from solarpunk.workorders import outbox


@dataclass(frozen=True)
class Drained:
    """One drain's outcome: Drained(3, 0, None) sent three events and left none; Drained(1, 2, "the tracker did not
    answer") was stopped by an unreachable tracker with two waiting."""

    sent: int
    waiting: int
    stopped_by: str | None


def opening_of(conn: sqlite3.Connection, event: OutboxEvent) -> OutboxEvent:
    """A create for the event's work order built from the order itself, for a tracker that never had it."""
    order = work_ledger.get(conn, event.wo_id)
    return OutboxEvent(0, order.wo_id, CREATE, order.opened, order.asset_id, order.note)


def drain_outbox(conn: sqlite3.Connection, sink: TicketSink, moment: datetime) -> Drained:
    """Hands every waiting event to the sink, oldest first, stamping each it takes at moment; stops at the first
    Unreachable (SP-022: the tracker being down never blocks the ledger, whose writes never call it)."""
    events = outbox.pending(conn)
    for index, event in enumerate(events):
        try:
            try:
                deliver(sink, event)
            except UnknownTicket:
                sink.create(opening_of(conn, event))
                deliver(sink, event)
        except Unreachable as down:
            return Drained(index, len(events) - index, str(down))
        outbox.mark_sent(conn, event.event_id, moment)
    return Drained(len(events), 0, None)


def local_tracker(conn: sqlite3.Connection) -> LocalTracker:
    """The local tracker over the store, the scheduled run's sink until a remote one is joined."""
    return LocalTracker(conn)


def tickets_waiting(conn: sqlite3.Connection) -> tuple[OutboxEvent, ...]:
    """The outbox's events no tracker has taken, oldest first."""
    return outbox.pending(conn)
