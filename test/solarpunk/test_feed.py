"""The feed holds its shape: a simulator on an ephemeral port answers ping with the very samples it was given (gaps
included, SOL-06), and every refusal (no endpoint, unreachable, slow, too large, malformed, another asset's record, off
the grid, out of the maintenance list's range or not in it, SOL-03) carries its exact message."""
import contextlib
import io
import json
import socket
import subprocess
import sys
import threading
import unittest
from collections.abc import Iterator
from dataclasses import replace
from datetime import date
from pathlib import Path

from solarpunk.feed import client, simulate
from solarpunk.feed.client import FeedError, ping, records
from solarpunk.leaf.assets import Asset, MalformedAssetId
from solarpunk.leaf.clock import Period, at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample, gap
from solarpunk.telemetry import generate as gen

ROOT = Path(__file__).resolve().parents[2]
DAY = Period(at(2026, 6, 1), at(2026, 6, 2))
INVERTER = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", None, "Inverter 1", 100.0, "127.0.0.1", 5020)
TRACKER = Asset("OAHE-TRK-001", AssetKind.TRACKER, "OAHE", None, "Tracker 1", None, "127.0.0.1", 5020)
READING = Sample("OAHE-INV-001", at(2026, 6, 1, 10, 5), 812.0, 78.4, False)
LINE = ('{"asset_id": "OAHE-INV-001", "at": "2026-06-01T10:05:00+00:00", "irradiance_w_m2": 812.0, "power_kw": 78.4, '
        '"gap": false}\n')
TEN_TWENTY = "2026-06-01T10:20:00+00:00"


def line_with(changes: dict) -> str:
    """LINE's record with some keys changed: line_with({"power_kw": 1.0}) is LINE with power_kw 1.0."""
    found = json.loads(LINE)
    found.update(changes)
    return json.dumps(found)


def free_port() -> int:
    """A port nothing listens on just now: free_port() is some int from 1 to 65535."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@contextlib.contextmanager
def served(payload: bytes) -> Iterator[int]:
    """A server answering one connection with the payload, on a thread; yields its port: with served(b"") as port, a
    ping of port reads nothing."""
    server = simulate.FeedServer(("127.0.0.1", 0), payload)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        thread.join(5)
        server.server_close()


class Flushes(io.StringIO):
    """A text buffer that counts its flushes: after print("x", file=f, flush=True), f.flushed is 1."""

    def __init__(self) -> None:
        """An empty buffer, nothing flushed: Flushes().flushed is 0."""
        super().__init__()
        self.flushed = 0

    def flush(self) -> None:
        """Counts one flush: f.flush() raises f.flushed by one."""
        self.flushed += 1
        super().flush()


def ping_text(text: str, asset: Asset = INVERTER) -> tuple[Sample, ...]:
    """Pings a one-shot server sending the text: ping_text(LINE) is (READING,)."""
    with served(text.encode()) as port:
        return ping(replace(asset, port=port), 2.0)


class TheWire(unittest.TestCase):
    def test_a_reading_is_one_line(self) -> None:
        self.assertEqual(records((READING,)), LINE)

    def test_a_gap_carries_nulls(self) -> None:
        self.assertEqual(records((gap("OAHE-INV-001", at(2026, 6, 1, 10, 20)),)),
                         f'{{"asset_id": "OAHE-INV-001", "at": "{TEN_TWENTY}", "irradiance_w_m2": null, '
                         '"power_kw": null, "gap": true}\n')

    def test_no_samples_is_no_text(self) -> None:
        self.assertEqual(records(()), "")

    def test_the_round_trip_holds_for_a_generated_day(self) -> None:
        day = gen.generate((INVERTER,), DAY, 7)
        self.assertEqual(client.parse(INVERTER, records(day).encode()), day)
        self.assertTrue(any(sample.gap for sample in day))

    def test_blank_lines_are_skipped(self) -> None:
        self.assertEqual(client.parse(INVERTER, ("\n" + LINE + "\n").encode()), (READING,))

    def test_an_integer_value_is_read_as_a_float(self) -> None:
        sample = client.record(INVERTER, line_with({"power_kw": 0}))
        self.assertEqual(sample.power_kw, 0.0)
        self.assertIsInstance(sample.power_kw, float)

    def test_the_range_ends_are_inside(self) -> None:
        self.assertEqual(client.record(INVERTER, line_with({"irradiance_w_m2": 1500})).irradiance_w_m2, 1500.0)
        self.assertEqual(client.record(INVERTER, line_with({"irradiance_w_m2": 0.0})).irradiance_w_m2, 0.0)


class ThePing(unittest.TestCase):
    def test_the_simulator_serves_a_day_and_ping_reads_it_whole(self) -> None:
        day = gen.generate((INVERTER,), DAY, 7)
        server = simulate.make_server(day, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
        thread.start()
        try:
            asset = replace(INVERTER, port=server.server_address[1])
            self.assertEqual(ping(asset), day)
            self.assertEqual(ping(asset, 2.0), day)
        finally:
            server.shutdown()
            thread.join(5)
            server.server_close()
        self.assertEqual(len(day), 288)

    def test_a_gap_record_is_a_gap_sample(self) -> None:
        self.assertEqual(ping_text(line_with({"at": TEN_TWENTY, "irradiance_w_m2": None, "power_kw": None,
                                              "gap": True})),
                         (gap("OAHE-INV-001", at(2026, 6, 1, 10, 20)),))

    def test_an_empty_feed_is_no_samples(self) -> None:
        self.assertEqual(ping_text(""), ())

    def test_no_endpoint(self) -> None:
        string = Asset("OAHE-STR-001", AssetKind.STRING, "OAHE", "OAHE-INV-001", "String 1", 50.0)
        with self.assertRaises(FeedError) as caught:
            ping(string)
        self.assertEqual(str(caught.exception), "OAHE-STR-001: no endpoint")

    def test_unreachable(self) -> None:
        port = free_port()
        with self.assertRaises(FeedError) as caught:
            ping(replace(INVERTER, port=port), 1.0)
        self.assertEqual(str(caught.exception), f"127.0.0.1:{port} is unreachable")

    def test_slow(self) -> None:
        with socket.create_server(("127.0.0.1", 0)) as silent:
            port = silent.getsockname()[1]
            with self.assertRaises(FeedError) as caught:
                ping(replace(INVERTER, port=port), 0.2)
        self.assertEqual(str(caught.exception), f"127.0.0.1:{port} is slow: nothing for 0.2 s")

    def test_a_refusal_comes_through_ping(self) -> None:
        with self.assertRaises(FeedError) as caught:
            ping_text(line_with({"irradiance_w_m2": 1600}))
        self.assertEqual(str(caught.exception), "irradiance_w_m2 1600 is out of range for INVERTER")

    def test_ping_caps_the_feed(self) -> None:
        self.assertEqual(client.FEED_CAP_BYTES, 4 * 1024 * 1024)
        with self.assertRaises(FeedError) as caught:
            ping_text("\n" * (client.FEED_CAP_BYTES + 1))
        self.assertEqual(str(caught.exception), "feed too large: over 4194304 bytes")


class TheCap(unittest.TestCase):
    def read(self, sent: bytes, cap: int) -> bytes:
        """What read_all gives for a peer that sends the bytes and closes: read(b"abc", 3) is b"abc"."""
        ours, theirs = socket.socketpair()
        with ours, theirs:
            theirs.sendall(sent)
            theirs.close()
            return client.read_all(ours, cap)

    def test_exactly_the_cap_is_read(self) -> None:
        self.assertEqual(self.read(b"abc", 3), b"abc")

    def test_one_over_the_cap_is_refused(self) -> None:
        with self.assertRaises(FeedError) as caught:
            self.read(b"abc", 2)
        self.assertEqual(str(caught.exception), "feed too large: over 2 bytes")

    def test_more_than_one_chunk_is_read(self) -> None:
        sent = b"x" * (client.CHUNK_BYTES * 2 + 7)
        self.assertEqual(self.read(sent, len(sent)), sent)


class TheRefusals(unittest.TestCase):
    def refused(self, line: str, asset: Asset = INVERTER) -> str:
        """The FeedError message parsing the line gives: refused("{") is "malformed record: not JSON: {"."""
        with self.assertRaises(FeedError) as caught:
            client.parse(asset, line.encode())
        return str(caught.exception)

    def test_not_utf8(self) -> None:
        with self.assertRaises(FeedError) as caught:
            client.parse(INVERTER, b"\xff\n")
        self.assertEqual(str(caught.exception), "malformed record: not utf-8")

    def test_not_json(self) -> None:
        self.assertEqual(self.refused("{"), "malformed record: not JSON: {")
        self.assertEqual(self.refused("y" * 100), "malformed record: not JSON: " + "y" * 80)

    def test_not_an_object(self) -> None:
        self.assertEqual(self.refused("[1]"), "malformed record: not an object: [1]")
        long = "[" + "1," * 50 + "1]"
        self.assertEqual(self.refused(long), "malformed record: not an object: " + long[:80])

    def test_a_missing_or_extra_key(self) -> None:
        self.assertEqual(self.refused('{"asset_id": 1}'), "malformed record: keys ['asset_id']")
        self.assertEqual(self.refused(line_with({"temperature_c": 20.0})),
                         "malformed record: keys ['asset_id', 'at', 'gap', 'irradiance_w_m2', 'power_kw', "
                         "'temperature_c']")

    def test_another_assets_record(self) -> None:
        self.assertEqual(self.refused(line_with({"asset_id": "OAHE-INV-002"})), "record for OAHE-INV-002, not OAHE-INV-001")

    def test_off_the_grid(self) -> None:
        self.assertEqual(self.refused(line_with({"at": "2026-06-01T10:02:00+00:00"})),
                         "record at 2026-06-01T10:02:00+00:00: 2026-06-01T10:02:00+00:00 is not on the 300 s grid")

    def test_not_utc(self) -> None:
        self.assertEqual(self.refused(line_with({"at": "2026-06-01T10:05:00"})),
                         "record at 2026-06-01T10:05:00: 2026-06-01T10:05:00 is not UTC")
        self.assertEqual(self.refused(line_with({"at": "2026-06-01T10:05:00+01:00"})),
                         "record at 2026-06-01T10:05:00+01:00: 2026-06-01T10:05:00+01:00 is not UTC")

    def test_an_unreadable_instant(self) -> None:
        self.assertEqual(self.refused(line_with({"at": "noon"})),
                         "record at noon: Invalid isoformat string: 'noon'")
        self.assertEqual(self.refused(line_with({"at": 5})), "malformed record: at is 5, not a string")

    def test_out_of_range(self) -> None:
        self.assertEqual(self.refused(line_with({"irradiance_w_m2": 1500.5})),
                         "irradiance_w_m2 1500.5 is out of range for INVERTER")
        self.assertEqual(self.refused(line_with({"power_kw": -0.1})), "power_kw -0.1 is out of range for INVERTER")

    def test_a_field_the_list_does_not_hold_for_the_kind(self) -> None:
        tracker_line = line_with({"asset_id": "OAHE-TRK-001"})
        self.assertEqual(self.refused(tracker_line, TRACKER), "record refused: TRACKER has no field irradiance_w_m2")

    def test_not_a_number(self) -> None:
        self.assertEqual(self.refused(line_with({"power_kw": "78"})), "malformed record: power_kw is '78', not a number")
        self.assertEqual(self.refused(line_with({"power_kw": True})), "malformed record: power_kw is True, not a number")
        self.assertEqual(self.refused(line_with({"power_kw": None})), "malformed record: power_kw is None, not a number")
        nan = LINE.replace("78.4", "NaN")
        self.assertEqual(self.refused(nan), "malformed record: power_kw is nan, not a number")
        self.assertEqual(self.refused(LINE.replace("812.0", "Infinity")),
                         "malformed record: irradiance_w_m2 is inf, not a number")

    def test_a_gap_flag_that_is_not_a_boolean(self) -> None:
        self.assertEqual(self.refused(line_with({"gap": 0})), "malformed record: gap is 0, not true or false")

    def test_a_gap_with_values(self) -> None:
        self.assertEqual(self.refused(line_with({"gap": True})),
                         "malformed record: a gap at 2026-06-01T10:05:00+00:00 carries values")
        self.assertEqual(self.refused(line_with({"gap": True, "power_kw": None})),
                         "malformed record: a gap at 2026-06-01T10:05:00+00:00 carries values")
        self.assertEqual(self.refused(line_with({"gap": True, "irradiance_w_m2": None})),
                         "malformed record: a gap at 2026-06-01T10:05:00+00:00 carries values")

    def test_a_feed_error_is_a_value_error(self) -> None:
        self.assertTrue(issubclass(FeedError, ValueError))


class TheSimulator(unittest.TestCase):
    def test_the_announcement(self) -> None:
        day = gen.generate((INVERTER,), DAY, 7)
        self.assertEqual(simulate.announcement(day, "127.0.0.1", 5020),
                         "feed: serving 288 records for OAHE-INV-001 on 127.0.0.1:5020")
        two = (replace(READING, asset_id="OAHE-INV-002"), READING, READING)
        self.assertEqual(simulate.announcement(two, "h", 1), "feed: serving 3 records for OAHE-INV-001, OAHE-INV-002 on h:1")

    def test_the_day(self) -> None:
        self.assertEqual(simulate.day_of(date(2026, 6, 1)), DAY)

    def test_the_arguments(self) -> None:
        args = simulate.arguments(["OAHE-INV-001", "--port", "5020", "--seed", "7", "--day", "2026-06-01"])
        self.assertEqual((args.asset_id, args.port, args.seed, args.day, args.rated_kw, args.once),
                         ("OAHE-INV-001", 5020, 7, date(2026, 6, 1), 100.0, False))
        args = simulate.arguments(["OAHE-INV-002", "--port", "1", "--seed", "3", "--day", "2026-01-02", "--rated-kw",
                                   "250", "--once"])
        self.assertEqual((args.rated_kw, args.once), (250.0, True))
        for missing in ("--port", "--seed", "--day"):
            whole = ["OAHE-INV-001", "--port", "5020", "--seed", "7", "--day", "2026-06-01"]
            at_flag = whole.index(missing)
            errors = io.StringIO()
            with self.subTest(missing=missing), contextlib.redirect_stderr(errors), self.assertRaises(SystemExit):
                simulate.arguments(whole[:at_flag] + whole[at_flag + 2:])
            self.assertIn(f"the following arguments are required: {missing}", errors.getvalue())
            self.assertTrue(errors.getvalue().startswith("usage: python3 -m solarpunk.feed.simulate "), errors.getvalue())

    def test_the_inverter(self) -> None:
        self.assertEqual(simulate.inverter("OAHE-INV-001", 100.0, 5020), INVERTER.__class__(
            "OAHE-INV-001", AssetKind.INVERTER, "OAHE", None, "OAHE-INV-001", 100.0, "127.0.0.1", 5020))
        with self.assertRaises(ValueError) as caught:
            simulate.inverter("OAHE-TRK-001", 100.0, 5020)
        self.assertEqual(str(caught.exception), "OAHE-TRK-001 is not an inverter; the simulator serves an inverter's day")
        with self.assertRaises(MalformedAssetId):
            simulate.inverter("OAHE-INV-1", 100.0, 5020)

    def test_serve_once_answers_one_ping_and_returns_its_port(self) -> None:
        port = free_port()
        found: list[int] = []
        out = Flushes()
        with contextlib.redirect_stdout(out):
            thread = threading.Thread(target=lambda: found.append(simulate.serve((READING,), "127.0.0.1", port, True)))
            thread.start()
            samples = self.ping_when_up(port)
            thread.join(5)
        self.assertEqual(samples, (READING,))
        self.assertEqual(found, [port])
        self.assertEqual(out.getvalue(), f"feed: serving 1 records for OAHE-INV-001 on 127.0.0.1:{port}\n")
        self.assertGreater(out.flushed, 0, "the announcement is flushed, so a caller reading the pipe sees it at once")

    def test_main_serves_the_sources_samples_for_the_day(self) -> None:
        port = free_port()
        asked: list[tuple] = []

        def source(assets: tuple[Asset, ...], period: Period, seed: int) -> tuple[Sample, ...]:
            """Records what it was asked and gives READING: source((a,), DAY, 7) is (READING,)."""
            asked.append((assets, period, seed))
            return (READING,)

        found: list[int] = []
        argv = ["OAHE-INV-001", "--port", str(port), "--seed", "7", "--day", "2026-06-01", "--rated-kw", "90", "--once"]
        with contextlib.redirect_stdout(io.StringIO()):
            thread = threading.Thread(target=lambda: found.append(simulate.main(argv, source)))
            thread.start()
            samples = self.ping_when_up(port)
            thread.join(5)
        self.assertEqual(samples, (READING,))
        self.assertEqual(found, [port])
        self.assertEqual(asked, [((replace(INVERTER, name="OAHE-INV-001", rated_kw=90.0, port=port),), DAY, 7)])

    def ping_when_up(self, port: int) -> tuple[Sample, ...]:
        """Pings port until the server there is listening, for up to about 5 s: a bound simulator's samples."""
        for _attempt in range(100):
            try:
                return ping(replace(INVERTER, port=port), 2.0)
            except FeedError:
                threading.Event().wait(0.05)
        return ping(replace(INVERTER, port=port), 2.0)

    def test_the_command_serves_the_generators_day_once(self) -> None:
        port = free_port()
        command = [sys.executable, "-m", "solarpunk.feed.simulate", "OAHE-INV-001", "--port", str(port), "--seed", "7",
                   "--day", "2026-06-01", "--once"]
        with subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, text=True) as process:
            first = process.stdout.readline()
            samples = ping(replace(INVERTER, port=port), 5.0)
            self.assertEqual(process.wait(10), 0)
        self.assertEqual(first, f"feed: serving 288 records for OAHE-INV-001 on 127.0.0.1:{port}\n")
        self.assertEqual(samples, gen.generate((INVERTER,), DAY, 7))


if __name__ == "__main__":
    unittest.main()
