"""The ticket outbox read back (11.1, SP-027): the events the ledger wrote beside each ticket change (ledger.outbox_add,
in the change's own commit), unsent ones in the order written, and the stamp a delivery leaves. Project hands them to a
tracker's sink and stamps each one the sink took; a tracker that is down leaves them waiting, and the ledger never
waits on it. It imports the leaf and its own module alone (MOD-05)."""
import sqlite3
from datetime import datetime

from solarpunk.leaf.clock import utc
from solarpunk.leaf.tickets import OutboxEvent
from solarpunk.workorders.ledger import WorkOrderError

PENDING = (
    "SELECT o.event_id, o.wo_id, o.kind, o.at, w.asset_id, o.detail FROM ticket_outbox o"
    " JOIN work_orders w ON w.wo_id = o.wo_id WHERE o.sent IS NULL ORDER BY o.event_id"
)


def pending(conn: sqlite3.Connection) -> tuple[OutboxEvent, ...]:
    """Every event no tracker has taken yet, oldest first: after the demo is built, the outage ticket's "create" is
    among them; after mark_sent, it is not."""
    return tuple(OutboxEvent(e, w, kind, datetime.fromisoformat(at), asset, detail)
                 for e, w, kind, at, asset, detail in conn.execute(PENDING))


def mark_sent(conn: sqlite3.Connection, event_id: int, moment: datetime) -> None:
    """Stamps an event as taken by the tracker at an instant; an event unknown or already sent raises WorkOrderError,
    so one is never sent twice by mistake."""
    changed = conn.execute("UPDATE ticket_outbox SET sent = ? WHERE event_id = ? AND sent IS NULL",
                           (utc(moment).isoformat(), event_id)).rowcount
    if changed != 1:
        raise WorkOrderError(f"outbox event {event_id} is not waiting to be sent")
    conn.commit()


def sent_count(conn: sqlite3.Connection) -> int:
    """How many events trackers have taken: 0 in a fresh store."""
    return conn.execute("SELECT count(*) FROM ticket_outbox WHERE sent IS NOT NULL").fetchone()[0]
