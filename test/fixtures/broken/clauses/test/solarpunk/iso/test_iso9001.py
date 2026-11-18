"""A planted break (test/test_clauses.py): test_unregistered is tagged with a clause the fixture's register lacks.
The class is not named Test*, so pytest does not collect it, and the folder is no package, so unittest does not."""


class Planted:
    def test_present(self) -> None:
        """Clause: 9001-8.7.1
        Tagged, and its row names it."""

    def test_unregistered(self) -> None:
        """Clause: 9001-10.2.2
        Tagged, and no row names its clause."""

    def test_untagged(self) -> None:
        """An untagged test is not the register's concern."""
