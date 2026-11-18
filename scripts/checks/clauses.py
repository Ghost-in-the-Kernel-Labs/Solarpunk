"""The clause register held to its tests (SOL-12; test/test_clauses.py; C-013).

docs/CLAUSE-REGISTER.md's table has one row per claimed clause, `| Clause | Requirement (our words) | Held by |
Status |`; a test under test/solarpunk/iso/ is tagged with a clause when the first line of its docstring is
`Clause: 9001-9.1.3`. Both ways must agree: a `held` row names `<file>::<test>`, a test function in that file tagged
with that row's clause; an `open` row names no test (`—`); every tagged test has a row; no clause has two rows and no
clause is tagged twice. Whether a held test passes is scripts/clauses.py's to say, not this check's. The files are
read from git's list (scripts/checks/common.py; C-001), so a new file is staged (`git add -N`) before the fast loop.
"""
import ast
from pathlib import Path

from scripts.checks.common import matching, tracked_files

REGISTER = "docs/CLAUSE-REGISTER.md"
TESTS = "test/solarpunk/iso/test_*.py"
STATUSES: tuple[str, ...] = ("held", "open")
NO_TEST = "—"
TAG = "Clause: "


def register_rows(text: str) -> list[list[str]]:
    """The register table's body rows, each its four stripped cells, the header and the rule left out.

    register_rows("| Clause | R | Held by | Status |\\n| --- | --- | --- | --- |\\n| 9001-7.5.3 | r | — | open |\\n")
    gives [["9001-7.5.3", "r", "—", "open"]].
    """
    found: list[list[str]] = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(cells) == 4 and cells[0] != "Clause" and not cells[0].startswith("---"):
            found.append(cells)
    return found


def tags_in(source: str, path: str) -> dict[str, str]:
    """Each test function's `path::name` and the clause its docstring's first line tags, untagged ones left out.

    For t.py holding `def test_a()` whose docstring starts "Clause: 9001-8.7.1", it gives {"t.py::test_a": "9001-8.7.1"}.
    """
    found: dict[str, str] = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            first = (ast.get_docstring(node) or "").split("\n")[0].strip()
            if first.startswith(TAG):
                found[f"{path}::{node.name}"] = first[len(TAG):].strip()
    return found


def tagged_tests(root: Path) -> dict[str, str]:
    """Every tagged test under root's test/solarpunk/iso/, by `file::name`: {"test/.../test_iso9001.py::test_a": "9001-8.7.1"}."""
    found: dict[str, str] = {}
    for path in matching(tracked_files(root), root, TESTS):
        found.update(tags_in(path.read_text(), str(path.relative_to(root))))
    return found


def row_problems(cells: list[str], tags: dict[str, str]) -> list[str]:
    """One row against the tagged tests: a held row's test exists and carries the row's clause; an open row names none.

    row_problems(["9001-7.5.3", "r", "—", "held"], {}) gives ["9001-7.5.3 is held and names no test"].
    """
    clause, _, held_by, status = cells
    if status not in STATUSES:
        return [f"{clause} has status {status!r}, not held or open"]
    if status == "open":
        return [] if held_by == NO_TEST else [f"{clause} is open and names a test ({held_by}): held, or Held by {NO_TEST}"]
    if held_by == NO_TEST:
        return [f"{clause} is held and names no test"]
    if held_by not in tags:
        return [f"{clause} is held by {held_by}, which is not a tagged test"]
    if tags[held_by] != clause:
        return [f"{clause} is held by {held_by}, which is tagged {TAG}{tags[held_by]}"]
    return []


def tag_problems(rows: list[list[str]], tags: dict[str, str]) -> list[str]:
    """Tagged tests with no row, and clauses tagged twice: a test tagged 9001-8.7.1 and no such row gives one problem."""
    claimed = {cells[0] for cells in rows}
    found = [f"{name} is tagged {TAG}{clause} and the register has no row for it"
             for name, clause in sorted(tags.items()) if clause not in claimed]
    clauses = list(tags.values())
    found += [f"{clause} is tagged by {clauses.count(clause)} tests" for clause in sorted(set(clauses)) if clauses.count(clause) > 1]
    return found


def problems(root: Path) -> list[str]:
    """Every way the register and the tagged tests disagree under root; [] when they hold. A register missing from git's
    list is itself a problem: ["docs/CLAUSE-REGISTER.md is not tracked"]."""
    listed = matching(tracked_files(root), root, REGISTER)
    if not listed:
        return [f"{REGISTER} is not tracked"]
    rows = register_rows(listed[0].read_text())
    tags = tagged_tests(root)
    clauses = [cells[0] for cells in rows]
    found = [f"{clause} has {clauses.count(clause)} rows" for clause in sorted(set(clauses)) if clauses.count(clause) > 1]
    for cells in rows:
        found += row_problems(cells, tags)
    return found + tag_problems(rows, tags)
