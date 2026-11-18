# Handoff: what to work on next, and what is waiting on whom

Read `CLAUDE.md` first, then this. `TODO.md` is the chain in order; `docs/DONE.md` is what is finished.

## Where the project stands (2026-11-18, 05:00, the morning hand-back)

Phases 0 to 3 are closed in one night: 31 commits on `main`, each landed through the gate and authored as Ghost.
**The demo is `python -m solarpunk.ui --demo`; `DEMO.md` has the Windows commands, what to click and the talk track.**
Under xvfb here it prints the simulator's port, `demo: store demo.db rebuilt`, `demo: run - 9 green, 1 yellow, 1 red`
and opens the window; it has not been run on Windows (this session has none, F-03), so run it once before the meeting,
from a fresh clone, and read DEMO.md's "If something goes wrong".

What exists: the fleet registry, the fault ledger over a closed catalogue, synthetic SCADA with gaps as data, the KPI
engine with its blind mirror (contractual availability, performance ratio, energy yield, MTBF/MTTR), the clause register
and `scripts/clauses.py` (9001: 7 held, 1 open; 55000: 4 held), the orchestrator and CLI; the asset maintenance list,
the feed by IP and port with a simulator, standalone remote tests with a registry, the receiver, cron and Task Scheduler
from one job, the mailer over SMTP, the scheduled run; the tkinter fleet window with the status glyphs, the asset window
with Save and Cancel, the add-asset window with the type dropdown, the demo; and Phase 4's work-order ledger with root-cause codes, so every row of the clause register is held (9001
eight, 55000 four). 487 product tests and 385 template tests; 4,720 mutants, every survivor killed or explained.
Phase 5 is Ghost's of 2026-11-18: 5.1 the one-word `solarpunk` command and the `test list|run|add` commands (J-033)
and 5.2 the help list behind `solarpunk --help` (J-035), both done; 5.3 the pass; Phase 6 is the network's security, 6.1 its
design pass (a document and proposed decisions first, Ghost's to rule on), 6.2 its pass. Other candidates, Ghost's to plan: the asset window listing open
work orders and closing one with a cause; the receiver and the clock exercised end to end in the demo; `tracker_moving`,
`energy_monotonic`, `irradiance_in_range` and `night_power_near_zero` as remote tests; a SOL-13 for root causes; the
structure-half candidates of J-024; a Windows run of the demo recorded as a journal trial.

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

## Advisories under the gate's threshold (Tune-up pass 0)

The Python stack's gate runs no audit step (`pip-audit` is not in the lock; `stacks/python/README.md` names it for a
dependency review, not the gate), so none were reported; the 20 pins are tools alone (pytest, ruff, mutmut and theirs).
A Core question: whether the stack gate should run an audit each pass.

## Trials: questions settled by a run, not an argument

(none yet)

## What to distrust

- The Python stack's "image" is a venv made per session (`stacks/python/README.md`), not a Docker image; the gate has run under it here.
- 19 tests under `test/test_stacks.py` skip as "no TypeScript stack in this tree": stamp residue from Core's `stamp.py`, which copies every stack's tests; left in place (a Core-owned file) and named for Core under "For Ghost" (Tune-up pass 1).
- `docs/AGENT.md`'s Fast loop and Gate cells are Ghost-Core's numbers until Tune-up pass 0 re-measures them here.
