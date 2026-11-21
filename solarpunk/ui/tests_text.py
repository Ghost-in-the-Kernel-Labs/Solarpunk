"""The Manage tests window's words (9.8, SP-030), with no tkinter so the fast loop tests them: a script's row (its
kinds, clauses and the codes a failure suggests, or the reason it cannot load), the line above the list, what the New
test form's fields become, and the command that opens the folder in the system's file manager."""
from collections.abc import Callable
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.codes import GENERIC_TEST_FAILURE

COLUMNS = ("Test", "Kinds", "Clauses", "Suggests", "Problem")
PADDING = 18
WIDEST = 460
NONE = "none"
BROKEN = "broken"


def suggests_text(test: project.RemoteTest) -> str:
    """The codes a failure suggests, in the test's kind order, a kind with none left out: reachable's is "INV-001,
    MTR-001, SEN-001" (a tracker's silence suggests nothing); on_grid's, which suggests nothing, is "none"."""
    codes = [code for code in (test.fault_code(kind) for kind in test.kinds) if code != GENERIC_TEST_FAILURE]
    return ", ".join(codes) or NONE


def row_of(found: project.Surveyed) -> tuple[str, str, str, str, str]:
    """A script's row: a test that loads gives its name, kinds, clauses and suggestions and no problem; one that does
    not gives its name and its reason alone: ("broken", "", "", "", "broken has no CLAUSES")."""
    if found.test is None:
        return found.name, "", "", "", found.problem or ""
    test = found.test
    return found.name, ", ".join(kind.name for kind in test.kinds), ", ".join(test.clauses), suggests_text(test), ""


def summary(entries: tuple[project.Surveyed, ...], folder: Path) -> str:
    """The line above the list: "7 tests in solarpunk/remote/tests"; with one broken "8 scripts in <folder>, 1 cannot
    load"; none "no scripts in <folder>: New test writes one"."""
    if not entries:
        return f"no scripts in {folder}: New test writes one"
    broken = sum(1 for found in entries if found.test is None)
    if broken == 0:
        return f"{len(entries)} test{'s' if len(entries) != 1 else ''} in {folder}"
    return f"{len(entries)} scripts in {folder}, {broken} cannot load"


def words_of(text: str) -> tuple[str, ...]:
    """A field's words, split at commas and spaces, blanks dropped: words_of(" METER, inverter ") is ("METER",
    "inverter")."""
    return tuple(word for word in text.replace(",", " ").split() if word)


def kinds_of(text: str) -> tuple[str, ...]:
    """The kinds field as kind names, upper case: kinds_of("meter, inverter") is ("METER", "INVERTER"); a blank field
    is (), the maintenance list's kinds."""
    return tuple(word.upper() for word in words_of(text))


def written(path: Path) -> str:
    """The line once a test is written: "wrote tracker_moving.py: open the folder, fill in its run, then Reload"."""
    return f"wrote {path.name}: open the folder, fill in its run, then Reload"


def open_command(platform: str, folder: Path) -> list[str]:
    """The command that opens a folder in the system's file manager: ["explorer", folder] on Windows ("win32"),
    ["open", folder] on a Mac ("darwin"), ["xdg-open", folder] elsewhere."""
    if platform == "win32":
        return ["explorer", str(folder)]
    if platform == "darwin":
        return ["open", str(folder)]
    return ["xdg-open", str(folder)]


def cannot_open(folder: Path, error: OSError) -> str:
    """The line when the file manager cannot be started: "cannot open /x: No such file or directory; the folder is /x"."""
    return f"cannot open {folder}: {error.strerror or error}; the folder is {folder}"


def widths(rows: list[tuple[str, ...]], measure: Callable[[str], int]) -> tuple[int, ...]:
    """Each column as wide as its heading or its widest cell plus padding, no wider than WIDEST, so no word is cut
    short below that: with each character 7 px, a Test column whose widest name is "reachable" is 18 + 63 = 81 px."""
    return tuple(min(WIDEST, PADDING + max(measure(text) for text in (heading, *(row[column] for row in rows))))
                 for column, heading in enumerate(COLUMNS))
