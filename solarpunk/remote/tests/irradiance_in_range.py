"""Irradiance in range: every irradiance an inverter's or a weather station's feed reports lies inside the maintenance
list's range for the asset's kind (0 to 1500 W/m², docs/ASSET-MAINTENANCE-LIST.md). Irradiance is the performance
ratio's denominator (SOL-08), so a sensor reading out of range is named on its own, apart from on_grid's sweep over
every field. Evidences ISO 9001 9.1.3 (the data is fit to analyse) and ISO 55000 7.5 (the information held about the
asset is what the list says it is)."""
from solarpunk.leaf.asset_types import in_range
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result

KINDS = (AssetKind.INVERTER, AssetKind.SENSOR)
CLAUSES = ("9001-9.1.3", "55000-7.5")
# SP-015's rule table: a weather station reading out of range is SEN-001; an inverter's irradiance channel has no code.
SUGGESTS = {AssetKind.INVERTER: None, AssetKind.SENSOR: "SEN-001"}
FIELD = "irradiance_w_m2"


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Passes when every irradiance read is in range, naming the first out of range otherwise: 0.0 and 980.0 give
    Result(True, "2 irradiance readings in range"); 1600.0 at 10:05 gives Result(False, "2026-06-01T10:05:00+00:00:
    irradiance 1600.0 W/m2 out of range"); gaps and records with no irradiance are not counted."""
    read = [sample for sample in samples if sample.irradiance_w_m2 is not None]
    for sample in read:
        if not in_range(asset.kind, FIELD, sample.irradiance_w_m2):
            return Result(False, f"{sample.at.isoformat()}: irradiance {sample.irradiance_w_m2} W/m2 out of range")
    return Result(True, f"{len(read)} irradiance readings in range")
