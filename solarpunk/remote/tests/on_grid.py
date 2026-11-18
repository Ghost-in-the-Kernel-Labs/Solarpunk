"""On grid: every record the feed answered falls on the sample grid (Invariant: SOL-06) and every value it carries
lies inside the maintenance list's range for the asset's kind. Evidences ISO 55000 7.5 (the information held about
the asset is what the list says it is) and ISO 9001 9.1.3 (the data is fit to analyse)."""
from solarpunk.leaf.asset_types import UnknownField, fields_of, in_range, kinds
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import OffTheGrid, on_grid
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result

KINDS = tuple(kind for kind in kinds() if fields_of(kind))
CLAUSES = ("55000-7.5", "9001-9.1.3")
# SP-015's rule table: a record off the grid or out of range is the data's fault, not the equipment's: no code.
SUGGESTS = {kind: None for kind in KINDS}
SAMPLE_FIELDS = ("irradiance_w_m2", "power_kw")


def problem(kind: AssetKind, sample: Sample) -> str | None:
    """What is wrong with one record, or None: an inverter's 10:05 sample with irradiance 1600 gives
    "2026-06-01T10:05:00+00:00: irradiance_w_m2 1600.0 out of range"; a tracker's sample carrying power_kw gives
    "…: TRACKER has no field power_kw"; an off-grid instant gives "…: off the grid"."""
    # Invariant: SOL-06
    try:
        on_grid(sample.at)
    except OffTheGrid:
        return f"{sample.at.isoformat()}: off the grid"
    for field in SAMPLE_FIELDS:
        value = getattr(sample, field)
        if value is None:
            continue
        try:
            held = in_range(kind, field, value)
        except UnknownField:
            return f"{sample.at.isoformat()}: {kind.name} has no field {field}"
        if not held:
            return f"{sample.at.isoformat()}: {field} {value} out of range"
    return None


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Passes when every record is on the grid and in range, naming the first bad one otherwise: two good inverter
    samples give Result(True, "2 records on the grid and in range"); a negative power at 10:05 gives
    Result(False, "2026-06-01T10:05:00+00:00: power_kw -1.0 out of range")."""
    for sample in samples:
        found = problem(asset.kind, sample)
        if found is not None:
            return Result(False, found)
    return Result(True, f"{len(samples)} records on the grid and in range")
