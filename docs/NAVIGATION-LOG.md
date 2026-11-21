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

### 2026-11-21 · coordinator assignment pointer · coordinator
- **Task**: make CLAUDE.md send the coordinator to the agent assignment logic (J-114).
- **Opened**: `docs/when/handoff.md`, `docs/when/coordinate.md`, `docs/HANDOFF.md`, `docs/when/grades.md`, `theGhost.md` (C-020, C-022, C-036), `docs/when/hand-out-a-task.md`, `scripts/checks/grades.py`.
- **Complaints**: "You coordinate other agents rather than build" did not read as an entry condition to a session Ghost started, so the assignment rules were met only when looked for.
- **Suggestions**: none beyond J-114.
