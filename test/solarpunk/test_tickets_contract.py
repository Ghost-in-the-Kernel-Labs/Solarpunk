"""SOL-14 held to the leaf (8.1): the contract's three tables (the moves, the targets, the field owners) read from
docs/CONTRACT.md and compared with solarpunk/leaf/tickets.py, so neither changes without the other; the worked example
as a golden, state by state; every move the table lacks refused; a planted break shows the table reader can fail."""
import re
import unittest
from datetime import timedelta

from solarpunk.leaf.clock import NotUtc, at
from solarpunk.leaf.codes import Severity
from solarpunk.leaf.tickets import (
    MOVES,
    OWNERS,
    TARGETS,
    BadMove,
    Priority,
    TargetState,
    TicketStatus,
    check_move,
    priority_of,
    target_state,
)
from test.support import ROOT

ROW = re.compile(r"^\| ([^|]+?) \| ([^|]+?) \|(?: ([^|]+?) \|)?(?: ([^|]+?) \|)?$", re.MULTILINE)
HOURS = re.compile(r"^(\d+) h$")


def section(contract: str) -> str:
    """SOL-14's text, up to the next section: section(CONTRACT) starts "## SOL-14"."""
    start = contract.index("## SOL-14")
    following = contract.find("\n## ", start + 1)
    return contract[start:] if following < 0 else contract[start:following]


def table(text: str, header: str) -> list[tuple[str, ...]]:
    """The rows of the table whose header row starts "| <header> |", header and rule left out: table(SOL14, "From")
    gives [("open", "acknowledged"), …]."""
    start = text.index(f"| {header} |")
    rows = []
    for line in text[start:].splitlines()[2:]:
        if not line.startswith("|"):
            break
        rows.append(tuple(cell.strip() for cell in line.strip("|").split("|")))
    return rows


def hours(cell: str) -> timedelta:
    """A table cell "4 h" as timedelta(hours=4); any other shape raises ValueError."""
    found = HOURS.match(cell)
    if found is None:
        raise ValueError(f"not a number of hours: {cell!r}")
    return timedelta(hours=int(found.group(1)))


def moves_of(text: str) -> set[tuple[TicketStatus, TicketStatus]]:
    """The moves the contract's table allows, as statuses: {(OPEN, ACKNOWLEDGED), …}."""
    return {(TicketStatus(source), TicketStatus(target)) for source, target in table(text, "From")}


def targets_of(text: str) -> dict[Severity, tuple[Priority, timedelta, timedelta]]:
    """The contract's targets by severity: {Severity.OUTAGE: (Priority.P1, 1 h, 4 h), …}."""
    return {Severity[sev]: (Priority(pri), hours(ack), hours(resp)) for sev, pri, ack, resp in table(text, "Severity")}


SOL14 = section((ROOT / "docs" / "CONTRACT.md").read_text(encoding="utf-8"))


class TheContractAndTheLeafAgree(unittest.TestCase):
    def test_the_moves(self) -> None:
        self.assertEqual(moves_of(SOL14), set(MOVES))

    def test_the_priorities_and_targets(self) -> None:
        leaf = {sev: (priority_of(sev), TARGETS[priority_of(sev)].acknowledge, TARGETS[priority_of(sev)].respond)
                for sev in Severity}
        self.assertEqual(targets_of(SOL14), leaf)

    def test_the_field_owners(self) -> None:
        self.assertEqual(dict(table(SOL14, "Field")), OWNERS)

    def test_a_planted_break_is_caught(self) -> None:
        broken = SOL14.replace("| resolved | closed |", "| resolved | open |")
        self.assertNotEqual(moves_of(broken), set(MOVES))
        with self.assertRaises(ValueError):
            targets_of(SOL14.replace("| 1 h | 4 h |", "| an hour | 4 h |"))


class TheWorkedExample(unittest.TestCase):
    def test_the_outage_acknowledged_in_time_and_responded_late(self) -> None:
        opened = at(2026, 6, 1, 10)
        p1 = TARGETS[priority_of(Severity.OUTAGE)]
        self.assertIs(target_state(opened, p1.acknowledge, at(2026, 6, 1, 10, 40), at(2026, 6, 1, 15)), TargetState.MET)
        self.assertIs(target_state(opened, p1.respond, at(2026, 6, 1, 14, 30), at(2026, 6, 1, 15)), TargetState.LATE)
        self.assertIs(target_state(opened, p1.respond, None, at(2026, 6, 1, 13)), TargetState.PENDING)
        self.assertIs(target_state(opened, p1.respond, None, at(2026, 6, 1, 14, 15)), TargetState.OVERDUE)

    def test_the_derate_still_open_at_three(self) -> None:
        opened, now = at(2026, 6, 1, 10), at(2026, 6, 1, 15)
        p2 = TARGETS[priority_of(Severity.DERATE)]
        self.assertIs(target_state(opened, p2.acknowledge, None, now), TargetState.OVERDUE)
        self.assertIs(target_state(opened, p2.respond, None, now), TargetState.PENDING)

    def test_the_due_instant_itself_is_in_time_and_instants_are_utc(self) -> None:
        opened = at(2026, 6, 1, 10)
        self.assertIs(target_state(opened, timedelta(hours=1), at(2026, 6, 1, 11), at(2026, 6, 1, 12)), TargetState.MET)
        self.assertIs(target_state(opened, timedelta(hours=1), None, at(2026, 6, 1, 11)), TargetState.PENDING)
        with self.assertRaises(NotUtc):
            target_state(opened.replace(tzinfo=None), timedelta(hours=1), None, opened)


class TheMoves(unittest.TestCase):
    def test_every_move_the_table_lacks_is_refused_by_name(self) -> None:
        for source in TicketStatus:
            for target in TicketStatus:
                with self.subTest(move=(source.value, target.value)):
                    if (source, target) in MOVES:
                        self.assertIs(check_move(source, target), target)
                    else:
                        with self.assertRaises(BadMove) as caught:
                            check_move(source, target)
                        self.assertEqual(str(caught.exception),
                                         f"a ticket cannot move from {source.value} to {target.value}")

    def test_closed_is_final(self) -> None:
        self.assertEqual([t for s, t in MOVES if s is TicketStatus.CLOSED], [])


if __name__ == "__main__":
    unittest.main()
