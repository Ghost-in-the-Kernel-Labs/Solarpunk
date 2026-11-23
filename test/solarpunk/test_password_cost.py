"""SOL-16 and 13.19: the product keeps its full scrypt strength while the tests hash cheaply, and a line at either cost
verifies because the line carries its parameters."""
import ast
import unittest

from solarpunk.accounts import passwords
from test import TEST_SCRYPT_COST
from test.support import ROOT

SOURCE = ROOT / "solarpunk" / "accounts" / "passwords.py"


def declared() -> tuple:
    """The constants the product module's source assigns: (16384, 8, 1, 32), read from the file, not the patched module."""
    for node in ast.parse(SOURCE.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple):
            names = [target.id for target in node.targets[0].elts]
            if names == ["SCRYPT_COST", "BLOCK_SIZE", "PARALLELISM", "DKLEN"]:
                return ast.literal_eval(node.value)
    raise AssertionError("the scrypt parameters are not assigned in passwords.py")


class TheProductsStrength(unittest.TestCase):
    def test_the_product_source_declares_cost_16384_block_8_parallel_1_length_32(self) -> None:
        self.assertEqual(declared(), (16384, 8, 1, 32))

    def test_the_product_reads_no_environment_variable(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("environ", text)
        self.assertNotIn("getenv", text)

    def test_the_tests_run_at_the_low_cost(self) -> None:
        self.assertEqual(passwords.SCRYPT_COST, TEST_SCRYPT_COST)
        self.assertLess(TEST_SCRYPT_COST, declared()[0])


class TheTwoCosts(unittest.TestCase):
    PASSWORD = "plainly-fake-pw-" + "one"

    def line_at(self, cost: int) -> str:
        """A stored line made at one cost, e.g. "scrypt$16384$8$1$..."; the module's cost is put back afterwards."""
        kept = passwords.SCRYPT_COST
        passwords.SCRYPT_COST = cost
        try:
            return passwords.stored_line(self.PASSWORD)
        finally:
            passwords.SCRYPT_COST = kept

    def test_a_line_at_either_cost_verifies_and_a_wrong_password_fails_at_both(self) -> None:
        for cost in (declared()[0], TEST_SCRYPT_COST):
            with self.subTest(cost=cost):
                line = self.line_at(cost)
                self.assertEqual(line.split("$")[1], str(cost))
                self.assertTrue(passwords.matches(self.PASSWORD, line))
                self.assertFalse(passwords.matches(self.PASSWORD + "x", line))
