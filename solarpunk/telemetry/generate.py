"""Synthetic SCADA samples from a seed: a clear-sky irradiance bell, inverter power with ±3 % jitter, and gaps at a
seeded 2 % of instants, carried as leaf gap() samples (Invariant: SOL-06). The same seed gives the same samples
(Invariant: SOL-02). Run from the repository root: python3 -m solarpunk.telemetry.generate --seed 7 writes the one-day
golden test/solarpunk/goldens/telemetry-seed7.txt (it reads no data, so -I is not needed; -I would hide the package)."""
import argparse
import math
import random
import sys
from datetime import datetime
from pathlib import Path

from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import Period, at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample, gap

DAWN_H = 6.0
DAYLIGHT_H = 14.0
PEAK_W_M2 = 1000.0
DERATE = 0.92
JITTER = 0.03
GAP_RATE = 0.02
GOLDEN_ASSET = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", None, "Inverter 1", 100.0)
GOLDEN_DAY = Period(at(2026, 6, 1), at(2026, 6, 2))
GOLDENS = Path(__file__).resolve().parents[2] / "test" / "solarpunk" / "goldens"


def irradiance(moment: datetime) -> float:
    """The clear-sky bell 1000 × sin(π × (h − 6) / 14) at the UTC hour h, to 1 decimal, clipped at zero, which is
    exactly 0.0 outside [06:00, 20:00]: irradiance(13:00) is 1000.0, irradiance(09:30) is 707.1, irradiance(05:55) and
    irradiance(20:05) are 0.0."""
    hour = moment.hour + moment.minute / 60
    bell = math.sin(math.pi * (hour - DAWN_H) / DAYLIGHT_H)
    return round(PEAK_W_M2 * max(0.0, bell), 1)


def power(rated_kw: float, irradiance_w_m2: float, jitter: float) -> float:
    """rated_kw × irradiance / 1000 × 0.92 × jitter, to 2 decimals: power(100.0, 1000.0, 1.0) is 92.0;
    power(100.0, 707.1, 1.0) is 65.05."""
    return round(rated_kw * irradiance_w_m2 / PEAK_W_M2 * DERATE * jitter, 2)


def rating(asset: Asset) -> float:
    """An inverter's rated_kw, refused when absent (SOL-03): rating(GOLDEN_ASSET) is 100.0; an inverter with
    rated_kw None raises ValueError."""
    if asset.rated_kw is None:
        raise ValueError(f"{asset.asset_id}: an inverter with no rated_kw cannot be simulated")
    return asset.rated_kw


def reading(asset: Asset, moment: datetime, rng: random.Random) -> Sample:
    """One instant's sample, drawing the gap first and the jitter second at every instant, gap or not, so instant n
    of a run always takes the run's draws 2n and 2n + 1: with rng.random() below 0.02 the sample is
    gap(asset_id, moment); else Sample(asset_id, 13:00, 1000.0, 92.0 × jitter, False) for a 100 kW inverter."""
    missing = rng.random() < GAP_RATE
    jitter = 1 + rng.uniform(-JITTER, JITTER)
    if missing:
        return gap(asset.asset_id, moment)
    light = irradiance(moment)
    return Sample(asset.asset_id, moment, light, power(rating(asset), light, jitter), False)


def generate(assets: tuple[Asset, ...], period: Period, seed: int) -> tuple[Sample, ...]:
    """Every inverter's sample at every expected instant of the period, in asset-id then time order, from one
    random.Random(seed); other kinds are ignored: one inverter over a day gives 288 samples, the same seed the same
    tuple."""
    # Invariant: SOL-06 (every expected instant present, a missing reading carried as a gap sample)
    # Invariant: SOL-02 (one seeded generator, drawn in a fixed order: the same seed gives the same samples)
    rng = random.Random(seed)
    inverters = sorted((asset for asset in assets if asset.kind is AssetKind.INVERTER), key=asset_key)
    return tuple(reading(inverter, moment, rng) for inverter in inverters for moment in period.instants())


def asset_key(asset: Asset) -> str:
    """The sort key of an asset, its id: asset_key(GOLDEN_ASSET) is "OAHE-INV-001"."""
    return asset.asset_id


def line(sample: Sample) -> str:
    """One golden line, tab-separated asset_id, isoformat, irradiance, power, gap:
    "OAHE-INV-001\\t2026-06-01T13:00:00+00:00\\t1000.0\\t91.62\\tFalse"; a gap's values print as None."""
    fields = (sample.asset_id, sample.at.isoformat(), sample.irradiance_w_m2, sample.power_kw, sample.gap)
    return "\t".join(str(field) for field in fields)


def golden_text(seed: int) -> str:
    """The golden: one line per sample, each ending in a newline, for OAHE-INV-001 rated 100.0 over 2026-06-01 UTC:
    golden_text(7) has 288 lines."""
    return "".join(line(sample) + "\n" for sample in generate((GOLDEN_ASSET,), GOLDEN_DAY, seed))


def main(argv: list[str], folder: Path) -> Path:
    """Parses --seed and writes golden_text(seed) as UTF-8 bytes to folder/telemetry-seed<seed>.txt, returning the path:
    main(["--seed", "7"], GOLDENS) writes test/solarpunk/goldens/telemetry-seed7.txt; no --seed exits."""
    # Invariant: SOL-02 (the golden is a file this command regenerates byte for byte)
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    seed = parser.parse_args(argv).seed
    target = folder / f"telemetry-seed{seed}.txt"
    target.write_bytes(golden_text(seed).encode())
    return target


if __name__ == "__main__":
    print(main(sys.argv[1:], GOLDENS))
