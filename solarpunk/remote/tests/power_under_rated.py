"""Power under rated: no record of an inverter's feed reports more power than the inverter's nameplate rated_kw.
Evidences ISO 9001 9.1.1 (a number the plant is judged by is checked against its written method): a power above the
rating is a bad reading or a bad rating, and either corrupts the KPIs."""
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result, no_data, nothing_to_check

KINDS = (AssetKind.INVERTER,)
CLAUSES = ("9001-9.1.1",)
# SP-015's rule table: power over the rating is a bad reading or a bad rating, neither a catalogue fault: no code.
SUGGESTS = {AssetKind.INVERTER: None}


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Passes when every record's power_kw is at or under rated_kw, naming the first excess otherwise: rated 100 and
    powers (60.0, 100.0) give Result(True, "2 records at or under 100.0 kW"); 100.5 at 10:05 gives
    Result(False, "2026-06-01T10:05:00+00:00: power 100.5 kW over rated 100.0 kW"); rated_kw None gives
    Result(False, "no rating"); gaps alone, or no samples, give no data, Result(False, "no records", no_data=True)."""
    rated = asset.rated_kw
    if rated is None:
        return Result(False, "no rating")
    missing = nothing_to_check(samples)
    if missing is not None:
        return no_data(missing)  # Decision: SP-039 (nothing to check is not a pass)
    for sample in samples:
        # A gap carries no power (Invariant: SOL-06), so it is skipped with any record that has none.
        if sample.power_kw is not None and sample.power_kw > rated:
            return Result(False, f"{sample.at.isoformat()}: power {sample.power_kw} kW over rated {rated} kW")
    return Result(True, f"{len(samples)} records at or under {rated} kW")
