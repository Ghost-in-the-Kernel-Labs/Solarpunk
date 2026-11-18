"""Contractual availability of one inverter over a period, in sample intervals (Invariants: SOL-06, SOL-07, SOL-11)."""
from collections.abc import Sequence
from datetime import datetime

from solarpunk.kpi.results import Availability, rounded
from solarpunk.leaf.clock import Period
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.kpi_defs import EXCLUDED_CODES
from solarpunk.leaf.telemetry import Sample


def is_excluded(instant: datetime, faults: Sequence[Fault]) -> bool:
    """Whether a fault with an excluded code covers the interval starting at the instant (SOL-07): a SIT-002 over
    [10:05, 10:15) gives True at 10:10 and False at 10:15."""
    # Invariant: SOL-07
    return any(fault.code in EXCLUDED_CODES and fault.covers(instant) for fault in faults)


def is_down(instant: datetime, faults: Sequence[Fault]) -> bool:
    """Whether an OUTAGE fault covers the interval starting at the instant; a DERATE or INFO never does (SOL-11):
    an INV-001 over [10:10, 10:30) gives True at 10:10, an INV-002 over the same gives False."""
    # Invariant: SOL-11
    return any(fault.catalogue_row().counts_against_availability() and fault.covers(instant) for fault in faults)


def availability(period: Period, faults: Sequence[Fault], samples: Sequence[Sample] = ()) -> Availability:
    """(contractual − down) / contractual for one inverter, the faults its own and its site's (SOL-07). The contract's
    example, 10:00 to 11:00 with SIT-002 over [10:05, 10:15), INV-001 over [10:10, 10:30) and a gap at 10:40, gives
    Availability(0.7, 12, 2, 3, 1); with contractual 0 the value is 1.0."""
    # Invariant: SOL-07
    expected = period.expected()
    excluded = 0
    down = 0
    for instant in period.instants():
        if is_excluded(instant, faults):
            excluded += 1
        elif is_down(instant, faults):
            down += 1
    contractual = expected - excluded
    value = 1.0 if contractual == 0 else (contractual - down) / contractual
    gaps = sum(1 for sample in samples if sample.gap)
    return Availability(rounded(value), expected, excluded, down, gaps)
