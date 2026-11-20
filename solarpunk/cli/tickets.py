"""The ticket commands (11.2, SOL-14): `ticket list` (the open tickets, the nearest target first, a breach marked),
`ticket ack ID`, `ticket comment ID WORDS…` and `ticket resolve ID --cause CODE --done WORDS…`, each one project call
(MOD-02) at the instant --at names, now when it names none, as the account signed in (12.4; a store with no accounts
names a comment's author with --by). main.py adds them to its parser."""
import argparse
import sqlite3
from datetime import datetime, timezone
from typing import TextIO

from solarpunk import project
from solarpunk.cli.signin import acting

BREACH = "  PAST TARGET"
LINE = "{wo_id}  {asset}  {priority}  {status}  acknowledge {ack}  respond {respond}{breach}"
NONE_OPEN = "no open ticket"
NO_TARGET = "—"


def moment_of(args: argparse.Namespace) -> datetime:
    """The instant a command acts at: --at as written, else now in UTC."""
    return datetime.fromisoformat(args.at) if args.at else datetime.now(timezone.utc)


def state_text(state: project.TargetState | None, due: datetime | None) -> str:
    """A target in one word and its due instant: "overdue (due 2026-06-01T12:30:00+00:00)", "met", "—"."""
    if state is None or due is None:
        return NO_TARGET
    if state in (project.TargetState.MET, project.TargetState.LATE):
        return state.value
    return f"{state.value} (due {due.isoformat()})"


def ticket_list(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """ticket list [--at INSTANT]: one line per open ticket, the nearest target first; the demo's at 13:00 is
    "1  OAHE-INV-002  P1  open  acknowledge overdue (due 2026-06-01T12:30:00+00:00)  respond pending (due …)  PAST
    TARGET"; none open prints "no open ticket"."""
    views = project.tickets_by_target(conn, moment_of(args))
    for view in views:
        found = view.ticket
        out.write(LINE.format(wo_id=found.wo_id, asset=found.asset_id,
                              priority=NO_TARGET if found.priority is None else found.priority.value,
                              status=found.status.value, ack=state_text(view.acknowledge, view.acknowledge_due),
                              respond=state_text(view.respond, view.respond_due),
                              breach=BREACH if view.breached else "") + "\n")
    if not views:
        out.write(NONE_OPEN + "\n")


def ticket_ack(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """ticket ack 1 [--at INSTANT]: acknowledges the ticket; prints "1 acknowledged"."""
    found = project.move_ticket_as(conn, args.account, args.wo_id, project.TicketStatus.ACKNOWLEDGED, moment_of(args))
    out.write(f"{found.wo_id} {found.status.value}\n")


def ticket_comment(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """ticket comment 1 --as site@oahe.example on my way: keeps the comment by the account signed in; prints "1 comment 1
    by site@oahe.example" (12.4); a store with no accounts names the author, --by site@oahe.example."""
    found = project.comment_on_ticket_as(conn, args.account, args.wo_id, moment_of(args), " ".join(args.words), args.by)
    out.write(f"{args.wo_id} comment {found.comment_id} by {found.author}\n")


def ticket_resolve(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """ticket resolve 1 --cause RC-COMPONENT --done fuse swapped: resolves and closes the ticket and its fault; prints
    "1 closed RC-COMPONENT"."""
    found = project.resolve_ticket_as(conn, args.account, args.wo_id, " ".join(args.done), args.cause, moment_of(args))
    out.write(f"{found.wo_id} {found.status.value} {args.cause}\n")


def add_tickets(commands: argparse._SubParsersAction) -> None:
    """The ticket subcommands: "ticket ack 1" parses to ticket_ack with wo_id 1; each takes --at."""
    ticket = commands.add_parser("ticket").add_subparsers(required=True)
    listing = ticket.add_parser("list")
    listing.set_defaults(handler=ticket_list)
    ack = acting(ticket.add_parser("ack"))
    ack.add_argument("wo_id", type=int)
    ack.set_defaults(handler=ticket_ack)
    comment = acting(ticket.add_parser("comment"))
    comment.add_argument("wo_id", type=int)
    comment.add_argument("--by")
    comment.add_argument("words", nargs="+")
    comment.set_defaults(handler=ticket_comment)
    resolve = acting(ticket.add_parser("resolve"))
    resolve.add_argument("wo_id", type=int)
    resolve.add_argument("--cause", required=True)
    resolve.add_argument("--done", nargs="+", required=True)
    resolve.set_defaults(handler=ticket_resolve)
    for parser in (listing, ack, comment, resolve):
        parser.add_argument("--at")
