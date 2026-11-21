"""What a failing test does (13.4, SP-020, SP-049): a test declares REACTIONS, for each kind it runs on a tuple of the
closed set REACTIONS_SET, and the scheduled run carries them out (project/reactions.py). Fault("SEN-001") raises that
catalogue fault itself (a failing test raises its fault, SP-046; Suggest(code) is Fault(code)), Mail() mails the asset's
engineers once at the first failure of a streak, RunSuite("deep_check") runs that suite on the asset at once, and
OpenPreventive("grease the bearing") opens a preventive work order. The set holds nothing that commands equipment, and
a test that names an action outside it, a code the catalogue lacks, a second fault for one kind, a suite the folder lacks
or a chain of started suites that loops or runs deeper than MAX_CHAIN is refused at load, so a typo fails at once.
Each reaction carried out, or skipped, is a row of the append-only reactions table. This module imports the leaf alone
(MOD-05): the registry checks a module's declarations with it, and project carries them out."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from solarpunk.leaf.clock import utc
from solarpunk.leaf.codes import GENERIC_TEST_FAILURE, AssetKind, codes_for

MAX_CHAIN = 3  # suites one failure may start one after another: a fourth is skipped, and a declared deeper chain refused
SKIPPED = "skipped: "
# The SQL lives here, at module level, where mutmut does not reach (docs/MUTATION.md, J-008).
SCHEMA = ("CREATE TABLE reactions (reaction_id INTEGER PRIMARY KEY, result_id INTEGER NOT NULL, "
          "action TEXT NOT NULL, detail TEXT NOT NULL, at TEXT NOT NULL)",)
INSERT = "INSERT INTO reactions (result_id, action, detail, at) VALUES (?, ?, ?, ?)"
OF_RESULT = "SELECT reaction_id, result_id, action, detail, at FROM reactions WHERE result_id = ? ORDER BY reaction_id"
ALL_ROWS = "SELECT reaction_id, result_id, action, detail, at FROM reactions ORDER BY reaction_id"


@dataclass(frozen=True)
class Fault:
    """Raise the catalogue fault of this code on the asset: Fault("SEN-001"); the generic SIT-004 where a test names none."""

    code: str


@dataclass(frozen=True)
class Mail:
    """Mail the asset's engineers the test and its reason, at the first failure of a streak only: Mail()."""


@dataclass(frozen=True)
class RunSuite:
    """Run this suite on the asset at once: RunSuite("deep_check"); the suite's own failures react in turn."""

    name: str


@dataclass(frozen=True)
class OpenPreventive:
    """Open a preventive work order on the asset with this note, unless one open with it is there: OpenPreventive("grease")."""

    note: str


# The closed set of what a test may declare: a new action is a new member, decided, never free (SP-020). None of them
# commands equipment.
REACTIONS_SET = (Fault, Mail, RunSuite, OpenPreventive)
GENERIC = Fault(GENERIC_TEST_FAILURE)


@dataclass(frozen=True)
class Row:
    """One row of the reactions table: Row(1, 7, "Mail", "mailed a@x.org", "2026-06-01T10:00:00+00:00")."""

    reaction_id: int
    result_id: int
    action: str
    detail: str
    stamp: str


def text(reaction: object) -> str:
    """A reaction as the line prints it: text(Fault("SIT-004")) is "Fault(SIT-004)", text(Mail()) "Mail()",
    text(RunSuite("deep")) "RunSuite(deep)", text(OpenPreventive("grease")) "OpenPreventive(grease)"."""
    fields = ", ".join(str(value) for value in vars(reaction).values())
    return f"{type(reaction).__name__}({fields})"


def with_fault(reactions: tuple) -> tuple:
    """The reactions with a Fault always among them, the generic one where none is named: () is (Fault(SIT-004),);
    (Mail(),) is (Fault(SIT-004), Mail()); (Fault("SEN-001"),) is itself."""
    return reactions if any(isinstance(item, Fault) for item in reactions) else (GENERIC, *reactions)


def fault_code_of(reactions: tuple) -> str:
    """The code a failure raises: the Fault reaction's, else the generic SIT-004: (Fault("MTR-001"),) is "MTR-001";
    (Mail(),) is "SIT-004"."""
    return next(item.code for item in with_fault(reactions) if isinstance(item, Fault))


def checked_reactions(module: str, kinds: tuple[AssetKind, ...], suites: frozenset[str],
                      declared: object) -> dict[AssetKind, tuple]:
    """A module's REACTIONS, held to its KINDS, the catalogue and the suites the folder holds (SP-020): {INVERTER:
    (Fault("INV-001"), Mail())} passes; a key not in KINDS, an action outside REACTIONS_SET, a Fault code the
    catalogue lacks or of another kind (SIT-004 is allowed for any), a second Fault for one kind, a RunSuite of a suite
    the folder lacks or an OpenPreventive with no note raises ValueError naming the module."""
    if not isinstance(declared, dict) or not set(declared) <= set(kinds):
        raise ValueError(f"{module}: REACTIONS must be a dict keyed by kinds of its KINDS")
    for kind, reactions in declared.items():
        if not isinstance(reactions, tuple):
            raise ValueError(f"{module}: REACTIONS for {kind.name} is not a tuple")
        for item in reactions:
            check_one(module, kind, suites, item)
        if sum(isinstance(item, Fault) for item in reactions) > 1:
            raise ValueError(f"{module}: REACTIONS names more than one Fault for {kind.name}")
    return dict(declared)


def check_one(module: str, kind: AssetKind, suites: frozenset[str], item: object) -> None:
    """One declared reaction held to the closed set and what it names: Fault("INV-001") for an INVERTER passes;
    Fault("SEN-001") for one raises "names SEN-001, which is no INVERTER code"; RunSuite("nope") raises "names no suite"."""
    if not isinstance(item, REACTIONS_SET):
        raise ValueError(f"{module}: REACTIONS names {item!r}, which is none of "
                         f"{', '.join(member.__name__ for member in REACTIONS_SET)}")
    if isinstance(item, Fault) and item.code != GENERIC_TEST_FAILURE and item.code not in {row.code for row in codes_for(kind)}:
        raise ValueError(f"{module}: REACTIONS names {item.code}, which is no {kind.name} code")
    if isinstance(item, RunSuite) and item.name not in suites:
        raise ValueError(f"{module}: REACTIONS runs suite {item.name}, which the folder does not hold")
    if isinstance(item, OpenPreventive) and not (isinstance(item.note, str) and item.note.strip()):
        raise ValueError(f"{module}: OpenPreventive needs a note")


def chain_problem(started: dict[str, tuple[str, ...]], contents: dict[str, tuple[str, ...]]) -> str | None:
    """Why the suites tests start loop or run too deep, or None: started maps a test to the suites its reactions run,
    contents a suite to its tests. {"a": ("s",)} with s holding a is "suite s starts itself (s, s)"; a chain of four
    suites is "starts 4 suites in a row, more than 3"."""
    def walk(suite: str, trail: tuple[str, ...]) -> str | None:
        """The first problem of the chains running on from this suite along the trail of suites started so far."""
        if suite in trail:
            return f"suite {suite} starts itself ({' -> '.join((*trail[trail.index(suite):], suite))})"
        trail = (*trail, suite)
        if len(trail) > MAX_CHAIN:
            return f"a failure starts {len(trail)} suites in a row ({' -> '.join(trail)}), more than {MAX_CHAIN}"
        for test in contents.get(suite, ()):
            for following in started.get(test, ()):
                if (found := walk(following, trail)) is not None:
                    return found
        return None
    for tests in started.values():
        for suite in tests:
            if (found := walk(suite, ())) is not None:
                return found
    return None


def schema() -> tuple[str, ...]:
    """The statements that make the reactions table: schema()[0] starts with "CREATE TABLE reactions"."""
    return SCHEMA


def record(conn: sqlite3.Connection, result_id: int, action: str, detail: str, moment: datetime) -> None:
    """Stores one reaction and commits: record(c, 7, "Mail", "mailed a@x.org", 10:00 UTC) adds a row; a reaction not
    carried out has the detail "skipped: <why>"; rows are only added, never changed; a naive instant raises NotUtc."""
    conn.execute(INSERT, (result_id, action, detail, utc(moment).isoformat()))
    conn.commit()


def of_result(conn: sqlite3.Connection, result_id: int) -> tuple[Row, ...]:
    """The reactions a result had, in the order they were carried out: of a failed result with a Fault and a Mail, two."""
    return tuple(Row(*row) for row in conn.execute(OF_RESULT, (result_id,)))


def all_rows(conn: sqlite3.Connection) -> tuple[Row, ...]:
    """Every reaction stored, oldest first; an empty table gives ()."""
    return tuple(Row(*row) for row in conn.execute(ALL_ROWS))
