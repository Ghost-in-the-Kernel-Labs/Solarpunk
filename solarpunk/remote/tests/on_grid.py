"""On grid: every record the feed answered falls on the sample grid (Invariant: SOL-06) and every value it carries
lies inside the maintenance list's range for the asset's kind. Evidences ISO 55000 7.5 (the information held about
the asset is what the list says it is) and ISO 9001 9.1.3 (the data is fit to analyse)."""
from solarpunk.leaf.asset_types import FieldRange, fields_of, kinds
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import OffTheGrid, on_grid
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result, no_data, nothing_to_check

KINDS = tuple(kind for kind in kinds() if fields_of(kind))
CLAUSES = ("55000-7.5", "9001-9.1.3")
# SP-020's reactions (SP-015's rule table): a record off the grid or out of range is the data's fault, not the equipment's: no code.
REACTIONS = {}  # the generic SIT-004 fault alone
SAMPLE_FIELDS = ("irradiance_w_m2", "power_kw")
POWER_FIELD = "power_kw"
# J-101: 9068's inverters draw 6 to 24 kW at night, up to 1.3% of their 1,910 kW rating; an inverter's power may fall
# this share of its rated_kw below zero, the list's minimum of 0 holding with no rating (SP-039, call 2).
NIGHT_DRAW_SHARE = 0.02


def field_range(asset: Asset, field: str) -> FieldRange | None:
    """The range one of the asset's fields is held to, None for a field its kind does not answer with: the list's,
    except an inverter's power_kw, whose minimum is -NIGHT_DRAW_SHARE of its rated_kw: rated 100 gives FieldRange("kW",
    -2.0, None); with no rating the list's FieldRange("kW", 0, None)."""
    # Decision: SP-039 (an inverter's power minimum is -2% of its rating, 0 with no rating)
    listed = fields_of(asset.kind).get(field)
    if listed is None or field != POWER_FIELD or asset.kind is not AssetKind.INVERTER or asset.rated_kw is None:
        return listed
    return FieldRange(listed.unit, -NIGHT_DRAW_SHARE * asset.rated_kw, listed.maximum)


def problem(asset: Asset, sample: Sample) -> str | None:
    """What is wrong with one record, or None: an inverter's 10:05 sample with irradiance 1600 gives
    "2026-06-01T10:05:00+00:00: irradiance_w_m2 1600.0 out of range"; a tracker's sample carrying power_kw gives
    "…: TRACKER has no field power_kw"; an off-grid instant gives "…: off the grid"."""
    # Invariant: SOL-06
    try:
        on_grid(sample.moment)
    except OffTheGrid:
        return f"{sample.moment.isoformat()}: off the grid"
    for field in SAMPLE_FIELDS:
        value = getattr(sample, field)
        if value is None:
            continue
        held = field_range(asset, field)
        if held is None:
            return f"{sample.moment.isoformat()}: {asset.kind.name} has no field {field}"
        if not held.holds(value):
            return f"{sample.moment.isoformat()}: {field} {value} out of range"
    return None


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Passes when every record is on the grid and in range, naming the first bad one otherwise: two good inverter
    samples give Result(True, "2 records on the grid and in range"); a power below -2% of a 100 kW rating at 10:05 gives
    Result(False, "2026-06-01T10:05:00+00:00: power_kw -2.5 out of range"); gaps alone, or no samples, give no data."""
    missing = nothing_to_check(samples)
    if missing is not None:
        return no_data(missing)  # Decision: SP-039 (nothing to check is not a pass)
    for sample in samples:
        found = problem(asset, sample)
        if found is not None:
            return Result(False, found)
    return Result(True, f"{len(samples)} records on the grid and in range")
