"""Signing in (12.3, SOL-16, SP-032): headless, the sign-in itself (a good pair gives the account, a bad one None with
the failure kept by account and instant and never the password), the store with no account asking nothing, and the
command line's --as and getpass (stood in for: no test types a real prompt); then, under a display, the dialog before
the fleet window, a refusal in red, the account in the status bar, and closing the dialog ending the program. Every
password is built at runtime (test_accounts.passphrase). Skips "no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from solarpunk import project
from solarpunk.cli import signin
from solarpunk.cli.main import main
from solarpunk.leaf.clock import at
from solarpunk.project import Role
from solarpunk.ui import cells
from test.solarpunk.test_accounts import CREATED, SITE, other_passphrase, passphrase, section

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import __main__ as entry
    from solarpunk.ui import sign_in

MOMENT = at(2026, 6, 1, 11)


def with_account(conn: sqlite3.Connection) -> None:
    """Gives a store the demo fleet and SOL-16's site engineer of OAHE."""
    project.load_fleet(conn, project.demo_fleet())
    project.create_account(conn, SITE, "Site engineer", Role.ENGINEER, passphrase(), ("OAHE",), CREATED)


class TheSignIn(unittest.TestCase):
    def setUp(self) -> None:
        """An in-memory store, its fleet loaded, with no account yet."""
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)

    def test_a_store_with_no_account_asks_nothing(self) -> None:
        self.assertFalse(project.needs_sign_in(self.conn))
        self.assertIsNone(signin.signed_in(self.conn, None, ask=self.fail))
        self.assertEqual(cells.who_text(None), "no accounts yet: anyone at this machine acts")

    def test_a_good_pair_and_a_bad_one(self) -> None:
        with_account(self.conn)
        self.assertTrue(project.needs_sign_in(self.conn))
        found = project.sign_in(self.conn, SITE, passphrase(), MOMENT)
        self.assertEqual((found.email, cells.who_text(found)), (SITE, "signed in as site@oahe.example (engineer)"))
        self.assertIsNone(project.sign_in(self.conn, SITE, other_passphrase(), MOMENT))
        self.assertIsNone(project.sign_in(self.conn, passphrase(), passphrase(), MOMENT))  # typed in the wrong field
        self.assertEqual(project.failed_sign_ins(self.conn), ((SITE, MOMENT), ("no such account", MOMENT)))

    def test_no_failure_keeps_anything_of_a_password(self) -> None:
        with_account(self.conn)
        project.sign_in(self.conn, SITE, other_passphrase(), MOMENT)
        project.sign_in(self.conn, passphrase(), other_passphrase(), MOMENT)
        kept = " ".join(str(value) for row in self.conn.execute("SELECT * FROM failed_sign_ins") for value in row)
        for secret in (passphrase(), other_passphrase()):
            self.assertNotIn(secret, kept)


class TheContract(unittest.TestCase):
    def test_the_rules_words_are_the_contracts(self) -> None:
        text = section()
        self.assertIn(f'A refusal says "{signin.NO_MATCH}"', text)
        self.assertEqual(cells.NO_MATCH, signin.NO_MATCH)
        self.assertIn("A failed sign-in is kept with the account it named, or \"no such account\"", text)


class TheCommandLine(unittest.TestCase):
    def setUp(self) -> None:
        """A store file holding the demo fleet, an open INV-001 on OAHE-INV-002 and SOL-16's site engineer."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "fleet.db")
        conn = project.open_or_create(self.db)
        with_account(conn)
        project.assign_fault(conn, "OAHE-INV-002", "INV-001", MOMENT, "inverter@oahe.example")
        conn.close()
        self.prompts: list[str] = []

    def run_cli(self, words: list[str], password: str | None) -> tuple[int, str, str]:
        """Runs the command line with getpass stood in for: it gives password and keeps each prompt; None fails the
        test if anything asks."""
        def ask(prompt: str) -> str:
            """The stand-in for getpass: keeps the prompt, gives the password (never echoed, never printed)."""
            if password is None:
                self.fail(f"asked {prompt!r}")
            self.prompts.append(prompt)
            return password
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(signin.getpass, "getpass", ask):
            code = main(["--db", self.db, *words], out, err)
        return code, out.getvalue(), err.getvalue()

    def test_an_acting_command_takes_as_and_a_password(self) -> None:
        code, out, err = self.run_cli(["ticket", "ack", "1", "--as", SITE, "--at", "2026-06-01T11:40:00+00:00"],
                                      passphrase())
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(self.prompts, ["password for site@oahe.example: "])
        self.assertNotIn(passphrase(), out)

    def test_no_as_or_a_wrong_password_is_refused_and_kept(self) -> None:
        self.assertEqual(self.run_cli(["ticket", "ack", "1"], None), (2, "", f"error: {signin.NAME_YOURS}\n"))
        self.assertEqual(self.run_cli(["ticket", "ack", "1", "--as", SITE], other_passphrase()),
                         (2, "", f"error: {signin.NO_MATCH}\n"))
        conn = project.open_or_create(self.db)
        self.addCleanup(conn.close)
        self.assertEqual([account for account, _at in project.failed_sign_ins(conn)], [SITE])
        self.assertEqual(project.ticket_of(conn, 1).status, project.TicketStatus.OPEN)

    def test_reading_and_the_scheduled_run_ask_nothing(self) -> None:
        self.assertEqual(self.run_cli(["fleet", "list"], None)[0], 0)
        self.assertEqual(self.run_cli(["test", "run", "--at", "2026-06-01T13:00:00+00:00"], None)[0], 0)


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheDialog(unittest.TestCase):
    def setUp(self) -> None:
        """A root, or the test skipped with no display, over a store with SOL-16's site engineer."""
        try:
            self.root = tkinter.Tk()
        except tkinter.TclError:
            self.skipTest("no display")
        self.addCleanup(self.destroy)
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        self.signed: list[project.Account | None] = []

    def destroy(self) -> None:
        """Destroys the root unless the test already did, as closing the dialog does."""
        try:
            self.root.destroy()
        except tkinter.TclError:
            pass

    def test_a_store_with_no_account_opens_at_once(self) -> None:
        self.assertIsNone(sign_in.start(self.root, self.conn, self.signed.append))
        self.assertEqual(self.signed, [None])

    def test_the_dialog_refuses_then_signs_in(self) -> None:
        with_account(self.conn)
        dialog = sign_in.start(self.root, self.conn, self.signed.append)
        self.root.update()
        self.assertEqual((self.root.state(), self.signed), ("withdrawn", []))
        dialog.email.set(SITE)
        dialog.password.set(other_passphrase())
        dialog.sign_in_button.invoke()
        self.assertEqual((dialog.line.cget("text"), dialog.password.get(), self.signed), (cells.NO_MATCH, "", []))
        dialog.password.set(passphrase())
        dialog.sign_in_button.invoke()
        self.assertEqual([found.email for found in self.signed], [SITE])
        self.assertFalse(dialog.winfo_exists())
        self.assertEqual(self.root.state(), "normal")
        self.assertEqual(len(project.failed_sign_ins(self.conn)), 1)

    def test_the_fleet_window_names_who_is_signed_in(self) -> None:
        with_account(self.conn)
        account = project.sign_in(self.conn, SITE, passphrase(), MOMENT)
        window = entry.open_fleet(self.root, self.conn, account)
        self.assertEqual((window.account, window.account_label.cget("text")),
                         (account, "signed in as site@oahe.example (engineer)"))
        empty = project.open_store()
        self.addCleanup(empty.close)
        unsigned = entry.open_fleet(tkinter.Toplevel(self.root), empty)
        self.assertEqual(unsigned.account_label.cget("text"), cells.NO_ACCOUNTS)

    def test_closing_the_dialog_ends_the_program(self) -> None:
        with_account(self.conn)
        dialog = sign_in.start(self.root, self.conn, self.signed.append)
        self.root.tk.call(dialog.protocol("WM_DELETE_WINDOW"))
        with self.assertRaises(tkinter.TclError):
            self.root.winfo_exists()
        self.assertEqual(self.signed, [])


if __name__ == "__main__":
    unittest.main()
