"""The password check (SOL-16): hashlib.scrypt with a fresh 16-byte salt per account, the stored line carrying its own
parameters ("scrypt$16384$8$1$<salt hex>$<hash hex>") so a later change of them reads old lines still, and a constant
time comparison. Nothing here logs, prints or keeps a password; a refusal names the rule, never the value."""
import hashlib
import hmac
import secrets

from solarpunk.leaf.accounts import MIN_PASSWORD

SCHEME = "scrypt"
N, R, P, DKLEN = 16384, 8, 1, 32
SALT_BYTES = 16
SEPARATOR = "$"


class WeakPassword(ValueError):
    """Raised for a password shorter than 12 characters: WeakPassword("a password is at least 12 characters")."""


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    """The scrypt hash of a password with a salt and parameters."""
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=DKLEN, maxmem=2 ** 26)


def stored_line(password: str) -> str:
    """The line to store for a new password, with a fresh salt: it starts "scrypt$16384$8$1$" and two calls on one
    password differ; a password under 12 characters raises WeakPassword."""
    if len(password) < MIN_PASSWORD:
        raise WeakPassword(f"a password is at least {MIN_PASSWORD} characters")
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt, N, R, P)
    return SEPARATOR.join((SCHEME, str(N), str(R), str(P), salt.hex(), digest.hex()))


def matches(password: str, line: str) -> bool:
    """Whether a password is the one a stored line was made from, read with the line's own parameters and compared in
    constant time; a line of another scheme or shape is False, never an error that could say why."""
    parts = line.split(SEPARATOR)
    if len(parts) != 6 or parts[0] != SCHEME:
        return False
    _, n, r, p, salt, digest = parts
    try:
        found = _derive(password, bytes.fromhex(salt), int(n), int(r), int(p))
    except ValueError:
        return False
    return hmac.compare_digest(found, bytes.fromhex(digest))
