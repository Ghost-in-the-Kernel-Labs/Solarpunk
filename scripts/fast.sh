#!/usr/bin/env bash
# The fast loop: every doc check and unit test, no data, no network, nothing installed (C-022, C-032).
# Run after every edit. Python 3 standard library only; -I ignores the environment and the current directory.
# With arguments, only those test modules: `scripts/fast.sh test.test_stamp` (or test_stamp, or test/test_stamp.py).
# Each becomes discover's -p pattern, since `-m unittest test.test_stamp` under -I finds the standard library's
# `test` package, and a module given to discover as a positional argument is read as its start folder (all of test/).
# A name that matches no file runs no test, which unittest reports as a failure.
# Every run is under `timeout` (SP-017): GHOST_FAST_TIMEOUT seconds, 300 by default, ten times the loop's target, so a
# test that never ends (a server thread left running after a failure, J-050) is a red line that says so, not a stall.
set -euo pipefail
cd "$(dirname "$0")/.."
limit=${GHOST_FAST_TIMEOUT:-300}
# run <pattern>: one discover under the timeout; a timeout's exit says what happened.
run() {
  local status=0
  timeout --kill-after=10 "$limit" python3 -I -m unittest discover -s test -t . -p "$1" || status=$?
  if [ "$status" -eq 124 ] || [ "$status" -eq 137 ]; then
    echo "fast loop: timed out after $limit s (a test that never ends: a thread or server left running?)" >&2
  fi
  return "$status"
}
if [ "$#" -eq 0 ]; then
  run 'test_*.py'
  exit
fi
status=0
for module in "$@"; do
  name=$(basename "${module%.py}")
  run "${name##*.}.py" || status=1
done
exit "$status"
