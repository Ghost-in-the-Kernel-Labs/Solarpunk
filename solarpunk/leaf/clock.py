"""Time in the fleet (Invariant: SOL-06): UTC only, samples every SAMPLE_INTERVAL_S on the grid from the hour, periods
half-open."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

SAMPLE_INTERVAL_S = 300
SAMPLE_INTERVAL = timedelta(seconds=SAMPLE_INTERVAL_S)
HOURS_PER_SAMPLE = SAMPLE_INTERVAL_S / 3600


class NotUtc(ValueError):
    """Raised for a naive datetime or one not in UTC: NotUtc(datetime(2026, 1, 1))."""


class OffTheGrid(ValueError):
    """Raised for an instant not on a SAMPLE_INTERVAL_S multiple from the hour: OffTheGrid(10:02)."""


def utc(moment: datetime) -> datetime:
    """The same instant, checked: utc(datetime(2026, 1, 1, tzinfo=timezone.utc)) returns it; a naive datetime raises NotUtc."""
    if moment.tzinfo is None or moment.utcoffset() != timedelta(0):
        raise NotUtc(f"{moment.isoformat()} is not UTC")
    return moment


def on_grid(moment: datetime) -> datetime:
    """The instant, checked to lie on the sample grid: on_grid(10:05 UTC) returns it; 10:02 raises OffTheGrid."""
    checked = utc(moment)
    seconds = checked.minute * 60 + checked.second + checked.microsecond / 1_000_000
    if seconds % SAMPLE_INTERVAL_S != 0:
        raise OffTheGrid(f"{checked.isoformat()} is not on the {SAMPLE_INTERVAL_S} s grid")
    return checked


@dataclass(frozen=True)
class Period:
    """A half-open interval [start, end) on the grid: Period(10:00, 11:00).expected() is 12."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        """Both ends on the grid, start before end: Period(11:00, 10:00) raises ValueError."""
        on_grid(self.start)
        on_grid(self.end)
        if self.start >= self.end:
            raise ValueError(f"period {self.start.isoformat()} .. {self.end.isoformat()} is empty or reversed")

    def expected(self) -> int:
        """The sample instants the period holds: Period(10:00, 11:00).expected() is 12."""
        return int((self.end - self.start) / SAMPLE_INTERVAL)

    def instants(self) -> list[datetime]:
        """Every expected instant in order: Period(10:00, 10:15).instants() is [10:00, 10:05, 10:10]."""
        return [self.start + SAMPLE_INTERVAL * i for i in range(self.expected())]

    def hours(self) -> float:
        """The period's length in hours: Period(10:00, 11:00).hours() is 1.0."""
        return (self.end - self.start) / timedelta(hours=1)


def at(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    """A UTC instant by its parts: at(2026, 6, 1, 10, 5) is 2026-06-01T10:05:00+00:00."""
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
