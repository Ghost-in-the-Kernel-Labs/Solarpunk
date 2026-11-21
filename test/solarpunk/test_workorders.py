"""The work-order ledger holds its refusals and its queries (4.1, SP-046): a naive instant, an unknown order, a close at
or before the opening, a second close and a second open corrective order for one fault are refused, each writing
nothing; instants round-trip as aware UTC; a store's old root-cause codes still read, as text; a corrective order closes
only once its fault's root cause is written (project), and a count of repeats is the fault ledger's, by fault code."""
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone

from solarpunk.leaf import store
from solarpunk.leaf.clock import NotUtc, at
from solarpunk.workorders import ledger
from solarpunk.workorders.ledger import WorkOrder, WorkOrderError
from solarpunk import project
from solarpunk.faults import ledger as fault_ledger
from solarpunk.leaf.codes import AssetStatus
from solarpunk.project import UnknownAsset

ENGINEER = "site@oahe.example"  # SP-015: a fault names the engineer who assigned it; the fixtures' site engineer

INV = "OAHE-INV-003"
INV1 = "OAHE-INV-001"
INV2_OAHE = "OAHE-INV-002"
INV2 = "OAHE-INV-004"
TRK = "OAHE-TRK-001"
OPENED = at(2026, 6, 1, 10, 10)
LATER = at(2026, 6, 1, 10, 30)


def fresh() -> sqlite3.Connection:
    """An in-memory store with the ledger's table: fresh().execute("SELECT count(*) FROM work_orders").fetchone()[0] is 0."""
    conn = store.connect()
    store.apply(conn, ledger.schema())
    return conn


def stored(conn: sqlite3.Connection) -> list[tuple[object, ...]]:
    """The raw rows of the work_orders table in id order, the order's own columns (4.1) without the ticket's (8.2):
    stored(fresh()) is []."""
    return [tuple(row) for row in conn.execute(
        "SELECT wo_id, asset_id, fault_id, kind, opened, closed, root_cause, note FROM work_orders ORDER BY wo_id")]


class TheSchema(unittest.TestCase):
    def test_the_table_has_the_settled_columns(self) -> None:
        info = [tuple(row)[1:] for row in fresh().execute("PRAGMA table_info(work_orders)")]
        self.assertEqual(info, [
            ("wo_id", "INTEGER", 0, None, 1),
            ("asset_id", "TEXT", 1, None, 0),
            ("fault_id", "INTEGER", 0, None, 0),
            ("kind", "TEXT", 1, None, 0),
            ("opened", "TEXT", 1, None, 0),
            ("closed", "TEXT", 0, None, 0),
            ("root_cause", "TEXT", 0, None, 0),
            ("note", "TEXT", 1, None, 0),
            ("status", "TEXT", 1, "'open'", 0),
            ("priority", "TEXT", 0, None, 0),
            ("assignee", "TEXT", 0, None, 0),
            ("acknowledged", "TEXT", 0, None, 0),
            ("responded", "TEXT", 0, None, 0),
            ("resolved", "TEXT", 0, None, 0),
            ("evidence", "TEXT", 0, None, 0),
            ("version", "INTEGER", 1, "1", 0),  # 12.2
        ])

    def test_a_kind_outside_the_two_is_refused_by_the_table(self) -> None:
        conn = fresh()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(ledger.INSERT_ORDER, (INV, None, "reactive", OPENED.isoformat(), "x", None))


class Opening(unittest.TestCase):
    def test_a_corrective_order_is_stored_and_returned(self) -> None:
        conn = fresh()
        order = ledger.open_corrective(conn, INV, 4, OPENED, "replace the fuse")
        self.assertEqual(order, WorkOrder(1, INV, 4, "corrective", OPENED, None, None, "replace the fuse"))
        self.assertEqual(stored(conn), [(1, INV, 4, "corrective", "2026-06-01T10:10:00+00:00", None, None, "replace the fuse")])
        self.assertIs(order.opened.tzinfo, timezone.utc)

    def test_a_preventive_order_has_no_fault(self) -> None:
        conn = fresh()
        order = ledger.open_preventive(conn, TRK, OPENED, "grease the drive")
        self.assertEqual(order, WorkOrder(1, TRK, None, "preventive", OPENED, None, None, "grease the drive"))

    def test_a_second_open_corrective_order_for_one_fault_is_refused(self) -> None:
        conn = fresh()
        ledger.open_corrective(conn, INV, 4, OPENED, "first")
        with self.assertRaises(WorkOrderError) as caught:
            ledger.open_corrective(conn, INV, 4, LATER, "second")
        self.assertEqual(str(caught.exception), "fault 4 already has open work order 1")
        self.assertEqual(len(stored(conn)), 1)
        ledger.open_corrective(conn, INV, 5, LATER, "another fault")
        ledger.open_preventive(conn, INV, LATER, "preventive beside it")
        self.assertEqual(len(stored(conn)), 3)

    def test_a_closed_order_does_not_block_a_new_one_for_its_fault(self) -> None:
        conn = fresh()
        first = ledger.open_corrective(conn, INV, 4, OPENED, "first")
        ledger.close(conn, first.wo_id, LATER)
        again = ledger.open_corrective(conn, INV, 4, at(2026, 6, 1, 11), "again")
        self.assertEqual(again.wo_id, 2)

    def test_a_naive_or_non_utc_instant_is_refused_and_nothing_stored(self) -> None:
        conn = fresh()
        plus_one = datetime(2026, 6, 1, 10, tzinfo=timezone(timedelta(hours=1)))
        for moment in (datetime(2026, 6, 1, 10), plus_one):
            with self.assertRaises(NotUtc):
                ledger.open_corrective(conn, INV, 4, moment, "x")
            with self.assertRaises(NotUtc):
                ledger.open_preventive(conn, INV, moment, "x")
        self.assertEqual(stored(conn), [])


class Closing(unittest.TestCase):
    def setUp(self) -> None:
        """One open corrective order, wo_id 1, for fault 4 on OAHE-INV-003 opened at 10:10, and the rows it left."""
        self.conn = fresh()
        self.order = ledger.open_corrective(self.conn, INV, 4, OPENED, "replace the fuse")
        self.before = stored(self.conn)

    def test_a_close_stamps_the_order_and_writes_no_cause(self) -> None:
        closed = ledger.close(self.conn, 1, LATER)
        self.assertEqual(closed, WorkOrder(1, INV, 4, "corrective", OPENED, LATER, None, "replace the fuse", version=2))
        self.assertEqual(stored(self.conn)[0][5:7], ("2026-06-01T10:30:00+00:00", None))  # the cause is the fault's (SP-046)
        self.assertIs(closed.closed.tzinfo if closed.closed else None, timezone.utc)

    def test_an_old_stores_code_reads_as_plain_text(self) -> None:
        self.conn.execute("UPDATE work_orders SET closed = ?, root_cause = 'RC-GRID', status = 'closed' WHERE wo_id = 1",
                          (LATER.isoformat(),))
        self.assertEqual(ledger.get(self.conn, 1).root_cause, "RC-GRID")

    def test_an_unknown_order_is_refused(self) -> None:
        with self.assertRaises(WorkOrderError) as caught:
            ledger.close(self.conn, 9, LATER)
        self.assertEqual(str(caught.exception), "work order 9 is not in the ledger")
        with self.assertRaises(WorkOrderError):
            ledger.get(self.conn, 9)

    def test_a_close_at_or_before_the_opening_is_refused(self) -> None:
        for moment in (OPENED, at(2026, 6, 1, 10)):
            with self.assertRaises(WorkOrderError) as caught:
                ledger.close(self.conn, 1, moment)
            self.assertEqual(str(caught.exception),
                             f"work order 1 cannot close at {moment.isoformat()}, at or before it opened")
        self.assertEqual(stored(self.conn), self.before)
        self.assertEqual(ledger.close(self.conn, 1, OPENED + timedelta(seconds=1)).closed,
                         OPENED + timedelta(seconds=1))

    def test_a_second_close_is_refused(self) -> None:
        ledger.close(self.conn, 1, LATER)
        after = stored(self.conn)
        with self.assertRaises(WorkOrderError) as caught:
            ledger.close(self.conn, 1, at(2026, 6, 1, 11))
        self.assertEqual(str(caught.exception), "work order 1 is already closed")
        self.assertEqual(stored(self.conn), after)

    def test_a_naive_close_is_refused(self) -> None:
        with self.assertRaises(NotUtc):
            ledger.close(self.conn, 1, datetime(2026, 6, 1, 11))
        self.assertEqual(stored(self.conn), self.before)


class Queries(unittest.TestCase):
    def setUp(self) -> None:
        """Three orders: 1 on OAHE-INV-003 (closed), 2 preventive on OAHE-TRK-001, 3 on OAHE-INV-004."""
        self.conn = fresh()
        ledger.open_corrective(self.conn, INV, 1, OPENED, "a")
        ledger.open_preventive(self.conn, TRK, OPENED, "b")
        ledger.open_corrective(self.conn, INV2, 2, OPENED, "c")
        ledger.close(self.conn, 1, LATER)

    def test_open_orders_leaves_out_the_closed(self) -> None:
        self.assertEqual([order.wo_id for order in ledger.open_orders(self.conn)], [2, 3])

    def test_by_asset_holds_that_assets_orders_alone(self) -> None:
        self.assertEqual([order.wo_id for order in ledger.by_asset(self.conn, INV)], [1])
        self.assertEqual([order.wo_id for order in ledger.by_asset(self.conn, TRK)], [2])
        self.assertEqual(ledger.by_asset(self.conn, "OAHE-INV-009"), ())
        ledger.open_preventive(self.conn, INV, LATER, "d")
        self.assertEqual([order.wo_id for order in ledger.by_asset(self.conn, INV)], [1, 4])


class ProjectWorkOrders(unittest.TestCase):
    def fleet(self) -> sqlite3.Connection:
        """A fresh store holding the OAHE fleet and nothing else: stored(self.fleet()) is []."""
        conn = project.open_store()
        self.addCleanup(conn.close)
        project.load_fleet(conn, project.demo_fleet())
        return conn

    def write_cause(self, conn: sqlite3.Connection, fault_id: int) -> None:
        """An engineer writes the fault's root cause at 12:30, free text: write_cause(conn, 1) leaves "worn fuse holder"."""
        project.write_fault_cause(conn, fault_id, "worn fuse holder", ENGINEER, at(2026, 6, 1, 12, 30))

    def outage(self, conn: sqlite3.Connection) -> project.Fault:
        """An INV-001 opened on OAHE-INV-001 at 12:00 on 2026-06-01: outage(conn).fault_id is 1 in a fresh store."""
        return project.assign_fault(conn, INV1, "INV-001", at(2026, 6, 1, 12), ENGINEER)

    def test_an_order_from_a_fault_takes_the_faults_asset(self) -> None:
        conn = self.fleet()
        fault = self.outage(conn)
        order = project.open_work_order_from_fault(conn, fault.fault_id, at(2026, 6, 1, 12), "swap the fuse")
        self.assertEqual(order, project.WorkOrder(1, INV1, fault.fault_id, "corrective", at(2026, 6, 1, 12), None, None,
                                                  "swap the fuse", version=2))  # the note set: a change
        self.assertEqual(project.work_orders_for(conn, INV1), (order,))
        self.assertEqual(project.work_orders_for(conn, INV2_OAHE), ())

    def test_a_fault_not_open_in_the_ledger_takes_no_order(self) -> None:
        conn = self.fleet()
        fault = self.outage(conn)
        project.close_fault(conn, fault.fault_id, at(2026, 6, 1, 13))
        for fault_id in (fault.fault_id, 9):
            with self.assertRaises(project.LedgerError) as caught:
                project.open_work_order_from_fault(conn, fault_id, at(2026, 6, 1, 14), "x")
            self.assertEqual(str(caught.exception), f"fault {fault_id} is not open in the ledger")
        self.assertEqual(len(stored(conn)), 1)  # the ticket assign_fault opened (8.2), alone

    def test_an_order_cannot_open_before_its_fault(self) -> None:
        conn = self.fleet()
        fault = self.outage(conn)
        with self.assertRaises(project.WorkOrderError) as caught:
            project.open_work_order_from_fault(conn, fault.fault_id, at(2026, 6, 1, 11, 55), "x")
        self.assertEqual(str(caught.exception), f"a work order for fault {fault.fault_id} cannot open before the fault did")
        self.assertEqual(len(stored(conn)), 1)  # the ticket assign_fault opened (8.2), alone

    def test_closing_a_corrective_order_closes_its_fault_in_one_call(self) -> None:
        conn = self.fleet()
        fault = self.outage(conn)
        order = project.open_work_order_from_fault(conn, fault.fault_id, at(2026, 6, 1, 12, 5), "swap the fuse")
        self.assertIs(project.asset_status(conn, INV1), AssetStatus.RED)
        self.write_cause(conn, fault.fault_id)
        closed = project.close_work_order(conn, order.wo_id, at(2026, 6, 1, 13))
        self.assertEqual(closed.closed, at(2026, 6, 1, 13))
        self.assertEqual(fault_ledger.by_asset(conn, INV1)[0].closed, at(2026, 6, 1, 13))
        self.assertIs(project.asset_status(conn, INV1), AssetStatus.GREEN)

    def test_a_blank_cause_closes_neither_the_order_nor_the_fault(self) -> None:
        conn = self.fleet()
        fault = self.outage(conn)
        order = project.open_work_order_from_fault(conn, fault.fault_id, at(2026, 6, 1, 12, 5), "x")
        with self.assertRaises(project.NoRootCause):
            project.close_work_order(conn, order.wo_id, at(2026, 6, 1, 13))
        self.assertEqual(project.work_orders_for(conn, INV1), (order,))
        self.assertEqual(fault_ledger.open_faults(conn), (fault,))

    def test_a_fault_closed_already_is_left_as_it_was(self) -> None:
        conn = self.fleet()
        fault = self.outage(conn)
        order = project.open_work_order_from_fault(conn, fault.fault_id, at(2026, 6, 1, 12, 5), "x")
        project.close_fault(conn, fault.fault_id, at(2026, 6, 1, 12, 30))
        self.write_cause(conn, fault.fault_id)
        closed = project.close_work_order(conn, order.wo_id, at(2026, 6, 1, 13))
        self.assertEqual(closed.closed, at(2026, 6, 1, 13))
        self.assertEqual(fault_ledger.by_asset(conn, INV1)[0].closed, at(2026, 6, 1, 12, 30))

    def test_a_preventive_order_closes_alone_and_leaves_open_faults_open(self) -> None:
        conn = self.fleet()
        fault = self.outage(conn)
        order = project.open_preventive_work_order(conn, INV1, at(2026, 6, 1, 12), "clean the filters")
        self.assertEqual((order.kind, order.fault_id), ("preventive", None))
        project.close_work_order(conn, order.wo_id, at(2026, 6, 1, 13))  # no fault, so no cause to wait for
        self.assertEqual(fault_ledger.open_faults(conn), (fault,))

    def test_closing_one_order_leaves_another_assets_fault_open(self) -> None:
        conn = self.fleet()
        first = self.outage(conn)
        other = project.assign_fault(conn, INV2_OAHE, "INV-001", at(2026, 6, 1, 12), ENGINEER)
        order = project.open_work_order_from_fault(conn, first.fault_id, at(2026, 6, 1, 12, 5), "x")
        self.write_cause(conn, first.fault_id)
        project.close_work_order(conn, order.wo_id, at(2026, 6, 1, 13))
        self.assertEqual(fault_ledger.open_faults(conn), (other,))

    def test_an_asset_the_fleet_lacks_takes_no_preventive_order_and_has_no_orders(self) -> None:
        conn = self.fleet()
        with self.assertRaises(UnknownAsset):
            project.open_preventive_work_order(conn, "OAHE-INV-009", at(2026, 6, 1, 12), "x")
        with self.assertRaises(UnknownAsset):
            project.work_orders_for(conn, "OAHE-INV-009")
        self.assertEqual(len(stored(conn)), 0)

    def test_the_asset_detail_shows_its_open_orders_alone(self) -> None:
        conn = self.fleet()
        fault = self.outage(conn)
        done = project.open_preventive_work_order(conn, INV1, at(2026, 6, 1, 9), "done")
        project.close_work_order(conn, done.wo_id, at(2026, 6, 1, 10))
        open_one = project.open_work_order_from_fault(conn, fault.fault_id, at(2026, 6, 1, 12, 5), "x")
        project.open_preventive_work_order(conn, INV2_OAHE, at(2026, 6, 1, 12), "elsewhere")
        self.assertEqual(project.asset_detail(conn, INV1).open_orders, (open_one,))
        self.assertEqual(project.asset_detail(conn, INV2_OAHE).open_orders[0].asset_id, INV2_OAHE)
        self.assertEqual(project.asset_detail(conn, "OAHE-INV-001").open_orders[0].wo_id, open_one.wo_id)


if __name__ == "__main__":
    unittest.main()
