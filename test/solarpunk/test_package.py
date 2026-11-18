"""The product package exists and says what it is; the product's tests live here, where mutmut runs them (F-004)."""
import unittest

import solarpunk


class ThePackage(unittest.TestCase):
    def test_it_names_the_project_and_its_modules_file(self) -> None:
        self.assertIn("Solarpunk", solarpunk.__doc__ or "")
        self.assertIn("docs/modules.json", solarpunk.__doc__ or "")
