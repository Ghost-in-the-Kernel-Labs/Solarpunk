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

Last review: 5cd02bd (2026-11-20, Tune-up commit 9)

## Entries

An entry is `

### 2026-11-20 · 12.2 versions · Claude
- **Task**: 12.2 Versions: a version on each record, raised with every change, a stale write refused.
- **Opened**: `TODO.md`, `theGhost.md` (SP-028), `solarpunk/fleet/registry.py`, `solarpunk/faults/ledger.py`, `solarpunk/remote/suggestions.py`, `solarpunk/workorders/ledger.py`, `solarpunk/workorders/tickets.py`, `solarpunk/project/orchestrator.py`, `docs/CONTRACT.md`, `test/solarpunk/test_accounts.py`.
- **Complaints**: the writes on a record are spread over its module and project with no list of them; finding all nine took a grep for UPDATE.
- **Suggestions**: none.

### 2026-11-20 · 12.3 signing in · Claude
- **Task**: 12.3 Signing in: the dialog, `--as` and getpass, failures kept, the scheduled run unattributed.
- **Opened**: `TODO.md`, `solarpunk/accounts/table.py`, `solarpunk/project/orchestrator.py`, `solarpunk/cli/main.py`, `solarpunk/cli/tickets.py`, `solarpunk/ui/app.py`, `solarpunk/ui/__main__.py`, `docs/CONTRACT.md`.
- **Complaints**: 12.3's check did not say what a store with no accounts does, though 12.5 makes the first; it took a question to Ghost.
- **Suggestions**: an item that depends on a later one names the dependency in its check.
