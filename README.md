# Solarpunk

A quality harness for utility-scale solar operations and maintenance: synthetic SCADA telemetry, a KPI engine (availability, performance ratio, energy yield, MTBF/MTTR) whose every number has a hand-checkable example, a CMMS-style work-order ledger with root-cause codes, and a clause register tracing each ISO 9001 and ISO 55000 requirement to the test that holds it.

Solarpunk models a solar site the way its operator sees it: a fleet of assets (the site, inverters, strings,
trackers, meters, sensors), a closed catalogue of fault codes and a ledger of when each fault opened and closed,
five-minute telemetry, and remote tests run against each asset's data feed on a schedule. Each asset wears a colour:
green when its last run passed, yellow when a remote test failed, red while it carries an open outage.

It is written in Python's standard library alone, with a native tkinter window on Windows and Linux, and nothing
installed for the product itself. The tests are the audit: every KPI is mirrored from its contract by an agent that
never saw the code, every product line is mutation-tested, and `scripts/clauses.py` reports which ISO clause each
test holds.

## Commands

    python3 -m solarpunk.ui --demo      # the demo: rebuilds demo.db and opens the fleet window (DEMO.md)
    bash scripts/fast.sh                # the fast loop: every document check and unit test, nothing installed
    python3 -I scripts/clauses.py       # the clause report: each ISO 9001 and ISO 55000 clause and its test

On Windows, `py -m solarpunk.ui --demo` and `python -I scripts\clauses.py`; `DEMO.md` has the setup, the click
order and the talk track. `scripts/save.sh` saves a session's work on its own branch, `scripts/gate.sh --fast` is the
check before a landing (`scripts/commit.sh`), `scripts/ship.sh` the only push to `main`, and the full
`scripts/gate.sh` runs at each tune-up (C-040).

## The roadmap

- Phase 0, founding: done.
- Phase 1, the fleet, its faults, its numbers (the registry, the ledger, telemetry, the KPI engine): done.
- Phase 2, the feed, the remote tests, the clock (simulator, receiver, scheduler, mailer, the scheduled run): done.
- Phase 3, the native front end (the fleet, asset and add-asset windows, the demo): the demo is 3.4, then a tune-up.
- Phase 4, the work-order ledger: planned when Phase 3 closes.

`docs/ROADMAP.md` holds the plan, `TODO.md` the open items in order.

## Where to read next

An agent starts at `CLAUDE.md`. The numbers, their invariants and their hand-checkable examples are in
`docs/CONTRACT.md`.
