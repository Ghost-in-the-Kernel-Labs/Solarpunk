"""Sending a mail: the settings (server, port, sender, STARTTLS, the name of the credential's environment variable),
read from a JSON file the caller names and never from the repository, and `send` over `smtplib` to that server, one
code path for Microsoft 365 and any Linux SMTP host (SP-009). The credential is read from the one environment variable
the settings name and goes to `login` alone: it is never put in a string, a message, a log line or a return (the
supply-chain rules). It imports the standard library alone."""
import json
import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from solarpunk.mailer.mail import Mail

SMTP_TIMEOUT_S = 10
SETTING_TYPES: dict[str, tuple[type, ...]] = {
    "host": (str,),
    "port": (int,),
    "sender": (str,),
    "starttls": (bool,),
    "password_variable": (str, type(None)),
    "username": (str, type(None)),
}
UNREADABLE = "{path}: not a readable JSON object of mail settings"
MISSING_KEY = "mail settings lack the key {key!r}"
WRONG_TYPE = "mail setting {key!r} is not of type {types}"
TYPE_SEPARATOR = " or "
SEND_FAILED = "mail to {host}:{port} was not sent"
HEADER_FROM = "From"
HEADER_TO = "To"
HEADER_SUBJECT = "Subject"
RECIPIENT_SEPARATOR = ", "


class BadSettings(ValueError):
    """Raised for a settings file that is not a JSON object, lacks a key or holds a value of the wrong type; it names
    the path or the key and never echoes the file: BadSettings("mail settings lack the key 'host'")."""


class MailError(ValueError):
    """Raised when the SMTP exchange fails; it names the host and port alone: MailError("mail to 127.0.0.1:25 was not sent")."""


@dataclass(frozen=True)
class Settings:
    """Where mail goes: Settings("smtp.office365.com", 587, "ops@example.org", True, "SOLARPUNK_SMTP_PASSWORD",
    "ops@example.org"); password_variable None means no login; username None logs in as the sender."""

    host: str
    port: int
    sender: str
    starttls: bool
    password_variable: str | None
    username: str | None


def _checked(raw: dict[str, object], key: str) -> object:
    """The value of one key, of its type: _checked({"port": 25}, "port") is 25; a missing "port" or "port": "25"
    raises BadSettings naming the key and not the value."""
    if key not in raw:
        raise BadSettings(MISSING_KEY.format(key=key))
    value = raw[key]
    allowed = SETTING_TYPES[key]
    if type(value) not in allowed:
        raise BadSettings(WRONG_TYPE.format(key=key, types=TYPE_SEPARATOR.join(kind.__name__ for kind in allowed)))
    return value


def load_settings(path: Path) -> Settings:
    """The settings a JSON file holds: a file {"host": "127.0.0.1", "port": 25, "sender": "ops@x.org", "starttls": false,
    "password_variable": null, "username": null} gives Settings("127.0.0.1", 25, "ops@x.org", False, None, None); every
    key is required (null where allowed); a missing file or one that is not a JSON object raises BadSettings naming the path."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BadSettings(UNREADABLE.format(path=path)) from None
    if not isinstance(raw, dict):
        raise BadSettings(UNREADABLE.format(path=path))
    checked = {key: _checked(raw, key) for key in SETTING_TYPES}
    return Settings(
        checked["host"], checked["port"], checked["sender"],  # type: ignore[arg-type]
        checked["starttls"], checked["password_variable"], checked["username"],  # type: ignore[arg-type]
    )


def message(mail: Mail, sender: str) -> EmailMessage:
    """The RFC 5322 message of a mail: message(Mail(("a@x.org",), "s", "b"), "ops@x.org")["To"] is "a@x.org" and its
    content is "b\\n"."""
    built = EmailMessage()
    built[HEADER_FROM] = sender
    built[HEADER_TO] = RECIPIENT_SEPARATOR.join(mail.to)
    built[HEADER_SUBJECT] = mail.subject
    built.set_content(mail.body)
    return built


def _login(client: smtplib.SMTP, settings: Settings) -> None:
    """Logs in when the settings name a credential variable and the environment holds it, else does nothing:
    password_variable None, or a variable not set, sends no AUTH. The value goes to login alone, never into a string."""
    if settings.password_variable is None:
        return
    credential = os.environ.get(settings.password_variable)
    if credential is None:
        return
    client.login(settings.username or settings.sender, credential)


def send(mail: Mail, settings: Settings) -> None:
    """Sends one mail over SMTP: send(Mail(("a@x.org",), "s", "b"), Settings("127.0.0.1", 2525, "ops@x.org", False,
    None, None)) delivers it to the server on 127.0.0.1:2525; STARTTLS first when settings.starttls; any SMTP or socket
    failure raises MailError naming host and port alone, with no chained cause."""
    # Decision: SP-009
    try:
        with smtplib.SMTP(settings.host, settings.port, timeout=SMTP_TIMEOUT_S) as client:
            if settings.starttls:
                client.starttls()
            _login(client, settings)
            client.sendmail(settings.sender, list(mail.to), message(mail, settings.sender).as_string())
    except (smtplib.SMTPException, OSError):
        raise MailError(SEND_FAILED.format(host=settings.host, port=settings.port)) from None
