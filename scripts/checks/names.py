"""Names of three characters or more (TODO 13.8, SP-042): every binding of two characters or fewer is refused, `_` and
`self` excepted. A binding is an assignment, a loop or comprehension target, a `with ... as` name, an `except ... as`
name, or any function or lambda argument. Run: python3 -I scripts/checks/names.py
It reads git's file list (scripts/checks/common.py; C-001) under the product package and the tool folders, and leaves out
test/fixtures/, where the planted breaks live."""
import ast
import sys
from pathlib import Path

if __name__ == "__main__":  # run as a script from the project's root: the root holds the scripts package
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.checks.common import matching, tracked_files  # noqa: E402

MIN_NAME_LENGTH = 3
EXCEPTED = ("_", "self")
OUR_CODE: tuple[str, ...] = ("solarpunk", "scripts", "test")
PLANTED = ("test", "fixtures")


def bound_name(node: ast.AST) -> str | None:
    """The name a syntax node binds, or None: an assignment target `x = 1` binds "x", an `except E as e` binds "e", an
    argument `def f(ab)` binds "ab"; `self.x = 1` and `d[k] = 1` bind no name."""
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        return node.id
    if isinstance(node, ast.ExceptHandler):
        return node.name
    if isinstance(node, ast.arg):
        return node.arg
    return None


def source_problems(source: str, path: str) -> list[str]:
    """Every too-short binding in one file's source text, as "path:line name", in line order:
    source_problems("for i in rows:\\n    pass\\n", "a.py") gives ["a.py:1 i"]."""
    found = []
    for node in ast.walk(ast.parse(source)):
        name = bound_name(node)
        if name is not None and len(name) < MIN_NAME_LENGTH and name not in EXCEPTED:
            found.append((node.lineno, f"{path}:{node.lineno} {name}"))
    return [message for _, message in sorted(found)]


def problems(root: Path) -> list[str]:
    """Every too-short binding in the tracked Python under `root`'s OUR_CODE folders, planted breaks left out."""
    found = []
    files = tracked_files(root)
    for top in OUR_CODE:
        for path in matching(files, root, f"{top}/**/*.py"):
            if path.relative_to(root).parts[:2] != PLANTED:
                found += source_problems(path.read_text(), str(path.relative_to(root)))
    return found


if __name__ == "__main__":
    problems_found = problems(Path(__file__).resolve().parent.parent.parent)
    print("\n".join(problems_found) if problems_found else "names: clean")
    sys.exit(1 if problems_found else 0)
