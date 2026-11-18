"""MTBF and MTTR per asset kind, from closed OUTAGE faults (Invariants: SOL-10, SOL-11)."""
from collections.abc import Sequence
from datetime import timedelta

from solarpunk.kpi.results import Reliability, rounded
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import Period
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.kpi_defs import OUTAGE


def outages_of(kind: AssetKind, assets: Sequence[Asset], faults: Sequence[Fault]) -> list[Fault]:
    """The faults of severity OUTAGE carried by assets of the kind; a DERATE or INFO never enters (SOL-11): of an
    INV-001 and an INV-002 on an inverter, only the INV-001."""
    # Invariant: SOL-11
    ids = {asset.asset_id for asset in assets if asset.kind is kind}
    return [fault for fault in faults if fault.asset_id in ids and fault.catalogue_row().severity is OUTAGE]


def mtbf_mttr(kind: AssetKind, assets: Sequence[Asset], period: Period, faults: Sequence[Fault]) -> Reliability:
    """MTTR = Σ repair / count, MTBF = (assets × period_hours − Σ repair) / count over the closed OUTAGE faults lying
    within the period (SOL-10). The contract's example, two inverters, 24 h, closed outages of 2 h and 4 h, gives
    Reliability(21.0, 3.0, 2, 0); an open fault opened in the period is counted in open alone; count 0 gives None."""
    # Invariant: SOL-10
    count = 0
    still_open = 0
    repair = timedelta(0)
    for fault in outages_of(kind, assets, faults):
        if fault.closed is None:
            still_open += fault.opened >= period.start and fault.opened < period.end
        elif fault.opened >= period.start and fault.closed <= period.end:
            count += 1
            repair += fault.closed - fault.opened
    if count == 0:
        return Reliability(None, None, 0, still_open)
    repair_h = repair / timedelta(hours=1)
    fleet = sum(1 for asset in assets if asset.kind is kind)
    mtbf = (fleet * period.hours() - repair_h) / count
    return Reliability(rounded(mtbf), rounded(repair_h / count), count, still_open)
