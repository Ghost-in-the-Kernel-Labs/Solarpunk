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

Last review: 883c4d5 (2026-11-19, Tune-up pass 10)

## Entries

An entry is `### <date> · <task> · <agent>` and four lines: **Task**, **Opened** (files, in order), **Complaints**,
**Suggestions**.

### 2026-11-19 · 11.1 the tracker adapters and the outbox · Claude
- **Task**: the `tickets` module, the outbox in the work-order ledger, the local tracker, the drain, the contract suite.
- **Opened**: `TODO.md`, `docs/modules.json`, `solarpunk/workorders/ledger.py`, `solarpunk/workorders/tickets.py`, `solarpunk/project/run.py`.
- **Complaints**: `docs/modules.json`'s "adding" text says how to propose a module but not where its approval is written; a decision record was used.
- **Suggestions**: the "adding" text could say "the approval is a decision in theGhost.md naming the entry".
