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

Last review: a595275 (2026-11-18, Tune-up pass 6)

## Entries

An entry is `### <date> · <task> · <agent>` and four lines: **Task**, **Opened** (files, in order), **Complaints**,
**Suggestions**.

### 2026-11-18 · 7.1, who assigned a fault · Claude

- **Task**: SP-015's first step: an engineer on every fault, an operator when called in, cover shown.
- **Opened**: `docs/paths/product.md` (the fleet-and-faults row), `solarpunk/leaf/faults.py`, `solarpunk/faults/ledger.py`, `solarpunk/project/orchestrator.py`, `solarpunk/receiver/server.py`, `solarpunk/cli/main.py`, `solarpunk/ui/asset_window.py`, `solarpunk/ui/demo.py`.
- **Complaints**: the product workpath's new row sent me to the right four files first; a rule added to `project.assign_fault` reached forty-five callers, and nothing lists the tests that build their own fleets (each needed an engineer the fleet holds); a failing test that leaves a server thread running hangs the fast loop after its summary, with no timeout to say so.
- **Suggestions**: a timeout on `scripts/fast.sh`'s run, so a hang is a red line, not a stall.

### 2026-11-18 · 7.2, the gate's reliability · Claude

- **Task**: SP-017's gate half: a frozen copy, timeouts, ruff and the window tests in the fast checks, daemon threads.
- **Opened**: `scripts/gate.sh`, `scripts/fast.sh`, `stacks/python/gate.sh`, `test/support_git.py`, `test/test_gates.py`, `scripts/checks/gate_record.py`.
- **Complaints**: the process workpath's gates row is long but named every file I needed; the gate's own header is the clearest description of it, and a new paragraph was needed there to keep it so.
- **Suggestions**: none.

### 2026-11-18 · 7.3, counts that follow from the registry · Claude

- **Task**: no test pins what the registry and the parser decide.
- **Opened**: `docs/paths/product.md` (the remote-test row, which named the counts), `test/solarpunk/test_remote.py`, `test/solarpunk/test_project_run.py`, `test/solarpunk/test_demo.py`, `test/solarpunk/test_cli_tests.py`, `test/solarpunk/test_ui_asset.py`.
- **Complaints**: what a run stores per asset (its kind's tests, and a failed ping beside them) is written in no document; it was read off the pinned numbers.
- **Suggestions**: a sentence in `docs/CONTRACT.md` or the remote module's docstring: what one scheduled run stores per asset.

### 2026-11-18 · 7.4, suggestions from the tests · Claude

- **Task**: SP-015's suggestions: the rule tables, the table, the run, the receiver, accept and dismiss.
- **Opened**: `docs/paths/product.md` (the remote-test and feed rows), `solarpunk/remote/registry.py`, `solarpunk/remote/results.py`, `solarpunk/remote/run.py`, `solarpunk/project/run.py`, `solarpunk/project/orchestrator.py`, `solarpunk/receiver/server.py`, `solarpunk/remote/scaffold.py`.
- **Complaints**: `git stash` does not stash files marked intent-to-add, so comparing against the last commit by stashing silently compared nothing; a worktree of HEAD was the way. The Tk rule (a window freed off the main thread aborts the run) was known to one test file's setUp and written nowhere a window test's author would read.
- **Suggestions**: the product workpath's window row to name `test/solarpunk/conftest.py` and the reason; "compare with a worktree of HEAD, never a stash" in the process workpath.

### 2026-11-18 · 7.5, suggestions in the window and on the command line · Claude

- **Task**: Accept and Dismiss in the asset window, three CLI commands, their tests.
- **Opened**: `docs/paths/product.md` (the window and command rows), `solarpunk/ui/asset_window.py`, `solarpunk/project/surface.py`, `solarpunk/cli/main.py`.
- **Complaints**: none for finding my way: the product rows named each file; the window and command rows' recipes (xvfb, the screenshot, one help line per command) held.
- **Suggestions**: none.
