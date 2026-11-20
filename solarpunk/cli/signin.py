"""Who is at the command line (12.3, SOL-16, SP-032): a command that acts takes --as EMAIL and, in a store that holds an
active account, asks for the password with getpass, which never echoes it, and the act is recorded as that account
(12.4). A store with no account asks nothing, as before accounts; a command that only reads, and the scheduled run
(`test run`, which acts as no person), never ask. A refusal is a ValueError, so the command line prints it and exits 2."""
import argparse
import getpass
import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone

from solarpunk import project

DEST = "account_email"
NAME_YOURS = "this store has accounts: name yours with --as EMAIL"
NO_MATCH = "that email and password do not match an active account"
Ask = Callable[[str], str]


class NotSignedIn(ValueError):
    """Raised for an acting command that is not signed in: NotSignedIn("that email and password do not match an
    active account")."""


def acting(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Marks a subcommand as one that acts: it takes --as EMAIL, and dispatch signs it in before its handler runs."""
    parser.add_argument("--as", dest=DEST, metavar="EMAIL", default=None)
    return parser


def attributed(parser: argparse.ArgumentParser, operator: bool = True) -> argparse.ArgumentParser:
    """Who a fault act is recorded as (SP-015, 12.4): --for ENGINEER, an operator's, signed in; --by (and, with
    operator, --recorded-by) where the store has no accounts. project refuses what the store does not take."""
    parser.add_argument("--by")
    if operator:
        parser.add_argument("--recorded-by")
    parser.add_argument("--for", dest="for_engineer", metavar="ENGINEER")
    return parser


def acts(args: argparse.Namespace) -> bool:
    """Whether the parsed subcommand is one that acts: "fault assign …" does, "fault list" does not."""
    return hasattr(args, DEST)


def prompt(email: str) -> str:
    """The password prompt: "password for site@oahe.example: "."""
    return f"password for {email}: "


def signed_in(conn: sqlite3.Connection, email: str | None, ask: Ask | None = None,
              moment: datetime | None = None) -> project.Account | None:
    """The account at the command line, or None in a store with no account: with accounts, no --as raises NotSignedIn
    naming --as, and a wrong password (the failure kept, SOL-16) NotSignedIn with words that say nothing of which part
    was wrong. ask is getpass.getpass unless a test gives another."""
    # Decision: SP-032 (no accounts, no sign-in; --as and getpass at the command line)
    if not project.needs_sign_in(conn):
        return None
    if not email:
        raise NotSignedIn(NAME_YOURS)
    password = (ask or getpass.getpass)(prompt(email))
    found = project.sign_in(conn, email, password, moment or datetime.now(timezone.utc))
    if found is None:
        raise NotSignedIn(NO_MATCH)
    return found
