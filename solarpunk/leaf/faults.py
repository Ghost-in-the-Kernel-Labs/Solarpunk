"""A fault is one catalogue code carried by one asset over [opened, closed) (Invariant: SOL-04); an open fault has no
closed instant yet."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from solarpunk.leaf.clock import utc
from solarpunk.leaf.codes import FaultCode, lookup


@dataclass(frozen=True)
class Fault:
    """One fault: Fault(7, "OAHE-INV-003", "INV-001", 10:10 UTC, 10:30 UTC); open: closed is None."""

    fault_id: int
    asset_id: str
    code: str
    opened: datetime
    closed: datetime | None

    def __post_init__(self) -> None:
        """The code in the catalogue, the instants UTC, closed after opened: Fault(1, id, "INV-999", …) raises UnknownFaultCode."""
        lookup(self.code)
        utc(self.opened)
        if self.closed is not None and utc(self.closed) <= self.opened:
            raise ValueError(f"fault {self.fault_id} closes at or before it opened")

    def catalogue_row(self) -> FaultCode:
        """The catalogue's row for the code: Fault(1, id, "INV-001", …).catalogue_row().severity is Severity.OUTAGE."""
        return lookup(self.code)

    def covers(self, instant: datetime) -> bool:
        """Whether [opened, closed) holds the instant; an open fault covers every instant from opened on:
        Fault(1, id, "INV-001", 10:10, 10:30).covers(10:10) is True and .covers(10:30) is False."""
        if instant < self.opened:
            return False
        return self.closed is None or instant < self.closed

    def duration(self) -> timedelta | None:
        """closed − opened, or None while open: Fault(1, id, "INV-001", 10:10, 10:30).duration() is 20 minutes."""
        return None if self.closed is None else self.closed - self.opened
