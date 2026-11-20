"""Who may act, and where (12.1, SOL-16, SP-026, SP-028): the role and the site scope held against the records. An
account sees an asset, a fault, a suggestion and a ticket only when the asset's site is in its scope; a viewer acts on
nothing, and no account acts outside its sites, each refusal naming the account. The account calls here are thin
wrappers of the accounts table, so the windows and the command line reach it through project alone (MOD-06). An admin
manages the accounts (12.5): the first is made once, on the machine; the rest are added, reset and stopped by an active
admin, never deleted. Nothing here logs, shows or keeps a password."""
import sqlite3
from datetime import datetime

from solarpunk.accounts import table as account_table
from solarpunk.faults.ledger import LedgerError
from solarpunk.leaf.accounts import ALL_SITES, Account, Role, site_of
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.tickets import TicketStatus
from solarpunk.project.orchestrator import faults_listing, fleet_assets, known_engineers
from solarpunk.project.surface import AssetRow, asset_rows
from solarpunk.project.tickets import move_ticket, open_tickets, ticket_of
from solarpunk.remote import suggestions as suggestion_table
from solarpunk.remote.suggestions import Suggestion
from solarpunk.workorders.tickets import Ticket


NO_ADMIN_YET = "this store has no active account: make the first admin with solarpunk account init"
ADMIN_EXISTS = "this store already has an admin: account init makes only the first; an admin adds the rest"


class NotPermitted(ValueError):
    """Raised for a write an account may not make (SOL-16): NotPermitted("auditor@oahe.example is a viewer and acts on
    nothing"), NotPermitted("crew@bigs.example may not act on site OAHE")."""


def create_account(conn: sqlite3.Connection, email: str, name: str, role: Role, password: str,
                   sites: tuple[str, ...], created: datetime) -> Account:
    """Makes an active account: create_account(conn, "site@oahe.example", "Site engineer", Role.ENGINEER, <a password>,
    ("OAHE",), 10:00 UTC).sites is ("OAHE",); an admin's is ("*",). A duplicate email raises AccountError, a password
    under 12 characters WeakPassword, each storing nothing."""
    return account_table.add(conn, email, name, role, password, sites, created)


def account_of(conn: sqlite3.Connection, email: str) -> Account:
    """The account of an email: account_of(conn, "site@oahe.example").role is Role.ENGINEER; none raises AccountError."""
    return account_table.get(conn, email)


def accounts(conn: sqlite3.Connection) -> tuple[Account, ...]:
    """Every account by email: with SOL-16's three, auditor@oahe.example, crew@bigs.example, site@oahe.example."""
    return account_table.every(conn)


def check_password(conn: sqlite3.Connection, email: str, password: str) -> Account | None:
    """The account when the password is its own and it is active, else None: a wrong password, an unknown email and a
    stopped account all give None, so a refusal says nothing of which."""
    return account_table.check(conn, email, password)


def permit_asset(account: Account, asset_id: str) -> None:
    """Refuses an account a write on an asset (SOL-16): a stopped account and a viewer act on nothing, and no account
    acts outside its sites. permit_asset(site engineer of OAHE, "OAHE-INV-002") passes; permit_asset(crew of BIGS,
    "OAHE-INV-002") raises NotPermitted("crew@bigs.example may not act on site OAHE")."""
    # Decision: SP-026 (a viewer acts on nothing; a record of another site is not written by it)
    if not account.active:
        raise NotPermitted(f"{account.email} is not active and acts on nothing")
    if account.role is Role.VIEWER:
        raise NotPermitted(f"{account.email} is a viewer and acts on nothing")
    site = site_of(asset_id)
    if not account.sees(site):
        raise NotPermitted(f"{account.email} may not act on site {site}")


def permit_fault(conn: sqlite3.Connection, account: Account, fault_id: int) -> Fault:
    """The fault when the account may act on its asset, else NotPermitted: a viewer asking for fault 1 is refused; a
    fault the ledger lacks raises LedgerError."""
    found = next((fault for fault in faults_listing(conn, False) if fault.fault_id == fault_id), None)
    if found is None:
        raise LedgerError(f"fault {fault_id} is not in the ledger")
    permit_asset(account, found.asset_id)
    return found


def permit_suggestion(conn: sqlite3.Connection, account: Account, suggestion_id: int) -> Suggestion:
    """The suggestion when the account may act on its asset, else NotPermitted: crew@bigs.example asking for an OAHE
    suggestion is refused with "crew@bigs.example may not act on site OAHE"."""
    found = suggestion_table.get(conn, suggestion_id)
    permit_asset(account, found.asset_id)
    return found


def permit_ticket(conn: sqlite3.Connection, account: Account, wo_id: int) -> Ticket:
    """The ticket when the account may act on its asset, else NotPermitted: permit_ticket(conn, site@oahe.example, 1)
    is OAHE-INV-002's ticket in SOL-16's example."""
    found = ticket_of(conn, wo_id)
    permit_asset(account, found.asset_id)
    return found


def move_ticket_as(conn: sqlite3.Connection, account: Account, wo_id: int, status: TicketStatus,
                   moment: datetime, evidence: str | None = None, read_at: int | None = None) -> Ticket:
    """Moves a ticket as move_ticket does, once the account may act on it: site@oahe.example acknowledging OAHE-INV-002's
    ticket at 11:40 UTC gives it acknowledged at 11:40; auditor@oahe.example is refused and nothing moves."""
    permit_ticket(conn, account, wo_id)
    return move_ticket(conn, wo_id, status, moment, evidence, read_at)


def fleet_for(conn: sqlite3.Connection, account: Account) -> tuple[Asset, ...]:
    """The fleet's assets in the account's sites, in id order: the demo fleet gives a viewer of all 11, an engineer of
    BIGS alone 0."""
    return tuple(asset for asset in fleet_assets(conn, None) if account.sees(asset.site))


def asset_rows_for(conn: sqlite3.Connection, account: Account) -> tuple[AssetRow, ...]:
    """The fleet window's rows in the account's sites: the demo fleet gives site@oahe.example 11, crew@bigs.example 0."""
    return tuple(row for row in asset_rows(conn) if account.sees(site_of(row.asset_id)))


def open_faults_for(conn: sqlite3.Connection, account: Account) -> tuple[Fault, ...]:
    """The open faults whose asset is in the account's sites: an open INV-001 on OAHE-INV-002 is listed to an OAHE
    engineer and not to a BIGS one."""
    return tuple(fault for fault in faults_listing(conn, True) if account.sees(site_of(fault.asset_id)))


def open_suggestions_for(conn: sqlite3.Connection, account: Account) -> tuple[Suggestion, ...]:
    """The open suggestions whose asset is in the account's sites: an open SEN-001 on OAHE-SEN-001 is listed to a
    viewer of all and not to an engineer of BIGS."""
    return tuple(found for found in suggestion_table.open_suggestions(conn) if account.sees(site_of(found.asset_id)))


def open_tickets_for(conn: sqlite3.Connection, account: Account) -> tuple[Ticket, ...]:
    """The open tickets whose asset is in the account's sites: OAHE-INV-002's ticket is listed to site@oahe.example and
    not to crew@bigs.example."""
    return tuple(found for found in open_tickets(conn) if account.sees(site_of(found.asset_id)))


def unaccounted_engineers(conn: sqlite3.Connection) -> tuple[str, ...]:
    """The engineer addresses the fleet names with no active engineer account, sorted (SOL-16): the demo fleet with an
    engineer account for site@oahe.example alone gives ("inverter@oahe.example",)."""
    engineers = {found.email for found in account_table.every(conn) if found.role is Role.ENGINEER and found.active}
    return tuple(email for email in known_engineers(conn) if email not in engineers)


def needs_sign_in(conn: sqlite3.Connection) -> bool:
    """Whether the windows and the acting commands ask who is there (12.3, SP-032): True once the store holds an active
    account; a store with none (the demo, a store made before accounts) opens as it did, anyone at the machine acting."""
    # Decision: SP-032 (no accounts, no sign-in)
    return account_table.any_active(conn)


def sign_in(conn: sqlite3.Connection, email: str, password: str, moment: datetime) -> Account | None:
    """The account when its password is given and it is active, else None and the failure kept with the account named
    and the instant, never the password (SOL-16): a wrong password for site@oahe.example at 11:00 keeps
    ("site@oahe.example", 11:00 UTC); an unknown email keeps ("no such account", 11:00 UTC)."""
    found = account_table.check(conn, email, password)
    if found is None:
        account_table.record_failure(conn, email, moment)
    return found


def failed_sign_ins(conn: sqlite3.Connection) -> tuple[tuple[str, datetime], ...]:
    """Every failed sign-in, oldest first, as (account, instant)."""
    return account_table.failures(conn)


def first_admin(conn: sqlite3.Connection, email: str, name: str, password: str, created: datetime) -> Account:
    """Makes the store's first admin, active, of every site: first_admin(conn, "admin@oahe.example", "Admin", <a
    password>, 10:00 UTC). A store that holds an admin, active or not, raises AccountError(ADMIN_EXISTS) and stores
    nothing, so the command on the machine makes one admin once."""
    permit_first_admin(conn)
    return account_table.add(conn, email, name, Role.ADMIN, password, (ALL_SITES,), created)


def permit_first_admin(conn: sqlite3.Connection) -> None:
    """Refuses a first admin to a store that holds an admin, active or not: AccountError(ADMIN_EXISTS); a store with
    none passes, so `account init` can refuse before it asks a password."""
    # Decision: SP-032 (no accounts, no sign-in; the first admin made on the machine, once, 12.5)
    if account_table.any_admin(conn):
        raise account_table.AccountError(ADMIN_EXISTS)


def permit_admin(account: Account | None) -> Account:
    """The account when it is an active admin, else NotPermitted: None (a store with no active account, where nobody is
    signed in) is refused with NO_ADMIN_YET, so "no accounts, anyone acts" never makes one; a stopped account and every
    other role are refused by name, "site@oahe.example is an engineer and does not manage accounts"."""
    # Decision: SP-032 (no accounts, no sign-in: but no account is made without an admin)
    if account is None:
        raise NotPermitted(NO_ADMIN_YET)
    if not account.active:
        raise NotPermitted(f"{account.email} is not active and acts on nothing")
    if account.role is not Role.ADMIN:
        raise NotPermitted(f"{account.email} is {article(account.role)} and does not manage accounts")
    return account


def article(role: Role) -> str:
    """A role with its article: "an engineer", "an operator", "a viewer", "an admin"."""
    return ("an " if role.value[0] in "aeiou" else "a ") + role.value


def add_account_as(conn: sqlite3.Connection, admin: Account | None, email: str, name: str, role: Role, password: str,
                   sites: tuple[str, ...], created: datetime) -> Account:
    """Makes an active account as an admin, as create_account does: refused (NotPermitted) unless admin is an active
    admin, storing nothing."""
    permit_admin(admin)
    return account_table.add(conn, email, name, role, password, sites, created)


def reset_password_as(conn: sqlite3.Connection, admin: Account | None, email: str, password: str) -> Account:
    """Gives an account a new password as an admin: the old one then fails sign-in and the new one passes. Refused
    (NotPermitted) unless admin is an active admin; an unknown email raises AccountError, a weak password WeakPassword."""
    permit_admin(admin)
    return account_table.set_password(conn, email, password)


def deactivate_account_as(conn: sqlite3.Connection, admin: Account | None, email: str) -> Account:
    """Stops an account as an admin: its row and email kept, so every record keeps its name, and it fails sign-in after
    (SP-022: accounts are never deleted). The last active admin is refused, so the store is never locked out."""
    # Decision: SP-022 (never delete: records keep their names)
    permit_admin(admin)
    found = account_table.get(conn, email)
    if found.role is Role.ADMIN and found.active and account_table.active_admins(conn) == 1:
        raise NotPermitted(f"{found.email} is the last active admin; add another admin before deactivating it")
    return account_table.deactivate(conn, email)
