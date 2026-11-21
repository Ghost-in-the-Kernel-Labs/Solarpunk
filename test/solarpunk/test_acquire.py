"""A test's own reads (13.3, SP-020): ACQUIRE is a value of a closed set the registry holds; the feed answers one live
reading per request and the simulator serves it from its day; the runner takes a burst through the feed on a clock it is
handed (never a minute's wait) and hands the reads to `run`, which reads nothing else; a test without ACQUIRE judges the
stored samples as ever. Every read here is the simulator's, never a real asset."""
import sqlite3
import threading
import types
import unittest
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

from solarpunk.feed import client, simulate
from solarpunk.leaf import store
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind, AssetStatus
from solarpunk.leaf.telemetry import Sample
from solarpunk.fleet import registry as fleet
from solarpunk.project import run as project_run
from solarpunk.remote import acquire, registry
from solarpunk.remote import results
from solarpunk.remote import run as remote_run
from solarpunk.remote.acquire import Burst, Read, ReadFailed
from solarpunk.remote.tests import power_ripple
from solarpunk.telemetry import generate as generator
from solarpunk.telemetry import samples as telemetry

DAY = date(2026, 6, 1)
START = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
INVERTER = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", None, "Inverter 1", 100.0, "127.0.0.1", 1)


def stepping(start: datetime = START) -> Callable[[float], datetime]:
    """A clock that never waits: each call moves the instant on by the wait it is asked for and says it."""
    moment = [start]

    def clock(wait_s: float) -> datetime:
        """The instant after waiting wait_s: stepping()(2) is 10:00:02, then stepping()(0) after it 10:00:02 again."""
        moment[0] += timedelta(seconds=wait_s)
        return moment[0]
    return clock


def simulated_day(seed: int = 7) -> tuple[Sample, ...]:
    """The generator's 288 samples of OAHE-INV-001 on 2026-06-01 for the seed: simulated_day(7)[0].at is midnight."""
    return generator.generate((simulate.inverter(INVERTER.asset_id, 100.0, 1),), simulate.day_of(DAY), seed)


class Serving:
    """A live simulator of one inverter's day on a free port, for the length of a with block."""

    def __init__(self, samples: tuple[Sample, ...]) -> None:
        """Binds a live simulator of the samples to a free port: Serving(simulated_day())."""
        self.server = simulate.make_server(samples, "127.0.0.1", 0, live=True)

    def __enter__(self) -> Asset:
        """Starts serving and gives the inverter at its port: `with Serving(day) as asset`."""
        thread = threading.Thread(daemon=True, target=self.server.serve_forever, kwargs={"poll_interval": 0.02})
        thread.start()
        self.thread = thread
        return Asset(INVERTER.asset_id, AssetKind.INVERTER, "OAHE", None, "Inverter 1", 100.0, "127.0.0.1",
                     self.server.server_address[1])

    def __exit__(self, kind: object, error: object, trace: object) -> None:
        """Stops serving and frees the port."""
        self.server.shutdown()
        self.server.server_close()


def reads(powers: tuple[float | None, ...]) -> tuple[Read, ...]:
    """One read a second from 10:00:00 with each power: reads((50.0, 52.0)) is two Reads, 10:00:00 and 10:00:01."""
    return tuple(Read(START + timedelta(seconds=n), power) for n, power in enumerate(powers))


class TheBurst(unittest.TestCase):
    def test_a_burst_counts_its_reads_and_a_shortening_cuts_the_duration(self) -> None:
        burst = Burst("power_kw", 1, 60)
        self.assertEqual((burst.count(), burst.count(5), burst.count(500), burst.count(0.1)), (60, 5, 60, 1))

    def test_a_burst_that_would_take_no_read_is_refused(self) -> None:
        for every, span in ((0, 60), (-1, 60), (5, 1)):
            with self.assertRaises(ValueError):
                Burst("power_kw", every, span)

    def test_take_keeps_each_reads_instant_and_never_waits(self) -> None:
        taken = acquire.take(INVERTER, Burst("power_kw", 2, 6), lambda asset, field, at: float(at.second), stepping())
        self.assertEqual([read.at.second for read in taken], [0, 2, 4])
        self.assertEqual([read.value for read in taken], [0.0, 2.0, 4.0])

    def test_a_read_that_fails_is_a_read_with_no_value(self) -> None:
        def reader(asset: Asset, field: str, at: datetime) -> float:
            """A reader whose feed is down."""
            raise ReadFailed("down")
        taken = acquire.take(INVERTER, Burst("power_kw", 1, 3), reader, stepping())
        self.assertEqual([read.value for read in taken], [None] * 3)
        self.assertEqual(acquire.nothing_read(taken), "no reads: 3 failed")
        self.assertEqual(acquire.nothing_read(()), "no reads")
        self.assertIsNone(acquire.nothing_read(reads((1.0,))))


class TheRegistry(unittest.TestCase):
    def module(self, declared: dict) -> types.ModuleType:
        """A test module with the four fields and what is declared besides: self.module({"ACQUIRE": Burst(...)})."""
        module = types.ModuleType("solarpunk.remote.tests.fake")
        module.KINDS, module.CLAUSES, module.SUGGESTS = (AssetKind.INVERTER,), ("9001-9.1.1",), {AssetKind.INVERTER: None}
        module.run = lambda asset, given: None
        for name, value in declared.items():
            setattr(module, name, value)
        return module

    def test_power_ripple_declares_a_burst_the_registry_holds(self) -> None:
        held = registry.discover()["power_ripple"]
        self.assertEqual(held.acquire, Burst("power_kw", 1, 60))
        self.assertIsNone(registry.discover()["power_under_rated"].acquire)

    def test_an_acquire_outside_the_closed_set_is_refused(self) -> None:
        for declared in ("burst", ("power_kw", 1, 60), 5):
            with self.assertRaisesRegex(registry.BadRemoteTest, "ACQUIRE is none of Burst"):
                registry.from_module("fake", self.module({"ACQUIRE": declared}))

    def test_a_burst_of_a_field_the_kind_does_not_hold_is_refused(self) -> None:
        with self.assertRaisesRegex(registry.BadRemoteTest, "reads angle_deg, which INVERTER does not hold"):
            registry.from_module("fake", self.module({"ACQUIRE": Burst("angle_deg", 1, 60)}))

    def test_a_test_with_a_burst_given_stored_samples_says_no_data(self) -> None:
        held = registry.discover()["power_ripple"]
        said = held.run(INVERTER, simulated_day()[:3])
        self.assertEqual((said.passed, said.no_data, said.reason), (False, True, acquire.NEEDS_READS))
        self.assertTrue(held.run(INVERTER, ()).no_data)


class TheFeedsLiveRead(unittest.TestCase):
    def test_the_simulator_answers_from_its_day_at_the_instant(self) -> None:
        day = simulated_day()
        with Serving(day) as asset:
            on_grid = client.read_now(asset, "power_kw", START)
            between = client.read_now(asset, "power_kw", START + timedelta(seconds=150))
        low = next(s for s in day if s.at == START).power_kw
        high = next(s for s in day if s.at == START + timedelta(minutes=5)).power_kw
        self.assertEqual(on_grid, low)
        self.assertAlmostEqual(between, (low + high) / 2)

    def test_the_day_is_still_pinged_whole_beside_it(self) -> None:
        day = simulated_day()
        with Serving(day) as asset:
            self.assertEqual(client.ping(asset), day)

    def test_a_reading_the_day_has_not_got_is_none_and_a_refusal_is_a_feed_error(self) -> None:
        with Serving(simulated_day()) as asset:
            self.assertIsNone(client.read_now(asset, "power_kw", START - timedelta(days=2)))
            with self.assertRaisesRegex(client.FeedError, "read refused"):
                client.read_now(asset, "temperature_c", START)

    def test_an_asset_with_no_endpoint_and_a_closed_port_are_feed_errors(self) -> None:
        with self.assertRaisesRegex(client.FeedError, "no endpoint"):
            client.read_now(Asset("OAHE-STR-001", AssetKind.STRING, "OAHE", None, "S", None), "power_kw", START)
        with self.assertRaises(client.FeedError):
            client.read_now(INVERTER, "power_kw", START, 0.2)

    def test_reading_refuses_a_wrong_asset_field_or_shape(self) -> None:
        good = b'{"asset_id": "OAHE-INV-001", "field": "power_kw", "at": "2026-06-01T10:00:00+00:00", "value": 78.4}'
        self.assertEqual(client.reading(INVERTER, "power_kw", good), 78.4)
        for bad in (good.replace(b"INV-001", b"INV-002"), good.replace(b"power_kw", b"irradiance_w_m2", 1), b"{", b"[]",
                    b'{"asset_id": 1}', good.replace(b"78.4", b"-3")):
            with self.assertRaises(client.FeedError):
                client.reading(INVERTER, "power_kw", bad)


class ThePowerRipple(unittest.TestCase):
    def test_the_edge_of_the_threshold_both_sides(self) -> None:
        self.assertTrue(power_ripple.run(INVERTER, reads((50.0, 55.0))).passed)  # 5% of 100 kW: at the limit
        said = power_ripple.run(INVERTER, reads((50.0, 55.1)))
        self.assertEqual((said.failed, said.reason),
                         (True, "2026-06-01T10:00:00+00:00: ripple 5.1 kW over rated 100.0 kW x 5%"))

    def test_the_other_results(self) -> None:
        said = power_ripple.run(INVERTER, reads((50.0, 52.0)))
        self.assertEqual(said.reason, "2 reads, ripple 2.0 kW within rated 100.0 kW x 5%")
        self.assertEqual(power_ripple.run(INVERTER, ()).reason, "no reads")
        self.assertTrue(power_ripple.run(INVERTER, reads((1.0,))).passed)
        self.assertEqual(power_ripple.run(Asset("A-INV-001", AssetKind.INVERTER, "A", None, "x", None), reads((1.0,))).reason,
                         "no rating")
        gappy = (Read(START, None),) + reads((50.0, 51.0))
        self.assertTrue(power_ripple.run(INVERTER, gappy).passed)

    def test_a_healthy_simulated_inverter_passes_a_minute_at_any_time_of_the_day(self) -> None:
        # The proposed 5% leaves room over the simulator's worst minute (about 1.2% of rating, 60 seeds).
        for seed in (1, 7, 42):
            day = simulated_day(seed)
            with Serving(day) as asset:
                for hour in (0, 6, 9, 12, 15, 18, 23):
                    start = datetime(2026, 6, 1, hour, 0, tzinfo=timezone.utc)
                    taken = acquire.take(asset, Burst("power_kw", 1, 60), lambda a, f, at: client.read_now(a, f, at),
                                         stepping(start), shorten_to_s=12)
                    self.assertEqual(len(taken), 12)
                    said = power_ripple.run(asset, taken)
                    self.assertTrue(said.passed or said.no_data, (seed, hour, said))


class TheRunner(unittest.TestCase):
    def conn(self) -> sqlite3.Connection:
        """An in-memory store with the fleet, samples and results tables."""
        conn = store.connect()
        store.apply(conn, fleet.schema() + telemetry.schema() + results.schema())
        self.addCleanup(conn.close)
        return conn

    def test_a_test_with_acquire_judges_the_reads_through_the_feed_and_the_rest_the_stored_samples(self) -> None:
        day = simulated_day()
        stored = tuple(s for s in day if s.at < START)
        conn = self.conn()
        with Serving(day) as asset:
            taker = project_run.feed_acquirer(stepping(), shorten_to_s=10)
            remote_run.run_suite(conn, (asset,), {asset.asset_id: stored}, {}, START, taker)
        latest = {r.test_name: r for r in results.latest_for(conn, asset.asset_id)}
        self.assertEqual(len(latest), len(registry.tests_for(AssetKind.INVERTER)))
        self.assertTrue(latest["power_ripple"].passed, latest["power_ripple"])
        self.assertTrue(latest["power_ripple"].reason.startswith("10 reads, ripple "))
        self.assertTrue(latest["power_under_rated"].reason.startswith(f"{len(stored)} records"))  # the stored samples

    def test_with_no_acquirer_a_burst_test_says_no_data_never_a_pass(self) -> None:
        conn = self.conn()
        remote_run.run_suite(conn, (INVERTER,), {INVERTER.asset_id: simulated_day()}, {}, START)
        latest = {r.test_name: r for r in results.latest_for(conn, INVERTER.asset_id)}
        self.assertTrue(latest["power_ripple"].no_data)

    def test_a_hunting_inverter_fails_with_the_instant_of_its_first_read(self) -> None:
        def hunting(asset: Asset, burst: Burst) -> tuple[Read, ...]:
            """An acquirer for an inverter whose power swings 20 kW a second."""
            return tuple(Read(START + timedelta(seconds=n), 40.0 + 20.0 * (n % 2)) for n in range(burst.count(4)))
        conn = self.conn()
        statuses = remote_run.run_suite(conn, (INVERTER,), {INVERTER.asset_id: simulated_day()}, {}, START, hunting)
        found = {r.test_name: r for r in results.latest_for(conn, INVERTER.asset_id)}["power_ripple"]
        self.assertEqual((found.failed, found.reason),
                         (True, "2026-06-01T10:00:00+00:00: ripple 20.0 kW over rated 100.0 kW x 5%"))
        self.assertIs(statuses[INVERTER.asset_id], AssetStatus.YELLOW)

    def test_a_suite_run_by_name_takes_the_reads_too(self) -> None:
        suite = types.SimpleNamespace(name="ripples", tests=("power_ripple",), reaches=lambda asset: True)
        conn = self.conn()
        written = remote_run.run_named(conn, suite, (INVERTER,), {}, START,
                                       lambda asset, burst: reads((50.0, 51.0)))
        self.assertEqual(written, 1)
        self.assertTrue(results.latest_for(conn, INVERTER.asset_id)[0].passed)

    def test_run_test_with_no_samples_to_hand_says_no_data(self) -> None:
        self.assertTrue(remote_run.run_test("power_ripple", INVERTER, ()).no_data)


if __name__ == "__main__":
    unittest.main()
