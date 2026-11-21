"""A planted break for scripts/checks/names.py: one binding of each kind, every name two characters or fewer."""


def total(rows: list[int], ab: int) -> int:
    """Add ab to every row: total([1, 2], 3) gives 9."""
    x = 0
    for i in rows:
        x += i + ab
    return x


def squares(rows: list[int]) -> list[int]:
    """The squares: squares([2]) gives [4]."""
    return [n * n for n in rows]


def guarded() -> int:
    """Zero, however it fails: guarded() gives 0."""
    try:
        return 1 // 0
    except ZeroDivisionError as e:
        return 0 * len(str(e))


def opened(path: str) -> int:
    """The length of a file: opened("a.txt") gives its size."""
    with open(path) as fh:
        return len(fh.read())


DOUBLE = lambda v: v * 2  # noqa: E731
