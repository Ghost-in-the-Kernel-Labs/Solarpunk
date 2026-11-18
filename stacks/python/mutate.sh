#!/usr/bin/env bash
# The mutation regime (SP-012, C-018): mutmut over the product, apart from the gate, so a landing and a tune-up are not
# held to its minutes. A scheduled session runs it nightly from a fresh clone; anyone may run it by hand. Every survivor
# is still killed by a test or explained by a line of docs/MUTATION.md that names it: scripts/survivors.py refuses any
# other, and a refusal is a fix-forward item for the next session, never a reason to undo a landing (C-040).
# mutmut keeps its results under mutants/ and re-tests only what changed; --cold starts from nothing (a fresh clone has
# no cache, so the nightly run is cold whether asked or not). Its output goes to build/mutmut.log, its results to
# build/mutmut-results.txt (docs/when/long-run.md), and one line comes last: `mutate: passed; <n> mutants, <k> killed,
# <s> survived and explained, <seconds> s` or `mutate: refused at <step> (<why>)`.
# Usage: stacks/python/mutate.sh [--cold]
set -uo pipefail
cd "$(dirname "$0")/../.."
bin=.venv/bin
refuse() { echo "mutate: refused at $1"; exit 1; }

cold=""
for arg in "$@"; do
  case "$arg" in
    --cold) cold=1;;
    *) refuse "the arguments (unknown argument $arg; usage: stacks/python/mutate.sh [--cold])";;
  esac
done
[ -x "$bin/mutmut" ] || refuse "the venv (no .venv: python3.12 -m venv .venv && $bin/pip install --only-binary :all: --require-hashes -r requirements.lock)"
mkdir -p build
started=$(date +%s)
[ -z "$cold" ] || rm -rf mutants
"$bin/mutmut" run > build/mutmut.log 2>&1 || refuse "mutmut run (build/mutmut.log)"
"$bin/mutmut" results > build/mutmut-results.txt || refuse "mutmut results (build/mutmut-results.txt)"
"$bin/python" -I scripts/survivors.py < build/mutmut-results.txt \
  || refuse "the survivors (named above: each gets a test that kills it, or a line in docs/MUTATION.md)"
total=$(tr '\r' '\n' < build/mutmut.log | grep -ao '[0-9]*/[0-9]*  ' | tail -1 | tr -d ' ' | cut -d/ -f2)
survived=$(grep -c ': survived$' build/mutmut-results.txt)
untested=$(grep -c ': no tests$' build/mutmut-results.txt)
timed_out=$(grep -c ': timeout$' build/mutmut-results.txt)
killed=$(( ${total:-0} - survived - untested - timed_out ))
echo "mutate: passed; ${total:-0} mutants, $killed killed, $survived survived and explained, $untested with no test, $timed_out timed out, $(( $(date +%s) - started )) s"
