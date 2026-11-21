# Handoff: what to work on next, and what is waiting on whom

Read `CLAUDE.md` first, then this. `TODO.md` is the chain in order; `docs/DONE.md` is what is finished.

## Start here (2026-11-21, the session that ended at SP-043)

Ghost, 2026-11-21 (SP-044, J-117): the roadmap leans into the ISO traceability matrix. After 13.3 to 13.13 comes Phase 14, the traceability matrix, then 15 quality management (was 18), 16, 17, 18 contractors (was 19), 19 vendors (was 20), 20 Azure (was 21), and last 21 the network's security with company sign-in (was 14) and 22 the central server (was 15).

Phase 12 is closed but for 12.7 (Phase W). `main` is clean and pushed at SP-043, every landing through the fast gate,
Tune-up commit 12 through the full gate (cold 1.47 min, warm 1.47 min, fast loop 24.13 s). Every session branch on
GitHub is deleted; only `main` remains.

**Next: 13.1 and 13.2, in parallel. Ghost approved starting them (2026-11-21: "start 13.1 and 13.2"); they were not
started before this hand-off, so nothing is in flight.** 13.1 is the remote test's contract (`docs/REMOTE-TESTS.md` and
a check); it must write down the three results 12.9 made (pass, fail, and "no data", `Result.no_data` and
`nothing_to_check` in `solarpunk/remote/results.py`), which its Check line predates. 13.2 is the suites folder. Phase 13
ends with Ghost's human maintainability pass (SP-042, 13.8 to 13.11), then its tune-up pass, 13.13.

What this session landed, newest first (the journal has each):
- SP-043 (J-113): the readability check runs in the fast checks (For Ghost 9 settled).
- SP-042 (J-112): the human maintainability pass placed as 13.8 to 13.11: no name of two characters or fewer (a
  check), names and purpose comments reviewed, a README for people in each module, a generated decision map.
- Tune-up commit 12 (J-111): the reopened Phase 12 closed; the cold gate caught 12.9's missing docstring.
- SP-041 (J-110): `docs/GHOST-IN-THE-KERNEL.md` opens with Suite Builder's text word for word.
- 12.10 (J-109): irradiance minimum -5 W/m2, an inverter's night floor -2% of its rating, 1% over the rating, inverter
  N reading pad N's station; the baseline re-run: about 2,700 threshold false alarms gone, every real event still
  caught, no new alarm (the counts are in J-109).
- 12.11 (J-108): deactivating twice refused, the password asked last, `solarpunk ticket show ID`, a dismissal's operator.
- 12.9 (J-107): no data is not a pass: `reachable` fails a disconnection, the other tests return a grey "no data".
- SP-039 and SP-040 (J-106): Ghost's eleven calls, all as recommended; Solarpunk no longer follows Ghost-Core.
- The asset window split (J-105): its words to `solarpunk/ui/asset_text.py`.
- Before those, from Tune-up pass 12 back: J-095 to J-104 (12.4, 12.5, 12.6, SP-033 to SP-038).

How this session worked: Ghost said what to build; the coordinator wrote a one-page brief per item
(`docs/when/hand-out-a-task.md`), an agent of the item's grade built it on an `agent/` branch and saved it with
`scripts/save.sh`; the coordinator read the diff, ran the fast checks and the window tests under
`xvfb-run -a /usr/bin/python3.12` (the default python3 has no tkinter), read the screenshot, squashed the branch onto
`main` (`git merge --squash`), wrote the records and landed it with `scripts/commit.sh --ship`. Two agents in parallel
worked in two checkouts, the main one and a clone beside it (`git clone`, its origin set to GitHub, `.venv` a symlink to
the main one's), since two branches cannot share one working tree and briefs forbid worktrees under `.claude/` (J-108).
Choice lists for Ghost were drawn by a read-only agent and put with a recommendation each (J-106).

Mind, before adding:
- The largest files sit at their edge: `test/solarpunk/test_project_run.py` 398 of 400 lines (a new test of the
  scheduled run goes in a new file); `solarpunk/project/orchestrator.py` near 390; `solarpunk/cli/main.py` near 395.
- A store some earlier test file leaves unclosed (J-033) is collected at random; a test that captures stderr then fails
  on its ResourceWarning (12.9 in `test_output`, 12.11 in `test_field`). The guard is `gc.collect()` at the top of the
  class's `setUp`; the fix is closing those stores (For Ghost 13d, now with two incidents).
- The field data's local copy (/home/user/field-data/) lives in this container and goes with it; `docs/FIELD-DATA.md`
  says how to fetch it again (the S3 listing stops at 1,000 keys: ask by prefix, J-109's debrief).
- Not run from here: the shortcut and Open folder on Windows or a Mac; the window's title bar (no window manager).

## Where the project stands (2026-11-20, rewritten at the mid-Phase 12 tune-up commit)

Phases 0 to 12 are closed (12.7 waits in Phase W);
12.7 waits in Phase W. What is done, item by item, is `docs/DONE.md`; why, the journal (`docs/journal/INDEX.md`). The
order of what is next is `TODO.md`; Ghost's direction for the product is `docs/GOAL.md`; the phases ahead are 13 (the
tests' record), 14 (the traceability matrix), 15 (quality management), 16 and 17, 18 (contractors), 19 (vendors),
20 (Azure), 21 (the network's security) and 22 (a central server).

What exists: the fleet registry, the fault ledger over a closed catalogue, synthetic SCADA with gaps as data, the KPI
engine with its blind mirror, the clause register, the asset maintenance list, the feed by IP and port with a
simulator, seven standalone remote tests with a registry and a scaffold, suggestions from a rule table, the receiver,
cron and Task Scheduler from one job, the mailer over SMTP, the scheduled run, local tickets with their outbox and
move log, accounts with sign-in, attribution and versions, the tkinter windows and the demo, the one-word launcher.

Still open from earlier sessions, said plainly: `solarpunk.cmd`'s paths other than `--help` (J-040) have not been
reported back from Windows; "Add a test suite" was read as scaffolding one remote test (`test add`), a reading Ghost
has not confirmed; some test leaves a store unclosed (a ResourceWarning, J-033; about 120 lines of them in the fast
loop's output by 12.5's count), not yet found.

Candidates Ghost has not placed: the asset window listing open work orders and closing one with a cause; the receiver
and the clock exercised end to end in the demo; `tracker_moving` and `energy_monotonic` as remote tests (`solarpunk
test add <name> --clause <id>` scaffolds each); a SOL-13 for root causes; whether a tune-up pass still needs a cold and
a warm gate run now that no step keeps a cache.

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
4. Settled 2026-11-21 (SP-040): Solarpunk no longer follows Ghost-Core; F-001 to F-004's local fixes are its own.
5. Settled 2026-11-21 (SP-039): no data is not a pass; `reachable` fails it as a disconnection, the other tests
   return a grey "no data". Built by 12.9.
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
9. The fast loop's margin: settled by SP-025 (J-071). The readability check in the fast checks: settled by SP-043
   (2026-11-21). Still open: run the fast loop with `-W error::DeprecationWarning`, which would have caught 8.2's Python 3.14
   placeholder warning at once (a change to `scripts/fast.sh`, so a decision).
10. The scheduled run still stops at the first test script that cannot load, naming it (SP-010), though the Manage
    tests window lists it and carries on (9.8, J-091). Say whether the run should skip a broken script, report it,
    and run the rest; it would be a roadmap item.
11. The icon's visor covers both eyes, not one as the brief said (SP-031, J-090); left as painted. Send it back to the
    art agent if you want the one-eye glass; new files replace `solarpunk/ui/art/` under the same decision.
12. The 33 session branches on GitHub, all landed or superseded, listed for Ghost on 2026-11-21, who deletes them.
    `claude/hold-8.1-token` alone holds code `main` lacks: SP-018's reply-token draft, dead since SP-021.

13. From the mid-Phase 12 tune-up commit (J-100), each a decision or a roadmap line, none acted on: (a) a worker's fast
    checks stop at `test_metrics` because the metrics row is the coordinator's, hiding lint and the window tests; the
    brief now sanctions a write-and-restore, but the gate could report the stale row on an `agent/` branch without
    stopping (a gate change). (b) The mandatory-context metric counts `CLAUDE.md` alone, though every agent is sent on to
    this file; count its "Start here" section, or make only that section required reading. (c) The supply-chain scan
    reads the disk, so an agent's worktree under `.claude/worktrees/` trips it with copies of the planted fixtures (J-096);
    skip that folder, or keep agents out of worktrees as the brief now says. (d) The unclosed store's ResourceWarning
    (J-033) as a roadmap item: a test change, outside a tune-up. (e) Settled by SP-038 (J-103): the gate's own scratch-repository tests
    run in the full gate; the fast loop is 25.6 s.
    (f) For Ghost-Core: the navigation log's entry line came from the stamp cut off at "An entry is `"; completed here.

14. Settled 2026-11-21 (SP-040): no Core look; Solarpunk no longer follows Ghost-Core.
15. Settled 2026-11-21 (SP-039, J-106): the open calls of 12.4 to 12.6, each as recommended; built by 12.10 and 12.11.
16. From 12.9 (J-107), the build's readings, each easy to change: `reachable`'s pass reason still counts gaps among its
    records (the demo's "156 records"; real records only would make CONTRACT's example 154); `python3 -m
    solarpunk.remote.run` exits 3 for no data; a run with failures and no data reads "N failed" in the Runs window.
    From 12.11 (J-108): `ticket show` signs in as the other ticket commands do, though it only reads; say if a read
    should need no sign-in.
17. From 12.10 (J-109): `solarpunk/feed/client.py` refuses a live reading outside the list's range, and the list keeps an
    inverter's power minimum at 0 (the -2% floor is `on_grid`'s, per rating), so a real inverter's night draw is refused
    at the feed before `on_grid` sees it. The likely fix: the feed holds power to the same per-asset range as `on_grid`,
    which means moving `field_range` where both can reach it (the leaf), a module question. Also: irradiance from -5 to
    0 now enters the performance ratio's reference sum as a small negative term (`solarpunk/kpi/performance.py`);
    clamping it to 0 there would be a change to SOL-08's arithmetic.
18. From 13.2 (J-115): a named suite's tests also run as `all` on every run, so once a named suite exists its
   results are stored twice at one instant, and `latest_for` and the windows read both rows; a named suite's results
   do not change an asset's status. Choose: readers filter to `all`, dedupe by test, or `all` stops being every test
   once named suites exist. No suite file ships, so nothing doubles today. The cadence spelling is the worker's:
   `"every run"`, `"hourly"`, `"daily at HH"` (UTC).
19. A stop hook in this cloud session's setup (not in the repository) asks for uncommitted changes to be committed
   and pushed whenever a turn ends with a dirty tree; it fired twice while a worker edited the coordinator's checkout
   (J-117). Reported, never edited (CLAUDE.md, `docs/when/coordinate.md`). Answered by Ghost's word of 2026-11-21
   (J-118): every worker in its own clone, so the coordinator's tree stays clean. Change the hook itself only if you
   want it to.
20. Settled 2026-11-21 (SP-047, J-125): "go with your recommendations": (a) SIT-004 for a lost link, (c) and (d) as 13.12 (done, J-126); (b) as built; (e), (f) and (g) stand open. From Phase 7's reopening (J-121 to J-124):
    (a) a failed `reachable` on an inverter raises INV-001, an OUTAGE, so it counts against availability with no one
    between; the coordinator recommends the generic SIT-004 (INFO) for an unreachable asset, since a lost link is not a
    dead inverter; (b) no data ends a ticket's streak, so a short comms gap splits one problem into two tickets; the
    other reading skips no-data results; (c) no command lists result ids for `ticket open --result ID` (proposed:
    `solarpunk test results --asset ID [--failed]`); (d) code left unused by 7.7: `cells.drawn` and its test,
    `access.permit_suggestion`, `access.open_suggestions_for`, the "Awaiting an engineer" band cell (reads 0 on new
    stores); (e) named suites raise no faults and join no streaks; (f) the gate skips the window tests where `python3`
    has no tkinter; running them under `xvfb-run python3.12` is a gate change; (g) the fast loop at 27.9 s of 30.

## Advisories under the gate's threshold (Tune-up commit 7, 2026-11-21; unchanged since pass 0)

The Python stack's gate runs no audit step (`pip-audit` is not in the lock; `stacks/python/README.md` names it for a
dependency review, not the gate), so none were reported; the 20 pins are tools alone (pytest, ruff, mutmut and theirs).
Whether the stack gate should run an audit each pass is Solarpunk's own question now (SP-040).

## Trials: questions settled by a run, not an argument

(none yet)

## What to distrust

- The Python stack's "image" is a venv made per session (`stacks/python/README.md`), not a Docker image; the gate has run under it here.
- 19 tests under `test/test_stacks.py` skip as "no TypeScript stack in this tree": stamp residue from Core's `stamp.py`, which copies every stack's tests; Solarpunk's own file since SP-040, to keep or trim.
- `docs/AGENT.md`'s Fast loop and Gate cells are Ghost-Core's numbers until Tune-up pass 0 re-measures them here.
