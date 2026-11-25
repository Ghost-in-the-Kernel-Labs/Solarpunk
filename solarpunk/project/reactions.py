"""Carrying out what a failing test declared (13.4, SP-020): for each failed result of a run (not no data, not a pass)
the reactions of its test for the asset's kind, each recorded as a row of the reactions table, one per reaction
carried out and one saying "skipped: <why>" for one not. Fault is SP-046's (the failure raises its fault and joins its
streak's ticket), Mail() mails the asset's engineers through the mailer at the first failure of a streak only,
RunSuite(name) runs that suite on that asset at once, its own failures reacting in turn down to MAX_CHAIN suites, and
OpenPreventive(note) opens a preventive order unless an open one with the note is already on the asset. Nothing here
commands equipment (SP-020); the status mail of the run (project/run.py) is a separate thing and is unchanged."""
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

from solarpunk.fleet import registry
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.faults import TEST_ASSIGNER
from solarpunk.leaf.telemetry import Sample
from solarpunk.mailer import mail as mailer
from solarpunk.mailer import transport
from solarpunk.project.result_tickets import join_streak
from solarpunk.project.suggest import raise_fault
from solarpunk.remote import reactions as table
from solarpunk.remote import results as result_table
from solarpunk.remote import run as remote
from solarpunk.remote import suite_registry
from solarpunk.remote.acquire import Acquirer
from solarpunk.remote.reactions import MAX_CHAIN, Fault, Mail, OpenPreventive, RunSuite
from solarpunk.remote.registry import BadRemoteTest, RemoteTest, discover, with_ping
from solarpunk.remote.results import Recorded
from solarpunk.workorders import ledger as work_ledger

PREVENTIVE = "preventive"


@dataclass
class Carrying:
    """What a run carries its reactions out with: the connection, the instant, the assets by id and their stored samples,
    the mail settings (None: no mail is sent), the acquirer, the tests that hold the reactions, and the mails sent."""

    conn: sqlite3.Connection
    run_at: datetime
    assets: dict[str, Asset]
    samples: dict[str, tuple[Sample, ...]]
    settings: transport.Settings | None
    acquirer: Acquirer | None
    held: dict[str, RemoteTest]
    mails: int = 0
    done: set[int] = field(default_factory=set)  # the results already reacted to, so none reacts twice


def skipped(why: str) -> str:
    """The detail of a reaction not carried out: skipped("an open order already holds it") is "skipped: an open order
    already holds it"."""
    return table.SKIPPED + why


def fault_reaction(doing: Carrying, found: Recorded, asset: Asset, item: Fault) -> str:
    """Raises the fault of the result as 7.7 does and joins its streak's ticket: a failing reachable on a sensor gives
    "SEN-001 raised", on a second failure "SEN-001 already open"."""
    raised = raise_fault(doing.conn, asset.asset_id, item.code, TEST_ASSIGNER.format(name=found.test_name), doing.run_at)
    join_streak(doing.conn, found)
    return f"{item.code} {'raised' if raised is not None else 'already open'}"


def mail_reaction(doing: Carrying, found: Recorded, asset: Asset) -> str:
    """Mails the asset's engineers the test and its reason at the first failure of a streak: a streak already mailed, no
    settings, no engineer or a mail that cannot go give "skipped: <why>"; a mail sent is recorded as the run's others."""
    previous = result_table.previous_of(doing.conn, found)
    if previous is not None and previous.failed:
        return skipped("the streak was mailed at its first failure")
    if doing.settings is None:
        return skipped("no mail settings")
    try:
        mail = mailer.compose_degradation(asset, mailer.RemoteFailure(found.test_name, found.reason),
                                          registry.engineers_for(doing.conn, asset.asset_id), doing.run_at)
        transport.send(mail, doing.settings)
    except (mailer.NoEngineer, transport.MailError) as refused:
        return skipped(str(refused))
    mailer.record(doing.conn, mail, asset.asset_id, doing.run_at)
    doing.mails += 1
    return f"mailed {', '.join(mail.recipients)}"


def preventive_reaction(doing: Carrying, asset: Asset, item: OpenPreventive) -> str:
    """Opens a preventive order with the note unless an open preventive order with it is on the asset: the first gives
    "opened work order 4", the next run's "skipped: an open preventive order with this note is already on it"."""
    for order in work_ledger.by_asset(doing.conn, asset.asset_id):
        if order.kind == PREVENTIVE and order.closed is None and order.note == item.note:
            return skipped("an open preventive order with this note is already on it")
    return f"opened work order {work_ledger.open_preventive(doing.conn, asset.asset_id, doing.run_at, item.note).wo_id}"


def suite_reaction(doing: Carrying, asset: Asset, item: RunSuite, depth: int) -> str:
    """Runs the suite on the asset at once, its results stored under the suite's name, and lets its failures react in
    turn one suite deeper; at MAX_CHAIN suites deep it is skipped: "ran deep_check: 2 results"."""
    if depth >= MAX_CHAIN:
        return skipped(f"the chain is {MAX_CHAIN} suites deep")
    try:
        suite = suite_registry.named(item.name)
    except BadRemoteTest as refused:
        return skipped(str(refused))
    written = remote.run_named(doing.conn, suite, (asset,), doing.samples, doing.run_at, doing.acquirer)
    for found in failed_at(doing, asset.asset_id, suite.name):
        react(doing, found, depth + 1)
    return f"ran {suite.name}: {written} results"


def failed_at(doing: Carrying, asset_id: str, suite: str | None = None) -> list[Recorded]:
    """The asset's failed results at the run's instant, oldest first, of one suite when it is named."""
    return sorted((found for found in result_table.results_of(doing.conn, asset_id)
                   if found.failed and found.run_at == doing.run_at and (suite is None or found.suite == suite)),
                  key=lambda found: found.result_id)


def react(doing: Carrying, found: Recorded, depth: int = 0) -> None:
    """Carries out one failed result's reactions in the order declared, the fault first, recording each: a test the
    registry no longer holds reacts with the generic fault alone."""
    # Decision: SP-020 (a failing test does what it declared, from the closed set, each reaction recorded)
    if found.result_id in doing.done:
        return
    doing.done.add(found.result_id)
    asset = doing.assets[found.asset_id]
    test = doing.held.get(found.test_name)
    for item in table.with_fault(() if test is None else test.reactions.get(asset.kind, ())):
        if isinstance(item, Fault):
            detail = fault_reaction(doing, found, asset, item)
        elif isinstance(item, Mail):
            detail = mail_reaction(doing, found, asset)
        elif isinstance(item, OpenPreventive):
            detail = preventive_reaction(doing, asset, item)
        else:
            detail = suite_reaction(doing, asset, item, depth)
        table.record(doing.conn, found.result_id, type(item).__name__, detail, doing.run_at)


def carry_out(conn: sqlite3.Connection, fed: tuple[Asset, ...], samples: dict[str, tuple[Sample, ...]], run_at: datetime,
              settings: transport.Settings | None = None, acquirer: Acquirer | None = None,
              held: dict[str, RemoteTest] | None = None) -> int:
    """Carries out the reactions of every failed result the run stored at run_at for the assets given, and returns the
    mails sent: one failing reachable on a sensor with the default reactions records one Fault row; a no data result
    and a pass record none. held is the tests whose reactions count, the registry's unless a test hands its own."""
    doing = Carrying(conn, run_at, {asset.asset_id: asset for asset in fed}, samples, settings, acquirer,
                     with_ping(discover()) if held is None else held)
    for asset in fed:
        for found in failed_at(doing, asset.asset_id):
            react(doing, found)
    return doing.mails

