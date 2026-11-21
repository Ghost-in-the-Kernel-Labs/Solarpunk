"""Power under rated: no record of an inverter's feed reports more power than the inverter's nameplate rated_kw, 1%
over allowed for metering (SP-039). Evidences ISO 9001 9.1.1 (a number the plant is judged by is checked against its
written method): a power further above the rating is a bad reading or a bad rating, and either corrupts the KPIs."""
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result, no_data, nothing_to_check

KINDS = (AssetKind.INVERTER,)
CLAUSES = ("9001-9.1.1",)
# SP-020's reactions (SP-015's rule table): power over the rating is a bad reading or a bad rating, neither a catalogue fault: no code.
REACTIONS = {}  # the generic SIT-004 fault alone
# J-101: 9069's rated inverters read 825.2 to 825.7 kW against 825 kW on 3 days, metering, not a fault; a power up to
# this share over the rating is allowed (SP-039, call 3).
OVER_RATING_SHARE = 0.01


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Passes when every record's power_kw is at or under rated_kw plus OVER_RATING_SHARE of it, naming the first
    excess otherwise: rated 100 and powers (60.0, 101.0) give Result(True, "2 records at or under rated 100.0 kW + 1%");
    101.5 at 10:05 gives Result(False, "2026-06-01T10:05:00+00:00: power 101.5 kW over rated 100.0 kW + 1%");
    rated_kw None gives Result(False, "no rating"); gaps alone, or no samples, give no data,
    Result(False, "no records", no_data=True)."""
    rated = asset.rated_kw
    if rated is None:
        return Result(False, "no rating")
    missing = nothing_to_check(samples)
    if missing is not None:
        return no_data(missing)  # Decision: SP-039 (nothing to check is not a pass)
    ceiling = rated * (1 + OVER_RATING_SHARE)  # Decision: SP-039 (1% over the rating is metering, not a fault)
    allowed = f"rated {rated} kW + {OVER_RATING_SHARE:.0%}"
    for sample in samples:
        # A gap carries no power (Invariant: SOL-06), so it is skipped with any record that has none.
        if sample.power_kw is not None and sample.power_kw > ceiling:
            return Result(False, f"{sample.moment.isoformat()}: power {sample.power_kw} kW over {allowed}")
    return Result(True, f"{len(samples)} records at or under {allowed}")
