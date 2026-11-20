"""The account commands (12.5, SOL-16): `account init` makes the store's first admin on the machine, once, asking a name,
an email and a password; `account add|reset|deactivate` act (--as EMAIL, signed in first) and are an active admin's
alone; `account list` reads. A password is asked with getpass, twice, never echoed, printed or kept here; the two must
match. Each handler is a project call (MOD-02). main.py adds them to its parser."""
import argparse
import getpass
import sqlite3
from datetime import datetime, timezone
from typing import TextIO

from solarpunk import project
from solarpunk.cli.signin import acting

NO_ACCOUNT = "no account"
MISMATCH = "the two passwords do not match; nothing was changed"
LINE = "{email}  {name}  {role}  {state}  {sites}  {created}"


def now() -> datetime:
    """The instant an account is made: now in UTC, to the second."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def new_password(email: str) -> str:
    """A new password for an account, asked twice with getpass ("new password for x@y: ", then "again: "); two that
    differ raise ValueError(MISMATCH). The password is returned, never shown."""
    first = getpass.getpass(f"new password for {email}: ")
    if getpass.getpass("again: ") != first:
        raise ValueError(MISMATCH)
    return first


def account_line(found: project.Account) -> str:
    """One account as a line, never its stored secret: "admin@oahe.example  Admin  admin  active  *
    2026-06-01T10:00:00+00:00"; a stopped one reads "deactivated"."""
    return LINE.format(email=found.email, name=found.name, role=found.role.value,
                       state="active" if found.active else "deactivated", sites=",".join(found.sites),
                       created=found.created.isoformat())


def account_init(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """account init: asks a name, an email and a password (twice) and makes the first admin; prints "admin
    admin@oahe.example made". A store that holds an admin refuses before asking anything."""
    project.permit_first_admin(conn)
    name, email = input("name: "), input("email: ")
    made = project.first_admin(conn, email, name, new_password(email), now())
    out.write(f"admin {made.email} made\n")


def account_add(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """account add site@oahe.example --name "Site engineer" --role engineer --site OAHE: asks its password twice and
    prints its account_line."""
    project.permit_admin(args.account)
    password = new_password(args.email)
    made = project.add_account_as(conn, args.account, args.email, args.name, project.Role(args.role), password,
                                  tuple(args.site), now())
    out.write(account_line(made) + "\n")


def account_reset(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """account reset site@oahe.example: asks the new password twice; prints "password reset for site@oahe.example"."""
    project.permit_admin(args.account)
    found = project.reset_password_as(conn, args.account, args.email, new_password(args.email))
    out.write(f"password reset for {found.email}\n")


def account_deactivate(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """account deactivate site@oahe.example: stops the account, its row kept; prints its account_line, "deactivated"."""
    out.write(account_line(project.deactivate_account_as(conn, args.account, args.email)) + "\n")


def account_list(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """account list: one account_line per account, by email; none prints "no account"."""
    found = project.accounts(conn)
    for account in found:
        out.write(account_line(account) + "\n")
    if not found:
        out.write(NO_ACCOUNT + "\n")


def add_accounts(commands: argparse._SubParsersAction) -> None:
    """The account subcommands: "account add x@y --name X --role viewer --site OAHE" parses to account_add with site
    ["OAHE"]; init and list take no --as."""
    account = commands.add_parser("account").add_subparsers(required=True)
    account.add_parser("init").set_defaults(handler=account_init)
    add = acting(account.add_parser("add"))
    add.add_argument("email")
    add.add_argument("--name", required=True)
    add.add_argument("--role", required=True, choices=[role.value for role in project.Role])
    add.add_argument("--site", action="append", default=[])
    add.set_defaults(handler=account_add)
    reset = acting(account.add_parser("reset"))
    reset.add_argument("email")
    reset.set_defaults(handler=account_reset)
    deactivate = acting(account.add_parser("deactivate"))
    deactivate.add_argument("email")
    deactivate.set_defaults(handler=account_deactivate)
    account.add_parser("list").set_defaults(handler=account_list)
