"""Every outside import in our Python is in requirements.lock or the standard library (C-034 rule 2).
Run: python3 -I scripts/checks/imports.py. STAMP: set OUR_CODE. It reads git's file list (scripts/checks/common.py;
C-001): a Python file on disk that git does not track is not read. The lock is read from the disk: it is the allow-list,
not a file under check, and an untracked lock read as empty would only refuse more."""
import ast
import re
import sys
from pathlib import Path

if __name__ == "__main__":  # run as a script from the project's root: the root holds the scripts package
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.checks.common import matching, tracked_files  # noqa: E402

OUR_CODE: tuple[str, ...] = ("PROJECT", "scripts", "test")
ROOT = Path(__file__).resolve().parent.parent.parent


def locked(lock: str) -> set[str]:
    """The package names a lock holds, lower-cased with dashes as underscores: "Polars==1.0 \\\\" gives {"polars"}."""
    return {name.lower().replace("-", "_") for name in re.findall(r"^([A-Za-z0-9_.-]+)==", lock, re.MULTILINE)}


def top_level_imports(source: str) -> set[str]:
    """The first segment of every import: "import a.b; from c import d" gives {"a", "c"}."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found |= {alias.name.split(".")[0] for alias in node.names}
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


def problems(root: Path) -> list[str]:
    """Each file that imports a name neither ours, nor standard, nor locked."""
    allowed = locked((root / "requirements.lock").read_text()) if (root / "requirements.lock").is_file() else set()
    ours = set(OUR_CODE)
    found: list[str] = []
    files = tracked_files(root)
    for top in OUR_CODE:
        for path in matching(files, root, f"{top}/**/*.py"):
            for name in sorted(top_level_imports(path.read_text())):
                if name not in ours and name not in sys.stdlib_module_names and name.lower() not in allowed:
                    found.append(f"{path.relative_to(root)} imports {name}, which requirements.lock does not hold")
    return found


if __name__ == "__main__":
    problems_found = problems(ROOT)
    print("\n".join(problems_found) if problems_found else "imports: all locked")
    sys.exit(1 if problems_found else 0)
