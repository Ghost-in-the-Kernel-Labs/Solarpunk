"""What every tracker implements (11.1, SP-027): a sink that takes Solarpunk's ticket changes (create, update, comment,
transition) and a source that gives back the changes people made in the tracker since a cursor; and deliver, which
hands one outbox event to the sink method its kind names. A tracker that cannot be reached raises Unreachable, and the
event waits in the outbox for the next drain; Solarpunk's ledger never waits on it (SP-022)."""
from typing import Protocol

from solarpunk.leaf.tickets import COMMENT, CREATE, TRANSITION, UPDATE, OutboxEvent, RemoteChange


class Unreachable(ConnectionError):
    """Raised by a sink or source whose tracker cannot be reached: Unreachable("the tracker did not answer")."""


class UnknownTicket(LookupError):
    """Raised by a sink for a ticket it was never sent: UnknownTicket("work order 9 is not in the tracker")."""


class TicketSink(Protocol):
    """Takes Solarpunk's changes. create is idempotent: a second create of one work order gives back the first's
    reference, so a delivery repeated after a lost answer makes no second issue."""

    def create(self, event: OutboxEvent) -> str:
        """Opens the ticket in the tracker and returns its reference ("local:1")."""

    def update(self, event: OutboxEvent) -> None:
        """Changes a field the tracker shows (the working assignee)."""

    def comment(self, event: OutboxEvent) -> None:
        """Adds a comment, its author and words in the event's detail."""

    def transition(self, event: OutboxEvent) -> None:
        """Moves the ticket to the status in the event's detail, or closes it with the root cause there."""


class TicketSource(Protocol):
    """Gives back what people did in the tracker, oldest first, and a cursor to ask from next time."""

    def changes_since(self, cursor: int) -> tuple[tuple[RemoteChange, ...], int]:
        """The changes after cursor and the cursor after the last of them; none gives ((), cursor)."""


def deliver(sink: TicketSink, event: OutboxEvent) -> None:
    """Hands one event to the sink method its kind names: a "create" to create, and so on; an unknown kind is a
    ValueError, never a silent drop."""
    method = {CREATE: sink.create, UPDATE: sink.update, COMMENT: sink.comment, TRANSITION: sink.transition}.get(event.kind)
    if method is None:
        raise ValueError(f"an outbox event of kind {event.kind!r} has no sink method")
    method(event)
