"""Attribution from the account (12.4, SOL-16, SP-015, SP-022, SP-032): in a store with an active account, assigning a
fault, accepting or dismissing a suggestion and every ticket act are the account signed in: an engineer acts as
themself, an operator on a named engineer's word (recorded as entered by the operator), an admin and a viewer assign
and decide nothing and work no ticket, each refused by name and writing nothing. A store with no account works as
before, --by and all. With accounts, an operator's decision records the operator on the suggestion too, and an address
the fleet names is no engineer without an engineer account (SP-035). The store with accounts is made once (four scrypt hashes) and copied for each test; every
password is built at runtime (test_accounts.passphrase)."""
import io
import sqlite3
import tempfile
import unittest
from collections.abc import Callable
from functools import cache
from pathlib import Path
from unittest import mock

from solarpunk import project
from solarpunk.cli import signin
from solarpunk.cli.main import main
from solarpunk.leaf.accounts import ALL_SITES, Account
from solarpunk.project import NotPermitted, Role, TicketStatus
from solarpunk.project import access, attribution
from solarpunk.remote import suggestions as suggestion_table
from solarpunk.ui import cells
from test.solarpunk.test_accounts import CREATED, CREW, SITE, passphrase, section

OPS, ADMIN, AUDITOR = "ops@oahe.example", "admin@oahe.example", "auditor@oahe.example"
INVERTER = "inverter@oahe.example"  # the fleet names it; it has no account
ASSET = "OAHE-INV-001"
OPENED = CREATED.replace(hour=11)
LATER = CREATED.replace(hour=12)
AT = "2026-06-01T11:00:00+00:00"


@cache
def template() -> sqlite3.Connection:
    """The demo fleet with an admin, site@oahe.example an engineer of OAHE, ops@oahe.example an operator of OAHE and
    crew@bigs.example an engineer of BIGS: made once, copied by stored()."""
    conn = project.open_store()
    project.load_fleet(conn, project.demo_fleet())
    project.first_admin(conn, ADMIN, "Admin", passphrase(), CREATED)
    for email, role, site in ((SITE, Role.ENGINEER, "OAHE"), (OPS, Role.OPERATOR, "OAHE"), (CREW, Role.ENGINEER, "BIGS")):
        project.create_account(conn, email, email.split("@")[0], role, passphrase(), (site,), CREATED)
    return conn


def stored(target: sqlite3.Connection) -> sqlite3.Connection:
    """The template copied into target, which is returned."""
    template().backup(target)
    return target


def held(email: str, role: Role, sites: tuple[str, ...] = ("OAHE",)) -> Account:
    """An account in memory, as signing in would give it: held(SITE, Role.ENGINEER) is the site engineer."""
    return Account(email, email.split("@")[0], role, True, CREATED, sites)


ENGINEER, OPERATOR = held(SITE, Role.ENGINEER), held(OPS, Role.OPERATOR)


class WithAccounts(unittest.TestCase):
    def setUp(self) -> None:
        """A copy of the store with accounts, in memory."""
        self.conn = stored(project.open_store())
        self.addCleanup(self.conn.close)

    def refused(self, act: Callable[[], object], words: str) -> None:
        """Asserts act raises NotPermitted with words, opening no fault and no ticket."""
        with self.assertRaises(NotPermitted) as caught:
            act()
        self.assertEqual(str(caught.exception), words)
        self.assertEqual((project.faults_listing(self.conn, False), project.open_tickets(self.conn)), ((), ()))

    def test_an_engineer_assigns_as_themself(self) -> None:
        fault = project.assign_fault_as(self.conn, ENGINEER, ASSET, "INV-001", OPENED)
        self.assertEqual((fault.assigned_by, fault.recorded_by), (SITE, None))
        self.assertEqual(project.open_tickets(self.conn)[0].asset_id, ASSET)

    def test_an_operator_enters_on_a_named_engineers_word(self) -> None:
        fault = project.assign_fault_as(self.conn, OPERATOR, ASSET, "INV-001", OPENED, for_engineer=SITE)
        self.assertEqual((fault.assigned_by, fault.recorded_by), (SITE, OPS))

    def test_the_engineer_an_operator_names_is_an_active_engineer_of_the_site(self) -> None:
        cases = {None: "ops@oahe.example is an operator: name the engineer whose word this is",
                 CREW: "crew@bigs.example is not an active engineer of site OAHE",
                 INVERTER: "inverter@oahe.example is not an active engineer of site OAHE",
                 OPS: "ops@oahe.example is not an active engineer of site OAHE"}
        for named, words in cases.items():
            with self.subTest(named=named):
                self.refused(lambda named=named: project.assign_fault_as(self.conn, OPERATOR, ASSET, "INV-001", OPENED,
                                                                         for_engineer=named), words)
        self.assertEqual(project.word_engineers(self.conn, ASSET), (SITE,))

    def test_an_address_chosen_is_not_taken_with_accounts(self) -> None:
        self.refused(lambda: project.assign_fault_as(self.conn, ENGINEER, ASSET, "INV-001", OPENED, by=INVERTER),
                     attribution.ACCOUNT_ACTS)
        self.refused(lambda: project.assign_fault_as(self.conn, ENGINEER, ASSET, "INV-001", OPENED, for_engineer=SITE),
                     "site@oahe.example is an engineer and acts as themself; --for is an operator's")
        self.refused(lambda: project.assign_fault_as(self.conn, None, ASSET, "INV-001", OPENED, by=SITE),
                     access.SIGN_IN_FIRST)

    def test_an_admin_a_viewer_and_another_sites_engineer_assign_nothing(self) -> None:
        cases = {held(ADMIN, Role.ADMIN, (ALL_SITES,)): "admin@oahe.example is an admin and assigns no fault",
                 held(AUDITOR, Role.VIEWER, (ALL_SITES,)): "auditor@oahe.example is a viewer and acts on nothing",
                 held(CREW, Role.ENGINEER, ("BIGS",)): "crew@bigs.example may not act on site OAHE"}
        for account, words in cases.items():
            with self.subTest(account=account.email):
                self.refused(lambda account=account: project.assign_fault_as(self.conn, account, ASSET, "INV-001",
                                                                             OPENED), words)

    def test_suggestions_are_decided_as_the_account(self) -> None:
        first = project.suggest_pushed(self.conn, ASSET, "INV-001", OPENED)
        admin = held(ADMIN, Role.ADMIN, (ALL_SITES,))
        self.refused(lambda: project.accept_suggestion_as(self.conn, admin, first.suggestion_id),
                     "admin@oahe.example is an admin and decides no suggestion")
        fault = project.accept_suggestion_as(self.conn, OPERATOR, first.suggestion_id, for_engineer=SITE)
        self.assertEqual((fault.assigned_by, fault.recorded_by), (SITE, OPS))
        second = project.suggest_pushed(self.conn, "OAHE-INV-002", "INV-001", OPENED)
        dismissed = project.dismiss_suggestion_as(self.conn, ENGINEER, second.suggestion_id, "reset remotely")
        self.assertEqual((dismissed.state, dismissed.decided_by), ("dismissed", SITE))

    def test_a_ticket_is_worked_by_an_engineer_or_an_operator_as_their_own(self) -> None:
        project.assign_fault_as(self.conn, ENGINEER, ASSET, "INV-001", OPENED)
        wo_id = project.open_tickets(self.conn)[0].wo_id
        admin = held(ADMIN, Role.ADMIN, (ALL_SITES,))
        for act in (lambda: project.move_ticket_as(self.conn, admin, wo_id, TicketStatus.ACKNOWLEDGED, OPENED),
                    lambda: project.comment_on_ticket_as(self.conn, admin, wo_id, OPENED, "x"),
                    lambda: project.resolve_ticket_as(self.conn, admin, wo_id, "x", "RC-COMPONENT", OPENED)):
            with self.assertRaises(NotPermitted) as caught:
                act()
            self.assertEqual(str(caught.exception), "admin@oahe.example is an admin and works no ticket")
        self.assertEqual(project.move_ticket_as(self.conn, OPERATOR, wo_id, TicketStatus.ACKNOWLEDGED, OPENED).status,
                         TicketStatus.ACKNOWLEDGED)
        self.assertEqual(project.comment_on_ticket_as(self.conn, OPERATOR, wo_id, OPENED, "on my way").author, OPS)
        with self.assertRaises(NotPermitted):
            project.comment_on_ticket_as(self.conn, ENGINEER, wo_id, OPENED, "x", by=INVERTER)
        with self.assertRaises(NotPermitted):
            project.move_ticket_as(self.conn, None, wo_id, TicketStatus.IN_PROGRESS, OPENED)
        self.assertEqual(project.resolve_ticket_as(self.conn, ENGINEER, wo_id, "fuse", "RC-COMPONENT", LATER).status,
                         TicketStatus.CLOSED)


    def test_an_operators_decision_records_the_operator_on_the_suggestion(self) -> None:
        first = project.suggest_pushed(self.conn, ASSET, "INV-001", OPENED)
        project.accept_suggestion_as(self.conn, OPERATOR, first.suggestion_id, for_engineer=SITE)
        second = project.suggest_pushed(self.conn, "OAHE-INV-002", "INV-001", OPENED)
        dismissed = project.dismiss_suggestion_as(self.conn, ENGINEER, second.suggestion_id, "reset remotely")
        accepted = suggestion_table.get(self.conn, first.suggestion_id)
        self.assertEqual([(found.decided_by, found.recorded_by) for found in (accepted, dismissed)],
                         [(SITE, OPS), (SITE, None)])

    def test_a_ticket_is_read_within_the_accounts_sites_by_any_role(self) -> None:
        project.assign_fault(self.conn, ASSET, "INV-001", OPENED, SITE)
        wo_id = project.open_tickets(self.conn)[0].wo_id
        project.move_ticket_as(self.conn, ENGINEER, wo_id, TicketStatus.ACKNOWLEDGED, OPENED)
        for viewer in (held(AUDITOR, Role.VIEWER, (ALL_SITES,)), ENGINEER):
            found, moves = project.moves_for(self.conn, viewer, wo_id)
            self.assertEqual((found.wo_id, [made.actor for made in moves]), (wo_id, [SITE]))
        with self.assertRaisesRegex(NotPermitted, "crew@bigs.example may not see site OAHE"):
            project.moves_for(self.conn, held(CREW, Role.ENGINEER, ("BIGS",)), wo_id)

    def test_a_dismissal_by_an_operator_prints_who_entered_it(self) -> None:
        from argparse import Namespace
        from solarpunk.cli.main import fault_dismiss
        lines = []
        for account, engineer in ((OPERATOR, SITE), (ENGINEER, None)):
            found = project.suggest_pushed(self.conn, ASSET, "INV-001", OPENED)
            out = io.StringIO()
            fault_dismiss(self.conn, Namespace(account=account, suggestion_id=found.suggestion_id, reason="why", by=None,
                                               for_engineer=engineer), out)
            lines.append(out.getvalue().split(" ", 2)[2])
        self.assertEqual(lines, [f"by {SITE} entered by {OPS}: why\n", f"by {SITE}: why\n"])

    def test_a_fleet_address_with_no_engineer_account_decides_nothing(self) -> None:
        found = project.suggest_pushed(self.conn, ASSET, "INV-001", OPENED)
        inverter, operator = (f"{who} is not an active engineer of site OAHE" for who in (INVERTER, OPS))
        for act, words in ((lambda: project.accept_suggestion(self.conn, found.suggestion_id, INVERTER), inverter),
                           (lambda: project.dismiss_suggestion(self.conn, found.suggestion_id, INVERTER, "x"), inverter),
                           (lambda: project.assign_fault(self.conn, ASSET, "INV-002", OPENED, OPS), operator)):
            with self.subTest(words=words), self.assertRaises(project.UnknownEngineer) as caught:
                act()
            self.assertEqual(str(caught.exception), words)
        self.assertEqual((project.open_suggestions(self.conn), project.faults_listing(self.conn, False)), ((found,), ()))


class TheFirstExample(WithAccounts):
    def test_it_runs_as_the_contract_says(self) -> None:
        text = section()
        first = project.assign_fault_as(self.conn, ENGINEER, ASSET, "INV-001", OPENED)
        second = project.assign_fault_as(self.conn, OPERATOR, ASSET, "INV-002", OPENED, for_engineer=SITE)
        with self.assertRaises(NotPermitted) as caught:
            project.assign_fault_as(self.conn, OPERATOR, ASSET, "INV-003", OPENED, for_engineer=CREW)
        said = project.comment_on_ticket_as(self.conn, OPERATOR, 2, OPENED, "on my way")
        for act, outcome in (
                ("site@oahe.example assigns INV-001 on OAHE-INV-001", f"open by {first.assigned_by}"),
                ("ops@oahe.example assigns INV-002 --for site@oahe.example",
                 f"open by {second.assigned_by} entered by {second.recorded_by}"),
                ("ops@oahe.example assigns INV-003 --for crew@bigs.example", f'refused: "{caught.exception}"'),
                ("ops@oahe.example comments on its ticket", f"the comment by {said.author}")):
            with self.subTest(act=act):
                self.assertIn(f"{act} {outcome}", text)
        self.assertEqual(len(project.faults_listing(self.conn, False)), 2)


class WithNoAccount(unittest.TestCase):
    def setUp(self) -> None:
        """The demo fleet in memory, no account: anyone at the machine acts (SP-032)."""
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        project.load_fleet(self.conn, project.demo_fleet())

    def test_the_addresses_given_are_taken_as_before(self) -> None:
        fault = project.assign_fault_as(self.conn, None, ASSET, "INV-001", OPENED, by=INVERTER, recorded_by=OPS)
        self.assertEqual((fault.assigned_by, fault.recorded_by), (INVERTER, OPS))
        wo_id = project.open_tickets(self.conn)[0].wo_id
        self.assertEqual(project.comment_on_ticket_as(self.conn, None, wo_id, OPENED, "x", by=SITE).author, SITE)
        for act, words in ((lambda: project.assign_fault_as(self.conn, None, ASSET, "INV-002", OPENED),
                            attribution.NAME_ENGINEER),
                           (lambda: project.assign_fault_as(self.conn, None, ASSET, "INV-002", OPENED, for_engineer=SITE),
                            attribution.FOR_NEEDS_ACCOUNTS),
                           (lambda: project.comment_on_ticket_as(self.conn, None, wo_id, OPENED, "x"),
                            attribution.NAME_AUTHOR)):
            with self.subTest(words=words), self.assertRaises(NotPermitted) as caught:
                act()
            self.assertEqual(str(caught.exception), words)


class TheContract(unittest.TestCase):
    def test_the_words_are_the_contracts(self) -> None:
        text = " ".join(section().split())
        for words in (attribution.ACCOUNT_ACTS, "crew@bigs.example is not an active engineer of site OAHE",
                      "admin@oahe.example is an admin and assigns no fault",
                      "admin@oahe.example is an admin and works no ticket"):
            with self.subTest(words=words):
                self.assertIn(f'"{words}"', text)


class ThePicker(unittest.TestCase):
    def test_who_sees_which_picker_and_what_it_names(self) -> None:
        self.assertEqual([cells.picker_title(a) for a in (None, OPERATOR, ENGINEER, held(ADMIN, Role.ADMIN))],
                         ["Assigned by", "On the word of", None, None])
        self.assertEqual(cells.who_named(None, SITE, ""), (SITE, None, None))
        self.assertEqual(cells.who_named(None, SITE, OPS), (SITE, OPS, None))
        self.assertEqual(cells.who_named(OPERATOR, SITE, ""), (None, None, SITE))
        self.assertEqual(cells.who_named(ENGINEER, "", ""), (None, None, None))


class TheCommandLine(unittest.TestCase):
    def setUp(self) -> None:
        """The store with accounts copied to a file the command line opens."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "attribution.db")
        stored(sqlite3.connect(self.db)).close()

    def run_cli(self, words: list[str]) -> tuple[int, str, str]:
        """Runs the command line, getpass stood in for with the accounts' password."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(signin.getpass, "getpass", lambda _prompt: passphrase()):
            code = main(["--db", self.db, *words], out, err)
        return code, out.getvalue(), err.getvalue()

    def test_the_signed_in_account_is_who_the_fault_and_the_comment_record(self) -> None:
        assign = ["fault", "assign", ASSET, "INV-001", AT]
        self.assertEqual(self.run_cli([*assign, "--as", SITE, "--by", INVERTER]),
                         (2, "", f"error: {attribution.ACCOUNT_ACTS}\n"))
        self.assertEqual(self.run_cli([*assign, "--as", OPS, "--for", SITE]),
                         (0, f"1 {ASSET} INV-001 {AT} open by {SITE} entered by {OPS}\n", ""))
        self.assertEqual(self.run_cli(["ticket", "comment", "1", "--as", OPS, "--at", AT, "on", "my", "way"]),
                         (0, f"1 comment 1 by {OPS}\n", ""))
        self.assertEqual(self.run_cli(["ticket", "ack", "1", "--as", ADMIN, "--at", AT]),
                         (2, "", "error: admin@oahe.example is an admin and works no ticket\n"))
