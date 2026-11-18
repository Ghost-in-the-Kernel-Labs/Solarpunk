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

Last review: 9bae81d (2026-11-18, Tune-up pass 5)

## Entries

An entry is `### <date> · <task> · <agent>` and four lines: **Task**, **Opened** (files, in order), **Complaints**,
**Suggestions**.

### 2026-11-18 · Tune-up pass 5 (the session that built 5.1 and 5.2) · Claude Fable

- **Task**: Phase 5's pass: two gate runs, the one debrief, the records, with Ghost in the chat.
- **Opened**: `docs/when/tune-up.md`, `stacks/python/gate.sh`, `scripts/gate.sh` (its header), `build/gate-cold-times.txt`, `docs/NAVIGATION-LOG.md`, `docs/HANDOFF.md`.
- **Complaints**: `docs/when/tune-up.md` asks for a cold and a warm gate run, and since SP-012 no step keeps a cache, so the two measure the same thing; a pass run by the session that built the phase is its own reviewer, which the file's "the reviewer, not you" does not foresee. One debrief again, so nothing converges.
- **Suggestions**: Ghost's word on whether a pass still needs two runs; a product workpath (`docs/paths/product.md`, a row per module), the builder's one complaint, open until a second agent meets it.
