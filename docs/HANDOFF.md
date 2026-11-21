# Handoff: what to work on next, and what is waiting on whom

Read `CLAUDE.md` first, then this. `TODO.md` is the chain in order; `docs/DONE.md` is what is finished.

## Start here (2026-11-21, the session that landed 13.5 to 13.7)

**Next: 13.8, Ghost's human maintainability pass (SP-042), names of three characters or more, then 13.9 to 13.11 in
parallel. 13.5 to 13.7 landed this session; `main` is clean and pushed.** `scripts/score.py` places 13.8 to 13.11
strong: they read most of the tree. Then 13.14 the pass. After Phase 13 comes Phase 14, the traceability matrix, now with historical mode inside it (SP-048:
14.5 historical import, 14.6 the historical run, 14.7 the replay's speed, 14.8 the matrix over a live or historical
store, 14.9 its window, 14.10 the pass), then 15 to 20, and last 21 security with company sign-in and 22 the server
(SP-044).

What this session landed, newest first (the journal has each):
- 13.7 (J-135): the Tests window (`record_window.py`, "Tests" beside Reports); J-133 moved it off 9.8's files.
- 13.6 (J-134): last run and duration in the asset window's diagnostics; `asset_text.duration_words`.
- SP-050 (J-132): 13.5's readings, as built.
- 13.5 (J-131): `results.duration_ms`, each test timed in `remote/run.py`'s `timed`; `project.tests_overview` and
  `project.test_log`. A duration not recorded reads None, never 0.
- 13.13 (J-130): the demo takes five quick burst reads, so OAHE-INV-001's `power_ripple` passes; `test run --acquire
  [--shorten N]`; the demo's feed made live, and the client's half-close race fixed (test_demo 12 of 12, was 5 of 7).
- 13.4 (J-129): `REACTIONS` (`Fault`, `Mail`, `RunSuite`, `OpenPreventive`) replace `SUGGESTS`, checked at load,
  carried out and recorded in the append-only `reactions` table.
- SP-048 and SP-049 (J-128): historical mode placed in Phase 14; bursts in the demo; 13.4's `Fault(code)`.
- 13.3 (J-127): a test's own reads: `ACQUIRE`, `Burst`, the feed's live read, `power_ripple` (5 % of rated, Ghost's).
- 13.12 (J-126) and SP-047 (J-125): a lost link raises SIT-004, not an outage; `solarpunk test results`; 7.7's unused
  code removed.
- Phase 7 reopened by SP-046 and closed again (J-120 to J-124): faults from telemetry, no accept or dismiss; a root
  cause written in words by an engineer, required before a ticket closes; a ticket opened from a failed result, one
  ticket to a streak of failures; Tune-up commit 7 (cold 1.68 min, warm 1.70 min).
- 13.1 and 13.2 (J-115, J-116); SP-044 and SP-045 (J-117, J-119: the matrix ahead, a tune-up every 25 commits);
  J-114 and J-118 (the coordinator pointer in CLAUDE.md; every worker in its own clone).

How this session worked: the coordinator scored each item (`python3 -I scripts/score.py`), made a clone per worker beside
the main checkout (`docs/when/coordinate.md`, "Every worker in its own clone"), handed it to a mid worker with `model`
set and a one-page brief, read the report and the diff, ran the window and demo tests under `xvfb-run -a python3.12`,
wrote the records and landed it with `scripts/commit.sh --ship`, then deleted the clone. Ghost answered open choices in
batches ("go with your recommendations"); each was recorded as a decision before its work started.

Mind, before adding:
- File sizes: `test/solarpunk/test_project_run.py` and `solarpunk/project/orchestrator.py` sit near 400 lines (a new
  test of the scheduled run goes in a new file; new project code in a new file of the package, as `causes.py`,
  `result_tickets.py` and `reactions.py` are). `solarpunk/cli/main.py` is 336 since the `test` commands moved out.
- The fast loop stands at 22 to 24 s of its 30 s target; a busy machine has twice pushed a run past 30 s (33.9 s,
  30.5 s), each re-run 22 to 24 s.
- `scripts/gate.sh`'s `python3` has no tkinter, so the window tests skip inside it (137); run them under
  `xvfb-run -a python3.12 -m unittest discover -s test -t . -p "test_ui*.py"` (`-t .` matters) and test_demo the same
  way. A ResourceWarning ("unclosed database") still shows in the fast loop's output (For Ghost 13d).
- DEMO.md still says a ticket resolves with a root cause (7.8 moved the cause to the fault) and names the Errors tab's
  "suggestions" column: bring its walk-through up to Phase 7 before the demo is shown.
- Session branches to delete on GitHub (the proxy refuses a remote delete): claude/coordinator-assignment, agent/13.1,
  agent/13.2, agent/13.3, agent/13.4, agent/13.12, agent/13.13, agent/7.7 to agent/7.10, agent/roadmap-sp044,
  agent/12.10-field-thresholds.
- The field data's local copy (/home/user/field-data/) lives in this container and goes with it; `docs/FIELD-DATA.md`
  says how to fetch it again (the S3 listing stops at 1,000 keys: ask by prefix, J-109's debrief).

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

21. Settled 2026-11-21 (SP-050): "go with your recommendations", each as built. From 13.5 (J-131), the worker's readings, each easy to change: `tests_overview` counts suite `all` alone (item 18's
    question, answered for the overview) and no data as a third count; `test_log` reads every suite, each entry naming
    its suite; an unknown test name, and a limit below 1, give () rather than a refusal; the ping's failed `reachable`
    is untimed (None). Say if any should change before 13.7 shows them.

22. Settled 2026-11-21 (SP-051): "go with your recommendations", as built. From 13.6 (J-134): a test that judges stored samples takes under a millisecond, so the asset window reads "0 ms"
    for most of the demo's tests (measured, not missing; only the ping's untimed `reachable` reads "—"). Say if a
    measured duration should round up to 1 ms, or read "<1 ms".

23. Settled 2026-11-21 (SP-051): as built. From 13.7 (J-135), the Tests window's readings: the log leaves out the suite; an overview row with any failure is
    red; `reachable` over the demo reads 3 failures where 2 assets are down, since a dead feed's ping stores its own
    failed `reachable` beside the suite's (J-050's double). Say if the overview should count one per run instead.

24. From the demo's ISO walk dry run (J-141, SP-052), six choices before the demo item is placed: (1) which asset carries
   the loop: OAHE-INV-002 (works with a revived feed, also carries the INV-001 outage) or OAHE-SEN-001 (a cleaner story,
   needs a sensor feed); (2) a demo store with accounts so every move names a person, or `--by` on `ticket ack` and
   `resolve`; (3) demo acts stamped on the demo's day or the wall clock; (4) the demo's telemetry at zero during
   OAHE-INV-002's outage; (5) the clause register's sentences reworded to cover every remote test that cites them (14.1);
   (6) the SOL-14 hours, still a proposal, and whether a result's ticket clock starts at the failure.

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
