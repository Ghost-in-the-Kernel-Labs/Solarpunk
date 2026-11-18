"""Performance ratio and energy yield over a set of inverters' samples (Invariants: SOL-03, SOL-08, SOL-09)."""
from collections.abc import Sequence
from datetime import datetime

from solarpunk.kpi.results import EnergyYield, PerformanceRatio, rounded
from solarpunk.leaf.assets import Asset, parse_asset_id
from solarpunk.leaf.clock import SAMPLE_INTERVAL, HOURS_PER_SAMPLE
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.kpi_defs import METER_LOST_CODE, STC_IRRADIANCE_W_M2, UNRELIABLE_IRRADIANCE_CODE
from solarpunk.leaf.telemetry import Sample


def rated_kw(assets: Sequence[Asset], asset_id: str) -> float:
    """The rated power of the asset a sample belongs to: rated_kw([Asset("OAHE-INV-001", …, 100.0)], "OAHE-INV-001")
    is 100.0; an id not among the assets, or one rated None, raises ValueError (SOL-03: refused, never a silent 0)."""
    # Invariant: SOL-03
    for asset in assets:
        if asset.asset_id == asset_id and asset.rated_kw is not None:
            return asset.rated_kw
    raise ValueError(f"{asset_id}: no rated power among the assets given")


def sensor_unreliable(samples: Sequence[Sample], faults: Sequence[Fault]) -> int:
    """The distinct sample intervals a SEN-001 fault covers (SOL-08): samples at 10:00 and 10:05 from two inverters
    each, with SEN-001 over [10:05, 10:10), give 1."""
    # Invariant: SOL-08
    sensor = [fault for fault in faults if fault.code == UNRELIABLE_IRRADIANCE_CODE]
    instants = {sample.at for sample in samples}
    return sum(1 for instant in instants if any(fault.covers(instant) for fault in sensor))


def performance_ratio(assets: Sequence[Asset], samples: Sequence[Sample], faults: Sequence[Fault] = ()) -> PerformanceRatio:
    """energy_kwh / reference_kwh over the samples with irradiance and power (SOL-08). The contract's example, one
    inverter rated 100 kW at 500, 1000, 0 W/m² producing 45, 92, 0 kW, gives PerformanceRatio(0.9133, 11.4167, 12.5, 0);
    a sample with no irradiance (a gap among them) is left out of both sums and counted in unreliable."""
    # Invariant: SOL-08
    energy = 0.0
    reference = 0.0
    unreliable = sensor_unreliable(samples, faults)
    for sample in samples:
        if sample.irradiance_w_m2 is None or sample.power_kw is None:
            unreliable += 1
            continue
        energy += sample.power_kw * HOURS_PER_SAMPLE
        reference += rated_kw(assets, sample.asset_id) * (sample.irradiance_w_m2 / STC_IRRADIANCE_W_M2) * HOURS_PER_SAMPLE
    value = None if reference == 0 else rounded(energy / reference)
    return PerformanceRatio(value, rounded(energy), rounded(reference), unreliable)


def overlaps(fault: Fault, start: datetime, end: datetime) -> bool:
    """Whether the fault covers any instant of [start, end): MTR-001 over [10:02, 10:03) and [10:00, 10:05) give True;
    over [10:05, 10:10) they give False."""
    return fault.opened < end and fault.covers(max(start, fault.opened))


def meter_lost(site: str, samples: Sequence[Sample], faults: Sequence[Fault]) -> bool:
    """Whether a MTR-001 of the site covers any instant from the first sample to the end of the last one's interval
    (SOL-09): samples at 10:00 to 10:55 and an OAHE MTR-001 over [10:50, 11:30) give True for "OAHE"."""
    # Invariant: SOL-09
    if not samples:
        return False
    start = min(sample.at for sample in samples)
    end = max(sample.at for sample in samples) + SAMPLE_INTERVAL
    lost = [fault for fault in faults if fault.code == METER_LOST_CODE and parse_asset_id(fault.asset_id)[0] == site]
    return any(overlaps(fault, start, end) for fault in lost)


def energy_yield(site: str, meter_kwh: float | None, samples: Sequence[Sample], faults: Sequence[Fault]) -> EnergyYield:
    """The meter's energy when it carried no MTR-001, else the site's inverters' (SOL-09): with the SOL-08 samples,
    energy_yield("OAHE", 11.2, samples, ()) is EnergyYield(11.2, "meter"), and with an OAHE MTR-001 over them it is
    EnergyYield(11.4167, "inverters"); samples and faults of other sites are left out."""
    # Invariant: SOL-09
    own = [sample for sample in samples if parse_asset_id(sample.asset_id)[0] == site]
    if meter_kwh is not None and not meter_lost(site, own, faults):
        return EnergyYield(rounded(meter_kwh), "meter")
    total = sum(sample.power_kw * HOURS_PER_SAMPLE for sample in own if not sample.gap and sample.power_kw is not None)
    return EnergyYield(rounded(total), "inverters")
