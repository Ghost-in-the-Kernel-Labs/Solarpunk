"""The names check refuses every binding of two characters or fewer, and passes names of three or more
(scripts/checks/names.py, TODO 13.8, SP-042). It is not run over the tree here: part 5 turns that on."""
import unittest

from scripts.checks import names
from test.support import BROKEN, scratch

PLANTED = BROKEN / "names" / "short.py"
EXPECTED = [
    "short.py:4 ab",
    "short.py:6 x",
    "short.py:7 i",
    "short.py:8 x",
    "short.py:14 n",
    "short.py:21 e",
    "short.py:27 fh",
    "short.py:31 v",
]


class TheNamesCheck(unittest.TestCase):
    def test_the_planted_break_is_refused_with_file_line_and_name(self) -> None:
        found = names.source_problems(PLANTED.read_text(), "short.py")
        self.assertEqual(sorted(found), sorted(EXPECTED))

    def test_a_scratch_root_reads_the_product_and_leaves_the_planted_breaks_out(self) -> None:
        root = scratch()
        for name in ("solarpunk/mod.py", "test/fixtures/broken/names/short.py"):
            (root / name).parent.mkdir(parents=True)
            (root / name).write_text("ab = 1\n")
        self.assertEqual(names.problems(root), ["solarpunk/mod.py:1 ab"])

    def test_a_clean_sample_passes(self) -> None:
        source = "def total(rows: list[int], bonus: int) -> int:\n    total_sum = 0\n    for row in rows:\n        total_sum += row\n    return total_sum + bonus\n"
        self.assertEqual(names.source_problems(source, "clean.py"), [])

    def test_underscore_and_self_are_excepted_but_not_a_prefixed_name(self) -> None:
        source = "class Box:\n    def put(self, item: int) -> None:\n        for _ in range(item):\n            self.ok = 1\n        try:\n            pass\n        except ValueError as _e:\n            pass\n"
        self.assertEqual(names.source_problems(source, "box.py"), ["box.py:7 _e"])

    def test_unpacking_and_keyword_arguments_count(self) -> None:
        source = "def f(*, kw: int, **ex: int) -> None:\n    first, (aa, *bb) = 1, (2, 3)\n"
        self.assertEqual(names.source_problems(source, "u.py"), ["u.py:1 ex", "u.py:1 kw", "u.py:2 aa", "u.py:2 bb"])
