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

Last review: 12f9a6c (2026-11-23, Tune-up commit 8)

## Entries

An entry is `### <date> · <task> · <who>`, then four bullets: **Task**, **Opened** (files, in order), **Complaints**,
**Suggestions**.

### 2026-11-23 · 13.19 cheaper password hashing in the tests · mid-grade worker
- **Task**: a low scrypt cost in the tests alone, the product's held by a test (J-150).
- **Opened**: `CLAUDE.md`, `docs/paths/process.md`, `docs/AGENT.md`, `solarpunk/accounts/passwords.py`, `test/solarpunk/test_accounts.py`, `scripts/fast.sh`.
- **Complaints**: none.
- **Suggestions**: none.

### 2026-11-23 · 13.18 output under the floor, its own fault · mid-grade worker
- **Task**: INV-005 for a performance ratio under the floor; SIT-004 kept for a lost link (J-151).
- **Opened**: `CLAUDE.md`, `docs/paths/product.md`, `docs/CONTRACT.md`, `solarpunk/leaf/codes.py`, `solarpunk/project/suggest.py`, `solarpunk/remote/tests/performance_above_floor.py`, `solarpunk/remote/tests/reachable.py`.
- **Complaints**: none.
- **Suggestions**: none.

### 2026-11-23 · 13.20 the ISO walk scripted · mid-grade worker
- **Task**: DEMO.md's walk of 55000-9.1 from requirement to corrective action, verified on a live `--demo`; the register's sentence (J-152).
- **Opened**: `CLAUDE.md`, `docs/paths/product.md`, `DEMO.md`, `docs/CLAUSE-REGISTER.md`, `scripts/checks/clauses.py`, `test/test_clauses.py`, `solarpunk/ui/__main__.py`, then the windows' code to confirm their words.
- **Complaints**: the asset window's ticket panel acts on the nearest-target ticket, not the one just opened; `pkill` was refused for a stray demo process.
- **Suggestions**: a ticket chooser in the panel.

### 2026-11-23 · 13.22 the walk clicked end to end · mid-grade worker
- **Task**: a ticket chooser in the asset window's panel; the walk's corrective acts all clicked (J-153).
- **Opened**: `CLAUDE.md`, `docs/paths/product.md`, `solarpunk/ui/ticket_panel.py`, `solarpunk/ui/open_ticket.py`, `solarpunk/ui/asset_window.py`, `solarpunk/ui/ticket_text.py`, `solarpunk/cli/main.py`, `DEMO.md`.
- **Complaints**: the demo's clock in whole seconds puts quick acts at one instant, refusing a close at its opening instant.
- **Suggestions**: none.

### 2026-11-23 · 13.20 a ping that answers records its pass · mid-grade worker
- **Task**: `ping_all` stores a `reachable` pass for a feed that answers (J-155).
- **Opened**: `CLAUDE.md`, `docs/paths/product.md`, `docs/CONTRACT.md`, `solarpunk/project/run.py`, `solarpunk/remote/results.py`, `solarpunk/remote/tests/reachable.py`, `solarpunk/project/revival.py`.
- **Complaints**: `save.sh` refused the push: the branch name was taken by an older branch of the same item number.
- **Suggestions**: none.

### 2026-11-23 · 13.21 the proof follows the action · mid-grade worker
- **Task**: a ticket from a failed result closes after a later pass; the revival after the last act; DEMO.md in that order (J-156).
- **Opened**: `CLAUDE.md`, `docs/paths/product.md`, `docs/CONTRACT.md`, `solarpunk/project/causes.py`, `solarpunk/project/tickets.py`, `solarpunk/project/attribution.py`, `solarpunk/project/trail.py`, `solarpunk/remote/results.py`, `solarpunk/ui/demo.py`, `DEMO.md`.
- **Complaints**: DEMO.md named result 1, a pass since 13.20; one `Tcl_AsyncDelete` abort of the window tests, not reproduced.
- **Suggestions**: none.

### 2026-11-25 · 13.25 one name, one check · mid-grade worker
- **Task**: the stored-records script renamed `records_stored`; `reachable` the ping alone (J-158).
- **Opened**: `CLAUDE.md`, `docs/paths/product.md`, `solarpunk/remote/tests/reachable.py`, `solarpunk/remote/registry.py`, `solarpunk/project/run.py`, `solarpunk/project/suggest.py`, `solarpunk/project/result_tickets.py`, `solarpunk/project/reactions.py`, the documents naming the test.
- **Complaints**: `scripts/checks/asset_types.py` fails run directly (`No module named 'scripts'`); its test passes. The window tests abort now and then with `Tcl_AsyncDelete`.
- **Suggestions**: the scaffold refuses the ping's name.
