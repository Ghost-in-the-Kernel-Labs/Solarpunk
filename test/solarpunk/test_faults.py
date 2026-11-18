"""The fault ledger holds its refusals and its queries: unknown codes (SOL-04), naive instants (SOL-06), a second open
fault, a close before the opening and a second close are refused; instants round-trip as aware UTC."""
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from solarpunk.faults import ledger
from solarpunk.faults.ledger import LedgerError
from solarpunk.leaf import store
from solarpunk.leaf.clock import NotUtc, Period, at
from solarpunk.leaf.codes import UnknownFaultCode
from solarpunk.leaf.faults import Fault

INV = "OAHE-INV-003"
INV2 = "OAHE-INV-004"
TRK = "OAHE-TRK-001"


def fresh() -> sqlite3.Connection:
    """An in-memory store with the ledger's table: fresh().execute("SELECT count(*) FROM faults").fetchone()[0] is 0."""
    conn = store.connect()
    store.apply(conn, ledger.schema())
    return conn


def stored(conn: sqlite3.Connection) -> list[tuple[object, ...]]:
    """The raw rows of the faults table in id order: stored(fresh()) is []."""
    return [tuple(row) for row in conn.execute("SELECT * FROM faults ORDER BY fault_id")]


class TheSchema(unittest.TestCase):
    def test_the_table_has_the_settled_columns(self) -> None:
        info = [tuple(row)[1:] for row in fresh().execute("PRAGMA table_info(faults)")]
        self.assertEqual(info, [
            ("fault_id", "INTEGER", 0, None, 1),
            ("asset_id", "TEXT", 1, None, 0),
            ("code", "TEXT", 1, None, 0),
            ("opened", "TEXT", 1, None, 0),
            ("closed", "TEXT", 0, None, 0),
            ("assigned_by", "TEXT", 1, "'unrecorded'", 0),
            ("recorded_by", "TEXT", 0, None, 0),
        ])

    def test_upgrade_adds_the_sp015_columns_to_an_old_table_and_its_rows_read_unrecorded(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE faults (fault_id INTEGER PRIMARY KEY, asset_id TEXT NOT NULL, code TEXT NOT NULL,"
                     " opened TEXT NOT NULL, closed TEXT NULL)")
        conn.execute("INSERT INTO faults (asset_id, code, opened) VALUES (?, ?, ?)", (INV, "INV-001", "2026-06-01T10:10:00+00:00"))
        ledger.upgrade(conn)
        ledger.upgrade(conn)
        self.assertEqual(ledger.open_faults(conn), (Fault(1, INV, "INV-001", at(2026, 6, 1, 10, 10), None, "unrecorded", None),))

    def test_the_table_has_no_foreign_key_to_assets(self) -> None:
        self.assertEqual(fresh().execute("PRAGMA foreign_key_list(faults)").fetchall(), [])


class Assigning(unittest.TestCase):
    def test_assign_returns_the_stored_fault_and_stores_iso_utc_text(self) -> None:
        conn = fresh()
        fault = ledger.assign(conn, INV, "INV-001", at(2026, 6, 1, 10, 10))
        self.assertEqual(fault, Fault(1, INV, "INV-001", at(2026, 6, 1, 10, 10), None))
        self.assertEqual(stored(conn), [(1, INV, "INV-001", "2026-06-01T10:10:00+00:00", None, "unrecorded", None)])

    def test_assign_stores_who_assigned_and_who_entered_it(self) -> None:
        conn = fresh()
        fault = ledger.assign(conn, INV, "INV-001", at(2026, 6, 1, 10, 10), "tech@oahe.example", "operator@oahe.example")
        self.assertEqual((fault.assigned_by, fault.recorded_by), ("tech@oahe.example", "operator@oahe.example"))
        self.assertEqual(stored(conn)[0][5:], ("tech@oahe.example", "operator@oahe.example"))

    def test_instants_round_trip_as_aware_utc(self) -> None:
        conn = fresh()
        opened = datetime(2026, 6, 1, 10, 10, 7, 123456, tzinfo=timezone.utc)
        ledger.assign(conn, INV, "INV-001", opened)
        ledger.close(conn, 1, opened + timedelta(minutes=20))
        (fault,) = ledger.by_asset(conn, INV)
        for instant, expected in ((fault.opened, opened), (fault.closed, opened + timedelta(minutes=20))):
            self.assertEqual(instant, expected)
            assert instant is not None
            self.assertEqual(instant.utcoffset(), timedelta(0))

    def test_an_unknown_code_is_refused_and_nothing_is_stored(self) -> None:
        conn = fresh()
        for bad in ("INV-999", "inv-001"):
            with self.assertRaises(UnknownFaultCode, msg=bad):
                ledger.assign(conn, INV, bad, at(2026, 6, 1, 10, 10))
        self.assertEqual(stored(conn), [])

    def test_a_naive_or_non_utc_instant_is_refused_and_nothing_is_stored(self) -> None:
        conn = fresh()
        naive = datetime(2026, 6, 1, 10, 10)
        eastern = datetime(2026, 6, 1, 10, 10, tzinfo=timezone(timedelta(hours=-5)))
        for moment in (naive, eastern):
            with self.assertRaises(NotUtc, msg=str(moment)):
                ledger.assign(conn, INV, "INV-001", moment)
        self.assertEqual(stored(conn), [])

    def test_a_second_open_fault_of_one_code_on_one_asset_is_refused(self) -> None:
        conn = fresh()
        ledger.assign(conn, INV, "INV-001", at(2026, 6, 1, 10, 10))
        with self.assertRaises(LedgerError) as refused:
            ledger.assign(conn, INV, "INV-001", at(2026, 6, 1, 11, 0))
        self.assertEqual(str(refused.exception), f"{INV} already carries open fault 1 of INV-001")
        self.assertEqual(len(stored(conn)), 1)

    def test_another_code_another_asset_or_a_closed_predecessor_is_allowed(self) -> None:
        conn = fresh()
        ledger.assign(conn, INV, "INV-001", at(2026, 6, 1, 10, 10))
        ledger.assign(conn, INV, "INV-002", at(2026, 6, 1, 10, 15))
        ledger.assign(conn, INV2, "INV-001", at(2026, 6, 1, 10, 20))
        ledger.close(conn, 1, at(2026, 6, 1, 10, 30))
        again = ledger.assign(conn, INV, "INV-001", at(2026, 6, 1, 11, 0))
        self.assertEqual(again, Fault(4, INV, "INV-001", at(2026, 6, 1, 11, 0), None))

    def test_assign_and_close_are_committed_for_another_connection(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fleet.db"
            writer = store.connect(path)
            store.apply(writer, ledger.schema())
            ledger.assign(writer, INV, "INV-001", at(2026, 6, 1, 10, 10))
            reader = store.connect(path)
            self.assertEqual(ledger.open_faults(reader), (Fault(1, INV, "INV-001", at(2026, 6, 1, 10, 10), None),))
            ledger.close(writer, 1, at(2026, 6, 1, 10, 30))
            self.assertEqual(ledger.open_faults(store.connect(path)), ())
            writer.close()
            reader.close()


class Closing(unittest.TestCase):
    def setUp(self) -> None:
        """A ledger with fault 1, INV-001 on OAHE-INV-003 opened 10:10 UTC: ledger.open_faults(self.conn) has one fault."""
        self.conn = fresh()
        ledger.assign(self.conn, INV, "INV-001", at(2026, 6, 1, 10, 10))

    def test_close_returns_the_closed_fault(self) -> None:
        closed = ledger.close(self.conn, 1, at(2026, 6, 1, 10, 30))
        self.assertEqual(closed, Fault(1, INV, "INV-001", at(2026, 6, 1, 10, 10), at(2026, 6, 1, 10, 30)))
        self.assertEqual(stored(self.conn)[0][4], "2026-06-01T10:30:00+00:00")

    def test_an_unknown_fault_id_is_refused(self) -> None:
        with self.assertRaises(LedgerError) as refused:
            ledger.close(self.conn, 9, at(2026, 6, 1, 10, 30))
        self.assertEqual(str(refused.exception), "fault 9 is not in the ledger")

    def test_a_close_at_or_before_the_opening_is_refused(self) -> None:
        for moment in (at(2026, 6, 1, 10, 10), at(2026, 6, 1, 10, 5)):
            with self.assertRaises(LedgerError, msg=str(moment)) as refused:
                ledger.close(self.conn, 1, moment)
            self.assertEqual(
                str(refused.exception), f"fault 1 cannot close at {moment.isoformat()}, at or before it opened"
            )
        self.assertIsNone(stored(self.conn)[0][4])

    def test_a_second_close_is_refused(self) -> None:
        ledger.close(self.conn, 1, at(2026, 6, 1, 10, 30))
        with self.assertRaises(LedgerError) as refused:
            ledger.close(self.conn, 1, at(2026, 6, 1, 10, 45))
        self.assertEqual(str(refused.exception), "fault 1 is already closed")
        self.assertEqual(stored(self.conn)[0][4], "2026-06-01T10:30:00+00:00")

    def test_a_naive_close_is_refused(self) -> None:
        with self.assertRaises(NotUtc):
            ledger.close(self.conn, 1, datetime(2026, 6, 1, 10, 30))
        self.assertIsNone(stored(self.conn)[0][4])


class Querying(unittest.TestCase):
    def setUp(self) -> None:
        """Four faults, fault 1 closed: ledger.open_faults(self.conn) holds faults 2, 3 and 4."""
        self.conn = fresh()
        ledger.assign(self.conn, INV, "INV-001", at(2026, 6, 1, 10, 10))
        ledger.assign(self.conn, TRK, "TRK-001", at(2026, 6, 1, 10, 20))
        ledger.assign(self.conn, INV, "INV-002", at(2026, 6, 1, 10, 30))
        ledger.assign(self.conn, INV2, "INV-001", at(2026, 6, 1, 10, 40))
        ledger.close(self.conn, 1, at(2026, 6, 1, 11, 0))

    def ids(self, faults: tuple[Fault, ...]) -> list[int]:
        """The fault ids of a query's answer, in order: self.ids(ledger.open_faults(self.conn)) is [2, 3, 4]."""
        return [fault.fault_id for fault in faults]

    def test_open_faults_are_the_unclosed_in_id_order(self) -> None:
        self.assertEqual(self.ids(ledger.open_faults(self.conn)), [2, 3, 4])

    def test_by_asset_is_that_asset_alone_in_id_order(self) -> None:
        self.assertEqual(self.ids(ledger.by_asset(self.conn, INV)), [1, 3])
        self.assertEqual(ledger.by_asset(self.conn, "OAHE-INV-099"), ())

    def test_by_code_is_that_code_alone_and_refuses_an_unknown_code(self) -> None:
        self.assertEqual(self.ids(ledger.by_code(self.conn, "INV-001")), [1, 4])
        self.assertEqual(ledger.by_code(self.conn, "INV-003"), ())
        with self.assertRaises(UnknownFaultCode):
            ledger.by_code(self.conn, "INV-999")


class InPeriod(unittest.TestCase):
    def test_overlap_is_half_open_on_both_sides(self) -> None:
        conn = fresh()
        cases = (  # (opened, closed or None, in Period(10:00, 11:00)?)
            (at(2026, 6, 1, 9), at(2026, 6, 1, 10), False),  # ends exactly at the start
            (at(2026, 6, 1, 9), at(2026, 6, 1, 10, 5), True),  # ends just inside
            (at(2026, 6, 1, 10, 10), at(2026, 6, 1, 10, 20), True),  # wholly inside
            (at(2026, 6, 1, 11), None, False),  # open, opened exactly at the end
            (at(2026, 6, 1, 10, 55), None, True),  # open, opened just before the end
            (at(2026, 6, 1, 8), None, True),  # open, opened before the start
            (at(2026, 6, 1, 11, 5), at(2026, 6, 1, 12), False),  # wholly after
        )
        for number, (opened, closed, _) in enumerate(cases, start=1):
            ledger.assign(conn, f"OAHE-INV-{number:03d}", "INV-001", opened)
            if closed is not None:
                ledger.close(conn, number, closed)
        found = [fault.fault_id for fault in ledger.in_period(conn, Period(at(2026, 6, 1, 10), at(2026, 6, 1, 11)))]
        self.assertEqual(found, [number for number, case in enumerate(cases, start=1) if case[2]])
        self.assertEqual(found, [2, 3, 5, 6])


class Repeated(unittest.TestCase):
    def setUp(self) -> None:
        """An empty ledger and the month of June 2026: self.june.start is at(2026, 6, 1)."""
        self.conn = fresh()
        self.june = Period(at(2026, 6, 1), at(2026, 7, 1))

    def repeat(self, asset_id: str, code: str, days: tuple[int, ...]) -> None:
        """Assigns and closes the code on the asset once on each June day: self.repeat(INV, "INV-001", (1, 2)) adds two."""
        for day in days:
            fault = ledger.assign(self.conn, asset_id, code, at(2026, 6, day, 10))
            ledger.close(self.conn, fault.fault_id, at(2026, 6, day, 11))

    def test_most_repeated_first_then_asset_then_code(self) -> None:
        self.repeat(INV, "INV-002", (1, 2))  # first in, so a tie left to insertion order would put it first
        self.repeat(INV2, "INV-001", (3, 4))
        self.repeat(TRK, "TRK-001", (5, 6, 7))  # last by asset id, first by count
        self.repeat(INV, "INV-001", (8, 9))
        self.repeat(INV2, "INV-002", (10,))
        self.assertEqual(ledger.repeated(self.conn, self.june, 2), (
            (TRK, "TRK-001", 3),
            (INV, "INV-001", 2),
            (INV, "INV-002", 2),
            (INV2, "INV-001", 2),
        ))
        self.assertEqual(ledger.repeated(self.conn, self.june, 3), ((TRK, "TRK-001", 3),))
        self.assertEqual(ledger.repeated(self.conn, self.june, 4), ())

    def test_only_openings_inside_the_half_open_period_count(self) -> None:
        ledger.assign(self.conn, INV, "INV-001", at(2026, 5, 31, 23, 55))
        ledger.close(self.conn, 1, at(2026, 6, 1, 1))
        self.repeat(INV, "INV-001", (1,))
        ledger.close(self.conn, ledger.assign(self.conn, INV, "INV-001", at(2026, 6, 1)).fault_id, at(2026, 6, 1, 1))
        ledger.assign(self.conn, INV, "INV-001", at(2026, 7, 1))
        self.assertEqual(ledger.repeated(self.conn, self.june, 1), ((INV, "INV-001", 2),))


if __name__ == "__main__":
    unittest.main()
