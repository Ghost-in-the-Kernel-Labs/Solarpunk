"""Power ripple: read once a second for a minute, an inverter's power moves by no more than RIPPLE_SHARE of its rating
between its lowest and highest read. A healthy inverter's output follows the sun and the clouds slowly; a swing within
the minute is a control loop hunting or a string dropping in and out, which the five-minute samples average away and
never show. The runner takes the reads (ACQUIRE, SP-020); `run` judges only the reads it is handed. Evidences ISO 9001
9.1.1 (a number the plant is judged by is checked against its written method). The threshold is Ghost's (SP-049):
5% of rated_kw peak to peak over the minute; the simulator's worst minute over 40 seeds moves 1.1% of rating (J-127), so
a healthy inverter passes with room, and hunting of more than 5% is flagged."""
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.remote.acquire import Burst, Read, nothing_read
from solarpunk.remote.results import Result, no_data

KINDS = (AssetKind.INVERTER,)
CLAUSES = ("9001-9.1.1",)
# SP-020's reactions (SP-015's rule table): a ripple has no code of its own in the catalogue (SP-047: no OUTAGE or DERATE for a test); the
# generic SIT-004 follows. No fault code of its own.
REACTIONS = {}  # the generic SIT-004 fault alone
# What the runner reads for this test: power, once a second, for a minute (Ghost's example, SP-020).
ACQUIRE = Burst(field="power_kw", every_s=1, for_s=60)
# Decision: SP-049. The lowest to highest power of the minute as a share of the rating. A healthy day moves at
# most 1.1% of rating in a minute (the simulator's, over 40 seeds, J-127), so 5% leaves four times the room.
RIPPLE_SHARE = 0.05


def run(asset: Asset, reads: tuple[Read, ...]) -> Result:
    """Passes when the reads' power, highest less lowest, is at most RIPPLE_SHARE of rated_kw: rated 100 and 60 reads
    from 50.0 to 52.0 give Result(True, "60 reads, ripple 2.0 kW within rated 100.0 kW x 5%"); reads from 50.0 to 58.0
    give Result(False, "2026-06-01T10:00:00+00:00: ripple 8.0 kW over rated 100.0 kW x 5%"), naming the first read;
    rated_kw None gives Result(False, "no rating"); no reads, or every read failed, give no data."""
    rated = asset.rated_kw
    if rated is None:
        return Result(False, "no rating")
    missing = nothing_read(reads)
    if missing is not None:
        return no_data(missing)  # Decision: SP-039 (nothing to check is not a pass)
    held = [read.value for read in reads if read.value is not None]
    ripple = round(max(held) - min(held), 3)
    allowed = f"rated {rated} kW x {RIPPLE_SHARE:.0%}"
    if ripple > rated * RIPPLE_SHARE:
        return Result(False, f"{reads[0].moment.isoformat()}: ripple {ripple} kW over {allowed}")
    return Result(True, f"{len(reads)} reads, ripple {ripple} kW within {allowed}")
