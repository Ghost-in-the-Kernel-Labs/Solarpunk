# Handoff: what to work on next, and what is waiting on whom

Read `CLAUDE.md` first, then this. `TODO.md` is the chain in order; `docs/DONE.md` is what is finished.

## Start here (2026-11-20, the session that ended at bf76dc6)

The last session closed Phase 9 again and landed 12.2 and 12.3; `main` is clean and pushed, every landing through
the fast gate. Next, by Phase 12's lanes: **12.5, account administration** (`solarpunk account init` makes the first
admin once, on the machine; `account add|reset|deactivate|list`; accounts are never deleted), **then 12.4,
attribution** (every act as the signed-in account; `--by` and the "Assigned by" dropdown gone; and, widened on Ghost's
word, every window that writes a record passes the version it read), then 12.6 the pass.

What that session landed, newest first (the journal has each):
- 12.3 signing in (J-094, SP-032): a store with no active account asks nobody and says "no accounts yet: anyone at this
  machine acts" (the demo holds none); with one, the windows open on a sign-in and an acting command takes `--as
  EMAIL` and asks with `getpass`; failed sign-ins kept by account and instant, never a password. Acts are still
  attributed as before: that is 12.4.
- 12.2 versions (J-093): a version on every asset, fault, suggestion and ticket, a stale write refused with SOL-16's
  words. Enforced in project and the modules; **no window passes a version yet**, so no screen is protected until 12.4.
- 9.9 Tune-up commit 9 (J-092): cold 1.32 min, warm 1.30 min, fast loop 24.3 s, 9 of 9 metrics, none regressed.
- 9.8 Manage tests (J-091): the button between Add asset and Reports; a broken script listed in red, not raised.
- SP-031 (J-090): the icon is Ghost's painted art, `solarpunk/ui/art/`, the repository's first binary files (CC0).
- 9.7 (J-089): the icon on every window; `solarpunk --shortcut` puts a desktop shortcut wearing it.

Mind, before adding:
- One metric sits at its edge: the largest file 398 of 400 lines (`test/solarpunk/test_project_run.py`: a new test of
  the scheduled run goes in a new file). `solarpunk/project/orchestrator.py` is at 391. Mandatory context is off its
  edge: 1,123 of 1,500 words, by SP-033 (five supply-chain rules on the act moved to `docs/SUPPLY-CHAIN.md`, J-095)
  and SP-034 (the ceiling raised on Ghost's word).
- One fast loop ran 31 s on a loaded machine; two reruns ran 26 s. Watch it at the next measure.
- The navigation log holds debriefs for 9.7, 9.8 (wiped at 9.9), 12.2 and 12.3 for the next pass; 12.1's agent's two
  suggestions are carried in J-092.
- Not run from here: the shortcut and Open folder on Windows or a Mac (no such machine in a cloud session); the
  window's title bar (the test display has no window manager).

## Where the project stands (2026-11-18, after Tune-up pass 5)

Phases 0 to 5 are closed. Phases 0 to 4 were one night's work; Phase 5 was built with Ghost in the chat after he ran
the demo on Windows: `solarpunk.cmd` (`solarpunk` opens the window, `solarpunk --demo` the demo, `solarpunk --help`
lists every command) and the CLI's `help`, `test list`, `test run` and `test add` (J-033, J-035). `docs/GOAL.md` is
Ghost's statement of where the product is going: five areas under one click (J-036). Mutation left the gate for its
own nightly regime (SP-012, J-038; the section below). Tune-up pass 5: cold gate 9.95 min, warm 0.80 min, fast loop
23.1 s (J-039).

**The first open item is 12.5, account administration** (`TODO.md`; 12.3, signing in, landed in J-094 (SP-032: no accounts, no sign-in), 12.4 after 12.5 by the lanes; 12.2, versions, landed in J-093, the windows not yet passing the version they read; Phase 9 closed again by its tune-up commit, J-092; reopened by SP-030 for the icon and Manage tests; 9.8, Manage tests, landed in J-091; the icon became Ghost's painted art by SP-031, J-090; 9.7, the window's icon and the desktop shortcut, landed in J-089; 12.1, accounts, landed in J-087, built by an agent; the module approved and the item split by SP-028; Phase 11 closed by its pass, J-084; 11.2, tickets in the windows and on the command line, landed in J-083; 11.1, the adapter, the outbox and the local tracker, landed in J-082 (SP-027); Phase 10 closed by its pass, J-081; 10.7, error counts across the fleet, landed in J-080; 10.6, errors by code, landed in J-079; 10.5, power over time, landed in J-077; 10.4, runs by test, landed in J-076; 10.3, the Runs button and window, landed in J-075; 10.2, the runs' surface, landed in J-074; 10.1, SOL-15, landed in J-073; Phase 9 closed by its pass, J-072; 9.5, the status bar, landed in J-070; 9.4, sort and filter, landed in J-069; 9.3, the attention band, landed in J-068; 9.2, the cause column, landed in J-066; 9.1, headings and readable cells, landed in J-065; Phase 8 closed by its pass, J-064; 8.2, the ticket ledger, landed in J-063; 8.1, the ticket contract SOL-14, in J-061; SP-022: local tickets, then accounts and auth, then the
tests' record, the security pass, and a central server; Phase 8's cause by email was withdrawn by SP-021; Phase 7 closed by its pass, J-056; 7.5, the suggestions in the window and on the command line,
landed in J-054; 7.4, the suggestions themselves, in J-053; SP-017's 7.2 and 7.3 in J-051 and J-052; 7.1, who assigned a fault, landed in J-050; until 7.4 the receiver holds every good push for an engineer and stores nothing): Phase 7 is Ghost's
fault assignment (SP-015): tests
suggest a likely fault, only an engineer assigns one, and the record says which; then (SP-022, renumbered by SP-023 and SP-024) Phase 8 local tickets (8.1 and 8.2), 9 the fleet window as an operations root, 10 runs per asset, 11 tickets in the windows, 12 accounts and auth, 13 the tests' record, 14 the security pass, 15 a central server. 6.3, the reports window, landed (J-043): "Reports" beside
"Add asset" in the fleet window; 6.4, the diagnostics in the asset window, landed (J-045). Phase 6 is reports and diagnostics, put ahead of the network's security by Ghost (SP-013, J-041): 6.1 (the
power-output report, `solarpunk report`, SOL-13) and 6.2 (four inverter diagnostics) are done. The security design pass
is now 14.1, with an advisor's research on industry addressing and security copied into it. An architecture review
(J-041) is Ghost's to place: no product workpath, entry points declared nowhere, `project` and the CLI as hotspots.

What exists: the fleet registry, the fault ledger over a closed catalogue, synthetic SCADA with gaps as data, the KPI
engine with its blind mirror (contractual availability, performance ratio, energy yield, MTBF/MTTR), the clause register
and `scripts/clauses.py` (9001 eight held, 55000 four), the orchestrator and CLI; the asset maintenance list, the feed
by IP and port with a simulator, standalone remote tests with a registry and a scaffold for a new one, the receiver,
cron and Task Scheduler from one job, the mailer over SMTP, the scheduled run; the tkinter fleet, asset and add-asset
windows, the demo; the work-order ledger with root-cause codes; the one-word launcher. 912 tests in the fast loop;
4,910 mutants, every survivor killed or explained.

`solarpunk.cmd` ran on Ghost's Windows machine from a fresh clone: `solarpunk --help` printed the list (J-040). Its
other paths (`solarpunk`, `solarpunk --demo`, `solarpunk test run --db demo.db`, a folder on PATH) have not been
reported back. Not verified, said plainly: "Add a test suite" was read as scaffolding one remote test (`test add`); Ghost has not
confirmed that reading. Some test file leaves a store unclosed (a ResourceWarning that lands in whatever test runs when
garbage is collected, J-033); it is not found.

Candidates Ghost has not placed: the asset window listing open work orders and closing one with a cause; the receiver
and the clock exercised end to end in the demo; `tracker_moving`, `energy_monotonic`, `irradiance_in_range` and
`night_power_near_zero` as remote tests (`solarpunk test add <name> --clause <id>` scaffolds each); a SOL-13 for root
causes; a product workpath for the routing table; whether a tune-up pass still needs a cold and a warm gate run now
that no step keeps a cache.

## The nightly mutation run (SP-012)

Mutation is not a gate step: `stacks/python/mutate.sh` is its own regime. A scheduled Claude cloud task, "Solarpunk
nightly mutation run", fires a fresh session each night at 02:17 America/Chicago (the zone read from Ghost's commits,
not confirmed by him): it clones `main`, makes the venv from the lock, runs `stacks/python/mutate.sh --cold` and
reports the verdict line; on an unexplained survivor it writes the killing test on a session branch and names the
branch, never landing on `main`. The task was created with no repository source and no connectors attached, so its
first run (the night of 2026-11-18) is the trial of whether a fresh session can reach the repository: read its report
before trusting the schedule. Ghost changes or stops it in claude.ai's scheduled tasks.

## Settled by Ghost (2026-11-17, in chat)

Python stack, prefix SP, floor mid; the five-lane shape of Phase 1 and the seven modules (SP-003); SQLite from the
standard library (SP-004); lanes built in parallel, landed in order (SP-005); the leaf's first code pulled into 0.2
(SP-002). Directions placed in Phases 2 and 3 (`docs/ROADMAP.md`): cron and Task Scheduler; a native UI, not web;
the scrollable asset list with the green/yellow/red panel glyph, mouseover last status and time, click-through to the
failing remote test; assets added by IP and port and pinged for a feed; standalone remote tests per asset type, each
its own lane; the asset maintenance list behind the type dropdown; assets pushing id and error code to the receiver;
ISO 9001 and ISO 55000 coverage from the test suite as one report; an asset's location and responsible engineer's
email on the asset, a mailer to those engineers on degradation, and the Save/Cancel engineer-assignment window.

## For Ghost: waiting on you

- Run the demo on Windows once before the meeting (DEMO.md). If `tkinter` is missing there, python.org's installer with
  "tcl/tk and IDLE" ticked is the fix; nothing else is installed for the product.

0. Settled 2026-11-18 (J-034): "Cold gate refusal is fine. We really care about the warm gate." A refused cold run is
   the pass's measurement; the warm gate is the one held to the 10 min target. Nothing in `scripts/gate.sh` changes.

1. SP-006 to SP-009 are `proposed`: say "in force" (or change them) and the coordinator lands the status.
   The two choices inside them that are the coordinator's, not yours: tkinter as the toolkit (SP-007) and SMTP as
   the one mail path (SP-009).
2. Phase 2's open question: does the scheduled job run `python3 -m solarpunk.cli`, or a frozen entry point?
3. The clause numbers in `docs/CLAUSE-REGISTER.md` (ISO 9001:2015 7.5.2, 7.5.3, 8.7.1, 8.7.2, 9.1.1, 9.1.3, 10.2.1, 10.2.2; ISO 55001:2014 6.2.1, 6.2.2, 7.5, 9.1) are from the worker's knowledge of the standards' numbering: confirm them against your copies.
4. Ghost-Core owes the fixes for F-001 to F-004 (`docs/FINDINGS.md`); this project carries them locally.
5. A remote test with no records passes (J-045): the demo's OAHE-SEN-001 does not answer, its `reachable` fails, and
   its `on_grid` and `irradiance_in_range` read "pass" over 0 readings in the asset window's diagnostics. The colour is
   right (yellow, from `reachable`); the passes are vacuous. The proposal: a third result, "no data", for a test that
   had nothing to check, shown grey like "not run" and never counted as a pass. It changes `Result` and every remote
   test, so it is your ruling first.
6. The rule table (7.4, J-053) is Claude's proposal, `solarpunk test list` prints it: an unreachable inverter suggests
   INV-001, a meter MTR-001, a weather station SEN-001 (as does its irradiance out of range); a tracker, and every
   data-quality failure, suggest nothing. Two gaps in the catalogue keep two diagnostics silent: no inverter code for
   output under the performance floor (soiling, a string down) and none for a logger replaying its last value. Say
   which rules to change and whether the catalogue gains the two codes.
7. Settled 2026-11-18 (SP-020): a suite is a Python module of declarations; a test may acquire its own reads; reactions
   are a closed vocabulary, nothing commanding equipment.
8. The ticket targets (SOL-14, J-061) are Claude's proposal, in force for the code until you set yours: OUTAGE (P1)
   acknowledged within 1 h and worked on within 4 h; DERATE (P2) 4 h and 24 h; INFO (P3) 24 h and 72 h. A preventive work
   order, having no fault, is P3 (J-063), also Claude's proposal. Closing a fault alone (`solarpunk fault close`) leaves
   its ticket open, to be closed with a root cause; since 11.2 `solarpunk ticket ack|comment|resolve` and the asset window's ticket panel move it (J-083).
9. The fast loop's margin (Tune-up pass 8, J-064): settled by SP-025 (J-071), `test/test_gates.py` moved to the full
   gate's "the slow tests" step on Ghost's word. Also open (Tune-up pass 9, J-072): the Python stack's fast checks
   do not run `scripts/checks/readability.py`, so a function grew past its 39 lines over five landings and only the
   pass's full gate refused it; running the check in `stacks/python/gate.sh --fast` costs under a second (a change to
   a gate script, so a decision). Still open: run the fast loop with `-W error::DeprecationWarning`, which would have caught 8.2's Python 3.14
   placeholder warning at once (a change to `scripts/fast.sh`, so a decision).
10. The scheduled run still stops at the first test script that cannot load, naming it (SP-010), though the Manage
    tests window lists it and carries on (9.8, J-091). Say whether the run should skip a broken script, report it,
    and run the rest; it would be a roadmap item.
11. The icon's visor covers both eyes, not one as the brief said (SP-031, J-090); left as painted. Send it back to the
    art agent if you want the one-eye glass; new files replace `solarpunk/ui/art/` under the same decision.
12. Six old `claude/*` session branches remain on GitHub, every one already in `main`; deleting one from a cloud
    session did nothing. Delete them from GitHub's branches page when convenient.

## Advisories under the gate's threshold (Tune-up commit 9; unchanged since pass 0)

The Python stack's gate runs no audit step (`pip-audit` is not in the lock; `stacks/python/README.md` names it for a
dependency review, not the gate), so none were reported; the 20 pins are tools alone (pytest, ruff, mutmut and theirs).
A Core question: whether the stack gate should run an audit each pass.

## Trials: questions settled by a run, not an argument

(none yet)

## What to distrust

- The Python stack's "image" is a venv made per session (`stacks/python/README.md`), not a Docker image; the gate has run under it here.
- 19 tests under `test/test_stacks.py` skip as "no TypeScript stack in this tree": stamp residue from Core's `stamp.py`, which copies every stack's tests; left in place (a Core-owned file) and named for Core under "For Ghost" (Tune-up pass 1).
- `docs/AGENT.md`'s Fast loop and Gate cells are Ghost-Core's numbers until Tune-up pass 0 re-measures them here.
