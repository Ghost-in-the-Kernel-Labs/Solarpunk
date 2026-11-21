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

Last review: 805522c (2026-11-21, Tune-up commit 7)

## Entries

An entry is `### <date> · <task> · <who>`, then four bullets: **Task**, **Opened** (files, in order), **Complaints**,
**Suggestions**.

### 2026-11-21 · 13.3 a test's own reads · mid-grade worker
- **Task**: `ACQUIRE` and `Burst`, the feed's live read, the runner's hand-off, `power_ripple` (J-127).
- **Opened**: `docs/REMOTE-TESTS.md`, `solarpunk/remote/tests/power_under_rated.py`, `solarpunk/remote/registry.py`, `solarpunk/feed/client.py`, `solarpunk/feed/simulate.py`, `solarpunk/remote/run.py`, `solarpunk/project/run.py`, `docs/modules.json`.
- **Complaints**: the live feed had to share the ping's port, so a request and a ping are told apart by a half-close; `RemoteTest` equality needed the read guard cached per `run`.
- **Suggestions**: none.

### 2026-11-21 · 13.12 Phase 7's loose ends · mid-grade worker
- **Task**: reachable's inverter row to SIT-004, `solarpunk test results`, 7.7's unused code removed (J-126).
- **Opened**: `solarpunk/remote/tests/reachable.py`, `grep -rn "INV-001"` over the tests and DEMO.md, `solarpunk/cli/main.py`, `solarpunk/project/runs.py`, `solarpunk/ui/cells.py`, `solarpunk/project/access.py`.
- **Complaints**: `solarpunk/cli/main.py` at 399 lines leaves no room for the next command; a brief's metrics restore leaves `test_metrics` red on the branch.
- **Suggestions**: split the CLI's `test` commands out of `main.py`, as `cli/tickets.py` is.

### 2026-11-21 · 7.10 tune-up commit 7 (re-measure) · mid-grade worker
- **Task**: steps 1, 2, 5 and 6 of a reopened Phase 7's closing tune-up commit: cold and warm full gate, the metrics table, the log wiped.
- **Opened**: `docs/when/tune-up.md`, `docs/when/long-run.md`, `docs/NAVIGATION-LOG.md`, `docs/AGENT.md`, `docs/HANDOFF.md`.
- **Complaints**: the gate's interpreter (`python3`) has no tkinter, so its 137 skips hide the window tests, and the brief's `discover -s test -p` line fails with 19 import errors without `-t .` (`scripts/fast.sh` has it); the brief called `attribution.recorded_as`'s `deed` unused, but it is the refusal's wording.
- **Suggestions**: `docs/when/tune-up.md` step 2 says the window tests run under `xvfb-run -a python3.12 -m unittest discover -s test -t . -p "test_ui*.py"`.
