"""Power not frozen: the inverter's power does not repeat the same non-zero value on FROZEN_RUN records in a row. A live
inverter's output moves with the sun and the clouds every five minutes; a value that sits still for half an hour is a
logger or gateway replaying its last register, and the energy counted from it is invented. Zero is left out, since a
stopped inverter at night is still. Evidences ISO 9001 9.1.3 (the data is fit to analyse)."""
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result

KINDS = (AssetKind.INVERTER,)
CLAUSES = ("9001-9.1.3",)
# SP-015's rule table: the catalogue has no code for a logger replaying its last value. A gap for Ghost: no suggestion.
SUGGESTS = {AssetKind.INVERTER: None}
# Six records on the five-minute grid (SOL-06) are half an hour.
FROZEN_RUN = 6


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Passes unless one non-zero power repeats on six records in a row (gaps skipped, records in time order): powers
    50.0, 51.2, 49.8 give Result(True, "3 power records, none frozen"); 50.0 six times from 10:00 gives Result(False,
    "power 50.0 kW unchanged on 6 records from 2026-06-01T10:00:00+00:00")."""
    read = sorted((s for s in samples if s.power_kw is not None), key=lambda sample: sample.at)
    run_start = 0
    for index in range(1, len(read) + 1):
        if index < len(read) and read[index].power_kw == read[run_start].power_kw:
            continue
        if index - run_start >= FROZEN_RUN and read[run_start].power_kw != 0:
            first = read[run_start]
            return Result(False, f"power {first.power_kw} kW unchanged on {index - run_start} records from "
                                 f"{first.at.isoformat()}")
        run_start = index
    return Result(True, f"{len(read)} power records, none frozen")
