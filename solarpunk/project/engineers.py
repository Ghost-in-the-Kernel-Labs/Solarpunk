"""Who counts as an engineer (SP-015, SP-035), split from orchestrator.py: the one rule every door that assigns a fault
or decides a suggestion asks. In a store with an active account, the engineer is an active engineer account whose sites
hold the asset's; the fleet need not also name the address, so a new engineer acts once their account is made. A store
with no active account keeps SP-015's rule as it was: an engineer address the fleet names."""
import sqlite3

from solarpunk.accounts import table as account_table
from solarpunk.fleet import registry
from solarpunk.leaf.accounts import Role, site_of
from solarpunk.leaf.codes import AssetKind


class UnknownEngineer(ValueError):
    """Raised for a fault assigned, or a suggestion decided, by someone who is not an engineer (SP-015, SP-035): with no
    account, UnknownEngineer("nobody@example.com is not an engineer the fleet holds"); with accounts,
    UnknownEngineer("inverter@oahe.example is not an active engineer of site OAHE")."""


def known_engineers(conn: sqlite3.Connection) -> tuple[str, ...]:
    """Every engineer address the fleet holds, distinct and sorted: the OAHE fleet gives ("inverter@oahe.example",
    "site@oahe.example"); a fleet with no engineer gives ()."""
    emails = {asset.engineer_email for kind in AssetKind for asset in registry.by_kind(conn, kind)
              if asset.engineer_email is not None}
    return tuple(sorted(emails))


def site_engineer(conn: sqlite3.Connection, email: str, site: str) -> str | None:
    """The account's email when it is an active engineer account whose sites hold the site, else None:
    site_engineer(conn, "site@oahe.example", "OAHE") is "site@oahe.example"; an operator, a stopped engineer, one of
    another site and an address with no account give None."""
    try:
        found = account_table.get(conn, email)
    except account_table.AccountError:
        return None
    if found.role is not Role.ENGINEER or not found.active or not found.sees(site):
        return None
    return found.email


def check_engineer(conn: sqlite3.Connection, email: str, asset_id: str) -> None:
    """Refuses an engineer who may not assign a fault or decide a suggestion on the asset: with an active account in
    the store, one site_engineer gives None for the asset's site, UnknownEngineer("crew@bigs.example is not an active
    engineer of site OAHE"), whether or not the fleet names the address; with none, an address the fleet does not hold,
    UnknownEngineer("nobody@example.com is not an engineer the fleet holds"), as SP-015 had it."""
    # Decision: SP-035 (with accounts, an engineer account is an engineer); SP-015 (with none, the fleet's engineers)
    if account_table.any_active(conn):
        site = site_of(asset_id)
        if site_engineer(conn, email, site) is None:
            raise UnknownEngineer(f"{email or 'nobody'} is not an active engineer of site {site}")
    elif email not in known_engineers(conn):
        raise UnknownEngineer(f"{email or 'nobody'} is not an engineer the fleet holds")
