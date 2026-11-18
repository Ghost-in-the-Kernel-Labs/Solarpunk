"""Reachable: the asset's feed answered at least one record (the maintenance list's first test for every kind with a
feed). Evidences ISO 55000 9.1, the asset is monitored. The record count is the feed's stored samples, gaps
included; the feed (2.2) pulls them, this test never opens a socket (MOD-05)."""
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result

KINDS = (AssetKind.INVERTER, AssetKind.METER, AssetKind.SENSOR, AssetKind.TRACKER)
CLAUSES = ("55000-9.1",)
# SP-015's rule table: an asset that does not answer suggests the fault its kind's catalogue names for that, for an
# engineer to confirm. An inverter that does not answer is most likely offline; a meter's lost link is MTR-001; a
# weather station that does not answer leaves the performance ratio unreliable, SEN-001's effect. A tracker's catalogue
# has no code for it (TRK-001 is a stalled tracker, which silence does not show).
SUGGESTS = {AssetKind.INVERTER: "INV-001", AssetKind.METER: "MTR-001", AssetKind.SENSOR: "SEN-001", AssetKind.TRACKER: None}


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Passes when the feed answered at least one record: run(inverter, (s1, s2, s3)) is Result(True, "3 records");
    run(inverter, ()) is Result(False, "no records")."""
    if not samples:
        return Result(False, "no records")
    return Result(True, f"{len(samples)} records")
