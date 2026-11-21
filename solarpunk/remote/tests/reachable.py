"""Reachable: the asset's feed answered at least one record that is not a gap (the maintenance list's first test for
every kind with a feed). Evidences ISO 55000 9.1, the asset is monitored. A feed whose every stored sample is a gap
answered nothing: a disconnection, said once here as a failure while every other test says "no data" (SP-039). The
feed (2.2) pulls the samples, this test never opens a socket (MOD-05)."""
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.reactions import Fault
from solarpunk.remote.results import Result, nothing_to_check

KINDS = (AssetKind.INVERTER, AssetKind.METER, AssetKind.SENSOR, AssetKind.TRACKER)
CLAUSES = ("55000-9.1",)
# SP-020's reactions (SP-015's rule table, as SP-047 narrowed it): an asset that does not answer raises the INFO fault its kind's catalogue
# names for that, for an engineer to confirm. A lost link is not a dead inverter, so an inverter names no OUTAGE or DERATE
# code and the generic SIT-004 follows (7.7's fault_code); a meter's lost link is MTR-001; a weather station that does not
# answer leaves the performance ratio unreliable, SEN-001's effect. A tracker's catalogue has no code for it (TRK-001 is a
# stalled tracker, which silence does not show).
REACTIONS = {AssetKind.METER: (Fault("MTR-001"),), AssetKind.SENSOR: (Fault("SEN-001"),)}


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Passes when the feed answered at least one record that is not a gap, counting every stored sample as before:
    run(inverter, (s1, s2, s3)) is Result(True, "3 records"); run(inverter, ()) is Result(False, "no records"); three
    gaps alone give Result(False, "no records: 3 gaps")."""
    # Decision: SP-039 (call 4: reachable fails when every record is a gap)
    missing = nothing_to_check(samples)
    if missing is not None:
        return Result(False, missing)
    return Result(True, f"{len(samples)} records")
