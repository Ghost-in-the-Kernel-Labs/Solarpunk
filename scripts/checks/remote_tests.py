"""Every remote test held to its written contract, as far as a check can see (TODO 13.1; SP-019; docs/REMOTE-TESTS.md).

For each module in solarpunk/remote/tests/ (read from git's list, scripts/checks/common.py; C-001, so a new file is
staged with `git add -N` first) it holds: a module docstring; the fields KINDS (a non-empty tuple of AssetKind),
CLAUSES (a non-empty tuple of strings), SUGGESTS (a dict with exactly one key per kind) and `run(asset, samples)`; a
`run` docstring with a passing case, `Result(True`, and a failing one, `Result(False`; a call to nothing_to_check, so
no records is "no data" and never a pass (SP-039); no import of a store, a network or a clock reader, and no call that
reads the time (`now`, `today`, `utcnow`); every numeric constant at module level carrying a comment (the line above,
or at the end of its own line) and no number in a function body but 0 and 1 and a rounding's digits; and the module's
name on the `Tests:` line of each of its kinds in docs/ASSET-MAINTENANCE-LIST.md. What a check cannot see, that `run`
returns a Result of the right shape, is held by test/solarpunk/test_diagnostics.py. The module is loaded to read its
KINDS and SUGGESTS (on_grid computes its kinds); a module that will not load is itself a problem.
"""
import ast
import importlib.util
import io
import sys
import tokenize
from pathlib import Path
from types import ModuleType

if __name__ == "__main__":  # run as a script from the project's root: the root holds the scripts package
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.checks.asset_types import DOCUMENT, sections, tests_named  # noqa: E402
from scripts.checks.common import matching, tracked_files  # noqa: E402
from solarpunk.leaf.codes import AssetKind  # noqa: E402

TESTS = "solarpunk/remote/tests/*.py"
FIELDS = ("KINDS", "CLAUSES", "SUGGESTS", "run")
RUN_ARGUMENTS = ["asset", "samples"]
# A module that opens a store, a socket or a clock reads what it was not handed; solarpunk.leaf.clock is allowed, it
# only does grid arithmetic on an instant it is given.
FORBIDDEN_MODULES = ("sqlite3", "socket", "ssl", "http", "urllib", "requests", "asyncio", "sched", "time",
                     "solarpunk.leaf.store", "solarpunk.feed", "solarpunk.receiver", "solarpunk.project",
                     "solarpunk.remote.run", "solarpunk.remote.registry")
CLOCK_CALLS = ("now", "today", "utcnow")
PASS_CASE = "Result(True"
FAIL_CASE = "Result(False"
JUDGE = "nothing_to_check"
PLAIN_NUMBERS = (0, 1)


def comment_lines(source: str) -> set[int]:
    """The line numbers holding a comment: comment_lines("# a\\nx = 1  # b\\ny = 2\\n") gives {1, 2}."""
    return {token.start[0] for token in tokenize.generate_tokens(io.StringIO(source).readline)
            if token.type == tokenize.COMMENT}


def imported(tree: ast.Module) -> list[str]:
    """Every dotted name the module imports: "import time" and "from solarpunk.leaf.store import Store" give
    ["time", "solarpunk.leaf.store", "solarpunk.leaf.store.Store"]."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names]
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found += [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
    return found


def import_problems(tree: ast.Module) -> list[str]:
    """The reads the module may not do: "imports sqlite3 (a store, a network or a clock reader)" for each forbidden
    module imported, and "calls datetime.now()" style problems for a call named now, today or utcnow."""
    found = []
    names = imported(tree)
    for module in FORBIDDEN_MODULES:
        if any(name == module or name.startswith(module + ".") for name in names):
            found.append(f"imports {module} (a store, a network or a clock reader)")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in CLOCK_CALLS:
            found.append(f"line {node.lineno} calls .{node.func.attr}() (reads the clock)")
    return found


def number(node: ast.AST) -> bool:
    """Whether a node is a numeric literal, a leading minus allowed: 100.0 and -2 are, True and "1" are not."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return number(node.operand)
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)


def threshold_problems(tree: ast.Module, comments: set[int]) -> list[str]:
    """Module-level numeric constants with no comment: `LIMIT = 40.0` with no comment on the line above or at the end of
    the line gives "line 9 LIMIT has no comment saying why"; a name that is not upper case is not a constant."""
    found = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and number(node.value):
            names = [t.id for t in node.targets if isinstance(t, ast.Name) and t.id.isupper()]
            if names and not ({node.lineno - 1, node.lineno} & comments):
                found.append(f"line {node.lineno} {names[0]} has no comment saying why")
    return found


def bare_numbers(tree: ast.Module) -> list[str]:
    """Numbers in a function body that are not a named constant: `ceiling = rated * 1.01` gives "line 12 uses the bare
    number 1.01 (name it)"; 0, 1 and the digits argument of round() are allowed."""
    digits = {id(arg) for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "round"
              for arg in node.args[1:]}
    found = []
    for function in (n for n in tree.body if isinstance(n, ast.FunctionDef)):
        for node in ast.walk(function):
            if isinstance(node, ast.Constant) and number(node) and id(node) not in digits \
                    and node.value not in PLAIN_NUMBERS:
                found.append(f"line {node.lineno} uses the bare number {node.value} (name it)")
    return found


def run_problems(tree: ast.Module) -> list[str]:
    """What `run` must be: a function of (asset, samples) whose docstring holds a passing and a failing case and that
    calls nothing_to_check; no `run` at all gives ["has no run(asset, samples)"]."""
    runs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run"]
    if not runs or [a.arg for a in runs[0].args.args] != RUN_ARGUMENTS:
        return ["has no run(asset, samples)"]
    found = []
    doc = ast.get_docstring(runs[0]) or ""
    found += [f"run's docstring has no {word} case ({case}...)" for word, case in (("passing", PASS_CASE),
              ("failing", FAIL_CASE)) if case not in doc]
    if not any(isinstance(n, ast.Name) and n.id == JUDGE for n in ast.walk(runs[0])):
        found.append(f"run never calls {JUDGE} (no records must be no data, never a pass)")
    return found


def loaded(path: Path) -> ModuleType | str:
    """The module read from its file, or why it would not load: a file whose import raises gives "will not load: ..."."""
    spec = importlib.util.spec_from_file_location(f"remote_tests_check_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:  # a test module that cannot load is the finding, whatever it raised
        return f"will not load: {type(error).__name__}: {error}"
    return module


def field_problems(tree: ast.Module, module: ModuleType) -> list[str]:
    """The fields and their shapes: a module without SUGGESTS gives "has no SUGGESTS"; KINDS not a tuple of AssetKind,
    CLAUSES not a tuple of strings, SUGGESTS keys other than KINDS each give one problem."""
    named = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            named |= {target.id for target in node.targets if isinstance(target, ast.Name)}
    found = [f"has no {field}" for field in FIELDS if field not in named]
    kinds, clauses = getattr(module, "KINDS", None), getattr(module, "CLAUSES", None)
    if not (isinstance(kinds, tuple) and kinds and all(isinstance(k, AssetKind) for k in kinds)):
        found.append("KINDS is not a non-empty tuple of AssetKind")
    if not (isinstance(clauses, tuple) and clauses and all(isinstance(c, str) for c in clauses)):
        found.append("CLAUSES is not a non-empty tuple of strings")
    rules = getattr(module, "SUGGESTS", None)
    if "SUGGESTS" in named and (not isinstance(rules, dict) or set(rules) != set(kinds or ())):
        found.append("SUGGESTS is not a dict with one key per kind in KINDS")
    return found


def list_problems(name: str, kinds: tuple, document: dict[str, list[str]]) -> list[str]:
    """A kind whose `Tests:` line does not name the test: "INVERTER's Tests line does not name broken"."""
    return [f"{kind.name}'s Tests line does not name {name}" for kind in kinds
            if name not in tests_named(document.get(kind.name, []))]


def module_problems(path: Path, document: dict[str, list[str]]) -> list[str]:
    """Every way one test module breaks the contract, each starting with its file name's stem:
    "broken: has no SUGGESTS"; [] when it holds."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    found = [] if ast.get_docstring(tree) else ["has no module docstring"]
    found += import_problems(tree) + threshold_problems(tree, comment_lines(source)) + bare_numbers(tree)
    found += run_problems(tree)
    module = loaded(path)
    if isinstance(module, str):
        return [f"{path.stem}: {text}" for text in found + [module]]
    found += field_problems(tree, module)
    kinds = module.KINDS if isinstance(getattr(module, "KINDS", None), tuple) else ()
    found += list_problems(path.stem, tuple(k for k in kinds if isinstance(k, AssetKind)), document)
    return [f"{path.stem}: {text}" for text in found]


def problems(root: Path) -> list[str]:
    """Every remote test module under root against the contract; [] when they hold. A missing maintenance list is
    itself a problem: ["docs/ASSET-MAINTENANCE-LIST.md is not tracked"]."""
    files = tracked_files(root)
    listed = matching(files, root, DOCUMENT)
    if not listed:
        return [f"{DOCUMENT} is not tracked"]
    document = sections(listed[0].read_text(encoding="utf-8"))
    found: list[str] = []
    for path in matching(files, root, TESTS):
        if path.name != "__init__.py":
            found += module_problems(path, document)
    return found


if __name__ == "__main__":
    problems_found = problems(Path(__file__).resolve().parent.parent.parent)
    print("\n".join(problems_found) if problems_found else "remote_tests: clean")
    sys.exit(1 if problems_found else 0)
