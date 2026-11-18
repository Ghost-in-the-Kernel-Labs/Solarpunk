"""The receiver: the one inbound surface, where an asset pushes a line `<asset-id> <fault-code>` over TCP. It refuses
first (an asset the fleet lacks, SOL-05; a code the catalogue lacks, SOL-04). A good line is no longer assigned: only an
engineer assigns a fault (SP-015, superseding SP-008 in part), so until 7.4 stores a pushed code as a suggestion for an
engineer, the receiver holds it, storing nothing, and says so. It reaches the fleet and the ledger only through project
(MOD-06, SP-010). One line per connection; the answer is `refused <reason>`, a good line's reason "held for an
engineer: <asset-id> <code> (SP-015)"."""
import argparse
import socketserver
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from solarpunk import project
from solarpunk.leaf.codes import UnknownFaultCode

ENCODING = "utf-8"
DECODE_ERRORS = "replace"
LINE_LIMIT = 256
NEWLINE = "\r\n"
SEPARATOR = " "
OK = "ok {}\n"
REFUSED = "refused {}\n"
HELD = "held for an engineer: {asset_id} {code} (SP-015)"
LISTENING = "receiver: listening on {}:{}\n"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5030
PROG = "python3 -m solarpunk.receiver"


class ReceiverError(ValueError):
    """Raised for a refused line, naming why: ReceiverError("unknown asset OAHE-INV-009")."""


def parse_line(line: str) -> tuple[str, str]:
    """The asset id and code of a line, its trailing newline stripped: parse_line("OAHE-INV-001 INV-001\\n") is
    ("OAHE-INV-001", "INV-001"); parse_line("OAHE-INV-001") raises ReceiverError("malformed line: 'OAHE-INV-001'")."""
    text = line.rstrip(NEWLINE)
    fields = text.split(SEPARATOR)
    if len(fields) != 2:
        raise ReceiverError(f"malformed line: {text!r}")
    return fields[0], fields[1]


def handle(conn: sqlite3.Connection, line: str, now: datetime) -> project.Fault:
    """Checks the line's asset and code through project and holds a good line for an engineer, storing nothing
    (SP-015): handle(conn, "OAHE-INV-001 INV-001", 10:10 UTC) on the OAHE fleet raises ReceiverError("held for an
    engineer: OAHE-INV-001 INV-001 (SP-015)"); "OAHE-INV-009 INV-001" raises ReceiverError("unknown asset
    OAHE-INV-009"), "OAHE-INV-001 INV-999" ReceiverError("unknown code INV-999"). It returns a fault again when 7.4
    makes a pushed code a suggestion; now is when the line arrived, which that suggestion will carry."""
    # Decision: SP-015 (a pushed code is not a fault until an engineer assigns one)
    # Invariant: SOL-04 (no fault of a code the catalogue lacks); SOL-05 (no fault on an asset the fleet lacks)
    asset_id, code = parse_line(line)
    try:
        project.check_fault(conn, asset_id, code)
    except project.UnknownAsset as refused:
        raise ReceiverError(f"unknown asset {asset_id}") from refused
    except UnknownFaultCode as refused:
        raise ReceiverError(f"unknown code {code}") from refused
    raise ReceiverError(HELD.format(asset_id=asset_id, code=code))


def reply(db_path: str | Path, line: str, now: datetime) -> str:
    """The answer to one pushed line, against the store at a path opened for this line alone: reply(db, "OAHE-INV-001
    INV-001\\n", now) on a fresh OAHE store is "refused held for an engineer: OAHE-INV-001 INV-001 (SP-015)\\n" (until
    7.4 makes it a suggestion); reply(db, "OAHE-INV-009 INV-001\\n", now) is
    "refused unknown asset OAHE-INV-009\\n"."""
    with closing(project.open_or_create(db_path)) as conn:
        try:
            fault = handle(conn, line, now)
        except ReceiverError as refused:
            return REFUSED.format(refused)
    return OK.format(fault.fault_id)


class LineHandler(socketserver.StreamRequestHandler):
    """Reads one line of at most LINE_LIMIT bytes from a connection, answers it, and lets the connection close."""

    def handle(self) -> None:
        """One request: the bytes b"OAHE-INV-001 INV-001\\n" on a fresh OAHE store are answered b"ok 1\\n"."""
        line = self.rfile.readline(LINE_LIMIT).decode(ENCODING, DECODE_ERRORS)
        answer = reply(self.server.db_path, line, datetime.now(timezone.utc))
        self.wfile.write(answer.encode(ENCODING))


class Receiver(socketserver.TCPServer):
    """A single-threaded TCP server over one store path: Receiver("fleet.db", "127.0.0.1", 0) listens on a free port;
    each request opens the store in the thread that handles it, since a SQLite connection belongs to one thread."""

    allow_reuse_address = True

    def __init__(self, db_path: str | Path, host: str, port: int) -> None:
        """Binds and listens: Receiver("fleet.db", "127.0.0.1", 0).server_address[1] is the port it was given."""
        self.db_path = db_path
        super().__init__((host, port), LineHandler)


def make_server(db_path: str | Path, host: str, port: int) -> Receiver:
    """A listening receiver over the store at a path; port 0 takes a free port: make_server("fleet.db", "127.0.0.1",
    0).server_address is ("127.0.0.1", <the port>). The caller serves it (handle_request, serve_forever) and closes it."""
    return Receiver(db_path, host, port)


def run(server: Receiver, once: bool) -> int:
    """Serves one connection when once, else until shut down, and returns the bound port: run(server, True) after one
    push returns server.server_address[1]."""
    if once:
        server.handle_request()
    else:
        server.serve_forever()
    return server.server_address[1]


def serve(db_path: str | Path, host: str, port: int, once: bool = False) -> int:
    """Listens on host and port over the store at a path and serves: serve(db, "127.0.0.1", 5030, once=True) answers
    one connection, closes, and returns 5030; without once it serves until the process ends."""
    with make_server(db_path, host, port) as server:
        return run(server, once)


def parser() -> argparse.ArgumentParser:
    """The command line: parser().parse_args(["--db", "fleet.db"]) has host "127.0.0.1", port 5030 and once False."""
    parsed = argparse.ArgumentParser(prog=PROG)
    parsed.add_argument("--db", required=True)
    parsed.add_argument("--host", default=DEFAULT_HOST)
    parsed.add_argument("--port", type=int, default=DEFAULT_PORT)
    parsed.add_argument("--once", action="store_true")
    return parsed


def main(argv: list[str], out: TextIO) -> int:
    """Runs the receiver: main(["--db", "fleet.db", "--port", "0", "--once"], out) writes "receiver: listening on
    127.0.0.1:<port>" to out, answers one connection, and returns 0."""
    args = parser().parse_args(argv)
    with make_server(args.db, args.host, args.port) as server:
        host, port = server.server_address
        out.write(LISTENING.format(host, port))
        out.flush()
        run(server, args.once)
    return 0
