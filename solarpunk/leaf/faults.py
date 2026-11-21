"""A fault is one catalogue code carried by one asset over [opened, closed) (Invariant: SOL-04); an open fault has no
closed instant yet. It names who assigned it: since SP-046 the test or device whose result raised it, before that an engineer and, when
it was called in, the operator who entered it (SP-015); a fault stored before SP-015 reads assigned_by "unrecorded"."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from solarpunk.leaf.clock import utc
from solarpunk.leaf.codes import FaultCode, lookup

# What a fault stored before SP-015 says of who assigned it: never an engineer's address, so never taken for one.
UNRECORDED = "unrecorded"
# SP-046: telemetry assigns a fault, and the record says which: a remote test ("test:reachable") or a device ("device").
TEST_ASSIGNER = "test:{name}"
DEVICE_ASSIGNER = "device"


def by_telemetry(assigned_by: str) -> bool:
    """Whether a fault was raised by telemetry, not by an engineer: by_telemetry("test:reachable") and
    by_telemetry("device") are True, by_telemetry("tech@oahe.example") is False."""
    return assigned_by == DEVICE_ASSIGNER or assigned_by.startswith(TEST_ASSIGNER.format(name=""))


@dataclass(frozen=True)
class Fault:
    """One fault: Fault(7, "OAHE-INV-003", "INV-001", 10:10 UTC, 10:30 UTC, "tech@oahe.example", None); open: closed is
    None; recorded_by names the operator who entered an engineer's called-in fault, None when the engineer did."""

    fault_id: int
    asset_id: str
    code: str
    opened: datetime
    closed: datetime | None
    assigned_by: str = UNRECORDED
    recorded_by: str | None = None
    version: int = 1  # 12.2: raised by one with every change the ledger stores

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
