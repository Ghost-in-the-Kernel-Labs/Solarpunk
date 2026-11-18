"""The feed simulator: serves some samples as the feed's wire text on a TCP port, every record then a close, so the
client, the remote tests and the UI run against a feed with no real inverter. Run from the repository root:
python3 -m solarpunk.feed.simulate OAHE-INV-001 --port 5020 --seed 7 --day 2026-06-01 [--rated-kw 100] [--once]
serves the synthetic generator's 288 samples of that day; --once answers one connection and exits. The importable
code imports the leaf alone (SP-010); the generator is reached through telemetry.generate in the __main__ block alone:
the simulator is the synthetic telemetry served over a socket, so feed may import telemetry (SP-010 as amended at J-021)."""
import argparse
import socketserver
import sys
from collections.abc import Callable
from datetime import date, timedelta

from solarpunk.feed.client import ENCODING, records
from solarpunk.leaf.assets import Asset, parse_asset_id
from solarpunk.leaf.clock import Period, at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample

HOST = "127.0.0.1"
DEFAULT_RATED_KW = 100.0
ANNOUNCEMENT = "feed: serving {count} records for {ids} on {host}:{port}"
NOT_AN_INVERTER = "{asset_id} is not an inverter; the simulator serves an inverter's day"

SampleSource = Callable[[tuple[Asset, ...], Period, int], tuple[Sample, ...]]


class FeedServer(socketserver.TCPServer):
    """A TCP server holding the wire bytes it answers every connection with: FeedServer((HOST, 0), b"") binds a free
    port, server_address[1]."""

    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], payload: bytes) -> None:
        """Binds the address and keeps the payload: FeedServer(("127.0.0.1", 0), b"x\\n").payload is b"x\\n"."""
        self.payload = payload
        super().__init__(address, FeedHandler)


class FeedHandler(socketserver.BaseRequestHandler):
    """Answers one connection with the server's payload, then the server closes it."""

    def handle(self) -> None:
        """Sends every byte of the payload: a client reading to EOF gets FeedServer.payload whole."""
        self.request.sendall(self.server.payload)


def make_server(samples: tuple[Sample, ...], host: str, port: int) -> FeedServer:
    """A bound server that answers each connection with records(samples) and closes: make_server(day, "127.0.0.1", 0)
    listens on a free port; a test calls handle_request() in a thread, or serve_forever() and shutdown()."""
    return FeedServer((host, port), records(samples).encode(ENCODING))


def announcement(samples: tuple[Sample, ...], host: str, port: int) -> str:
    """The line the simulator prints on binding: for 288 samples of OAHE-INV-001 on 127.0.0.1:5020, "feed: serving 288
    records for OAHE-INV-001 on 127.0.0.1:5020"; two assets' ids are sorted and joined with ", "."""
    ids = ", ".join(sorted({sample.asset_id for sample in samples}))
    return ANNOUNCEMENT.format(count=len(samples), ids=ids, host=host, port=port)


def serve(samples: tuple[Sample, ...], host: str, port: int, once: bool) -> int:
    """Binds, prints the announcement, answers one connection when once is True or every one until interrupted, and
    returns the bound port: serve(day, "127.0.0.1", 0, True) answers one ping and returns the port it chose."""
    with make_server(samples, host, port) as server:
        bound = server.server_address[1]
        print(announcement(samples, host, bound), flush=True)
        if once:
            server.handle_request()
        else:
            server.serve_forever()
    return bound


def day_of(day: date) -> Period:
    """One UTC day, midnight to midnight: day_of(date(2026, 6, 1)) is Period(at(2026, 6, 1), at(2026, 6, 2))."""
    start = at(day.year, day.month, day.day)
    return Period(start, start + timedelta(days=1))


def arguments(argv: list[str]) -> argparse.Namespace:
    """The command line: arguments(["OAHE-INV-001", "--port", "5020", "--seed", "7", "--day", "2026-06-01"]) has
    rated_kw 100.0 and once False; a missing --port, --seed or --day exits."""
    parser = argparse.ArgumentParser(prog="python3 -m solarpunk.feed.simulate")
    parser.add_argument("asset_id")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--day", type=date.fromisoformat, required=True)
    parser.add_argument("--rated-kw", type=float, default=DEFAULT_RATED_KW)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args(argv)


def inverter(asset_id: str, rated_kw: float, port: int) -> Asset:
    """The simulated inverter: inverter("OAHE-INV-001", 100.0, 5020) is Asset("OAHE-INV-001", INVERTER, "OAHE", None,
    "OAHE-INV-001", 100.0, "127.0.0.1", 5020); "OAHE-TRK-001" raises ValueError, a malformed id MalformedAssetId."""
    site, kind, _number = parse_asset_id(asset_id)
    if kind is not AssetKind.INVERTER:
        raise ValueError(NOT_AN_INVERTER.format(asset_id=asset_id))
    return Asset(asset_id, kind, site, None, asset_id, rated_kw, HOST, port)


def main(argv: list[str], source: SampleSource) -> int:
    """Builds the inverter, takes the day's samples from source(assets, period, seed) and serves them on 127.0.0.1,
    returning the bound port: main(["OAHE-INV-001", "--port", "5020", "--seed", "7", "--day", "2026-06-01", "--once"],
    generate) serves 288 records to one ping and returns 5020."""
    args = arguments(argv)
    asset = inverter(args.asset_id, args.rated_kw, args.port)
    samples = source((asset,), day_of(args.day), args.seed)
    return serve(samples, HOST, args.port, args.once)


if __name__ == "__main__":
    from solarpunk.telemetry import generate as generator

    try:
        main(sys.argv[1:], generator.generate)
    except KeyboardInterrupt:
        sys.exit(0)
