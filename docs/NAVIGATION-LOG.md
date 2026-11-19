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

Last review: 09e5dc4 (2026-11-19, Tune-up pass 9)

## Entries

An entry is `### <date> · <task> · <agent>` and four lines: **Task**, **Opened** (files, in order), **Complaints**,
**Suggestions**.

### 2026-11-19 · 10.1 what a run and a count are · Claude
- **Task**: SOL-15, the Runs window's readings, with worked examples over the demo store.
- **Opened**: `TODO.md`, `docs/CONTRACT.md`, `test/test_contract.py`, `solarpunk/leaf/clock.py`.
- **Complaints**: no row says how to see the demo store's rows; it was built and read with SQL from a scratch folder.
- **Suggestions**: none yet; one agent's.
