"""The readability rules a linter cannot say: short functions, small comprehensions, no *args or **kwargs, a docstring
with an example on every function (stacks/python/README.md; from Neon Rain R-015). Run: python3 -I scripts/checks/readability.py
STAMP: set OUR_CODE to the product package and the tool folders. It reads git's file list (scripts/checks/common.py; C-001):
a file on disk that git does not track is not read."""
import ast
import sys
from pathlib import Path

if __name__ == "__main__":  # run as a script from the project's root: the root holds the scripts package
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.checks.common import matching, tracked_files  # noqa: E402

MAX_FUNCTION_LINES = 40
MAX_COMPREHENSION_CLAUSES = 3
OUR_CODE: tuple[str, ...] = ("PROJECT", "scripts", "test")


def clauses(node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp) -> int:
    """The `for` and `if` clauses of a comprehension: [x for x in y if x] has 2."""
    return sum(1 + len(generator.ifs) for generator in node.generators)


def node_problems(node: ast.AST, path: str) -> list[str]:
    """One syntax node against the rules; each message starts "path:line"."""
    found = []
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        where = f"{path}:{node.lineno}"
        length = (node.end_lineno or node.lineno) - node.lineno + 1
        if length >= MAX_FUNCTION_LINES:
            found.append(f"{where} {node.name} is {length} lines, at most {MAX_FUNCTION_LINES - 1}")
        if node.args.vararg is not None or node.args.kwarg is not None:
            found.append(f"{where} {node.name} takes *args or **kwargs")
        if not node.name.startswith("test_") and not ast.get_docstring(node):
            found.append(f"{where} {node.name} has no docstring (one with a concrete example)")
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        if clauses(node) > MAX_COMPREHENSION_CLAUSES:
            found.append(f"{path}:{node.lineno} a comprehension has {clauses(node)} clauses, at most {MAX_COMPREHENSION_CLAUSES}")
    return found


def source_problems(source: str, path: str) -> list[str]:
    """Every rule broken in one file's source text."""
    found = []
    for node in ast.walk(ast.parse(source)):
        found += node_problems(node, path)
    return found


def problems(root: Path) -> list[str]:
    """Every rule broken in the tracked Python under `root`'s OUR_CODE folders (neonrain/, scripts/, test/)."""
    found = []
    files = tracked_files(root)
    for top in OUR_CODE:
        for path in matching(files, root, f"{top}/**/*.py"):
            found += source_problems(path.read_text(), str(path.relative_to(root)))
    return found


if __name__ == "__main__":
    problems_found = problems(Path(__file__).resolve().parent.parent.parent)
    print("\n".join(problems_found) if problems_found else "readability: clean")
    sys.exit(1 if problems_found else 0)
