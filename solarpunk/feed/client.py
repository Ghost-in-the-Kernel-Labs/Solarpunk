"""The feed client: ping(asset) opens asset.host:asset.port over plain TCP, reads newline-delimited JSON records until
the server closes, and turns each into a leaf Sample, refusing a record whose instant is off the grid (Invariant:
SOL-06) or whose fields the asset maintenance list does not hold or holds out of range (Invariant: SOL-03); records()
is the inverse, the wire text for some samples. One record on the wire:
{"asset_id": "OAHE-INV-001", "at": "2026-06-01T10:05:00+00:00", "irradiance_w_m2": 812.0, "power_kw": 78.4, "gap": false}."""
import errno
import json
import math
import socket
from datetime import datetime

from solarpunk.leaf import asset_types
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import on_grid, utc
from solarpunk.leaf.telemetry import Sample, gap

FIELDS = ("asset_id", "at", "irradiance_w_m2", "power_kw", "gap")
VALUE_FIELDS = ("irradiance_w_m2", "power_kw")
FEED_CAP_BYTES = 4 * 1024 * 1024
CHUNK_BYTES = 65536
ENCODING = "utf-8"
NEWLINE = "\n"
DEFAULT_TIMEOUT_S = 5.0
READ_FIELDS = ("asset_id", "field", "at", "value")
READ_CAP_BYTES = 4096


class FeedError(ValueError):
    """Raised for an unreachable, slow, oversized or malformed feed: FeedError("malformed record: not JSON: {")."""


def ping(asset: Asset, timeout_s: float = DEFAULT_TIMEOUT_S) -> tuple[Sample, ...]:
    """The asset's feed as samples: against a simulator serving OAHE-INV-001's 288 samples of 2026-06-01, ping(that
    inverter at its host and port) is those 288 samples; an asset with no host raises FeedError("OAHE-STR-001: no
    endpoint")."""
    if asset.port is None:  # the leaf's Asset holds host and port together, so no port is no host
        raise FeedError(f"{asset.asset_id}: no endpoint")
    return parse(asset, fetch(asset.host, asset.port, timeout_s, FEED_CAP_BYTES))


def read_now(asset: Asset, field: str, moment: datetime, timeout_s: float = DEFAULT_TIMEOUT_S) -> float | None:
    """The live-read mode (13.3, SP-020): one current reading of one field of the asset, asked for at the instant given
    (a simulator answers from its day at that instant, a real asset with what it reads now): against a simulator of
    OAHE-INV-001, read_now(inverter, "power_kw", 10:00:30 UTC) is the day's power half way from 10:00 to 10:05; a
    reading the asset has not got is None; an asset with no endpoint raises FeedError("OAHE-STR-001: no endpoint")."""
    if asset.port is None:
        raise FeedError(f"{asset.asset_id}: no endpoint")
    request = json.dumps({"read": field, "at": utc(moment).isoformat()}) + NEWLINE
    return reading(asset, field, fetch(asset.host, asset.port, timeout_s, READ_CAP_BYTES, request.encode(ENCODING)))


def reading(asset: Asset, field: str, payload: bytes) -> float | None:
    """The answer to one live read: reading(inverter, "power_kw", b'{"asset_id": "OAHE-INV-001", "field": "power_kw",
    "at": "2026-06-01T10:00:30+00:00", "value": 78.4}') is 78.4, a null value None; an answer for another asset or
    field, one that is not those four keys, or {"error": "..."} raises FeedError."""
    try:
        raw = json.loads(payload.decode(ENCODING))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FeedError("malformed reading: not JSON") from error
    if isinstance(raw, dict) and "error" in raw:
        raise FeedError(f"read refused: {raw['error']}")
    if not isinstance(raw, dict) or sorted(raw) != sorted(READ_FIELDS):
        raise FeedError("malformed reading: keys are not " + ", ".join(READ_FIELDS))
    if raw["asset_id"] != asset.asset_id or raw["field"] != field:
        raise FeedError(f"reading of {raw['field']} for {raw['asset_id']}, not {field} for {asset.asset_id}")
    return value(asset, field, raw["value"], raw["value"] is None)


def fetch(host: str, port: int, timeout_s: float, cap: int, request: bytes = b"") -> bytes:
    """Every byte the endpoint sends before it closes, after sending it the request (none for the day's feed) and then
    closing the sending side, so a live simulator tells the two apart at once: fetch("127.0.0.1", 5020, 5.0,
    FEED_CAP_BYTES) against a simulator is its records() text, encoded; a closed port raises FeedError("127.0.0.1:5020
    is unreachable")."""
    try:
        conn = socket.create_connection((host, port), timeout=timeout_s)
    except OSError as error:
        raise FeedError(f"{host}:{port} is unreachable") from error
    with conn:
        try:
            if request:
                conn.sendall(request)
            half_close(conn)
            return read_all(conn, cap)
        except TimeoutError as error:
            raise FeedError(f"{host}:{port} is slow: nothing for {timeout_s} s") from error


def half_close(conn: socket.socket) -> None:
    """Closes the sending side; a server that already answered and closed makes that raise ENOTCONN, which is no failure
    of the read, so the answer it sent is still read: any other OSError raises."""
    try:
        conn.shutdown(socket.SHUT_WR)
    except OSError as error:
        if error.errno != errno.ENOTCONN:
            raise


def read_all(conn: socket.socket, cap: int) -> bytes:
    """A connection's bytes until EOF, at most cap of them: a peer that sends b"abc" and closes gives b"abc" under
    cap 3; under cap 2 it raises FeedError("feed too large: over 2 bytes")."""
    received = bytearray()
    while chunk := conn.recv(CHUNK_BYTES):
        received.extend(chunk)
        if len(received) > cap:
            raise FeedError(f"feed too large: over {cap} bytes")
    return bytes(received)


def parse(asset: Asset, payload: bytes) -> tuple[Sample, ...]:
    """The feed's bytes as samples, one per non-empty line: parse(inverter, records((s,)).encode()) is (s,);
    b"\\xff" raises FeedError("malformed record: not utf-8")."""
    try:
        text = payload.decode(ENCODING)
    except UnicodeDecodeError as error:
        raise FeedError("malformed record: not utf-8") from error
    return tuple(record(asset, line) for line in text.split(NEWLINE) if line)


def record(asset: Asset, line: str) -> Sample:
    """One wire line as a sample for the asset: the line above, for OAHE-INV-001, is Sample("OAHE-INV-001", 10:05 UTC,
    812.0, 78.4, False); a record for another asset raises FeedError("record for OAHE-INV-002, not OAHE-INV-001")."""
    raw = fields(line)
    if raw["asset_id"] != asset.asset_id:
        raise FeedError(f"record for {raw['asset_id']}, not {asset.asset_id}")
    moment = instant(raw["at"])
    if not isinstance(raw["gap"], bool):
        raise FeedError(f"malformed record: gap is {raw['gap']!r}, not true or false")
    values = [value(asset, name, raw[name], raw["gap"]) for name in VALUE_FIELDS]
    if raw["gap"] and values != [None, None]:
        raise FeedError(f"malformed record: a gap at {raw['at']} carries values")
    if raw["gap"]:
        return gap(asset.asset_id, moment)
    return Sample(asset.asset_id, moment, values[0], values[1], False)


def fields(line: str) -> dict:
    """One line as a JSON object with exactly the five wire keys: fields('{"asset_id": …}') is the dict; "{" raises
    FeedError("malformed record: not JSON: {"), '{"asset_id": 1}' FeedError("malformed record: keys ['asset_id']")."""
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as error:
        raise FeedError(f"malformed record: not JSON: {line[:80]}") from error
    if not isinstance(raw, dict):
        raise FeedError(f"malformed record: not an object: {line[:80]}")
    if sorted(raw) != sorted(FIELDS):
        raise FeedError(f"malformed record: keys {sorted(raw)}")
    return raw


def instant(text: object) -> datetime:
    """A wire instant, aware UTC on the grid: instant("2026-06-01T10:05:00+00:00") is 10:05 UTC; "…T10:02:00+00:00"
    raises FeedError("record at …T10:02:00+00:00: 2026-06-01T10:02:00+00:00 is not on the 300 s grid")."""
    # Invariant: SOL-06
    if not isinstance(text, str):
        raise FeedError(f"malformed record: at is {text!r}, not a string")
    try:
        return on_grid(datetime.fromisoformat(text))
    except ValueError as error:
        raise FeedError(f"record at {text}: {error}") from error


def value(asset: Asset, name: str, raw: object, is_gap: bool) -> float | None:
    """One field's value checked against the maintenance list for the asset's kind: value(inverter, "power_kw", 78.4,
    False) is 78.4; 1600 for irradiance_w_m2 raises FeedError("irradiance_w_m2 1600 is out of range for INVERTER");
    None is a gap's value, refused in a reading."""
    # Invariant: SOL-03 (a value out of the list's range is refused, never silently stored)
    if raw is None and is_gap:
        return None
    if isinstance(raw, bool) or not isinstance(raw, int | float) or not math.isfinite(raw):
        raise FeedError(f"malformed record: {name} is {raw!r}, not a number")
    try:
        held = asset_types.in_range(asset.kind, name, raw)
    except asset_types.UnknownField as error:
        raise FeedError(f"record refused: {error}") from error
    if not held:
        raise FeedError(f"{name} {raw} is out of range for {asset.kind.name}")
    return float(raw)


def records(samples: tuple[Sample, ...]) -> str:
    """The wire text for some samples, one JSON object per line, each newline-terminated: records((Sample("OAHE-INV-001",
    10:05 UTC, 812.0, 78.4, False),)) is the record above plus "\\n"; a gap's values are null; records(()) is ""."""
    return "".join(json.dumps(wire(sample)) + NEWLINE for sample in samples)


def wire(sample: Sample) -> dict:
    """One sample as its wire object, keys in FIELDS order: wire(gap("OAHE-INV-001", 10:20 UTC)) is {"asset_id":
    "OAHE-INV-001", "at": "2026-06-01T10:20:00+00:00", "irradiance_w_m2": None, "power_kw": None, "gap": True}."""
    found = (sample.asset_id, sample.moment.isoformat(), sample.irradiance_w_m2, sample.power_kw, sample.gap)
    return dict(zip(FIELDS, found))
