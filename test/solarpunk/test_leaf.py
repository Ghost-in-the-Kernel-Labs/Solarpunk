"""The leaf's refusals and numbers, tested in the leaf's own file (lane 1.8): the clock (SOL-06), the sample and its
gap (SOL-06), the asset and its id (SOL-05), the fault (SOL-04), and the store. Each refusal is pinned by its exact
message, so a reader of a refusal knows what was wrong and a mutant that empties the message dies here."""
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from solarpunk.leaf import store
from solarpunk.leaf.assets import Asset, MalformedAssetId, parse_asset_id, site_id
from solarpunk.leaf.clock import SAMPLE_INTERVAL, NotUtc, OffTheGrid, Period, at, on_grid, utc
from solarpunk.leaf.codes import AssetKind, Severity, UnknownFaultCode
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.telemetry import Sample, gap

INVERTER = "OAHE-INV-003"


def asset(host: str | None, port: int | None, email: str | None = None) -> Asset:
    """Inverter 3 at OAHE with the given endpoint and engineer: asset("10.0.0.3", 5020).port is 5020."""
    return Asset(INVERTER, AssetKind.INVERTER, "OAHE", None, "Inverter 3", 100.0, host, port, None, email)


def fault(opened: datetime, closed: datetime | None, code: str = "INV-001") -> Fault:
    """Fault 7 on inverter 3: fault(at(2026, 6, 1, 10, 10), None).closed is None."""
    return Fault(7, INVERTER, code, opened, closed)


class TheUtcCheck(unittest.TestCase):
    def test_a_utc_instant_is_returned_as_it_is(self) -> None:
        """SOL-06: a UTC instant passes unchanged, whether made by at() or by timezone(timedelta(0))."""
        moment = at(2026, 6, 1, 10, 2)
        self.assertIs(utc(moment), moment)
        zero = datetime(2026, 6, 1, 10, 2, tzinfo=timezone(timedelta(0)))
        self.assertIs(utc(zero), zero)

    def test_a_naive_datetime_is_refused(self) -> None:
        """SOL-06: a naive datetime is refused, and the refusal names the instant."""
        with self.assertRaises(NotUtc) as raised:
            utc(datetime(2026, 1, 1))
        self.assertEqual(str(raised.exception), "2026-01-01T00:00:00 is not UTC")

    def test_an_offset_other_than_zero_is_refused(self) -> None:
        """SOL-06: an aware datetime at +01:00 or -00:01 is not UTC, even when it names the same instant."""
        cases = ((timedelta(hours=1), "2026-06-01T11:00:00+01:00 is not UTC"),
                 (timedelta(minutes=-1), "2026-06-01T09:59:00-00:01 is not UTC"))
        for offset, message in cases:
            moment = at(2026, 6, 1, 10).astimezone(timezone(offset))
            with self.assertRaises(NotUtc, msg=message) as raised:
                utc(moment)
            self.assertEqual(str(raised.exception), message)

    def test_not_utc_is_a_value_error(self) -> None:
        self.assertTrue(issubclass(NotUtc, ValueError))
        self.assertTrue(issubclass(OffTheGrid, ValueError))


class TheGrid(unittest.TestCase):
    def test_every_five_minutes_from_the_hour_is_on_the_grid(self) -> None:
        """SOL-06: 10:00, 10:05 … 10:55 are on the grid and come back unchanged."""
        for minute in range(0, 60, 5):
            moment = at(2026, 6, 1, 10, minute)
            self.assertIs(on_grid(moment), moment)

    def test_an_instant_off_the_grid_is_refused(self) -> None:
        """SOL-06: a sample off the grid is refused: a minute, a second or a microsecond off, each said exactly."""
        cases = ((at(2026, 6, 1, 10, 2), "2026-06-01T10:02:00+00:00"),
                 (at(2026, 6, 1, 10, 4) + timedelta(seconds=59), "2026-06-01T10:04:59+00:00"),
                 (at(2026, 6, 1, 10, 5) + timedelta(seconds=30), "2026-06-01T10:05:30+00:00"),
                 (at(2026, 6, 1, 10) + timedelta(microseconds=1), "2026-06-01T10:00:00.000001+00:00"),
                 (at(2026, 6, 1, 10) + timedelta(microseconds=3), "2026-06-01T10:00:00.000003+00:00"),
                 (at(2026, 6, 1, 10, 5) - timedelta(microseconds=1), "2026-06-01T10:04:59.999999+00:00"))
        for moment, shown in cases:
            with self.assertRaises(OffTheGrid, msg=shown) as raised:
                on_grid(moment)
            self.assertEqual(str(raised.exception), f"{shown} is not on the 300 s grid")

    def test_the_grid_checks_utc_first(self) -> None:
        """SOL-06: a naive instant on the grid is still refused, as NotUtc."""
        with self.assertRaises(NotUtc):
            on_grid(datetime(2026, 6, 1, 10, 5))


class ThePeriod(unittest.TestCase):
    def test_an_hour_holds_twelve_instants(self) -> None:
        """SOL-06: for [10:00, 11:00) the expected instants are 10:00, 10:05, …, 10:55, twelve in all."""
        hour = Period(at(2026, 6, 1, 10), at(2026, 6, 1, 11))
        self.assertEqual(hour.expected(), 12)
        self.assertEqual(hour.instants(), [at(2026, 6, 1, 10, m) for m in range(0, 60, 5)])
        self.assertEqual(hour.hours(), 1.0)

    def test_shorter_and_longer_periods(self) -> None:
        one = Period(at(2026, 6, 1, 10), at(2026, 6, 1, 10, 5))
        self.assertEqual((one.expected(), one.instants(), one.hours()), (1, [at(2026, 6, 1, 10)], 300 / 3600))
        quarter = Period(at(2026, 6, 1, 10), at(2026, 6, 1, 10, 15))
        self.assertEqual(quarter.instants(), [at(2026, 6, 1, 10), at(2026, 6, 1, 10, 5), at(2026, 6, 1, 10, 10)])
        self.assertEqual(quarter.hours(), 0.25)
        day = Period(at(2026, 6, 1), at(2026, 6, 2))
        self.assertEqual((day.expected(), day.hours()), (288, 24.0))
        self.assertEqual(day.instants()[-1], at(2026, 6, 1, 23, 55))
        self.assertEqual(SAMPLE_INTERVAL, timedelta(seconds=300))

    def test_an_empty_or_reversed_period_is_refused(self) -> None:
        """SOL-06: periods are half-open, so [10:00, 10:00) is empty and [11:00, 10:00) reversed; both are refused."""
        cases = ((at(2026, 6, 1, 10), at(2026, 6, 1, 10)), (at(2026, 6, 1, 11), at(2026, 6, 1, 10)))
        for start, end in cases:
            with self.assertRaises(ValueError) as raised:
                Period(start, end)
            self.assertEqual(str(raised.exception),
                             f"period {start.isoformat()} .. {end.isoformat()} is empty or reversed")

    def test_both_ends_lie_on_the_grid(self) -> None:
        """SOL-06: a period whose start or end is off the grid is refused as OffTheGrid."""
        with self.assertRaises(OffTheGrid):
            Period(at(2026, 6, 1, 10, 2), at(2026, 6, 1, 11))
        with self.assertRaises(OffTheGrid):
            Period(at(2026, 6, 1, 10), at(2026, 6, 1, 10, 58))


class TheAt(unittest.TestCase):
    def test_at_builds_a_utc_instant_with_hour_and_minute_defaulting_to_zero(self) -> None:
        """SOL-06: at() always gives UTC; at(2026, 6, 1) is midnight, at(2026, 6, 1, 10) is 10:00."""
        self.assertEqual(at(2026, 6, 1), datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(at(2026, 6, 1, 10), datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc))
        self.assertEqual(at(2026, 6, 1, 10, 5).isoformat(), "2026-06-01T10:05:00+00:00")
        self.assertIs(at(2026, 6, 1).tzinfo, timezone.utc)


class TheSample(unittest.TestCase):
    def test_a_reading_keeps_its_values(self) -> None:
        sample = Sample(INVERTER, at(2026, 6, 1, 10, 5), 812.0, 78.4, False)
        self.assertEqual((sample.irradiance_w_m2, sample.power_kw, sample.gap), (812.0, 78.4, False))

    def test_a_sample_off_the_grid_is_refused(self) -> None:
        """SOL-06: a sample off the grid is refused."""
        with self.assertRaises(OffTheGrid):
            Sample(INVERTER, at(2026, 6, 1, 10, 2), 812.0, 78.4, False)

    def test_a_gap_carrying_either_value_is_refused(self) -> None:
        """SOL-06: a gap's values are None; a gap that carries irradiance, power or both is refused."""
        for irradiance, power in ((812.0, None), (None, 78.4), (812.0, 78.4), (0.0, None), (None, 0.0)):
            with self.assertRaises(ValueError, msg=(irradiance, power)) as raised:
                Sample(INVERTER, at(2026, 6, 1, 10, 20), irradiance, power, True)
            self.assertEqual(str(raised.exception), "a gap at 2026-06-01T10:20:00+00:00 carries values")

    def test_a_reading_may_lack_a_value_without_being_a_gap(self) -> None:
        self.assertIsNone(Sample(INVERTER, at(2026, 6, 1, 10, 20), None, None, False).power_kw)

    def test_gap_builds_the_gap_sample(self) -> None:
        """SOL-06: an expected instant with no reading is a gap sample, never dropped."""
        self.assertEqual(gap(INVERTER, at(2026, 6, 1, 10, 20)),
                         Sample(INVERTER, at(2026, 6, 1, 10, 20), None, None, True))
        with self.assertRaises(OffTheGrid):
            gap(INVERTER, at(2026, 6, 1, 10, 21))


class TheAsset(unittest.TestCase):
    def test_an_asset_with_or_without_a_feed(self) -> None:
        self.assertEqual((asset("10.0.0.3", 5020).host, asset("10.0.0.3", 5020).port), ("10.0.0.3", 5020))
        self.assertIsNone(asset(None, None).port)

    def test_host_and_port_come_together(self) -> None:
        for host, port in (("10.0.0.3", None), (None, 5020)):
            with self.assertRaises(ValueError, msg=(host, port)) as raised:
                asset(host, port)
            self.assertEqual(str(raised.exception), "OAHE-INV-003: host and port come together")

    def test_a_port_is_one_to_65535(self) -> None:
        for port in (1, 65535):
            self.assertEqual(asset("10.0.0.3", port).port, port)
        for port in (0, 65536, -1):
            with self.assertRaises(ValueError, msg=port) as raised:
                asset("10.0.0.3", port)
            self.assertEqual(str(raised.exception), f"OAHE-INV-003: port {port} is not 1 to 65535")

    def test_an_engineer_email_has_one_shape(self) -> None:
        for good in ("ops@oahe.example", "a.b@c.d.e"):
            self.assertEqual(asset(None, None, good).engineer_email, good)
        for bad in ("ops.oahe.example", "ops@@oahe.example", "ops@oa@he.example", "ops@oahe", "ops @oahe.example",
                    "ops@oahe .example", "@oahe.example", "ops@.example", "ops@oahe.", ""):
            with self.assertRaises(ValueError, msg=bad) as raised:
                asset(None, None, bad)
            self.assertEqual(str(raised.exception), f"OAHE-INV-003: {bad!r} is not an email address")


class TheAssetId(unittest.TestCase):
    def test_a_well_formed_id_splits_into_site_kind_and_number(self) -> None:
        """SOL-05: OAHE-INV-003 is the third inverter at site OAHE; every kind's prefix parses to its kind."""
        self.assertEqual(parse_asset_id("OAHE-INV-003"), ("OAHE", AssetKind.INVERTER, 3))
        self.assertEqual(parse_asset_id("S1-TRK-120"), ("S1", AssetKind.TRACKER, 120))
        self.assertEqual(parse_asset_id("ABCDE9-SEN-999"), ("ABCDE9", AssetKind.SENSOR, 999))
        for kind in AssetKind:
            self.assertEqual(parse_asset_id(f"OAHE-{kind.value}-001"), ("OAHE", kind, 1))

    def test_a_malformed_id_is_refused(self) -> None:
        """SOL-05: OAHE-INV-3, oahe-INV-003 and OAHE-INVERTER-003 are refused, as are a one- or seven-char site."""
        for bad in ("OAHE-INV-3", "oahe-INV-003", "OAHE-INVERTER-003", "O-INV-003", "ABCDEFG-INV-003",
                    "OAHE-INV-0003", "OAHE-inv-003", "OAHE-INV-003 ", " OAHE-INV-003", "OAHE_INV_003", ""):
            with self.assertRaises(MalformedAssetId, msg=bad) as raised:
                parse_asset_id(bad)
            self.assertEqual(str(raised.exception), f"{bad!r} is not of the shape SITE-KIND-nnn")

    def test_an_unknown_kind_is_refused(self) -> None:
        """SOL-05: the kind is an AssetKind's prefix; OAHE-XYZ-003 has the shape but not a kind."""
        with self.assertRaises(MalformedAssetId) as raised:
            parse_asset_id("OAHE-XYZ-003")
        self.assertEqual(str(raised.exception), "'OAHE-XYZ-003': XYZ is not an asset kind")
        self.assertTrue(issubclass(MalformedAssetId, ValueError))

    def test_a_site_id_is_the_site_then_sit_001(self) -> None:
        """SOL-05: a site's own id is <SITE>-SIT-001, and it parses back to the site."""
        self.assertEqual(site_id("OAHE"), "OAHE-SIT-001")
        self.assertEqual(parse_asset_id(site_id("S1")), ("S1", AssetKind.SITE, 1))


class TheFault(unittest.TestCase):
    def test_a_closed_and_an_open_fault(self) -> None:
        closed = fault(at(2026, 6, 1, 10, 10), at(2026, 6, 1, 10, 30))
        self.assertEqual(closed.duration(), timedelta(minutes=20))
        self.assertIsNone(fault(at(2026, 6, 1, 10, 10), None).duration())
        self.assertEqual(fault(at(2026, 6, 1, 10), at(2026, 6, 2, 10)).duration(), timedelta(days=1))

    def test_an_unknown_code_is_refused(self) -> None:
        """SOL-04: a fault's code is in the catalogue; INV-999 and a malformed code are refused."""
        with self.assertRaises(UnknownFaultCode) as raised:
            fault(at(2026, 6, 1, 10), None, "INV-999")
        self.assertEqual(str(raised.exception), "INV-999 is not in the catalogue")
        with self.assertRaises(UnknownFaultCode):
            fault(at(2026, 6, 1, 10), None, "inv-1")

    def test_its_instants_are_utc(self) -> None:
        """SOL-06: a fault opened or closed at a naive instant is refused."""
        with self.assertRaises(NotUtc):
            fault(datetime(2026, 6, 1, 10), None)
        with self.assertRaises(NotUtc):
            fault(at(2026, 6, 1, 10), datetime(2026, 6, 1, 11))

    def test_a_fault_closes_after_it_opens(self) -> None:
        for closed in (at(2026, 6, 1, 10, 10), at(2026, 6, 1, 10, 5)):
            with self.assertRaises(ValueError, msg=closed) as raised:
                fault(at(2026, 6, 1, 10, 10), closed)
            self.assertEqual(str(raised.exception), "fault 7 closes at or before it opened")
        one_microsecond = fault(at(2026, 6, 1, 10, 10), at(2026, 6, 1, 10, 10) + timedelta(microseconds=1))
        self.assertEqual(one_microsecond.duration(), timedelta(microseconds=1))

    def test_covers_is_half_open(self) -> None:
        closed = fault(at(2026, 6, 1, 10, 10), at(2026, 6, 1, 10, 30))
        tick = timedelta(microseconds=1)
        cases = ((at(2026, 6, 1, 10, 10) - tick, False), (at(2026, 6, 1, 10, 10), True),
                 (at(2026, 6, 1, 10, 30) - tick, True), (at(2026, 6, 1, 10, 30), False))
        self.assertEqual([(instant, closed.covers(instant)) for instant, _ in cases], list(cases))

    def test_an_open_fault_covers_every_instant_from_opened_on(self) -> None:
        open_fault = fault(at(2026, 6, 1, 10, 10), None)
        self.assertFalse(open_fault.covers(at(2026, 6, 1, 10, 5)))
        self.assertTrue(open_fault.covers(at(2026, 6, 1, 10, 10)))
        self.assertTrue(open_fault.covers(at(2030, 1, 1)))

    def test_catalogue_row_is_the_codes_row(self) -> None:
        """SOL-04: a fault's meaning is the catalogue's row for its code."""
        self.assertIs(fault(at(2026, 6, 1, 10), None).catalogue_row().severity, Severity.OUTAGE)
        row = fault(at(2026, 6, 1, 10), None, "INV-002").catalogue_row()
        self.assertEqual((row.code, row.kind, row.severity), ("INV-002", AssetKind.INVERTER, Severity.DERATE))


class TheStore(unittest.TestCase):
    def test_a_connection_enforces_foreign_keys_and_reads_rows_by_name(self) -> None:
        conn = store.connect()
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        row = conn.execute("SELECT 7 AS answer").fetchone()
        self.assertIsInstance(row, sqlite3.Row)
        self.assertEqual(row["answer"], 7)

    def test_a_foreign_key_is_held(self) -> None:
        conn = store.connect()
        self.addCleanup(conn.close)
        store.apply(conn, ("CREATE TABLE parent (id INTEGER PRIMARY KEY)",
                           "CREATE TABLE child (parent_id INTEGER REFERENCES parent (id))"))
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO child VALUES (1)")

    def test_apply_runs_in_order_and_commits_to_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fleet.db"
            first = store.connect(path)
            store.apply(first, ("CREATE TABLE t (x INTEGER)", "INSERT INTO t VALUES (1)", "INSERT INTO t VALUES (2)"))
            second = store.connect(str(path))
            self.assertEqual([r["x"] for r in second.execute("SELECT x FROM t ORDER BY rowid")], [1, 2])
            self.assertFalse(first.in_transaction)
            first.close()
            second.close()

    def test_apply_with_no_statements_changes_nothing(self) -> None:
        conn = store.connect()
        self.addCleanup(conn.close)
        store.apply(conn, ())
        self.assertEqual(conn.execute("SELECT count(*) FROM sqlite_master").fetchone()[0], 0)
        self.assertEqual(store.MEMORY, ":memory:")


class TheAssetStatus(unittest.TestCase):
    def test_the_three_colours_are_distinct_members(self) -> None:
        """A dataclass decorator once sat on this Enum and made every member equal (J-020): the colours differ."""
        from solarpunk.leaf.codes import AssetStatus
        self.assertIsNot(AssetStatus.RED, AssetStatus.GREEN)
        self.assertNotEqual(AssetStatus.RED, AssetStatus.GREEN)
        self.assertNotEqual(AssetStatus.YELLOW, AssetStatus.GREEN)
        self.assertEqual(len({AssetStatus.RED, AssetStatus.YELLOW, AssetStatus.GREEN}), 3)
        self.assertEqual([s.value for s in AssetStatus], ["green", "yellow", "red"])
        self.assertEqual(repr(AssetStatus.RED), "<AssetStatus.RED: 'red'>")
