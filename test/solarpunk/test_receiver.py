"""The receiver (lane 2.4): an asset pushes `<asset-id> <fault-code>` over TCP; the receiver, started on an ephemeral
port in a thread, answers a good line `ok <fault_id>` with the fault in the ledger and the asset RED, and refuses an
unknown asset (SOL-05), an unknown code (SOL-04), a malformed line and a second open fault, each with its exact reply."""
import io
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import closing
from pathlib import Path

from solarpunk import project
from solarpunk import receiver
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetStatus
from solarpunk.receiver import server

ROOT = Path(__file__).resolve().parents[2]
HOST = "127.0.0.1"
INV1 = "OAHE-INV-001"
NOW = at(2026, 6, 1, 10, 10)
# SP-046: a good push raises a fault itself, assigned by the device (it was a suggestion under SP-015, 7.4).
OK_1 = "ok fault 1\n"
OK_2 = "ok fault 2\n"
WAIT = 10.0


def push(port: int, payload: bytes) -> str:
    """Sends bytes to the receiver on a port and returns its whole answer: push(port, b"OAHE-INV-001 INV-001\\n") on
    a fresh OAHE store is OK_1 (SP-046: a fault from the device)."""
    with socket.create_connection((HOST, port), timeout=WAIT) as sock:
        sock.sendall(payload)
        sock.shutdown(socket.SHUT_WR)
        chunks = []
        while chunk := sock.recv(1024):
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8")


def free_port() -> int:
    """A port the system reports free at this moment: free_port() is an int from 1 to 65535."""
    with socket.socket() as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


class Receiving(unittest.TestCase):
    """A test case with a file store holding the OAHE fleet, removed when it ends."""

    def setUp(self) -> None:
        """A temporary directory with fleet.db holding the eleven OAHE assets and no faults."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "fleet.db")
        with closing(project.open_or_create(self.db)) as conn:
            project.load_fleet(conn, project.demo_fleet())

    def store(self) -> sqlite3.Connection:
        """A fresh connection to the test's store, closed when the test ends: self.store() sees every committed fault."""
        conn = project.open_or_create(self.db)
        self.addCleanup(conn.close)
        return conn

    def served(self, payload: bytes) -> str:
        """Pushes bytes to a receiver on an ephemeral port that serves exactly that one connection in a thread, and
        returns the answer: self.served(b"OAHE-INV-001 INV-001\\n") is OK_1 (SP-046: a fault from the device)."""
        with server.make_server(self.db, HOST, 0) as listening:
            worker = threading.Thread(daemon=True, target=listening.handle_request)
            worker.start()
            answer = push(listening.server_address[1], payload)
            worker.join(WAIT)
        return answer


class Handle(Receiving):
    """handle and parse_line, called directly with a fixed instant."""

    def test_a_good_line_is_a_fault_assigned_by_the_device(self) -> None:
        conn = self.store()
        found = receiver.handle(conn, "OAHE-INV-001 INV-001\n", NOW)
        self.assertEqual((found.fault_id, found.asset_id, found.code, found.assigned_by, found.opened, found.closed),
                         (1, INV1, "INV-001", "device", NOW, None))
        self.assertEqual(project.faults_listing(conn, False), (found,))
        self.assertEqual(project.open_suggestions(conn, INV1), ())  # nothing is suggested since 7.7
        self.assertIs(project.asset_status(conn, INV1), AssetStatus.RED)  # INV-001 is an outage

    def test_carriage_return_is_stripped(self) -> None:
        self.assertEqual(receiver.parse_line("OAHE-INV-001 INV-001\r\n"), (INV1, "INV-001"))

    def test_only_trailing_newline_characters_are_stripped(self) -> None:
        self.assertEqual(receiver.parse_line("OAHE-INV-001 INV-00X\n"), (INV1, "INV-00X"))

    def test_refusals_name_their_reason_and_store_nothing(self) -> None:
        conn = self.store()
        cases = (
            ("OAHE-INV-009 INV-001", "unknown asset OAHE-INV-009"),
            ("OAHE-INV-001 INV-999", "unknown code INV-999"),
            ("OAHE-INV-009 INV-999", "unknown asset OAHE-INV-009"),
            ("oahe-inv-001 INV-001", "unknown asset oahe-inv-001"),
            ("OAHE-INV-001", "malformed line: 'OAHE-INV-001'"),
            ("OAHE-INV-001 INV-001 extra", "malformed line: 'OAHE-INV-001 INV-001 extra'"),
            ("OAHE-INV-001  INV-001", "malformed line: 'OAHE-INV-001  INV-001'"),
            ("", "malformed line: ''"),
            ("OAHE-INV-001 INV-001 ", "malformed line: 'OAHE-INV-001 INV-001 '"),
        )
        for line, reason in cases:
            with self.subTest(line=line):
                with self.assertRaises(receiver.ReceiverError) as raised:
                    receiver.handle(conn, line + "\n", NOW)
                self.assertEqual(str(raised.exception), reason)
        self.assertEqual(project.faults_listing(conn, False), ())

    def test_the_same_good_line_twice_is_one_open_fault(self) -> None:
        conn = self.store()
        first = receiver.handle(conn, "OAHE-INV-001 INV-001", NOW)
        self.assertEqual(receiver.handle(conn, "OAHE-INV-001 INV-001", NOW).fault_id, first.fault_id)
        self.assertEqual(len(project.faults_listing(conn, True)), 1)

    def test_refusal_keeps_its_cause(self) -> None:
        conn = self.store()
        with self.assertRaises(receiver.ReceiverError) as raised:
            receiver.handle(conn, "OAHE-INV-009 INV-001", NOW)
        self.assertIsInstance(raised.exception.__cause__, project.UnknownAsset)

    def test_reply_lines(self) -> None:
        self.assertEqual(receiver.reply(self.db, "OAHE-INV-001 INV-001\n", NOW), OK_1)
        self.assertEqual(receiver.reply(self.db, "OAHE-INV-001 INV-999\n", NOW), "refused unknown code INV-999\n")


class Serving(Receiving):
    """The TCP receiver on an ephemeral port, pushed with a plain socket."""

    def test_good_line_then_refusals(self) -> None:
        self.assertEqual(self.served(b"OAHE-INV-001 INV-001\n"), OK_1)
        self.assertEqual(self.served(b"OAHE-INV-009 INV-001\n"), "refused unknown asset OAHE-INV-009\n")
        self.assertEqual(self.served(b"OAHE-INV-001 INV-999\n"), "refused unknown code INV-999\n")
        self.assertEqual(self.served(b"OAHE-INV-001\n"), "refused malformed line: 'OAHE-INV-001'\n")
        conn = self.store()
        self.assertEqual([f.asset_id for f in project.faults_listing(conn, False)], [INV1])  # SP-046: a fault, by the device
        self.assertIs(project.asset_status(conn, INV1), AssetStatus.RED)
        self.assertIs(project.asset_status(conn, "OAHE-INV-002"), AssetStatus.GREEN)

    def test_a_line_is_read_up_to_its_limit(self) -> None:
        answer = self.served(b"A" * 300)
        self.assertEqual(answer, "refused malformed line: '" + "A" * 256 + "'\n")

    def test_bytes_that_are_not_utf8_are_refused_not_dropped(self) -> None:
        answer = self.served(b"\xff\xfe INV-001\n")
        self.assertEqual(answer, "refused unknown asset ��\n")

    def test_serve_once_answers_one_connection_and_returns_its_port(self) -> None:
        port = free_port()
        found: list[int] = []
        worker = threading.Thread(daemon=True, target=lambda: found.append(receiver.serve(self.db, HOST, port, once=True)))
        worker.start()
        self.assertEqual(self.pushed_when_up(port, b"OAHE-INV-001 INV-001\n"), OK_1)
        worker.join(WAIT)
        self.assertEqual(found, [port])

    def test_serve_by_default_keeps_serving(self) -> None:
        port = free_port()
        threading.Thread(daemon=True, target=receiver.serve, args=(self.db, HOST, port)).start()
        self.assertEqual(self.pushed_when_up(port, b"OAHE-INV-001 INV-001\n"), OK_1)
        self.assertEqual(push(port, b"OAHE-INV-002 INV-001\n"), OK_2)

    def test_run_serves_until_shut_down(self) -> None:
        with server.make_server(self.db, HOST, 0) as listening:
            found: list[int] = []
            worker = threading.Thread(daemon=True, target=lambda: found.append(server.run(listening, False)))
            worker.start()
            port = listening.server_address[1]
            self.assertEqual(push(port, b"OAHE-INV-001 INV-001\n"), OK_1)
            self.assertEqual(push(port, b"OAHE-INV-002 INV-001\n"), OK_2)
            listening.shutdown()
            worker.join(WAIT)
        self.assertEqual(found, [port])

    def test_receiver_allows_address_reuse(self) -> None:
        self.assertIs(server.Receiver.allow_reuse_address, True)

    def pushed_when_up(self, port: int, payload: bytes) -> str:
        """Pushes once the receiver on a port accepts connections, retrying a refused connect for up to WAIT seconds:
        self.pushed_when_up(port, b"OAHE-INV-001 INV-001\\n") is OK_1 (SP-046: a fault from the device)."""
        deadline = time.monotonic() + WAIT
        while True:
            try:
                return push(port, payload)
            except ConnectionRefusedError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.02)


class Command(Receiving):
    """The command line: parser defaults, main in a thread, and python3 -m solarpunk.receiver as a subprocess."""

    def test_parser_defaults(self) -> None:
        args = server.parser().parse_args(["--db", "fleet.db"])
        self.assertEqual((args.db, args.host, args.port, args.once), ("fleet.db", "127.0.0.1", 5030, False))

    def test_parser_names_the_command(self) -> None:
        self.assertTrue(server.parser().format_usage().startswith("usage: python3 -m solarpunk.receiver "))

    def test_parser_requires_db(self) -> None:
        with self.assertRaises(SystemExit):
            server.parser().parse_args([])

    def test_parser_reads_every_option(self) -> None:
        args = server.parser().parse_args(["--db", "x.db", "--host", "0.0.0.0", "--port", "6000", "--once"])
        self.assertEqual((args.db, args.host, args.port, args.once), ("x.db", "0.0.0.0", 6000, True))

    def test_main_announces_and_serves_once(self) -> None:
        out = io.StringIO()
        found: list[int] = []
        argv = ["--db", self.db, "--host", HOST, "--port", "0", "--once"]
        worker = threading.Thread(daemon=True, target=lambda: found.append(receiver.main(argv, out)))
        worker.start()
        deadline = time.monotonic() + WAIT
        while not out.getvalue() and time.monotonic() < deadline:
            time.sleep(0.02)
        announced = out.getvalue()
        self.assertRegex(announced, r"^receiver: listening on 127\.0\.0\.1:\d+\n$")
        port = int(announced.strip().rsplit(":", 1)[1])
        self.assertEqual(push(port, b"OAHE-INV-001 INV-001\n"), OK_1)
        worker.join(WAIT)
        self.assertEqual(found, [0])

    def test_module_runs_as_a_command(self) -> None:
        argv = [sys.executable, "-m", "solarpunk.receiver", "--db", self.db, "--port", "0", "--once"]
        with subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, text=True, env=dict(os.environ)) as child:
            announced = child.stdout.readline()
            port = int(announced.strip().rsplit(":", 1)[1])
            self.assertEqual(push(port, b"OAHE-INV-001 INV-001\n"), OK_1)
            self.assertEqual(child.wait(WAIT), 0)
        self.assertTrue(announced.startswith("receiver: listening on 127.0.0.1:"))


if __name__ == "__main__":
    unittest.main()
