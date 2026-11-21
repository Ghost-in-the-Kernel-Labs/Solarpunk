import sqlite3

from solarpunk.leaf.codes import AssetKind
from solarpunk.remote.results import Result

KINDS = (AssetKind.INVERTER,)
CLAUSES = ("9001-9.1.1",)
LIMIT = 40.0


def run(asset, samples):
    """Passes when the power is under the limit."""
    over = [s for s in samples if s.power_kw > 40.0]
    return Result(not over, str(sqlite3.version))
