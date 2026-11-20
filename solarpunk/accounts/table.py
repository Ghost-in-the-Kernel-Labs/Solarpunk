"""The accounts table (12.1, SOL-16): one row per account, its email the key, its role, whether it is active, when it
was made, its site scope, and its password's stored line (passwords.stored_line), never the password. A check of a
password gives the account back or None, saying no more than that. Accounts are never deleted (12.5 stops them). A
failed sign-in is kept with the account it named and its instant, never what was typed for the password (12.3). A
password is replaced by a new stored line, and an account is stopped by its active flag, its row kept (12.5)."""
import sqlite3
from datetime import datetime

from solarpunk.accounts import passwords
from solarpunk.leaf.accounts import ALL_SITES, Account, Role
from solarpunk.leaf.clock import utc

CREATE_TABLE = (
    "CREATE TABLE IF NOT EXISTS accounts (email TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL CHECK (role IN"
    " ('engineer', 'operator', 'viewer', 'admin')), active INTEGER NOT NULL, created TEXT NOT NULL, sites TEXT NOT NULL,"
    " secret TEXT NOT NULL)"
)
CREATE_FAILURES = (
    "CREATE TABLE IF NOT EXISTS failed_sign_ins (failure_id INTEGER PRIMARY KEY, account TEXT NOT NULL, at TEXT NOT NULL)"
)
NO_SUCH_ACCOUNT = "no such account"
COLUMNS = "email, name, role, active, created, sites"
SITE_SEPARATOR = ","


class AccountError(ValueError):
    """Raised for an account refused: AccountError("site@oahe.example already has an account")."""


def schema() -> tuple[str, ...]:
    """The accounts table and the failed sign-ins', for leaf.store.apply."""
    return (CREATE_TABLE, CREATE_FAILURES)


def upgrade(conn: sqlite3.Connection) -> None:
    """Gives a store made before 12.3 the failed sign-ins' table; one that has it is left as it is."""
    conn.execute(CREATE_FAILURES)
    conn.commit()


def _account(row: tuple) -> Account:
    """A stored row as an Account, without its secret."""
    email, name, role, active, created, sites = row
    return Account(email, name, Role(role), bool(active), datetime.fromisoformat(created),
                   tuple(sites.split(SITE_SEPARATOR)))


def add(conn: sqlite3.Connection, email: str, name: str, role: Role, password: str, sites: tuple[str, ...],
        created: datetime) -> Account:
    """Makes an active account: add(conn, "site@oahe.example", "Site engineer", ENGINEER, <a password>, ("OAHE",),
    10:00 UTC); an admin's sites are all whatever is given. A second account of one email, a blank email or name, no
    site, or a weak password (WeakPassword) raises and stores nothing."""
    email, name = email.strip(), name.strip()
    if not email or not name:
        raise AccountError("an account needs an email and a name")
    scope = (ALL_SITES,) if role is Role.ADMIN else tuple(site.strip() for site in sites if site.strip())
    if not scope:
        raise AccountError(f"{email} needs a site, or {ALL_SITES} for all")
    secret = passwords.stored_line(password)
    try:
        conn.execute(f"INSERT INTO accounts ({COLUMNS}, secret) VALUES (?, ?, ?, 1, ?, ?, ?)",
                     (email, name, role.value, utc(created).isoformat(), SITE_SEPARATOR.join(scope), secret))
    except sqlite3.IntegrityError:
        raise AccountError(f"{email} already has an account") from None
    conn.commit()
    return get(conn, email)


def get(conn: sqlite3.Connection, email: str) -> Account:
    """The account of an email; none raises AccountError("nobody@x has no account")."""
    row = conn.execute(f"SELECT {COLUMNS} FROM accounts WHERE email = ?", (email.strip(),)).fetchone()
    if row is None:
        raise AccountError(f"{email} has no account")
    return _account(row)


def every(conn: sqlite3.Connection) -> tuple[Account, ...]:
    """Every account, by email."""
    return tuple(_account(row) for row in conn.execute(f"SELECT {COLUMNS} FROM accounts ORDER BY email"))


def check(conn: sqlite3.Connection, email: str, password: str) -> Account | None:
    """The account when the password is its own and the account is active, else None: a wrong password, an unknown
    email and a stopped account answer the same, so a refusal tells nobody which."""
    row = conn.execute(f"SELECT {COLUMNS}, secret FROM accounts WHERE email = ?", (email.strip(),)).fetchone()
    if row is None or not passwords.matches(password, row[-1]):
        return None
    account = _account(row[:-1])
    return account if account.active else None


def record_failure(conn: sqlite3.Connection, email: str, at: datetime) -> None:
    """Keeps a failed sign-in: the account's email when it names one, else "no such account", so a password typed into
    the email field by mistake is never stored; and its instant. Nothing of the password is kept."""
    named = conn.execute("SELECT email FROM accounts WHERE email = ?", (email.strip(),)).fetchone()
    conn.execute("INSERT INTO failed_sign_ins (account, at) VALUES (?, ?)",
                 (named[0] if named else NO_SUCH_ACCOUNT, utc(at).isoformat()))
    conn.commit()


def failures(conn: sqlite3.Connection) -> tuple[tuple[str, datetime], ...]:
    """Every failed sign-in, oldest first, as (account, instant): (("site@oahe.example", 11:00 UTC),)."""
    rows = conn.execute("SELECT account, at FROM failed_sign_ins ORDER BY failure_id")
    return tuple((account, datetime.fromisoformat(at)) for account, at in rows)


def any_active(conn: sqlite3.Connection) -> bool:
    """Whether the store holds an active account: False for a store with none, so its windows open as before 12.3."""
    return conn.execute("SELECT 1 FROM accounts WHERE active = 1 LIMIT 1").fetchone() is not None


def set_password(conn: sqlite3.Connection, email: str, password: str) -> Account:
    """Replaces an account's stored line with a new password's, fresh salt and all; the account is unchanged
    otherwise. An email with no account raises AccountError, a weak password WeakPassword, each storing nothing."""
    found = get(conn, email)
    conn.execute("UPDATE accounts SET secret = ? WHERE email = ?", (passwords.stored_line(password), found.email))
    conn.commit()
    return found


def deactivate(conn: sqlite3.Connection, email: str) -> Account:
    """Stops an account: its active flag false, its row and email kept, so every record that names it keeps the name
    (SP-022); an email with no account raises AccountError."""
    found = get(conn, email)
    conn.execute("UPDATE accounts SET active = 0 WHERE email = ?", (found.email,))
    conn.commit()
    return get(conn, found.email)


def any_admin(conn: sqlite3.Connection) -> bool:
    """Whether the store holds an admin account, active or not."""
    return conn.execute("SELECT 1 FROM accounts WHERE role = ? LIMIT 1", (Role.ADMIN.value,)).fetchone() is not None


def active_admins(conn: sqlite3.Connection) -> int:
    """How many active admin accounts the store holds."""
    return conn.execute("SELECT COUNT(*) FROM accounts WHERE role = ? AND active = 1", (Role.ADMIN.value,)).fetchone()[0]
