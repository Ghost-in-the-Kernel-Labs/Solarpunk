"""Account administration (12.5, SOL-16, SP-022, SP-032): the first admin made once by `account init`; an active admin
adds, resets and deactivates (never deletes) accounts, every other role refused by name and a store with no active
account pointed to `account init`; the last active admin kept; `account list` without the stored line. The command
line runs with input and getpass stood in for. Every password is built at runtime (test_accounts.passphrase), and the
number of scrypt hashes is kept small: a refusal is held on an Account made in memory, never a stored one."""
import io
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

from solarpunk import project
from solarpunk.cli import accounts as cli_accounts
from solarpunk.cli.main import main
from solarpunk.leaf.accounts import ALL_SITES, Account
from solarpunk.project import AccountError, NotPermitted, Role
from solarpunk.project import access
from test.solarpunk.test_accounts import CREATED, SITE, other_passphrase, passphrase, section

ADMIN = "admin@oahe.example"
OPENED = "2026-06-01T11:30:00+00:00"


def held(email: str, role: Role, active: bool = True) -> Account:
    """An account in memory, never stored: held(ADMIN, Role.ADMIN) is an active admin of every site."""
    return Account(email, email.split("@")[0], role, active, CREATED, (ALL_SITES,))


class ThePermits(unittest.TestCase):
    def test_only_an_active_admin_manages_accounts(self) -> None:
        admin = held(ADMIN, Role.ADMIN)
        self.assertIs(project.permit_admin(admin), admin)
        refusals = {
            None: access.NO_ADMIN_YET,
            held(SITE, Role.ENGINEER): "site@oahe.example is an engineer and does not manage accounts",
            held(SITE, Role.VIEWER): "site@oahe.example is a viewer and does not manage accounts",
            held(ADMIN, Role.ADMIN, active=False): "admin@oahe.example is not active and acts on nothing",
        }
        for account, words in refusals.items():
            with self.subTest(account=account), self.assertRaises(NotPermitted) as caught:
                project.permit_admin(account)
            self.assertEqual(str(caught.exception), words)

    def test_the_words_are_the_contracts(self) -> None:
        text = section()
        for words in (access.ADMIN_EXISTS, access.NO_ADMIN_YET,
                      "site@oahe.example is an engineer and does not manage accounts"):
            with self.subTest(words=words):
                self.assertIn(f'"{words}"', text)


class TheProjectCalls(unittest.TestCase):
    def setUp(self) -> None:
        """An in-memory store holding the demo fleet and its first admin."""
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        project.load_fleet(self.conn, project.demo_fleet())
        self.admin = project.first_admin(self.conn, ADMIN, "Admin", passphrase(), CREATED)

    def test_the_first_admin_is_made_once(self) -> None:
        self.assertEqual((self.admin.role, self.admin.active, self.admin.sites), (Role.ADMIN, True, (ALL_SITES,)))
        self.conn.execute("UPDATE accounts SET active = 0")  # a stopped admin still holds the store
        with self.assertRaises(AccountError) as caught:
            project.first_admin(self.conn, SITE, "Site engineer", passphrase(), CREATED)
        self.assertEqual(str(caught.exception), access.ADMIN_EXISTS)
        self.assertEqual([found.email for found in project.accounts(self.conn)], [ADMIN])

    def test_a_refused_add_stores_nothing(self) -> None:
        with self.assertRaises(NotPermitted):
            project.add_account_as(self.conn, held(SITE, Role.OPERATOR), "x@oahe.example", "X", Role.ADMIN,
                                   passphrase(), (), CREATED)
        with self.assertRaises(NotPermitted):
            project.add_account_as(self.conn, None, "x@oahe.example", "X", Role.ADMIN, passphrase(), (), CREATED)
        self.assertEqual(len(project.accounts(self.conn)), 1)

    def test_a_reset_password_replaces_the_old(self) -> None:
        project.reset_password_as(self.conn, self.admin, ADMIN, other_passphrase())
        self.assertIsNone(project.check_password(self.conn, ADMIN, passphrase()))
        self.assertEqual(project.check_password(self.conn, ADMIN, other_passphrase()).email, ADMIN)
        with self.assertRaises(NotPermitted):
            project.reset_password_as(self.conn, held(SITE, Role.ENGINEER), ADMIN, passphrase())

    def test_deactivating_keeps_the_name_and_stops_the_sign_in(self) -> None:
        project.add_account_as(self.conn, self.admin, SITE, "Site engineer", Role.ENGINEER, passphrase(), ("OAHE",),
                               CREATED)
        project.assign_fault(self.conn, "OAHE-INV-002", "INV-001", CREATED, SITE)
        stopped = project.deactivate_account_as(self.conn, self.admin, SITE)
        self.assertEqual((stopped.email, stopped.name, stopped.active), (SITE, "Site engineer", False))
        self.assertEqual(project.account_of(self.conn, SITE), stopped)
        self.assertEqual([fault.assigned_by for fault in project.faults_listing(self.conn, False)], [SITE])
        self.assertIsNone(project.sign_in(self.conn, SITE, passphrase(), CREATED))

    def test_the_last_active_admin_is_kept(self) -> None:
        with self.assertRaises(NotPermitted) as caught:
            project.deactivate_account_as(self.conn, self.admin, ADMIN)
        self.assertEqual(str(caught.exception),
                         "admin@oahe.example is the last active admin; add another admin before deactivating it")
        self.assertTrue(project.account_of(self.conn, ADMIN).active)


class TheCommandLine(unittest.TestCase):
    def setUp(self) -> None:
        """A store file with the demo fleet and no account."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "fleet.db")
        conn = project.open_or_create(self.db)
        project.load_fleet(conn, project.demo_fleet())
        conn.close()
        self.prompts: list[str] = []

    def run_cli(self, words: list[str], typed: tuple[str, ...] = (), secrets: tuple[str, ...] = ()) -> tuple:
        """Runs the command line with input giving typed and getpass giving secrets in turn, each prompt kept; asking
        for more than is given fails the test."""
        answers = {"input": list(typed), "getpass": list(secrets)}

        def stand_in(kind: str) -> Callable[[str], str]:
            """The stand-in for input ("input") or getpass ("getpass"): stand_in("input")("name: ") gives "Admin"."""
            def ask(prompt: str) -> str:
                """Keeps the prompt and gives the next answer of its kind, never printing it."""
                if not answers[kind]:
                    self.fail(f"asked {prompt!r}")
                self.prompts.append(prompt)
                return answers[kind].pop(0)
            return ask
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("builtins.input", stand_in("input")), \
                mock.patch.object(cli_accounts.getpass, "getpass", stand_in("getpass")):
            code = main(["--db", self.db, *words], out, err)
        return code, out.getvalue(), err.getvalue()

    def init(self) -> tuple:
        """account init as the first admin, Admin of ADMIN, with passphrase() typed twice."""
        return self.run_cli(["account", "init"], ("Admin", ADMIN), (passphrase(), passphrase()))

    def test_init_makes_the_first_admin_once(self) -> None:
        self.assertEqual(self.init(), (0, f"admin {ADMIN} made\n", ""))
        self.assertEqual(self.prompts, ["name: ", "email: ", f"new password for {ADMIN}: ", "again: "])
        self.assertEqual(self.run_cli(["account", "init"]), (2, "", f"error: {access.ADMIN_EXISTS}\n"))
        code, out, err = self.run_cli(["account", "list"])
        self.assertEqual((code, err), (0, ""))
        self.assertRegex(out, rf"^{ADMIN}  Admin  admin  active  \*  \d{{4}}-\d\d-\d\dT[\d:]+\+00:00\n$")

    def test_two_passwords_that_differ_make_nothing(self) -> None:
        refused = self.run_cli(["account", "init"], ("Admin", ADMIN), (passphrase(), other_passphrase()))
        self.assertEqual(refused, (2, "", f"error: {cli_accounts.MISMATCH}\n"))
        self.assertEqual(self.run_cli(["account", "list"]), (0, "no account\n", ""))

    def test_with_no_account_nobody_adds_one(self) -> None:
        refused = self.run_cli(["account", "add", SITE, "--name", "Site", "--role", "admin"])
        self.assertEqual(refused, (2, "", f"error: {access.NO_ADMIN_YET}\n"))
        self.assertEqual(self.prompts, [])

    def test_an_admin_adds_resets_and_deactivates(self) -> None:
        self.init()
        add = ["account", "add", SITE, "--name", "Site engineer", "--role", "engineer", "--site", "OAHE", "--as", ADMIN]
        code, out, err = self.run_cli(add, secrets=(passphrase(), other_passphrase(), other_passphrase()))
        self.assertEqual((code, err, out.split("  ")[:5]), (0, "", [SITE, "Site engineer", "engineer", "active", "OAHE"]))
        reset = self.run_cli(["account", "reset", SITE, "--as", ADMIN], secrets=(passphrase(),) * 3)
        self.assertEqual(reset, (0, f"password reset for {SITE}\n", ""))
        refused = self.run_cli(["account", "reset", ADMIN, "--as", SITE], secrets=(passphrase(),))
        self.assertEqual(refused, (2, "", "error: site@oahe.example is an engineer and does not manage accounts\n"))
        code, out, err = self.run_cli(["account", "deactivate", SITE, "--as", ADMIN], secrets=(passphrase(),))
        self.assertEqual((code, err, out.split("  ")[3]), (0, "", "deactivated"))
        listed = self.run_cli(["account", "list"])[1]
        self.assertEqual([line.split("  ")[3] for line in listed.splitlines()], ["active", "deactivated"])
        self.assertNotIn("scrypt", listed)
        self.assertNotIn(passphrase(), listed)
