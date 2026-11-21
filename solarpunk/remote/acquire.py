"""What a remote test may ask the runner to read for it (13.3, SP-020): a test declares ACQUIRE, a value of the closed
set ACQUISITIONS, and the runner takes the reads through the feed and hands them to `run`, which reads nothing else.
Burst("power_kw", 1, 60) is a power read once a second for a minute. A read keeps its instant, and an instant comes
from a clock the runner is handed, so a test drives a minute without waiting one. This module reads no feed itself
(MOD-05): the runner gives it a reader."""
import functools
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from solarpunk.leaf.assets import Asset
from solarpunk.remote.results import no_data

NO_READS = "no reads"
NEEDS_READS = "needs live reads, not stored samples"


class ReadFailed(ValueError):
    """Raised by a reader for a read it could not take: ReadFailed("127.0.0.1:5020 is unreachable")."""


@dataclass(frozen=True)
class Read:
    """One live reading and the instant it was taken: Read(2026-06-01T10:00:03Z, 78.4); a read that failed has no value."""

    moment: datetime
    value: float | None


@dataclass(frozen=True)
class Burst:
    """A field read every every_s seconds for for_s seconds: Burst("power_kw", 1, 60) takes 60 reads; a non-positive
    period or a duration shorter than the period raises ValueError."""

    field: str
    every_s: float
    for_s: float

    def __post_init__(self) -> None:
        """Refuses a burst that would take no reads: Burst("power_kw", 0, 60) and Burst("power_kw", 5, 1) raise."""
        if self.every_s <= 0 or self.for_s < self.every_s:
            raise ValueError(f"a burst reads at least once: every {self.every_s} s for {self.for_s} s")

    def count(self, shorten_to_s: float | None = None) -> int:
        """The reads it takes, the duration shortened to shorten_to_s when that is given: Burst("power_kw", 1, 60).count()
        is 60 and .count(5) is 5; a shortening below the period still takes one read."""
        span = self.for_s if shorten_to_s is None else min(self.for_s, shorten_to_s)
        return max(1, int(span // self.every_s))


# The closed set of what a test may declare as ACQUIRE: a new kind of acquisition is a new member, decided, never free.
ACQUISITIONS = (Burst,)
Clock = Callable[[float], datetime]  # waits that many seconds, then says the instant: a test hands one that never waits
Reader = Callable[[Asset, str, datetime], float | None]  # asset, field, instant: one current reading
Acquirer = Callable[[Asset, Burst], tuple[Read, ...]]


def wall_clock(wait_s: float) -> datetime:
    """The runner's real clock: waits wait_s seconds and returns the UTC instant; wall_clock(0) is now."""
    if wait_s > 0:
        time.sleep(wait_s)
    return datetime.now(timezone.utc)


def take(asset: Asset, burst: Burst, reader: Reader, clock: Clock, shorten_to_s: float | None = None) -> tuple[Read, ...]:
    """The burst's reads, each at the instant the clock gave: a clock stepping one second from 10:00:00 and a reader
    answering 50.0 give for Burst("power_kw", 1, 60) sixty Reads, the first Read(10:00:00, 50.0); shorten_to_s cuts the
    duration (a test's way of not waiting a minute); a read the reader could not take is Read(instant, None)."""
    reads: list[Read] = []
    for number in range(burst.count(shorten_to_s)):
        moment = clock(0.0 if number == 0 else burst.every_s)
        try:
            value = reader(asset, burst.field, moment)
        except ReadFailed:
            value = None
        reads.append(Read(moment, value))
    return tuple(reads)


def nothing_read(reads: tuple[Read, ...]) -> str | None:
    """Why the reads hold nothing to judge, or None when one has a value: () gives "no reads", three failed reads
    "no reads: 3 failed"."""
    if any(read.value is not None for read in reads):
        return None
    return f"{NO_READS}: {len(reads)} failed" if reads else NO_READS


@functools.cache  # one guard to a `run`, so the registry's tests compare equal from one look to the next
def reads_only(run: Callable[[Asset, tuple[Read, ...]], object]) -> Callable:
    """A test's `run` that judges reads, guarded: handed stored samples (the field baseline, a one-off command line) it
    says no data, never a crash and never a pass, and handed reads, or nothing, it judges."""
    def guarded(asset: Asset, given: tuple) -> object:
        """Judges the reads, or says no data for anything that is not a read."""
        if all(isinstance(read, Read) for read in given):
            return run(asset, given)
        return no_data(NEEDS_READS)
    guarded.__doc__ = run.__doc__
    return guarded
