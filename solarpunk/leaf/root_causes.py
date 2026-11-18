"""The root-cause codes: the closed list a work order is closed with, each with a one-line meaning (SP-011). A code
outside the list is refused, so every closed work order says why the asset failed in words written here
(docs/GHOST-IN-THE-KERNEL.md, "A corrective action carries its cause"). A new code is a change to this file with its
test, never a string written where the order is closed."""
from enum import Enum


class RootCause(Enum):
    """Why an asset failed, one code per cause: RootCause.COMPONENT.value is "RC-COMPONENT"; UNKNOWN is a code, so an
    honest closure is possible and its count is visible."""

    COMPONENT = "RC-COMPONENT"
    FIRMWARE = "RC-FIRMWARE"
    GRID = "RC-GRID"
    WEATHER = "RC-WEATHER"
    SENSOR = "RC-SENSOR"
    COMMS = "RC-COMMS"
    MAINTENANCE_OVERDUE = "RC-MAINTENANCE-OVERDUE"
    DESIGN = "RC-DESIGN"
    UNKNOWN = "RC-UNKNOWN"


class UnknownRootCause(ValueError):
    """Raised for a code the list does not hold: UnknownRootCause("not-a-cause is not a root-cause code")."""


MEANINGS: dict[RootCause, str] = {
    RootCause.COMPONENT: "A part failed: a module, fuse, contactor, fan or board wore out or broke",
    RootCause.FIRMWARE: "The asset's own software misbehaved or an update left it in a bad state",
    RootCause.GRID: "The grid outside the plant tripped, sagged or curtailed it",
    RootCause.WEATHER: "Wind, hail, snow, heat, flood or lightning did the damage or forced the stop",
    RootCause.SENSOR: "A measurement was wrong: the asset was healthy but a sensor said otherwise",
    RootCause.COMMS: "The link to the asset failed: the data stopped, not the asset",
    RootCause.MAINTENANCE_OVERDUE: "A scheduled maintenance task was late and the asset failed for want of it",
    RootCause.DESIGN: "The asset was specified, sized or installed wrongly for its place",
    RootCause.UNKNOWN: "The cause was not found; said honestly so its count is visible",
}

BY_VALUE: dict[str, RootCause] = {cause.value: cause for cause in RootCause}


def lookup_root_cause(code: str) -> RootCause:
    """The list's member for a code: lookup_root_cause("RC-GRID") is RootCause.GRID; lookup_root_cause("GRID") and
    lookup_root_cause("not-a-cause") raise UnknownRootCause."""
    # Invariant: SOL-04 (the pattern: a closed list, lookup refuses any other; SP-011)
    if code not in BY_VALUE:
        raise UnknownRootCause(f"{code} is not a root-cause code")
    return BY_VALUE[code]
