"""A mail and what it says: one `Mail` to an asset's engineers on degradation, composed from the asset and its cause (a
catalogue fault or a failing remote test), and the `mails` table that records what was sent and to whom (2.6, SP-009).
Every instant is ISO 8601 text of an aware UTC datetime (Invariant: SOL-06). It imports the leaf alone (MOD-05)."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import utc
from solarpunk.leaf.codes import lookup
from solarpunk.leaf.faults import Fault

SUBJECT = "Solarpunk: {asset_id} {cause}"
ASSET_LINE = "Asset: {asset_id} ({name})"
LOCATION_LINE = "Location: {location}"
LOCATION_UNKNOWN = "location unknown"
FAULT_LINE = "Cause: fault {code}, {meaning}, opened {opened}"
REMOTE_LINE = "Cause: remote test {test_name} failed: {reason}"
INSTANT_LINE = "Instant: {now}"
CHAIN_LINE = "Engineers: {chain}"
CHAIN_SEPARATOR = ", "
RECIPIENT_SEPARATOR = ","
NO_ENGINEER = "{asset_id}: no engineer to mail"
INSERT_MAIL = "INSERT INTO mails (sent_at, recipients, subject, body, asset_id) VALUES (?, ?, ?, ?, ?)"
SELECT_SENT_FOR = "SELECT recipients, subject, body FROM mails WHERE asset_id = ? ORDER BY mail_id"
MAILS_TABLE = (
    "CREATE TABLE mails (mail_id INTEGER PRIMARY KEY, sent_at TEXT NOT NULL, recipients TEXT NOT NULL,"
    " subject TEXT NOT NULL, body TEXT NOT NULL, asset_id TEXT NOT NULL)"
)


class NoEngineer(ValueError):
    """Raised when a mail would go to nobody: NoEngineer("OAHE-INV-003: no engineer to mail")."""


@dataclass(frozen=True)
class Mail:
    """One mail: Mail(("a@example.com",), "Solarpunk: OAHE-INV-003 INV-001", "Asset: OAHE-INV-003 (Inverter 3)\\n…")."""

    to: tuple[str, ...]
    subject: str
    body: str


@dataclass(frozen=True)
class RemoteFailure:
    """A remote test that failed against an asset: RemoteFailure("reachable", "no answer within 5 s"). The remote
    module is a parallel lane (SP-005), so the mailer holds its own small shape of the result it mails about."""

    test_name: str
    reason: str


def _cause_line(cause: Fault | RemoteFailure) -> str:
    """The body's cause line: a Fault INV-001 opened 10:10 gives "Cause: fault INV-001, Inverter offline: …, opened
    2026-06-01T10:10:00+00:00"; RemoteFailure("reachable", "timeout") gives "Cause: remote test reachable failed: timeout"."""
    if isinstance(cause, RemoteFailure):
        return REMOTE_LINE.format(test_name=cause.test_name, reason=cause.reason)
    meaning = lookup(cause.code).meaning
    return FAULT_LINE.format(code=cause.code, meaning=meaning, opened=cause.opened.isoformat())


def _cause_name(cause: Fault | RemoteFailure) -> str:
    """The subject's name for the cause: a Fault gives its code ("INV-001"); a RemoteFailure its test name ("reachable")."""
    return cause.test_name if isinstance(cause, RemoteFailure) else cause.code


def compose_degradation(asset: Asset, cause: Fault | RemoteFailure, engineers: tuple[str, ...], now: datetime) -> Mail:
    """The mail to an asset's engineers: compose_degradation(inverter3, fault INV-001, ("a@x.org",), 10:15 UTC).subject
    is "Solarpunk: OAHE-INV-003 INV-001", and its body is five lines (asset, location, cause, instant, engineers);
    engineers () raises NoEngineer; a naive now raises NotUtc."""
    # Invariant: SOL-06
    if not engineers:
        raise NoEngineer(NO_ENGINEER.format(asset_id=asset.asset_id))
    lines = (
        ASSET_LINE.format(asset_id=asset.asset_id, name=asset.name),
        LOCATION_LINE.format(location=asset.location or LOCATION_UNKNOWN),
        _cause_line(cause),
        INSTANT_LINE.format(now=utc(now).isoformat()),
        CHAIN_LINE.format(chain=CHAIN_SEPARATOR.join(engineers)),
    )
    subject = SUBJECT.format(asset_id=asset.asset_id, cause=_cause_name(cause))
    return Mail(engineers, subject, "\n".join(lines))


def schema() -> tuple[str, ...]:
    """The mailer's schema statements, for leaf.store.apply: schema()[0] starts with "CREATE TABLE mails"."""
    return (MAILS_TABLE,)


def record(conn: sqlite3.Connection, mail: Mail, asset_id: str, sent_at: datetime) -> int:
    """Stores one sent mail and returns its mail_id; recipients are stored comma-joined: the first record on a fresh
    table returns 1 and stores ("a@x.org,b@x.org", subject, body); a naive sent_at raises NotUtc."""
    # Invariant: SOL-06
    stamp = utc(sent_at).isoformat()
    recipients = RECIPIENT_SEPARATOR.join(mail.to)
    cursor = conn.execute(INSERT_MAIL, (stamp, recipients, mail.subject, mail.body, asset_id))
    conn.commit()
    return int(cursor.lastrowid)  # type: ignore[arg-type]


def sent_for(conn: sqlite3.Connection, asset_id: str) -> tuple[Mail, ...]:
    """The mails recorded for an asset, oldest first: sent_for(conn, "OAHE-INV-003") after one record of mail m is (m,);
    an asset never mailed gives ()."""
    rows = conn.execute(SELECT_SENT_FOR, (asset_id,)).fetchall()
    return tuple(Mail(tuple(recipients.split(RECIPIENT_SEPARATOR)), subject, body) for recipients, subject, body in rows)
