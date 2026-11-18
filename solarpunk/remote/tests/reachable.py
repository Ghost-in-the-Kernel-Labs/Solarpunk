"""Reachable: the asset's feed answered at least one record (the maintenance list's first test for every kind with a
feed). Evidences ISO 55000 9.1, the asset is monitored. The record count is the feed's stored samples, gaps
included; the feed (2.2) pulls them, this test never opens a socket (MOD-05)."""
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result

KINDS = (AssetKind.INVERTER, AssetKind.METER, AssetKind.SENSOR, AssetKind.TRACKER)
CLAUSES = ("55000-9.1",)


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Passes when the feed answered at least one record: run(inverter, (s1, s2, s3)) is Result(True, "3 records");
    run(inverter, ()) is Result(False, "no records")."""
    if not samples:
        return Result(False, "no records")
    return Result(True, f"{len(samples)} records")
