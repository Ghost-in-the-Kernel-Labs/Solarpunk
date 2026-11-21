"""Who an act is recorded as (12.4, SOL-16, SP-015, SP-032, SP-035): in a store with an active account the actor is the
account signed in, never an address chosen. An engineer assigns a fault as themself; an operator enters one on a named
engineer's word, the record saying both (the engineer as assigned_by, the operator as recorded_by); an admin and a
viewer assign nothing. A fault telemetry raises (SP-046) names its test or device and no account. A ticket is worked by an
engineer or an operator, as their own act, each move logged with their email. A store with no active account works as before accounts: the addresses given are taken as written, and
nobody signed in acts. Every refusal names the account and writes nothing."""
import sqlite3
from datetime import datetime

from solarpunk.accounts import table as account_table
from solarpunk.leaf.accounts import Account, Role, site_of
from solarpunk.faults import ledger
from solarpunk.faults.ledger import FaultCause
from solarpunk.leaf.faults import Fault
from solarpunk.project.access import (SIGN_IN_FIRST, NotPermitted, actor_of, article, needs_sign_in, permit_asset,
                                      permit_ticket_work)
from solarpunk.project.causes import write_fault_cause
from solarpunk.project.engineers import site_engineer
from solarpunk.project.orchestrator import assign_fault
from solarpunk.project.result_tickets import ResultTicket, ResultTicketError, open_ticket_from_result
from solarpunk.remote import results as result_table
from solarpunk.project.tickets import comment_on_ticket, resolve_ticket
from solarpunk.workorders.tickets import Comment, Ticket

ACCOUNT_ACTS = "this store has accounts: the signed-in account is used, so --by and --recorded-by are not taken"
FOR_NEEDS_ACCOUNTS = ("this store has no accounts: name the engineer with --by, and the operator with --recorded-by;"
                      " --for is an operator's, signed in")
NAME_ENGINEER = "this store has no accounts: name the engineer with --by"
NAME_AUTHOR = "this store has no accounts: name the comment's author with --by"
ASSIGNS = "assigns no fault"
WRITES = "writes no root cause"
OPENS = "opens no ticket"


def no_account_acts(conn: sqlite3.Connection, actor: str | None, missing: str, for_engineer: str | None = None) -> None:
    """Lets nobody signed in act only where the store holds no active account (SP-032), naming who acts with actor: with
    an account, NotPermitted(SIGN_IN_FIRST); actor not given, NotPermitted(missing); --for given where there are no
    accounts, NotPermitted(FOR_NEEDS_ACCOUNTS), as only a signed-in operator acts on an engineer's word."""
    # Decision: SP-032 (no accounts, no sign-in: anyone at the machine acts, as before)
    if needs_sign_in(conn):
        raise NotPermitted(SIGN_IN_FIRST)
    if for_engineer:
        raise NotPermitted(FOR_NEEDS_ACCOUNTS)
    if actor is None:
        raise NotPermitted(missing)


def word_engineer(conn: sqlite3.Connection, email: str, site: str) -> str:
    """The engineer an operator names, when that is an active engineer account whose sites hold the site:
    word_engineer(conn, "site@oahe.example", "OAHE") is "site@oahe.example"; an operator, a stopped engineer, one of
    another site or no account at all raises NotPermitted("crew@bigs.example is not an active engineer of site OAHE")."""
    found = site_engineer(conn, email, site)
    if found is None:
        raise NotPermitted(f"{email} is not an active engineer of site {site}")
    return found


def recorded_as(conn: sqlite3.Connection, account: Account | None, asset_id: str, actor: str | None = None,
                recorded_by: str | None = None, for_engineer: str | None = None,
                deed: str = ASSIGNS) -> tuple[str, str | None]:
    """Who a fault or a decision on an asset is recorded as, (engineer, operator): with no account, (actor, recorded_by)
    as given; an engineer signed in, (their email, None); an operator, (the engineer named by for_engineer, their own
    email). Refused by name (NotPermitted): --by or --recorded-by given with an account, an engineer giving
    for_engineer, an operator naming none or one word_engineer refuses, an admin ("admin@oahe.example is an admin and
    assigns no fault"), a viewer, a stopped account and one outside the asset's site (permit_asset)."""
    # Decision: SP-015 (only an engineer assigns, and the record says which; an operator's entry recorded as theirs)
    if account is None:
        no_account_acts(conn, actor, NAME_ENGINEER, for_engineer)
        return str(actor), recorded_by
    if actor is not None or recorded_by is not None:
        raise NotPermitted(ACCOUNT_ACTS)
    permit_asset(account, asset_id)
    if account.role is Role.ENGINEER:
        if for_engineer:
            raise NotPermitted(f"{account.email} is an engineer and acts as themself; --for is an operator's")
        return account.email, None
    if account.role is Role.OPERATOR:
        if not for_engineer:
            raise NotPermitted(f"{account.email} is an operator: name the engineer whose word this is")
        return word_engineer(conn, for_engineer.strip(), site_of(asset_id)), account.email
    raise NotPermitted(f"{account.email} is {article(account.role)} and {deed}")


def word_engineers(conn: sqlite3.Connection, asset_id: str) -> tuple[str, ...]:
    """The engineers an operator may name for an asset, sorted: the active engineer accounts whose sites hold the
    asset's; SOL-16's three accounts give ("site@oahe.example",) for OAHE-INV-002."""
    site = site_of(asset_id)
    return tuple(sorted(found.email for found in account_table.every(conn)
                        if found.role is Role.ENGINEER and found.active and found.sees(site)))


def assign_fault_as(conn: sqlite3.Connection, account: Account | None, asset_id: str, code: str, opened: datetime,
                    actor: str | None = None, recorded_by: str | None = None, for_engineer: str | None = None) -> Fault:
    """Opens a fault as assign_fault does, recorded as recorded_as says: site@oahe.example signed in assigns INV-001 on
    OAHE-INV-002 as itself; ops@oahe.example, an operator, for site@oahe.example gives assigned_by site@oahe.example,
    recorded_by ops@oahe.example. A refusal opens no fault and no ticket."""
    # Decision: SP-015
    engineer, operator = recorded_as(conn, account, asset_id, actor, recorded_by, for_engineer)
    return assign_fault(conn, asset_id, code, opened, engineer, operator)


def write_cause_as(conn: sqlite3.Connection, account: Account | None, fault_id: int, cause: str, moment: datetime,
                   actor: str | None = None, recorded_by: str | None = None, for_engineer: str | None = None) -> FaultCause:
    """Writes a fault's root cause as write_fault_cause does, recorded as recorded_as says, as an assignment is: an
    engineer signed in writes as themself, an operator on the word of the engineer named by for_engineer; an admin,
    a viewer or an account outside the fault's site is refused ("admin@oahe.example is an admin and writes no root
    cause") and nothing is written."""
    # Decision: SP-046 (an engineer writes the root cause); SP-015 (the record says whose word it is)
    engineer, operator = recorded_as(conn, account, ledger.get(conn, fault_id).asset_id, actor, recorded_by, for_engineer, WRITES)
    return write_fault_cause(conn, fault_id, cause, engineer, moment, operator)


def open_ticket_from_result_as(conn: sqlite3.Connection, account: Account | None, result_id: int, opened: datetime,
                               actor: str | None = None, recorded_by: str | None = None,
                               for_engineer: str | None = None) -> ResultTicket:
    """Opens the ticket for a failed result as open_ticket_from_result does, recorded as recorded_as says, as an
    assignment is: an engineer signed in opens it as themself, an operator on the word of for_engineer; an admin, a
    viewer or an account outside the result's site is refused and nothing is written. A result already in a ticket
    shows that ticket, opening nothing."""
    # Decision: SP-046 (a ticket opens from a failed result, by an engineer); SP-015 (the record says whose word it is)
    found = result_table.get(conn, result_id)
    if found is None:
        raise ResultTicketError(f"result {result_id} is not stored")
    engineer, operator = recorded_as(conn, account, found.asset_id, actor, recorded_by, for_engineer, OPENS)
    return open_ticket_from_result(conn, result_id, opened, engineer, operator)


def comment_on_ticket_as(conn: sqlite3.Connection, account: Account | None, wo_id: int, moment: datetime, body: str,
                         actor: str | None = None) -> Comment:
    """Adds a comment as comment_on_ticket does, its author the account signed in (an engineer or an operator, as
    their own); with no account, the author given by actor (none given, NAME_AUTHOR). --by given with an account is refused
    (ACCOUNT_ACTS)."""
    # Decision: SP-022 (every act carries the signed-in account)
    if account is None:
        no_account_acts(conn, actor, NAME_AUTHOR)
        return comment_on_ticket(conn, wo_id, str(actor), moment, body)
    if actor is not None:
        raise NotPermitted(ACCOUNT_ACTS)
    permit_ticket_work(conn, account, wo_id)
    return comment_on_ticket(conn, wo_id, account.email, moment, body)


def resolve_ticket_as(conn: sqlite3.Connection, account: Account | None, wo_id: int, done: str,
                      moment: datetime, read_at: int | None = None) -> Ticket:
    """Resolves and closes a ticket as resolve_ticket does (its fault's root cause written first), once the account may work it (permit_ticket_work): an
    admin is refused ("… is an admin and works no ticket") and nothing moves; a ticket read at an older version than
    read_at, StaleWrite (12.2) and nothing moves. Each move is logged as the account's (SP-035)."""
    # Decision: SP-035 (a ticket's every move is logged with who made it)
    permit_ticket_work(conn, account, wo_id)
    return resolve_ticket(conn, wo_id, done, moment, read_at, actor_of(account))
