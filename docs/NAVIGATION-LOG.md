# Navigation log: what agents found hard to find

Each new task goes to a fresh agent of the grade it is placed at (C-026, C-036; `docs/when/grades.md`). At the end of its task the agent
debriefs here: one entry, its complaints and suggestions about finding its way (routing rows,
documents, names, rules that were unclear), not about the task's code. "none" is an answer.

**The review is part of every tune-up** (steps 4 and 5 of `docs/when/tune-up.md`; C-024, C-025;
`scripts/commit.sh` says when one is due): read the entries for what agents who did not see each other converge on; wipe the entries
(git keeps them); check each item against the code and act on the valid ones; take an open question
to the ruling grade; record the review in the journal; set the line below to the commit the
review ran at (`git rev-parse --short HEAD`, not the tune-up's own, which does not exist yet). Each entry's **Opened** list, read against the routing row its task matched, is the measure
of whether a fresh agent found its way: files, in order; `CLAUDE.md` does not count.

Last review: 3be733f (2026-11-21, Tune-up commit 12)

## Entries

An entry is `### <date> · <task> · <who>`, then four bullets: **Task**, **Opened** (files, in order), **Complaints**,
**Suggestions**.

### 2026-11-21 · 7.8 the root cause · mid-grade worker
- **Task**: a fault's root cause as free text an engineer writes, append-only; a ticket closes only once it is written (J-122).
- **Opened**: `grep -rn "root_cause\|RootCause"` first, then the product row's ledgers, `project/orchestrator.py`, the CLI and window files, the clause register.
- **Complaints**: the brief's working set missed the files holding the dropdown and `--cause` (`ui/ticket_panel.py`, `cli/tickets.py`), which the grep found at once; `docs/DEMO.md` named in the brief does not exist.
- **Suggestions**: a brief that removes a name builds its working set from the grep, not from the routing row.

### 2026-11-21 · 7.7 faults from telemetry · mid-grade worker
- **Task**: a failing remote test raises its fault itself; accept and dismiss removed (J-121).
- **Opened**: the brief's working set: `solarpunk/remote/suggestions.py`, `solarpunk/project/suggest.py`, the receiver, the CLI and UI files, `solarpunk/leaf/codes.py`, `docs/CLAUSE-REGISTER.md`, `docs/DEMO.md`, then the tests the removal broke.
- **Complaints**: the working set was right but narrow on tests: eight test files outside the brief's list pinned the removed behaviour or the demo's counts; `test_metrics` needs `metrics.py --write` before `gate.sh --fast`, and its largest-file limit caught `test_project_run.py` at 402 lines.
- **Suggestions**: a brief that removes a behaviour lists the tests by `grep -rln` for its names, not by guess.

### 2026-11-21 · coordinator assignment pointer · coordinator
- **Task**: make CLAUDE.md send the coordinator to the agent assignment logic (J-114).
- **Opened**: `docs/when/handoff.md`, `docs/when/coordinate.md`, `docs/HANDOFF.md`, `docs/when/grades.md`, `theGhost.md` (C-020, C-022, C-036), `docs/when/hand-out-a-task.md`, `scripts/checks/grades.py`.
- **Complaints**: "You coordinate other agents rather than build" did not read as an entry condition to a session Ghost started, so the assignment rules were met only when looked for.
- **Suggestions**: none beyond J-114.

### 2026-11-21 · 13.2 the suites folder · mid-grade worker
- **Task**: TODO 13.2, SP-019 and SP-020.
- **Opened**: theGhost.md (SP-019, SP-020), `TODO.md`, `solarpunk/remote/registry.py`, `solarpunk/remote/run.py`, `solarpunk/remote/results.py`, `solarpunk/remote/scaffold.py`, `solarpunk/project/run.py`, `solarpunk/cli/main.py`, `solarpunk/cli/tickets.py`, `docs/modules.json`.
- **Complaints**: the fast checks stop at `test_metrics` on a worker's tree (the copy-aside works); a writer that imports a folder function by name escapes a test's patch and writes into the real folder.
- **Suggestions**: a routing row "A suite" in `docs/paths/product.md`; a line on the suites folder in `docs/`.

### 2026-11-21 · 13.1 what a test looks like · mid-grade worker
- **Task**: TODO 13.1, SP-019: the remote test's contract and its check.
- **Opened**: `docs/paths/process.md`, `docs/paths/product.md`, `solarpunk/remote/results.py`, `solarpunk/remote/scaffold.py`, the seven modules of `solarpunk/remote/tests/`, `scripts/checks/asset_types.py`, `scripts/checks/common.py`, `scripts/checks/readability.py`, `test/test_asset_types.py`, `test/support.py`, theGhost.md (SP-019, SP-020), `TODO.md`.
- **Complaints**: the readability check reads fixtures under `test/` too, so a planted Python break needs docstrings and short comprehensions, which no row says; the fast checks stop at `test_metrics` on a worker's tree.
- **Suggestions**: a reverse check (every `Tests:` name has a module) once `tracker_moving` and `energy_monotonic` exist; 13.3 and 13.4 change this check's fields.

### 2026-11-21 · SP-044 roadmap renumbering · mid-grade worker
- **Task**: move six phases to SP-044's order and write Phase 14 in `TODO.md` and `docs/ROADMAP.md`.
- **Opened**: theGhost.md (SP-044), `TODO.md`, `docs/ROADMAP.md`, `README.md`, `test/test_readme.py`, `docs/HANDOFF.md`.
- **Complaints**: none.
- **Suggestions**: none.
