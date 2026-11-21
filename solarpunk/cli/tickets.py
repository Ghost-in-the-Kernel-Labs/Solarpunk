"""The ticket commands (11.2, SOL-14): `ticket list` (the open tickets, the nearest target first, a breach marked),
`ticket show ID` (its line, its moves and the failed results it holds), `ticket open --result ID` (a ticket opens from a
failed test result, 7.9, SP-046), `ticket ack ID`, `ticket comment ID WORDS…` and `ticket resolve ID --done WORDS…`, each one project call
(MOD-02) at the instant --at names, now when it names none, as the account signed in (12.4; a store with no accounts
names a comment's author with --by). main.py adds them to its parser."""
import argparse
import sqlite3
from datetime import datetime, timezone
from typing import TextIO

from solarpunk import project
from solarpunk.cli.signin import acting, attributed

BREACH = "  PAST TARGET"
LINE = "{wo_id}  {asset}  {priority}  {status}  acknowledge {ack}  respond {respond}{breach}"
NONE_OPEN = "no open ticket"
NO_TARGET = "—"
MOVE = "  {at}  {status}  {who}"
NOBODY = "nobody signed in"
RESULT = "  result {result_id}  {test}  {at}  {reason}"


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


def view_line(view: project.TicketView) -> str:
    """One ticket's line, as `ticket list` writes it: "1  OAHE-INV-002  P1  open  acknowledge overdue (due …)  respond
    pending (due …)  PAST TARGET"."""
    found = view.ticket
    return LINE.format(wo_id=found.wo_id, asset=found.asset_id,
                       priority=NO_TARGET if found.priority is None else found.priority.value,
                       status=found.status.value, ack=state_text(view.acknowledge, view.acknowledge_due),
                       respond=state_text(view.respond, view.respond_due), breach=BREACH if view.breached else "")


def move_line(found: project.Move) -> str:
    """One move of a ticket's history: "  2026-06-01T11:40:00+00:00  acknowledged  ops@oahe.example"; a move made where
    nobody was signed in names "nobody signed in" (SP-035)."""
    return MOVE.format(at=found.moment.isoformat(), status=found.status.value, who=found.actor or NOBODY)


def ticket_show(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """ticket show 1 [--as EMAIL] [--at INSTANT]: the ticket's line, then one line per move, oldest first, whatever its
    status, when the account sees its site (SP-039); a ticket never moved has no move line."""
    found, moves = project.moves_for(conn, args.account, args.wo_id)
    out.write(view_line(project.view_of(found, moment_of(args))) + "\n")
    for made in moves:
        out.write(move_line(made) + "\n")
    for result in project.results_of_ticket(conn, args.wo_id):
        out.write(RESULT.format(result_id=result.result_id, test=result.test_name, at=result.run_at.isoformat(),
                                reason=result.reason) + "\n")


def ticket_list(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """ticket list [--at INSTANT]: one line per open ticket, the nearest target first; the demo's at 13:00 is
    "1  OAHE-INV-002  P1  open  acknowledge overdue (due 2026-06-01T12:30:00+00:00)  respond pending (due …)  PAST
    TARGET"; none open prints "no open ticket"."""
    views = project.tickets_by_target(conn, moment_of(args))
    for view in views:
        out.write(view_line(view) + "\n")
    if not views:
        out.write(NONE_OPEN + "\n")


def ticket_open(conn: sqlite3.Connection, args: argparse.Namespace, out: TextIO) -> None:
    """ticket open --result 2 --by site@oahe.example [--at INSTANT]: opens the ticket for a failed test result, as the
    account signed in or as named (--as; --for an engineer's word; with no accounts --by [--recorded-by]), and prints "1
    opened on result 2 (2 failed results: 1, 2)"; a result already in a ticket prints that ticket, "1 already open on
    result 1 (…)", opening none; a pass, no data or an unstored result is refused, "error: result 9 is not stored" (7.9)."""
    found = project.open_ticket_from_result_as(conn, args.account, args.result, moment_of(args), args.by,
                                               args.recorded_by, args.for_engineer)
    held = ", ".join(str(result.result_id) for result in found.results)
    state = "opened" if found.opened else "already open"
    out.write(f"{found.ticket.wo_id} {state} on result {args.result} ({len(found.results)} failed results: {held})\n")


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
    """ticket resolve 1 --done fuse swapped: resolves and closes the ticket and its fault once the fault's root cause is
    written (`fault cause`, SP-046); prints "1 closed"; without it, "error: fault 1 has no root cause written: …"."""
    found = project.resolve_ticket_as(conn, args.account, args.wo_id, " ".join(args.done), moment_of(args))
    out.write(f"{found.wo_id} {found.status.value}\n")


def add_tickets(commands: argparse._SubParsersAction) -> None:
    """The ticket subcommands: "ticket ack 1" parses to ticket_ack with wo_id 1; each takes --at."""
    ticket = commands.add_parser("ticket").add_subparsers(required=True)
    listing = ticket.add_parser("list")
    listing.set_defaults(handler=ticket_list)
    show = acting(ticket.add_parser("show"))
    show.add_argument("wo_id", type=int)
    show.set_defaults(handler=ticket_show)
    opening = attributed(acting(ticket.add_parser("open")))
    opening.add_argument("--result", type=int, required=True,
                         help="the failed result's id (ids: solarpunk test results --asset ID --failed)")
    opening.set_defaults(handler=ticket_open)
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
    resolve.add_argument("--done", nargs="+", required=True)
    resolve.set_defaults(handler=ticket_resolve)
    for parser in (listing, show, opening, ack, comment, resolve):
        parser.add_argument("--at")
