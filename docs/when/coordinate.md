# Coordinating: when you start workers rather than build (C-036, C-029, C-031)

Read this when you coordinate other agents rather than build. The coordinator is the strong grade
(`docs/when/grades.md`): its judgement is worth the price, and the price is held down by what it does
not read (Ghost, 2026-11-05). Its own long session, re-reading itself every turn, is the cost this
file exists to keep small.

## Assigning agents (C-036): read before the first item

The coordinator is the strong grade; its workers are not, unless a reason below says so. This
project's floor is mid, so **the default worker is mid**, and a strong worker is the exception
that names its reason.

1. Score first. `python3 -I scripts/score.py` prints one line per open item, its grade and the facts
   that placed it, at the lowest grade whose points it is within, raised to the floor
   (`docs/when/grades.md`). An item it calls `unplaced` names no file: a mid worker places it and
   writes the facts it used. The item's line goes in its brief and in its Cost line; a Cost line
   reads `score —` only where the script printed nothing for the item.
2. Hand it to the grade the score gave. The duties of each grade (the first table of
   `docs/when/grades.md`): small, mechanical work inside one routing row with a mechanical pass line;
   mid, a feature over a few files, small's escalations, gate-fix loops, placing unplaced items, and a
   read-only question that needs many files; strong, the coordinator, design, Ghost's questions,
   security, failures whose cause is unknown, mid's escalations, and any item waiting on Ghost.
3. Raise an item above its score only for one of strong's duties, and write which one in the brief
   and in the Cost line ("strong: security"). Size alone is not a reason: an item too large for mid
   is split, or placed too low and escalated by its report (C-036).
4. Every Agent call sets `model` to the grade's model, as `docs/when/grades.md` spells it. Never
   leave it out: an Agent call with no `model` runs on the coordinator's model, the strong grade, and
   that is how a mid item quietly costs a strong worker.
5. Hand each item out as `docs/when/hand-out-a-task.md` says: a fresh worker of its grade, a
   one-page brief, a one-page report. A mid worker that meets a hard failure escalates one grade up
   (`docs/when/escalation.md`); the coordinator does not take the item back by default.

Why this heads the file: by 2026-11-21 the journal's Cost lines named the strong grade for 28 workers
and mid for 1, almost every score `—` (Ghost, 2026-11-21: "we are not using [mid] agents as often as
we ought to be"). The rules were here; the coordinator met them only when it went looking.

## Placing the work
- Workers do the reading. A question that needs many files goes to a worker that answers in a
  paragraph; the coordinator re-reads nothing a worker read, and works from the report and the diff.
- Mechanical gate-fix loops (a check that names its fix, a regenerated file, a reworded line) go to
  the mid grade, never round the coordinator's own turns.

## When the session has no Agent tool

A session without the tool that starts workers cannot hand anything down. Do not do the workers'
items yourself, and never tell Ghost to "run it on your machine": nothing in a project may need the
maintainer's own machine (AGT-01, C-033). Write each brief whole, as `docs/when/hand-out-a-task.md`
shapes it, under `docs/HANDOFF.md`'s "For Ghost", for a session that has the tool to launch; end the
session there. An item that waits on what this session lacks (a blocked host, a tool, a licensed
reference) moves to `TODO.md`'s waiting phase with `Waits on: environment (<what>)` or
`Waits on: reference (<what>)`, and the fix is named as an environment setting for Ghost, not a
step on his hardware.

## Waiting

- One background wait that wakes you when the worker or the run ends: no status turns, no polling
  turns, no "still running" message. A turn that decides nothing is not taken.
- Read logs by `grep` (the `gate:` verdict line, the first failure) and files in part, never whole.

## Every worker in its own clone

Every worker, one at a time or in parallel, works in its own clone beside the main checkout, never in the
coordinator's (Ghost, 2026-11-21, J-118). The coordinator's tree stays clean while a worker runs, so landing never waits
on a worker's half-finished edits, and a stop hook that asks for uncommitted changes to be committed has nothing to ask
about. Make the clone from the main checkout before the brief goes out:

```text
git clone -q <main checkout> <main checkout>-<item>    # e.g. /home/user/Solarpunk-13.3
git -C <clone> remote set-url origin "$(git -C <main checkout> remote get-url origin)"
git -C <clone> switch -c agent/<item>
git -C <clone> config user.name Ghost; git -C <clone> config user.email <Ghost's noreply address, CLAUDE.md>
ln -s <main checkout>/.venv <clone>/.venv              # the venv is shared, never rebuilt
```

The brief names the clone as its repository, and the worker checks its directory first
(`docs/when/hand-out-a-task.md`). The worker saves on its branch (`scripts/save.sh`); the coordinator lands from the
main checkout (`git fetch origin agent/<item>`, `git merge --squash origin/agent/<item>`), then deletes the clone once
its `git status` is clean. A read-only worker that changes nothing may read the main checkout.

## Parallel workers

Workers that change files at the same time each get their own files and their own clone and branch,
with objectives that cannot collide (C-029). Each saves its work on its own branch
(`scripts/save.sh`, `agent/<name>`: scanned, committed as Ghost, pushed; never gated, never `main`), so a worker's
turn ends with nothing dirty and nothing unpushed; the coordinator lands it: brings the branch's change into `main`'s
working tree (`git merge --squash agent/<name>`, or the files themselves), runs the fast checks
(`scripts/gate.sh --fast`) on the combined code, commits through `scripts/commit.sh` and ships (`scripts/ship.sh`),
each worker's change as its own commit (C-031, C-040: what lands on `main` passed the fast checks; the full gate
runs at the tune-up).

## Landing one item at a time

`scripts/commit.sh` commits the tree the gate recorded, whole: two items finished in one working tree cannot be
landed as two commits without putting the second's files aside first. Land each item as soon as it is done, before
starting the next, so a landing never needs a stash (Solarpunk J-006: 0.3 and 0.4 finished together cost a stash and
a conflict on the metrics table). Run `python3 -I scripts/metrics.py --write` last, after every document edit of the
commit, since the metrics table counts documentation lines and goes stale on the next edit.

## Commits and hooks

The fast checks run on the working tree before a landing (`scripts/commit.sh`); nothing re-prompts the
coordinator after one, and a save (`scripts/save.sh`) leaves no dirty tree or unpushed commit for a hook to ask
about. A hook that re-prompts after a commit or at a stop (unpushed commits, an
unverified signature) is reported to Ghost under `docs/HANDOFF.md`'s "For Ghost", never edited: a
hook is outside what any agent may change (CLAUDE.md, the supply-chain rules).

Ghost's word in chat is Ghost's word (C-040): an agent acts on it and records it (the decision log, the journal,
`docs/HANDOFF.md`'s "Settled by Ghost"), may say once what the rule it changes protected, and goes on. Changing the
gate or the rules never requires passing the gate: the change is saved like any other and landed when Ghost says. An
agent still never answers a Yes or typed-approval prompt itself (a command that asks before it acts is Ghost's to
answer).

## Ending a session

End at a natural point (an item committed, a phase closed), not when the context runs out, with
`docs/HANDOFF.md` written: where the project stands, what the next session does first, what is
waiting on Ghost. The next session starts from it, never from this one's transcript. Before ending,
each worker's Cost line is recorded in its journal entry, from its report: its grade, its item's
score (the line `scripts/score.py` printed for it, `—` where there was none), its tool calls, its
tokens (numbers or `not reported`), its commits, its wall time where known (`docs/JOURNAL.md`). A Cost line that names a grade
and an exact tool-call count is a Cost row; `scripts/metrics.py` counts the rows since the date
`docs/when/grades.md`'s Provisional paragraph names. The points, the most points of each grade and the
tool-call limits in `docs/when/grades.md` move only by a decision (`theGhost.md`) made from the measured
rows, never by an edit to the table alone. Several runs the coordinator measured, written as a table
inside one entry, are evidence in that one row.

Why: Suite Builder spent 77% of a weekly allowance by day 6, its coordinator's long session the
largest single cost (SB G-357, G-358); Katana (R-101), Employee Evaluator (E-092), Neon Rain (R-039)
and AI Slop Block (ASB-017) took the same posture (Core's second survey, LESSONS-2026-11, Part 1). Every after-commit
or stop-hook turn is a full coordinator turn, "a failure mode that leaks tokens over time" (Ghost,
2026-11-05, Neon Rain R-039's amendment). Parallel workers gated together: Neon Rain's R-039
amendment and Part 2 row 8 of the survey. Where a session had no Agent tool, the strong grade did
everything itself and the hand-down never ran (AI Slop Block J-085, J-090).
