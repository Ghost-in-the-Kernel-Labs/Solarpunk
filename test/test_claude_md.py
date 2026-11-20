"""CLAUDE.md holds its shape, its ceiling, its inline binding block, the When line to the rules on the act and its canary line; docs/SUPPLY-CHAIN.md holds the rules on the act; the six credential bullets are held between them (C-037); and planted breaks are caught (C-020, C-021, C-022, C-034, C-036, SP-033)."""
import unittest

from scripts.checks import claude_md
from test.support import BROKEN, ROOT

RULES = "\n".join(claude_md.INLINE_RULES) + "\n\n" + claude_md.CANARY + "\n"
WHEN = "## When X happens, read Y\n\n- x: `docs/when/x.md`\n- a dependency: " + claude_md.ON_ACT_POINTER + "\n\n"
GOOD = "# X\n\n## Where to start\n\n| Task | Start here |\n| --- | --- |\n| a | `docs/a.md` |\n\n" + WHEN + RULES
GOOD_DOC = "# Supply chain\n\n## Rules on the act\n\n" + "\n".join(claude_md.ON_ACT_RULES) + "\n"


class TheRepository(unittest.TestCase):
    def test_the_real_file_holds(self) -> None:
        self.assertEqual(claude_md.problems((ROOT / "CLAUDE.md").read_text()), [])

    def test_the_real_file_has_headroom(self) -> None:
        self.assertLess(claude_md.words((ROOT / "CLAUDE.md").read_text()), claude_md.WORD_CEILING)

    def test_the_planted_break_is_caught(self) -> None:
        found = claude_md.problems((BROKEN / "claude_md" / "CLAUDE.md").read_text())
        self.assertEqual(found, ["row 'wide' opens 6 files, more than 5", "binding rule missing or reworded: '- A secret found in the tree, the history, a log o'…", "the When line to the rules on the act is missing or reworded", "the Context Canary line is missing or reworded"])

    def test_the_real_supply_chain_document_holds_the_rules_on_the_act(self) -> None:
        self.assertEqual(claude_md.on_act_problems((ROOT / "docs" / "SUPPLY-CHAIN.md").read_text()), [])

    def test_the_planted_supply_chain_break_is_caught(self) -> None:
        found = claude_md.on_act_problems((BROKEN / "claude_md" / "SUPPLY-CHAIN.md").read_text())
        self.assertEqual(found, ["rule on the act missing or reworded: '- Every GitHub Action is pinned to a full commit S'…", "rule on the act missing or reworded: '- The commit path refuses a staged file or diff th'…"])


class TheCheck(unittest.TestCase):
    def test_a_good_file_holds(self) -> None:
        self.assertEqual(claude_md.problems(GOOD), [])

    def test_over_the_ceiling_is_caught(self) -> None:
        self.assertIn("words, over 1500", claude_md.problems(GOOD + "word " * 1500)[0])

    def test_a_missing_when_section_is_caught(self) -> None:
        self.assertEqual(claude_md.problems(GOOD.replace("## When X happens, read Y", "## Later")), ["CLAUDE.md has no 'When X happens, read Y' section"])

    def test_a_reworded_binding_rule_is_caught(self) -> None:
        self.assertEqual(len(claude_md.problems(GOOD.replace("Do not revoke tokens.", "Revoke tokens."))), 1)

    def test_the_six_credential_bullets_are_held(self) -> None:
        self.assertEqual((len(claude_md.INLINE_RULES), len(claude_md.ON_ACT_RULES)), (8, 5))
        for phrase in ("Never dump the environment", "a dummy value, never a real one", "never read into context unless Ghost asks",
                       "report its file and line only (never the value)"):
            with self.subTest(phrase=phrase):
                rule = next(r for r in claude_md.INLINE_RULES if phrase in r)
                self.assertEqual(len(claude_md.problems(GOOD.replace(rule, ""))), 1)
        for phrase in ("assembled at runtime from fragments", "matches a key pattern"):
            with self.subTest(phrase=phrase):
                rule = next(r for r in claude_md.ON_ACT_RULES if phrase in r)
                self.assertEqual(len(claude_md.on_act_problems(GOOD_DOC.replace(rule, ""))), 1)

    def test_a_good_supply_chain_document_holds(self) -> None:
        self.assertEqual(claude_md.on_act_problems(GOOD_DOC), [])

    def test_a_missing_when_line_to_the_rules_on_the_act_is_caught(self) -> None:
        self.assertEqual(claude_md.problems(GOOD.replace(claude_md.ON_ACT_POINTER, "the rules")), ["the When line to the rules on the act is missing or reworded"])

    def test_a_missing_or_reworded_canary_is_caught(self) -> None:
        self.assertEqual(claude_md.problems(GOOD.replace(claude_md.CANARY, "")), ["the Context Canary line is missing or reworded"])
        self.assertEqual(claude_md.problems(GOOD.replace("Context Canary", "Canary")), ["the Context Canary line is missing or reworded"])

    def test_a_row_with_six_files_is_caught(self) -> None:
        wide = GOOD.replace("| a | `docs/a.md` |", "| a | " + " ".join(f"`docs/{i}.md`" for i in range(6)) + " |")
        self.assertEqual(claude_md.problems(wide), ["row 'a' opens 6 files, more than 5"])
