"""The clause register and its tagged tests hold; planted breaks of each direction are caught (SOL-12, C-013)."""
import unittest

from scripts.checks import clauses
from test.support import BROKEN, ROOT, scratch

HEADER = "| Clause | Requirement (our words) | Held by | Status |\n| --- | --- | --- | --- |\n"
FILE = "test/solarpunk/iso/test_iso9001.py"


def tagged(name: str, clause: str) -> str:
    """One test method tagged with a clause, as source: tagged("test_a", "9001-8.7.1") starts "    def test_a"."""
    return f'    def {name}(self) -> None:\n        """Clause: {clause}\n        x"""\n'


def tree(rows: str, tests: str) -> list[str]:
    """The check's problems for a scratch tree holding a register of those rows and one test file of those methods:
    tree("", "") gives []."""
    root = scratch()
    (root / "docs" / "CLAUSE-REGISTER.md").write_text(HEADER + rows)
    (root / "test" / "solarpunk" / "iso").mkdir(parents=True)
    (root / FILE).write_text("class Planted:\n" + (tests or "    pass\n"))
    return clauses.problems(root)


class TheRepository(unittest.TestCase):
    def test_the_real_register_holds(self) -> None:
        self.assertEqual(clauses.problems(ROOT), [])

    def test_the_real_register_has_eight_to_twelve_rows(self) -> None:
        rows = clauses.register_rows((ROOT / "docs" / "CLAUSE-REGISTER.md").read_text())
        self.assertTrue(8 <= len(rows) <= 12, len(rows))
        self.assertTrue(all(cells[0].split("-")[0] in ("9001", "55000") for cells in rows))

    def test_the_planted_breaks_are_caught(self) -> None:
        self.assertEqual(clauses.problems(BROKEN / "clauses"), [
            f"9001-7.5.3 is held by {FILE}::test_missing, which is not a tagged test",
            f"{FILE}::test_unregistered is tagged Clause: 9001-10.2.2 and the register has no row for it",
        ])


class TheCheck(unittest.TestCase):
    def test_a_held_row_with_its_tagged_test_holds(self) -> None:
        self.assertEqual(tree(f"| 9001-8.7.1 | r | {FILE}::test_a | held |\n", tagged("test_a", "9001-8.7.1")), [])

    def test_an_open_row_with_no_test_holds(self) -> None:
        self.assertEqual(tree("| 9001-9.1.3 | r | — | open |\n", ""), [])

    def test_a_held_row_with_no_test_is_caught(self) -> None:
        self.assertEqual(tree("| 9001-9.1.3 | r | — | held |\n", ""), ["9001-9.1.3 is held and names no test"])

    def test_a_test_tagged_with_another_clause_is_caught(self) -> None:
        found = tree(f"| 9001-8.7.1 | r | {FILE}::test_a | held |\n", tagged("test_a", "9001-8.7.2"))
        self.assertEqual(found[0], f"9001-8.7.1 is held by {FILE}::test_a, which is tagged Clause: 9001-8.7.2")

    def test_an_open_row_naming_a_test_is_caught(self) -> None:
        found = tree(f"| 9001-8.7.1 | r | {FILE}::test_a | open |\n", tagged("test_a", "9001-8.7.1"))
        self.assertEqual(found, [f"9001-8.7.1 is open and names a test ({FILE}::test_a): held, or Held by —"])

    def test_a_duplicated_row_and_a_double_tag_are_caught(self) -> None:
        rows = f"| 9001-8.7.1 | r | {FILE}::test_a | held |\n" * 2
        found = tree(rows, tagged("test_a", "9001-8.7.1") + tagged("test_b", "9001-8.7.1"))
        self.assertEqual(found, ["9001-8.7.1 has 2 rows", "9001-8.7.1 is tagged by 2 tests"])

    def test_an_unknown_status_is_caught(self) -> None:
        self.assertEqual(tree("| 9001-8.7.1 | r | — | maybe |\n", ""), ["9001-8.7.1 has status 'maybe', not held or open"])

    def test_a_missing_register_is_caught(self) -> None:
        root = scratch()
        self.assertEqual(clauses.problems(root), ["docs/CLAUSE-REGISTER.md is not tracked"])

    def test_only_the_first_docstring_line_tags(self) -> None:
        source = 'def test_a() -> None:\n    """x\n    Clause: 9001-8.7.1"""\n'
        self.assertEqual(clauses.tags_in(source, "t.py"), {})
