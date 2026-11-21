"""Night power near zero: when the irradiance says the sun is down, the inverter reports next to no power. Power with no
sun is a stuck meter, a mislabelled channel or a clock off by hours, and any of them corrupts the energy the KPIs count.
"Down" is irradiance at or under NIGHT_W_M2; "next to no power" is at or under NIGHT_SHARE of the rating. Evidences
ISO 9001 9.1.3 (the data is fit to analyse)."""
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result, no_data, nothing_to_check

KINDS = (AssetKind.INVERTER,)
CLAUSES = ("9001-9.1.3",)
# SP-015's rule table: power with no sun is a metering or clock fault the catalogue has no code for.
SUGGESTS = {AssetKind.INVERTER: None}
# A pyranometer reads a few W/m² of sky light and offset at night; 5 is above that and far below any useful sun.
NIGHT_W_M2 = 5.0
# An inverter's own standby draw and metering noise stay well under 1 % of its rating.
NIGHT_SHARE = 0.01


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Passes when every night record's power is at or under 1 % of rated_kw: rated 100 with (irradiance 0, 0.4 kW)
    gives Result(True, "1 night records near zero"); (0, 3.0) at 02:00 gives Result(False, "2026-06-01T02:00:00+00:00:
    3.0 kW at night, over 1.0 kW"); rated_kw None gives Result(False, "no rating"); gaps alone, or no samples, give
    no data, Result(False, "no records", no_data=True), while records with none at night pass, "0 night records near
    zero" (SP-039)."""
    if asset.rated_kw is None:
        return Result(False, "no rating")
    missing = nothing_to_check(samples)
    if missing is not None:
        return no_data(missing)  # Decision: SP-039 (nothing to check is not a pass)
    limit = asset.rated_kw * NIGHT_SHARE
    night = [s for s in samples if s.irradiance_w_m2 is not None and s.power_kw is not None
             and s.irradiance_w_m2 <= NIGHT_W_M2]
    for sample in night:
        if sample.power_kw > limit:
            return Result(False, f"{sample.at.isoformat()}: {sample.power_kw} kW at night, over {limit} kW")
    return Result(True, f"{len(night)} night records near zero")
