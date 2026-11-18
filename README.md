# Solarpunk

A quality harness for utility-scale solar operations and maintenance: synthetic SCADA telemetry, a KPI engine (availability, performance ratio, energy yield, MTBF/MTTR) whose every number has a hand-checkable example, a CMMS-style work-order ledger with root-cause codes, and a clause register tracing each ISO 9001 and ISO 55000 requirement to the test that holds it.

## Status

No feature exists yet. The project is stamped from Ghost-Core 9a29945; it begins at TODO 0.1, and
`docs/HANDOFF.md` says what the human fills in first.

## Running the fast loop

    bash scripts/fast.sh

Every document check and unit test, with nothing installed; `scripts/save.sh` saves a session's work on its own
branch, `scripts/gate.sh --fast` is the check before a landing (`scripts/commit.sh`), `scripts/ship.sh` the only push
to `main`, and the full `scripts/gate.sh` runs at each tune-up (C-040).
