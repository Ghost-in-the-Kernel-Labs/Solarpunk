"""Print each clause of docs/CLAUSE-REGISTER.md as held, failing or open, from a run of its tagged tests (SOL-12).

    python3 -I scripts/clauses.py

Runs test/solarpunk/iso/ with the standard library's unittest (what `python3 -I -m unittest discover -s
test/solarpunk/iso -t .` runs, in this process so each result is read by its test's name), then prints one line per
register row, `<clause>  held|failing|open  <requirement>`: `failing` is a held row whose test failed, raised or did
not run; and last one line per standard, `9001: 6 held, 0 failing, 2 open`. Exits 1 when a clause is failing. Whether
the register and the tags agree is scripts/checks/clauses.py's (the fast loop runs it); this says whether they pass.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.checks import clauses  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ISO_TESTS = ROOT / "test" / "solarpunk" / "iso"
STANDARDS: tuple[str, ...] = ("9001", "55000")


def test_ids(suite: unittest.TestSuite) -> list[str]:
    """Every test's id in a suite, nested suites flattened: ["test.solarpunk.iso.test_iso9001.Iso9001.test_a", ...]."""
    found: list[str] = []
    for item in suite:
        found += test_ids(item) if isinstance(item, unittest.TestSuite) else [item.id()]
    return found


def passed_tests() -> set[str]:
    """The ids of the ISO tests that ran and passed: a failure, an error or a skip leaves a test out of the set."""
    suite = unittest.TestLoader().discover(str(ISO_TESTS), top_level_dir=str(ROOT))
    ran = set(test_ids(suite))  # before the run: a suite lets go of its tests as it runs them
    result = unittest.TestResult()
    suite.run(result)
    not_passed = {test.id() for test, _ in result.failures + result.errors + result.skipped}
    return ran - not_passed


def verdict(cells: list[str], passed: set[str]) -> str:
    """A row's word: "open" for an open row; "held" when its test passed, else "failing".
    verdict(["9001-8.7.1", "r", "test/solarpunk/iso/test_iso9001.py::test_a", "held"],
    {"test.solarpunk.iso.test_iso9001.Iso9001.test_a"}) gives "held"."""
    if cells[3] != "held":
        return "open"
    path, _, name = cells[2].partition("::")
    module = path.removesuffix(".py").replace("/", ".")
    hits = [rid for rid in passed if rid.startswith(module + ".") and rid.endswith("." + name)]
    return "held" if hits else "failing"


def counts(lines: list[tuple[str, str]]) -> list[str]:
    """One count line per standard from (clause, verdict) pairs:
    counts([("9001-8.7.1", "held"), ("55000-7.5", "open")]) gives ["9001: 1 held, 0 failing, 0 open", "55000: 0 held,
    0 failing, 1 open"]."""
    found: list[str] = []
    for standard in STANDARDS:
        words = [word for clause, word in lines if clause.split("-")[0] == standard]
        found.append(f"{standard}: {words.count('held')} held, {words.count('failing')} failing, {words.count('open')} open")
    return found


def main() -> int:
    """Print the report and return 1 when a clause is failing, else 0."""
    rows = clauses.register_rows((ROOT / clauses.REGISTER).read_text())
    passed = passed_tests()
    lines = [(cells[0], verdict(cells, passed)) for cells in rows]
    width = max((len(clause) for clause, _ in lines), default=0)
    for (clause, word), cells in zip(lines, rows):
        print(f"{clause:<{width}}  {word:<7}  {cells[1]}")
    print("\n".join(counts(lines)))
    return 1 if any(word == "failing" for _, word in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
