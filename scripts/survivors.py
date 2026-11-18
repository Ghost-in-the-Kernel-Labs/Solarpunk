"""Reads `mutmut results` on stdin; exits 1 on a survivor that docs/MUTATION.md does not explain (C-018).
A surviving mutant's name (file.function__mutmut_n) is explained by a line of docs/MUTATION.md that names it."""
import sys
from pathlib import Path


def survivors(results: str) -> list[str]:
    """The names with a survived status: "a.b__mutmut_1: survived\\n" gives ["a.b__mutmut_1"]."""
    return [line.split(":")[0].strip() for line in results.splitlines() if line.strip().endswith(": survived")]


def unexplained(names: list[str], mutation_doc: str) -> list[str]:
    """The survivors the document never names."""
    return [name for name in names if name not in mutation_doc]


if __name__ == "__main__":
    doc = Path(__file__).resolve().parent.parent / "docs" / "MUTATION.md"
    missing = unexplained(survivors(sys.stdin.read()), doc.read_text() if doc.is_file() else "")
    print("\n".join(f"unexplained survivor: {m}" for m in missing) if missing else "survivors: every one explained")
    sys.exit(1 if missing else 0)
