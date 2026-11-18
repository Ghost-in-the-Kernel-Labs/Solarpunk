#!/usr/bin/env bash
# The Python stack's gate, run by scripts/gate.sh when stacks/python/PRESENT exists: pytest, ruff, the readability
# and lockfile checks, mutmut with every survivor explained.
# With --fast (the fast checks, C-040) it stops after the fast loop and says `python gate: fast checks passed`.
set -euo pipefail
cd "$(dirname "$0")/../.."
bin=.venv/bin
# A fresh stamp ships requirements.in and no lock (TODO 0.2 makes it): the refusal names the file and the step, as
# stacks/python/README.md's Dependencies row says ("requirements.lock is compiled from it with hashes").
[ -f requirements.lock ] || { echo "python gate: no requirements.lock; the stamp ships requirements.in, and requirements.lock is compiled from it with hashes by the command in requirements.in's header: uv pip compile --generate-hashes --python-version 3.12 --exclude-newer <the date seven days ago> requirements.in -o requirements.lock"; exit 1; }
[ -x "$bin/python" ] || { echo "python gate: no .venv (python3.12 -m venv .venv && $bin/pip install --only-binary :all: --require-hashes -r requirements.lock)"; exit 1; }
$bin/pytest -q || { echo "python gate: the fast loop"; exit 1; }
[ "${1:-}" != --fast ] || { echo "python gate: fast checks passed"; exit 0; }
$bin/ruff check . || { echo "python gate: ruff"; exit 1; }
$bin/python -I scripts/checks/readability.py || { echo "python gate: readability (stacks/python/README.md)"; exit 1; }
$bin/python -I scripts/checks/imports.py || { echo "python gate: an import not in requirements.lock"; exit 1; }
rm -rf mutants
$bin/mutmut run > build/mutmut.log 2>&1 || { echo "python gate: mutmut run (build/mutmut.log)"; exit 1; }
$bin/mutmut results | $bin/python -I scripts/survivors.py || { echo "python gate: a surviving mutant with no line in docs/MUTATION.md"; exit 1; }
echo "python gate: passed"
