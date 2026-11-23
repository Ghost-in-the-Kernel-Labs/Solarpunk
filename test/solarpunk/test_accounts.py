"""SOL-16 held headless (12.1, SP-026, SP-028): the worked example run literally over the demo fleet, the password
check, the viewer refused at every write project exposes, and the site scope on every reading. Every password here is
assembled at runtime from fragments, so no secret-shaped literal is in source, and none is ever printed."""
import importlib.util
import sqlite3
import unittest

from solarpunk import project
from solarpunk.accounts import passwords
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind
from solarpunk.project import (
    ALL_SITES,
    AccountError,
    NotPermitted,
    Role,
    TicketStatus,
    WeakPassword,
)
from test.support import ROOT
from test.solarpunk.old_store import old_suggestion

SITE, AUDITOR, CREW = "site@oahe.example", "auditor@oahe.example", "crew@bigs.example"
CREATED = at(2026, 6, 1, 10)
OPENED = at(2026, 6, 1, 11, 30)
ACKNOWLEDGED = at(2026, 6, 1, 11, 40)
BIGS = (
    Asset("BIGS-SIT-001", AssetKind.SITE, "BIGS", None, "Big Stone", None),
    Asset("BIGS-INV-001", AssetKind.INVERTER, "BIGS", "BIGS-SIT-001", "Inverter 1", 50.0),
)


def passphrase() -> str:
    """A test password of 22 characters, built from fragments at runtime: never a literal, never printed."""
    return "-".join(("tern", "lupin", "basalt", "kelp"))


def other_passphrase() -> str:
    """A second test password, built the same way, that is not passphrase()."""
    return "-".join(("heron", "sorrel", "granite", "moss"))


def short_passphrase() -> str:
    """A password of 11 characters, one under the rule's 12."""
    return "-".join(("tern", "kelp", "m"))


def section() -> str:
    """SOL-16's text, to the end of the contract or the next section, its spacing made single."""
    contract = (ROOT / "docs" / "CONTRACT.md").read_text(encoding="utf-8")
    start = contract.index("## SOL-16")
    following = contract.find("\n## ", start + 1)
    return " ".join((contract[start:] if following < 0 else contract[start:following]).split())


def example_store() -> sqlite3.Connection:
    """SOL-16's example: the demo fleet, its three accounts, an open INV-001 on OAHE-INV-002 with its ticket (work
    order 1) assigned by site@oahe.example, and a pushed SEN-001 suggestion on OAHE-SEN-001."""
    conn = project.open_store()
    project.load_fleet(conn, project.demo_fleet())
    project.create_account(conn, SITE, "Site engineer", Role.ENGINEER, passphrase(), ("OAHE",), CREATED)
    project.create_account(conn, AUDITOR, "Auditor", Role.VIEWER, passphrase(), (ALL_SITES,), CREATED)
    project.create_account(conn, CREW, "BIGS crew", Role.ENGINEER, passphrase(), ("BIGS",), CREATED)
    project.assign_fault(conn, "OAHE-INV-002", "INV-001", OPENED, SITE)
    old_suggestion(conn, "OAHE-SEN-001", "SEN-001", OPENED)
    return conn


class Store(unittest.TestCase):
    def setUp(self) -> None:
        """SOL-16's example store, closed after each test."""
        self.conn = example_store()
        self.addCleanup(self.conn.close)

    def account(self, email: str) -> project.Account:
        """The stored account of an email."""
        return project.account_of(self.conn, email)

    def ticket_id(self) -> int:
        """The one open ticket's work order: OAHE-INV-002's."""
        (ticket,) = project.open_tickets(self.conn)
        self.assertEqual(ticket.asset_id, "OAHE-INV-002")
        return ticket.wo_id


class TheWorkedExample(Store):
    def test_site_acknowledges_the_ticket(self) -> None:
        moved = project.move_ticket_as(self.conn, self.account(SITE), self.ticket_id(), TicketStatus.ACKNOWLEDGED,
                                       ACKNOWLEDGED)
        self.assertEqual((moved.status, moved.acknowledged), (TicketStatus.ACKNOWLEDGED, ACKNOWLEDGED))

    def test_the_auditor_lists_the_fleet(self) -> None:
        self.assertEqual(len(project.fleet_for(self.conn, self.account(AUDITOR))), 11)

    def test_the_auditor_is_refused_by_name(self) -> None:
        with self.assertRaises(NotPermitted) as caught:
            project.move_ticket_as(self.conn, self.account(AUDITOR), self.ticket_id(), TicketStatus.ACKNOWLEDGED,
                                   ACKNOWLEDGED)
        self.assertEqual(str(caught.exception), "auditor@oahe.example is a viewer and acts on nothing")
        self.assertEqual(project.ticket_of(self.conn, self.ticket_id()).status, TicketStatus.OPEN)

    def test_the_crew_lists_nothing(self) -> None:
        self.assertEqual(len(project.fleet_for(self.conn, self.account(CREW))), 0)

    def test_the_crew_is_refused_by_site(self) -> None:
        with self.assertRaises(NotPermitted) as caught:
            project.move_ticket_as(self.conn, self.account(CREW), self.ticket_id(), TicketStatus.ACKNOWLEDGED,
                                   ACKNOWLEDGED)
        self.assertEqual(str(caught.exception), "crew@bigs.example may not act on site OAHE")
        self.assertEqual(project.ticket_of(self.conn, self.ticket_id()).status, TicketStatus.OPEN)

    def test_the_unaccounted_engineer_is_flagged(self) -> None:
        self.assertEqual(project.unaccounted_engineers(self.conn), ("inverter@oahe.example",))

    def test_each_line_is_in_the_contract(self) -> None:
        text = section()
        for line in (
            "site@oahe.example acknowledges OAHE-INV-002's ticket allowed",
            "auditor@oahe.example lists the fleet 11 assets",
            'auditor@oahe.example acknowledges it refused: "auditor@oahe.example is a viewer and acts on nothing"',
            "crew@bigs.example lists the fleet 0 assets",
            'crew@bigs.example acknowledges it refused: "crew@bigs.example may not act on site OAHE"',
            "the fleet's engineers with no engineer account inverter@oahe.example",
            "scrypt$16384$8$1$<salt as hex>$<hash as hex>",
        ):
            with self.subTest(line=line):
                self.assertIn(line, text)


class TheUnaccountedQuery(Store):
    def test_a_viewer_or_stopped_engineer_does_not_account_for_an_address(self) -> None:
        project.create_account(self.conn, "inverter@oahe.example", "Inverter", Role.VIEWER, passphrase(), ("OAHE",),
                               CREATED)
        self.conn.execute("UPDATE accounts SET active = 0 WHERE email = ?", (SITE,))
        self.assertEqual(project.unaccounted_engineers(self.conn), ("inverter@oahe.example", SITE))

    def test_every_address_accounted_gives_none(self) -> None:
        project.create_account(self.conn, "inverter@oahe.example", "Inverter", Role.ENGINEER, passphrase(), ("OAHE",),
                               CREATED)
        self.assertEqual(project.unaccounted_engineers(self.conn), ())


class ThePasswords(Store):
    def stored(self, email: str) -> str:
        """An account's stored line, read straight from the table and never shown."""
        return self.conn.execute("SELECT secret FROM accounts WHERE email = ?", (email,)).fetchone()[0]

    def test_the_stored_line_carries_its_parameters(self) -> None:
        parts = self.stored(SITE).split("$")
        self.assertEqual(parts[:4], ["scrypt", str(passwords.SCRYPT_COST), "8", "1"])
        self.assertEqual((len(bytes.fromhex(parts[4])), len(bytes.fromhex(parts[5]))), (16, 32))
        self.assertNotIn(passphrase(), self.stored(SITE))

    def test_two_lines_for_one_password_differ(self) -> None:
        self.assertNotEqual(self.stored(SITE), self.stored(AUDITOR))

    def test_the_right_password_gives_the_account(self) -> None:
        self.assertEqual(project.check_password(self.conn, SITE, passphrase()), self.account(SITE))

    def test_a_wrong_password_an_unknown_email_and_a_stopped_account_give_none(self) -> None:
        self.conn.execute("UPDATE accounts SET active = 0 WHERE email = ?", (CREW,))
        for email, password in ((SITE, other_passphrase()), ("nobody@oahe.example", passphrase()),
                                (CREW, passphrase())):
            with self.subTest(email=email):
                self.assertIsNone(project.check_password(self.conn, email, password))

    def test_a_weak_password_is_refused_without_its_value(self) -> None:
        self.assertEqual(len(short_passphrase()), 11)
        with self.assertRaises(WeakPassword) as caught:
            project.create_account(self.conn, "new@oahe.example", "New", Role.OPERATOR, short_passphrase(), ("OAHE",),
                                   CREATED)
        self.assertEqual(str(caught.exception), "a password is at least 12 characters")
        self.assertEqual(len(project.accounts(self.conn)), 3)

    def test_an_account_shows_no_password_or_hash(self) -> None:
        shown = repr(project.accounts(self.conn))
        self.assertNotIn(passphrase(), shown)
        self.assertNotIn("scrypt", shown)

    def test_no_secret_shaped_literal_is_in_source(self) -> None:
        spec = importlib.util.spec_from_file_location("secret_scan", ROOT / "scripts" / "checks" / "secrets.py")
        scan = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scan)
        for path in (ROOT / "test" / "solarpunk" / "test_accounts.py", ROOT / "solarpunk" / "project" / "access.py",
                     *sorted((ROOT / "solarpunk" / "accounts").glob("*.py"))):
            with self.subTest(path=path.name):
                self.assertEqual(scan.scan_text(path.read_text(encoding="utf-8"), path.name), [])


class TheTable(Store):
    def test_a_duplicate_email_is_refused(self) -> None:
        with self.assertRaises(AccountError) as caught:
            project.create_account(self.conn, SITE, "Again", Role.OPERATOR, other_passphrase(), ("OAHE",), CREATED)
        self.assertEqual(str(caught.exception), "site@oahe.example already has an account")
        self.assertEqual(self.account(SITE).role, Role.ENGINEER)

    def test_an_admins_scope_is_always_all(self) -> None:
        admin = project.create_account(self.conn, "admin@oahe.example", "Admin", Role.ADMIN, passphrase(), ("BIGS",),
                                       CREATED)
        self.assertEqual(admin.sites, (ALL_SITES,))
        self.assertTrue(admin.sees("OAHE") and admin.sees("BIGS"))

    def test_the_accounts_list_by_email(self) -> None:
        self.assertEqual([a.email for a in project.accounts(self.conn)], [AUDITOR, CREW, SITE])

    def test_an_unknown_email_has_no_account(self) -> None:
        with self.assertRaises(AccountError):
            project.account_of(self.conn, "nobody@oahe.example")


class TheViewer(Store):
    def test_every_write_is_refused_by_name(self) -> None:
        auditor = self.account(AUDITOR)
        (fault,) = project.open_faults_for(self.conn, auditor)
        writes = {
            "asset": lambda: project.permit_asset(auditor, "OAHE-INV-002"),
            "fault": lambda: project.permit_fault(self.conn, auditor, fault.fault_id),
            "ticket": lambda: project.permit_ticket(self.conn, auditor, self.ticket_id()),
            "move": lambda: project.move_ticket_as(self.conn, auditor, self.ticket_id(), TicketStatus.ACKNOWLEDGED,
                                                   ACKNOWLEDGED),
        }
        for name, write in writes.items():
            with self.subTest(write=name):
                with self.assertRaises(NotPermitted) as caught:
                    write()
                self.assertEqual(str(caught.exception), "auditor@oahe.example is a viewer and acts on nothing")

    def test_it_reads_everything_its_sites_hold(self) -> None:
        auditor = self.account(AUDITOR)
        self.assertEqual(len(project.asset_rows_for(self.conn, auditor)), 11)
        self.assertEqual(len(project.open_faults_for(self.conn, auditor)), 1)
        self.assertEqual(len(project.open_tickets_for(self.conn, auditor)), 1)

    def test_a_stopped_engineer_acts_on_nothing(self) -> None:
        self.conn.execute("UPDATE accounts SET active = 0 WHERE email = ?", (SITE,))
        with self.assertRaises(NotPermitted) as caught:
            project.permit_asset(self.account(SITE), "OAHE-INV-002")
        self.assertEqual(str(caught.exception), "site@oahe.example is not active and acts on nothing")


class TheSiteScope(Store):
    def setUp(self) -> None:
        """The example store with BIGS loaded too, an open INV-001 and a pushed suggestion on BIGS-INV-001."""
        super().setUp()
        project.load_fleet(self.conn, BIGS)
        project.assign_fault(self.conn, "BIGS-INV-001", "INV-001", OPENED, CREW)  # SP-035: BIGS's engineer account
        old_suggestion(self.conn, "BIGS-INV-001", "INV-001", OPENED)

    def sites(self, records: tuple) -> set[str]:
        """The sites of the assets a listing names: {"OAHE"} for OAHE's eleven."""
        return {record.asset_id.split("-")[0] for record in records}

    def test_each_reading_holds_the_scope(self) -> None:
        readings = (project.fleet_for, project.asset_rows_for, project.open_faults_for,
                    project.open_tickets_for)
        for reading in readings:
            for email, sites in ((SITE, {"OAHE"}), (CREW, {"BIGS"}), (AUDITOR, {"OAHE", "BIGS"})):
                with self.subTest(reading=reading.__name__, email=email):
                    self.assertEqual(self.sites(reading(self.conn, self.account(email))), sites)

    def test_a_record_of_another_site_is_not_written(self) -> None:
        crew = self.account(CREW)
        (oahe_fault,) = project.open_faults_for(self.conn, self.account(SITE))
        (oahe_ticket,) = project.open_tickets_for(self.conn, self.account(SITE))
        writes = {
            "fault": lambda: project.permit_fault(self.conn, crew, oahe_fault.fault_id),
            "ticket": lambda: project.permit_ticket(self.conn, crew, oahe_ticket.wo_id),
        }
        for name, write in writes.items():
            with self.subTest(write=name):
                with self.assertRaises(NotPermitted) as caught:
                    write()
                self.assertEqual(str(caught.exception), "crew@bigs.example may not act on site OAHE")

    def test_its_own_site_is_written(self) -> None:
        bigs_ticket = next(t for t in project.open_tickets(self.conn) if t.asset_id == "BIGS-INV-001")
        moved = project.move_ticket_as(self.conn, self.account(CREW), bigs_ticket.wo_id, TicketStatus.ACKNOWLEDGED,
                                       ACKNOWLEDGED)
        self.assertEqual(moved.status, TicketStatus.ACKNOWLEDGED)


if __name__ == "__main__":
    unittest.main()
