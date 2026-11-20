# Solarpunk

A quality harness for utility-scale solar operations and maintenance: synthetic SCADA telemetry, a KPI engine (availability, performance ratio, energy yield, MTBF/MTTR) whose every number has a hand-checkable example, a CMMS-style work-order ledger with root-cause codes, and a clause register tracing each ISO 9001 and ISO 55000 requirement to the test that holds it.

Solarpunk models a solar site the way its operator sees it: a fleet of assets (the site, inverters, strings,
trackers, meters, sensors), a closed catalogue of fault codes and a ledger of when each fault opened and closed,
five-minute telemetry, and remote tests run against each asset's data feed on a schedule. Each asset wears a colour:
green when its last run passed, yellow when a remote test failed, red while it carries an open outage.

It is written in Python's standard library alone, with a native tkinter window on Windows and Linux, and nothing
installed for the product itself. The tests are the audit: every KPI has a worked example in its contract held as a
golden, the first four (SOL-07 to SOL-10) are also recomputed by a blind mirror written by an agent that never saw the
code, every product line is mutation-tested nightly, and `scripts/clauses.py` reports which ISO clause each test holds.

## Commands

    python3 -m solarpunk.ui --demo      # the demo: rebuilds demo.db and opens the fleet window (DEMO.md)
    python3 -m solarpunk.cli test run   # every remote test over every asset of solarpunk.db, once (--db for another)
    python3 -m solarpunk.cli test list  # the remote tests, each with its asset kinds and clauses
    python3 -m solarpunk.cli test add tracker_moving --clause 55000-9.1   # scaffold a new remote test
    python3 -m solarpunk.cli report OAHE 2026-06-01T00:00:00+00:00 2026-06-02T00:00:00+00:00 --csv   # power output
    bash scripts/fast.sh                # the fast loop: every document check and unit test, nothing installed
    python3 -I scripts/clauses.py       # the clause report: each ISO 9001 and ISO 55000 clause and its test

On Windows the repository's `solarpunk.cmd` makes it one word, typed in the `Solarpunk` folder (or anywhere, with that
folder on PATH): `solarpunk` opens the window, `solarpunk --demo` the demo, `solarpunk test run --db demo.db` runs the
remote tests, `solarpunk test list` and `solarpunk test add <name> --clause <id>` as above, `solarpunk report <site>
<start> <end>` the power-output report; the clause report is `solarpunk clauses`, and `solarpunk --help` lists every
command. In the window, "Reports" opens the same report with the site's power curve. `DEMO.md` has the setup, the click
order and the talk track. `scripts/save.sh` saves a session's work on its own branch, `scripts/gate.sh --fast` is the
check before a landing, `scripts/commit.sh -a -F <message> --ship` lands it and pushes `main` in one step, `main`
moving only once origin takes it (SP-014), and the full `scripts/gate.sh` runs at each tune-up (C-040).

## The roadmap

- Phase 0, founding: done.
- Phase 1, the fleet, its faults, its numbers (the registry, the ledger, telemetry, the KPI engine): done.
- Phase 2, the feed, the remote tests, the clock (simulator, receiver, scheduler, mailer, the scheduled run): done.
- Phase 3, the native front end (the fleet, asset and add-asset windows, the demo): done.
- Phase 4, the work-order ledger: done.
- Phase 5, one word to run it (`solarpunk`, `solarpunk --help`, the `test` commands): done.
- Phase 6, reports and diagnostics (the power-output report, four inverter diagnostics, their windows): done.
- Phase 7, faults suggested by tests, assigned by engineers (and the gate hardened): done.
- Phase 8, local tickets (status flow, priorities, response targets, the ticket ledger): done (SP-022).
- Phase 9, the fleet window as an operations root (headings, causes, what waits on a person): done (SP-023).
- Phase 10, runs per asset (a Runs button, each run, runs by test, power, error counts, graphed): done (SP-024).
- Phase 11, tickets in the windows (the adapter, the local tracker, a Tickets window): done (SP-022, SP-023).
- Phase 12, accounts and authentication (every act attributed to a signed-in account): not started (SP-022).
- Phase 13, the tests and their record (what a test is, suites, a Tests window): not started (SP-016, SP-019,
  SP-020).
- Phase 14, the network's security (the feed, the receiver, and the central server's design): not started.
- Phase 15, the network (a central server with many clients, planned from Phase 14's decisions): not started.

`docs/ROADMAP.md` holds the plan, `TODO.md` the open items in order, `docs/DONE.md` what is finished;
`test/test_readme.py` holds each line above to those two files.

## Where to read next

An agent starts at `CLAUDE.md`. Where the product is going, in Ghost's words, is `docs/GOAL.md`. The numbers, their invariants and their hand-checkable examples are in
`docs/CONTRACT.md`.
