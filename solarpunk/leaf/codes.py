"""The fault-code catalogue: the closed list of error codes an asset may carry, each with the kind of asset it belongs
to and its severity. A code outside the list is refused, so every fault in the ledger has a meaning written here
(docs/GHOST-IN-THE-KERNEL.md, "A corrective action carries its cause"). Run: python3 -m solarpunk.leaf.codes prints the list (it reads no data, so -I is not needed; -I would hide the package)."""
import re
from dataclasses import dataclass
from enum import Enum

CODE_SHAPE = re.compile(r"^(?P<prefix>[A-Z]{3})-(?P<number>\d{3})$")


class AssetKind(Enum):
    """The kinds of asset the fleet holds, each the prefix of its codes: AssetKind.INVERTER.value is "INV"."""

    SITE = "SIT"
    INVERTER = "INV"
    STRING = "STR"
    TRACKER = "TRK"
    METER = "MTR"
    SENSOR = "SEN"


class Severity(Enum):
    """How a fault bears on production, lowest first: INFO changes nothing, DERATE cuts output, OUTAGE stops it.
    Severity.OUTAGE.value is 3 and Severity.INFO.value < Severity.OUTAGE.value."""

    INFO = 1
    DERATE = 2
    OUTAGE = 3


class AssetStatus(Enum):
    """The one glyph the front end shows per asset (Phase 3): GREEN, the last scheduled run's remote tests all passed;
    YELLOW, one failed; RED, the asset carries an open OUTAGE fault. AssetStatus.RED.value is "red"."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass(frozen=True)
class FaultCode:
    """One row of the catalogue: FaultCode("INV-001", AssetKind.INVERTER, Severity.OUTAGE, "Inverter offline")."""

    code: str
    kind: AssetKind
    severity: Severity
    meaning: str

    def counts_against_availability(self) -> bool:
        """An asset carrying this code is unavailable: OUTAGE does, DERATE and INFO do not.
        FaultCode("INV-001", AssetKind.INVERTER, Severity.OUTAGE, "x").counts_against_availability() is True."""
        return self.severity is Severity.OUTAGE


class UnknownFaultCode(ValueError):
    """Raised for a code the catalogue does not hold: UnknownFaultCode("INV-999")."""


CATALOGUE: tuple[FaultCode, ...] = (
    FaultCode("SIT-001", AssetKind.SITE, Severity.OUTAGE, "Grid outage: the point of interconnection is de-energised"),
    FaultCode("SIT-002", AssetKind.SITE, Severity.DERATE, "Grid curtailment: output capped by the operator's instruction"),
    FaultCode("SIT-003", AssetKind.SITE, Severity.INFO, "Client-requested outage: planned, excluded from availability by contract"),
    FaultCode("SIT-004", AssetKind.SITE, Severity.INFO, "Remote test failed: its cause is not yet known"),
    FaultCode("INV-001", AssetKind.INVERTER, Severity.OUTAGE, "Inverter offline: no AC output while irradiance is above the start threshold"),
    FaultCode("INV-002", AssetKind.INVERTER, Severity.DERATE, "Inverter over-temperature derate"),
    FaultCode("INV-003", AssetKind.INVERTER, Severity.OUTAGE, "DC ground fault: the inverter has isolated itself"),
    FaultCode("INV-004", AssetKind.INVERTER, Severity.INFO, "Firmware update pending"),
    FaultCode("INV-005", AssetKind.INVERTER, Severity.DERATE, "Output under the performance floor: the performance ratio fell below its floor"),
    FaultCode("STR-001", AssetKind.STRING, Severity.DERATE, "String open: zero current while sibling strings produce"),
    FaultCode("STR-002", AssetKind.STRING, Severity.DERATE, "String under-performing: current below 80 % of its siblings' median"),
    FaultCode("TRK-001", AssetKind.TRACKER, Severity.DERATE, "Tracker stalled: angle unchanged while the sun moved"),
    FaultCode("TRK-002", AssetKind.TRACKER, Severity.INFO, "Tracker in wind stow"),
    FaultCode("MTR-001", AssetKind.METER, Severity.INFO, "Revenue meter communication lost: energy yield estimated from inverters"),
    FaultCode("SEN-001", AssetKind.SENSOR, Severity.INFO, "Irradiance sensor out of range: performance ratio marked unreliable"),
)

# SP-046: the code a failing remote test raises where its rule table names none; it belongs to no one kind of asset.
GENERIC_TEST_FAILURE = "SIT-004"

BY_CODE: dict[str, FaultCode] = {fault.code: fault for fault in CATALOGUE}


def parse(code: str) -> tuple[str, int]:
    """The prefix and number of a well-formed code: parse("INV-001") is ("INV", 1); parse("inv-1") raises UnknownFaultCode."""
    match = CODE_SHAPE.match(code)
    if match is None:
        raise UnknownFaultCode(f"{code!r} is not of the shape AAA-000")
    return match.group("prefix"), int(match.group("number"))


def lookup(code: str) -> FaultCode:
    """The catalogue's row for a code: lookup("INV-001").severity is Severity.OUTAGE; lookup("INV-999") raises UnknownFaultCode."""
    parse(code)
    if code not in BY_CODE:
        raise UnknownFaultCode(f"{code} is not in the catalogue")
    return BY_CODE[code]


def codes_for(kind: AssetKind) -> tuple[FaultCode, ...]:
    """The catalogue's rows for one kind, in catalogue order: codes_for(AssetKind.TRACKER) has 2 rows, TRK-001 first."""
    return tuple(fault for fault in CATALOGUE if fault.kind is kind)


def listing() -> str:
    """The catalogue as lines "code kind severity meaning", one per row: listing().splitlines()[0] starts with "SIT-001 SITE OUTAGE"."""
    return "\n".join(f"{fault.code} {fault.kind.name} {fault.severity.name} {fault.meaning}" for fault in CATALOGUE)


if __name__ == "__main__":
    print(listing())
