"""Running remote tests: one test against one asset, or the whole suite against every asset of each test's kinds,
recording each result and giving each asset's status (SP-006). The remote module cannot read the fault ledger
(MOD-05), so the suite takes each asset's open-OUTAGE flag from its caller (project).
Run: python3 -m solarpunk.remote.run <test> <asset-id> --db <path> prints "pass" or "fail <reason>", exit 0 or 1,
or "no data <reason>", exit 3 (SP-039: neither); a test or asset the store does not know prints "error <why>",
exit 2."""
import argparse
import sqlite3
import sys
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import TextIO

from solarpunk.leaf import store
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetStatus
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.acquire import Acquirer
from solarpunk.remote.registry import BadRemoteTest, RemoteTest, discover, tests_for
from solarpunk.remote.results import NO_DATA, NotStored, Result, record, stored_asset, stored_samples
from solarpunk.remote.suite_registry import Suite

NO_DATA_EXIT = 3


def run_test(name: str, asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """One discovered test against one asset's samples: run_test("records_stored", inverter, ()) is
    Result(False, "no records"); a name no module provides, or an asset not of the test's kinds, raises BadRemoteTest."""
    found = discover()
    if name not in found:
        raise BadRemoteTest(f"no remote test {name}")
    test = found[name]
    if asset.kind not in test.kinds:
        raise BadRemoteTest(f"{name} does not run against a {asset.kind.name}")
    return judged(test, asset, samples)


def judged(test: RemoteTest, asset: Asset, samples: tuple[Sample, ...], acquirer: Acquirer | None = None) -> Result:
    """One test's verdict on one asset (13.3, SP-020): a test with no ACQUIRE judges the stored samples as ever; one with
    ACQUIRE judges the reads the acquirer takes for it, and given no acquirer (nothing to read through) says no data,
    never a pass: judged(power_ripple, inverter, samples) is no data, "needs live reads, not stored samples"."""
    # Decision: SP-020 (the runner reads, `run` judges only what it is handed)
    if test.acquire is None or acquirer is None:
        return test.run(asset, samples)
    return test.run(asset, acquirer(asset, test.acquire))


def timed(test: RemoteTest, asset: Asset, samples: tuple[Sample, ...],
          acquirer: Acquirer | None = None) -> tuple[Result, int]:
    """judged, with the whole milliseconds it took (13.5, SP-016), reads an acquirer waits for included: a test that
    judges at once is (result, 0 or a few); the duration is an int, never negative."""
    started = time.perf_counter()
    result = judged(test, asset, samples, acquirer)
    return result, int((time.perf_counter() - started) * 1000)


def status_of(open_outage: bool, results: tuple[Result, ...]) -> AssetStatus:
    """The asset's glyph: RED with an open OUTAGE fault whatever the results, YELLOW when a result failed, GREEN
    otherwise: status_of(False, (Result(True, "a"), Result(False, "b"))) is AssetStatus.YELLOW; status_of(False, ())
    is AssetStatus.GREEN; no data is no failure, and its colour comes from records_stored's failure (SP-039)."""
    if open_outage:
        return AssetStatus.RED
    if any(result.failed for result in results):
        return AssetStatus.YELLOW
    return AssetStatus.GREEN


def run_suite(
    conn: sqlite3.Connection,
    assets: tuple[Asset, ...],
    samples_by_asset: dict[str, tuple[Sample, ...]],
    open_outages: dict[str, bool],
    run_at: datetime,
    acquirer: Acquirer | None = None,
) -> dict[str, AssetStatus]:
    """Every discovered test against every asset of its kinds, each result recorded at run_at, and each asset's
    status by id: two inverters with stored samples, one over its rating, give {INV-001: GREEN, INV-002: YELLOW};
    an asset missing from samples_by_asset is tested with no samples, one missing from open_outages has none. A test
    with ACQUIRE is judged on the reads the acquirer takes for it, each read's instant kept (13.3)."""
    statuses: dict[str, AssetStatus] = {}
    for asset in assets:
        samples = samples_by_asset.get(asset.asset_id, ())
        results = []
        for test in tests_for(asset.kind):
            result, took = timed(test, asset, samples, acquirer)
            record(conn, test.name, asset.asset_id, run_at, result, duration_ms=took)
            results.append(result)
        # An asset missing from open_outages carries no open OUTAGE fault.
        statuses[asset.asset_id] = status_of(open_outages.get(asset.asset_id) is True, tuple(results))
    return statuses


def run_named(
    conn: sqlite3.Connection,
    suite: Suite,
    assets: tuple[Asset, ...],
    samples_by_asset: dict[str, tuple[Sample, ...]],
    run_at: datetime,
    acquirer: Acquirer | None = None,
) -> int:
    """One suite's tests against the assets in its reach, each result recorded at run_at carrying the suite's name
    (13.2) and its duration (13.5), and the count of results written: a suite of records_stored over two inverters and a meter, its KINDS the
    INVERTER, writes 2; an asset a test does not run on is passed over."""
    found = discover()
    written = 0
    for asset in assets:
        if not suite.reaches(asset):
            continue
        for name in suite.tests:
            if asset.kind in found[name].kinds:
                result, took = timed(found[name], asset, samples_by_asset.get(asset.asset_id, ()), acquirer)
                record(conn, name, asset.asset_id, run_at, result, suite.name, took)
                written += 1
    return written


def parser() -> argparse.ArgumentParser:
    """The command line: parser().parse_args(["records_stored", "OAHE-INV-001", "--db", "f.db"]).db is "f.db"."""
    built = argparse.ArgumentParser()
    built.add_argument("test")
    built.add_argument("asset_id")
    built.add_argument("--db", required=True)
    return built


def main(argv: list[str], out: TextIO) -> int:
    """Runs one test against one stored asset and writes the verdict: "pass\\n" and 0, "fail no records\\n" and 1,
    "no data no records\\n" and 3; an unknown test, an unknown asset or a missing store file writes "error <why>\\n"
    and returns 2."""
    args = parser().parse_args(argv)
    if not Path(args.db).is_file():
        out.write(f"error no store at {args.db}\n")
        return 2
    with closing(store.connect(args.db)) as conn:
        try:
            asset = stored_asset(conn, args.asset_id)
            result = run_test(args.test, asset, stored_samples(conn, args.asset_id))
        except (BadRemoteTest, NotStored) as refused:
            out.write(f"error {refused}\n")
            return 2
    if result.no_data:
        out.write(f"{NO_DATA} {result.reason}\n")
        return NO_DATA_EXIT
    out.write("pass\n" if result.passed else f"fail {result.reason}\n")
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout))
