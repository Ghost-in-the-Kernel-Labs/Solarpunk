"""The mailer holds its word: a degradation mail names the asset, its location, the cause and the instant (SOL-06);
nobody to mail is refused; the settings come from a file the caller names and a bad one is refused by key, never
echoed; send delivers to a local fake SMTP server on an ephemeral port, logs in only when the named variable holds a
credential, and that credential appears in no log line, output, exception or table row; the mails table round-trips."""
import base64
import contextlib
import io
import json
import logging
import os
import socket
import socketserver
import sqlite3
import tempfile
import threading
import traceback
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from solarpunk.leaf import store
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import NotUtc, at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.faults import Fault
from solarpunk.mailer import mail as mailer
from solarpunk.mailer import transport
from solarpunk.mailer.mail import Mail, NoEngineer, RemoteFailure
from solarpunk.mailer.transport import BadSettings, MailError, Settings

INV = "OAHE-INV-003"
LOCATION = "Block B, row 4"
SENDER = "ops@example.org"
ENGINEERS = ("ana@example.org", "ben@example.org")
NOW = at(2026, 6, 1, 10, 15)
OPENED = at(2026, 6, 1, 10, 10)
INVERTER = Asset(INV, AssetKind.INVERTER, "OAHE", None, "Inverter 3", 100.0, location=LOCATION)
OUTAGE = Fault(7, INV, "INV-001", OPENED, None)
UNSET_VARIABLE = "SOLARPUNK_TEST_MAILER_UNSET"
CREDENTIAL_VARIABLE = "SOLARPUNK_TEST_MAILER_CREDENTIAL"
GREETING = "220 fake.local ESMTP"
DATA_GO = "354 end with a dot"
DATA_DONE = "250 queued"
UNKNOWN = "502 not implemented"
REPLIES = {
    "EHLO": "250-fake.local\r\n250 AUTH PLAIN",
    "HELO": "250 fake.local",
    "MAIL": "250 OK",
    "RCPT": "250 OK",
    "RSET": "250 OK",
    "NOOP": "250 OK",
    "QUIT": "221 bye",
}
AUTH_OK = "235 accepted"
AUTH_REFUSED = "535 refused"


def dummy_credential() -> str:
    """A dummy credential assembled from fragments, so no key-shaped literal is in source: it is "dummy-…-value"."""
    return "-".join(("dummy", "not", "a", "real", "value"))


class FakeSmtpServer(socketserver.TCPServer):
    """A one-thread SMTP fake on 127.0.0.1 and an ephemeral port: FakeSmtpServer(AUTH_OK).server_address[1] is the
    port; it records every command line and every DATA payload, and answers AUTH with auth_reply."""

    def __init__(self, auth_reply: str) -> None:
        """Binds to 127.0.0.1 port 0: FakeSmtpServer(AUTH_OK).commands is []."""
        self.auth_reply = auth_reply
        self.commands: list[str] = []
        self.data: list[str] = []
        super().__init__(("127.0.0.1", 0), FakeSmtpHandler)


class FakeSmtpHandler(socketserver.StreamRequestHandler):
    """Speaks enough SMTP for one message: 220, EHLO, MAIL, RCPT, DATA (354 … 250), AUTH, QUIT (221)."""

    def say(self, reply: str) -> None:
        """Writes one reply with CRLF: say("250 OK") sends b"250 OK\\r\\n"."""
        self.wfile.write(reply.encode() + b"\r\n")

    def read_data(self) -> str:
        """The DATA payload up to the lone dot line: "Subject: s\\r\\n\\r\\nb\\r\\n.\\r\\n" gives "Subject: s\\r\\n\\r\\nb\\r\\n"."""
        lines = []
        for raw in self.rfile:
            if raw == b".\r\n":
                break
            lines.append(raw.decode())
        return "".join(lines)

    def handle(self) -> None:
        """Answers one session until QUIT or the client closes: EHLO gets REPLIES["EHLO"]; DATA gets 354 then 250."""
        server: FakeSmtpServer = self.server  # type: ignore[assignment]
        self.say(GREETING)
        for raw in self.rfile:
            line = raw.decode().rstrip("\r\n")
            verb = line.split(" ", 1)[0].upper()
            server.commands.append(line)
            if verb == "DATA":
                self.say(DATA_GO)
                server.data.append(self.read_data())
                self.say(DATA_DONE)
            elif verb == "AUTH":
                self.say(server.auth_reply)
            else:
                self.say(REPLIES.get(verb, UNKNOWN))
            if verb == "QUIT":
                return


def settings_for(server: FakeSmtpServer, password_variable: str | None, username: str | None = None) -> Settings:
    """Settings that reach the fake: settings_for(server, None).host is "127.0.0.1", starttls False."""
    return Settings("127.0.0.1", server.server_address[1], SENDER, False, password_variable, username)


def a_mail() -> Mail:
    """The degradation mail for the inverter's outage: a_mail().to is ENGINEERS."""
    return mailer.compose_degradation(INVERTER, OUTAGE, ENGINEERS, NOW)


def fresh() -> sqlite3.Connection:
    """An in-memory store with the mails table: fresh().execute("SELECT count(*) FROM mails").fetchone()[0] is 0."""
    conn = store.connect()
    store.apply(conn, mailer.schema())
    return conn


class WithFakeServer(unittest.TestCase):
    """Starts a fake SMTP server per test on a daemon thread and stops it after."""

    auth_reply = AUTH_OK

    def setUp(self) -> None:
        """A running fake: self.server.commands is [] until a client speaks."""
        self.server = FakeSmtpServer(self.auth_reply)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def verbs(self) -> list[str]:
        """The verbs the fake heard, in order: ["EHLO", "MAIL", "RCPT", "RCPT", "DATA", "QUIT"] for one plain mail."""
        return [line.split(" ", 1)[0].upper() for line in self.server.commands]


class Composing(unittest.TestCase):
    def test_a_fault_mail_names_asset_location_code_meaning_opening_instant_and_chain(self) -> None:
        mail = a_mail()
        self.assertEqual(mail.to, ENGINEERS)
        self.assertEqual(mail.subject, "Solarpunk: OAHE-INV-003 INV-001")
        self.assertEqual(mail.body.split("\n"), [
            "Asset: OAHE-INV-003 (Inverter 3)",
            "Location: Block B, row 4",
            "Cause: fault INV-001, Inverter offline: no AC output while irradiance is above the start threshold,"
            " opened 2026-06-01T10:10:00+00:00",
            "Instant: 2026-06-01T10:15:00+00:00",
            "Engineers: ana@example.org, ben@example.org",
        ])

    def test_a_remote_failure_mail_names_the_test_and_its_reason(self) -> None:
        mail = mailer.compose_degradation(INVERTER, RemoteFailure("reachable", "no answer in 5 s"), ENGINEERS[:1], NOW)
        self.assertEqual(mail.to, ("ana@example.org",))
        self.assertEqual(mail.subject, "Solarpunk: OAHE-INV-003 reachable")
        self.assertEqual(mail.body.split("\n")[2], "Cause: remote test reachable failed: no answer in 5 s")
        self.assertEqual(mail.body.split("\n")[4], "Engineers: ana@example.org")

    def test_an_asset_without_a_location_says_so(self) -> None:
        nowhere = Asset(INV, AssetKind.INVERTER, "OAHE", None, "Inverter 3", 100.0)
        mail = mailer.compose_degradation(nowhere, OUTAGE, ENGINEERS, NOW)
        self.assertEqual(mail.body.split("\n")[1], "Location: location unknown")

    def test_nobody_to_mail_is_refused_naming_the_asset(self) -> None:
        with self.assertRaises(NoEngineer) as caught:
            mailer.compose_degradation(INVERTER, OUTAGE, (), NOW)
        self.assertEqual(str(caught.exception), "OAHE-INV-003: no engineer to mail")
        self.assertTrue(issubclass(NoEngineer, ValueError))

    def test_a_naive_instant_is_refused(self) -> None:
        with self.assertRaises(NotUtc):
            mailer.compose_degradation(INVERTER, OUTAGE, ENGINEERS, datetime(2026, 6, 1, 10, 15))


class TheMailsTable(unittest.TestCase):
    def test_the_table_has_the_settled_columns(self) -> None:
        info = [tuple(row)[1:] for row in fresh().execute("PRAGMA table_info(mails)")]
        self.assertEqual(info, [
            ("mail_id", "INTEGER", 0, None, 1),
            ("sent_at", "TEXT", 1, None, 0),
            ("recipients", "TEXT", 1, None, 0),
            ("subject", "TEXT", 1, None, 0),
            ("body", "TEXT", 1, None, 0),
            ("asset_id", "TEXT", 1, None, 0),
        ])

    def test_record_returns_the_id_and_stores_iso_utc_and_joined_recipients(self) -> None:
        conn = fresh()
        mail = a_mail()
        self.assertEqual(mailer.record(conn, mail, INV, NOW), 1)
        self.assertEqual(mailer.record(conn, mail, INV, NOW), 2)
        row = tuple(conn.execute("SELECT * FROM mails WHERE mail_id = 1").fetchone())
        self.assertEqual(row, (1, "2026-06-01T10:15:00+00:00", "ana@example.org,ben@example.org",
                               mail.subject, mail.body, INV))

    def test_sent_for_round_trips_in_order_and_by_asset(self) -> None:
        conn = fresh()
        first = a_mail()
        second = mailer.compose_degradation(INVERTER, RemoteFailure("reachable", "timeout"), ENGINEERS[:1], NOW)
        mailer.record(conn, first, INV, NOW)
        mailer.record(conn, second, INV, NOW)
        mailer.record(conn, first, "OAHE-INV-004", NOW)
        self.assertEqual(mailer.sent_for(conn, INV), (first, second))
        self.assertEqual(mailer.sent_for(conn, "OAHE-TRK-001"), ())

    def test_a_naive_sent_at_is_refused(self) -> None:
        with self.assertRaises(NotUtc):
            mailer.record(fresh(), a_mail(), INV, datetime(2026, 6, 1, 10, 15))


class LoadingSettings(unittest.TestCase):
    GOOD = {"host": "smtp.example.org", "port": 587, "sender": SENDER, "starttls": True,
            "password_variable": CREDENTIAL_VARIABLE, "username": "ops"}

    def write(self, text: str) -> Path:
        """A settings file in a temporary folder outside the repository: write("{}") is a path whose text is "{}"."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "mail.json"
        path.write_text(text)
        return path

    def test_a_good_file_gives_the_settings(self) -> None:
        settings = transport.load_settings(self.write(json.dumps(self.GOOD)))
        self.assertEqual(settings, Settings("smtp.example.org", 587, SENDER, True, CREDENTIAL_VARIABLE, "ops"))

    def test_null_credential_variable_and_username_are_allowed(self) -> None:
        raw = dict(self.GOOD, password_variable=None, username=None)
        settings = transport.load_settings(self.write(json.dumps(raw)))
        self.assertEqual(settings, Settings("smtp.example.org", 587, SENDER, True, None, None))

    def test_each_missing_key_is_named(self) -> None:
        for key in self.GOOD:
            with self.subTest(key=key):
                raw = {name: value for name, value in self.GOOD.items() if name != key}
                with self.assertRaises(BadSettings) as caught:
                    transport.load_settings(self.write(json.dumps(raw)))
                self.assertEqual(str(caught.exception), f"mail settings lack the key {key!r}")

    def test_a_wrong_type_is_named_without_its_value(self) -> None:
        cases = {"host": (25, "str"), "port": ("587", "int"), "sender": (None, "str"),
                 "starttls": ("yes", "bool"), "password_variable": (1, "str or NoneType"),
                 "username": (False, "str or NoneType")}
        for key, (value, types) in cases.items():
            with self.subTest(key=key):
                with self.assertRaises(BadSettings) as caught:
                    transport.load_settings(self.write(json.dumps(dict(self.GOOD, **{key: value}))))
                self.assertEqual(str(caught.exception), f"mail setting {key!r} is not of type {types}")

    def test_a_boolean_port_is_not_an_int(self) -> None:
        with self.assertRaises(BadSettings):
            transport.load_settings(self.write(json.dumps(dict(self.GOOD, port=True))))

    def test_a_file_that_is_not_a_json_object_is_named_and_not_echoed(self) -> None:
        for text in ("host = secretive-hostname", "[1, 2]"):
            with self.subTest(text=text):
                path = self.write(text)
                with self.assertRaises(BadSettings) as caught:
                    transport.load_settings(path)
                self.assertEqual(str(caught.exception), f"{path}: not a readable JSON object of mail settings")
                self.assertIsNone(caught.exception.__cause__)

    def test_a_missing_file_is_named(self) -> None:
        path = self.write("{}").with_name("absent.json")
        with self.assertRaises(BadSettings) as caught:
            transport.load_settings(path)
        self.assertEqual(str(caught.exception), f"{path}: not a readable JSON object of mail settings")


class TheMessage(unittest.TestCase):
    def test_headers_and_content(self) -> None:
        built = transport.message(Mail(ENGINEERS, "the subject", "line one\nline two"), SENDER)
        self.assertEqual(built["From"], SENDER)
        self.assertEqual(built["To"], "ana@example.org, ben@example.org")
        self.assertEqual(built["Subject"], "the subject")
        self.assertEqual(built.get_content(), "line one\nline two\n")


class SendingToTheFake(WithFakeServer):
    def test_the_mail_arrives_with_its_sender_recipients_subject_and_body(self) -> None:
        mail = a_mail()
        transport.send(mail, settings_for(self.server, None))
        self.assertEqual(self.verbs(), ["EHLO", "MAIL", "RCPT", "RCPT", "DATA", "QUIT"])
        # SMTP verbs are case-insensitive, and smtplib's casing differs between 3.12 ("mail FROM:") and 3.13 ("mail from:").
        self.assertEqual(self.server.commands[1].lower(), "mail from:<ops@example.org>")
        self.assertEqual([c.lower() for c in self.server.commands[2:4]], ["rcpt to:<ana@example.org>", "rcpt to:<ben@example.org>"])
        (data,) = self.server.data
        self.assertIn("Subject: Solarpunk: OAHE-INV-003 INV-001\r\n", data)
        self.assertIn("To: ana@example.org, ben@example.org\r\n", data)
        self.assertIn("From: ops@example.org\r\n", data)
        self.assertIn("\r\nAsset: OAHE-INV-003 (Inverter 3)\r\nLocation: Block B, row 4\r\n", data)

    def test_a_named_variable_that_is_not_set_sends_no_auth(self) -> None:
        with mock.patch.dict(os.environ, {}):
            os.environ.pop(UNSET_VARIABLE, None)
            transport.send(a_mail(), settings_for(self.server, UNSET_VARIABLE, "ops"))
        self.assertNotIn("AUTH", self.verbs())
        self.assertEqual(len(self.server.data), 1)

    def test_a_set_variable_logs_in_as_the_username(self) -> None:
        with mock.patch.dict(os.environ, {CREDENTIAL_VARIABLE: dummy_credential()}):
            transport.send(a_mail(), settings_for(self.server, CREDENTIAL_VARIABLE, "ops"))
        self.assertEqual(self.verbs(), ["EHLO", "AUTH", "MAIL", "RCPT", "RCPT", "DATA", "QUIT"])
        payload = base64.b64decode(self.server.commands[1].split(" ")[2]).decode()
        self.assertEqual(payload, "\0ops\0" + dummy_credential())

    def test_without_a_username_it_logs_in_as_the_sender(self) -> None:
        with mock.patch.dict(os.environ, {CREDENTIAL_VARIABLE: dummy_credential()}):
            transport.send(a_mail(), settings_for(self.server, CREDENTIAL_VARIABLE))
        payload = base64.b64decode(self.server.commands[1].split(" ")[2]).decode()
        self.assertEqual(payload.split("\0")[1], SENDER)

    def test_starttls_the_server_does_not_offer_is_a_mail_error(self) -> None:
        settings = Settings("127.0.0.1", self.server.server_address[1], SENDER, True, None, None)
        with self.assertRaises(MailError):
            transport.send(a_mail(), settings)
        self.assertEqual(self.server.data, [])


class TheCredentialIsNeverShown(WithFakeServer):
    auth_reply = AUTH_REFUSED

    def test_a_refused_login_shows_the_credential_nowhere(self) -> None:
        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        root = logging.getLogger()
        root.addHandler(handler)
        self.addCleanup(root.removeHandler, handler)
        self.addCleanup(root.setLevel, root.level)
        root.setLevel(logging.DEBUG)
        settings = settings_for(self.server, CREDENTIAL_VARIABLE, "ops")
        with mock.patch.dict(os.environ, {CREDENTIAL_VARIABLE: dummy_credential()}), \
                contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            with self.assertRaises(MailError) as caught:
                transport.send(a_mail(), settings)
            logging.getLogger("solarpunk").debug("after the send")
        error = caught.exception
        port = self.server.server_address[1]
        self.assertEqual(str(error), f"mail to 127.0.0.1:{port} was not sent")
        shown = "".join(traceback.format_exception(error)) + repr(error) + captured.getvalue()
        self.assertIn("after the send", shown)
        self.assertNotIn(dummy_credential(), shown)
        conn = fresh()
        mailer.record(conn, a_mail(), INV, NOW)
        rows = " ".join(str(tuple(row)) for row in conn.execute("SELECT * FROM mails"))
        self.assertNotIn(dummy_credential(), rows)


class SendFailures(unittest.TestCase):
    def test_a_refused_connection_is_a_mail_error_naming_host_and_port(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        settings = Settings("127.0.0.1", port, SENDER, False, None, None)
        with self.assertRaises(MailError) as caught:
            transport.send(a_mail(), settings)
        self.assertEqual(str(caught.exception), f"mail to 127.0.0.1:{port} was not sent")
        self.assertIsNone(caught.exception.__cause__)
        self.assertTrue(caught.exception.__suppress_context__)
        self.assertTrue(issubclass(MailError, ValueError))


class TheSmtpCalls(unittest.TestCase):
    def calls(self, starttls: bool) -> list[mock._Call]:
        """The calls send makes on a mocked smtplib client: calls(True)[0] is call.starttls()."""
        settings = Settings("smtp.example.org", 587, SENDER, starttls, None, None)
        with mock.patch.object(transport.smtplib, "SMTP") as factory:
            transport.send(a_mail(), settings)
        factory.assert_called_once_with("smtp.example.org", 587, timeout=10)
        return factory.return_value.__enter__.return_value.method_calls

    def test_starttls_comes_before_the_send_when_asked(self) -> None:
        names = [name for name, _, _ in self.calls(True)]
        self.assertEqual(names, ["starttls", "sendmail"])

    def test_no_starttls_when_not_asked(self) -> None:
        (only,) = self.calls(False)
        name, args, _ = only
        self.assertEqual(name, "sendmail")
        self.assertEqual(args[:2], (SENDER, list(ENGINEERS)))
        self.assertIn("Subject: Solarpunk: OAHE-INV-003 INV-001", args[2])


if __name__ == "__main__":
    unittest.main()
