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

Last review: b62491e (2026-11-18, Tune-up pass 3)

## Entries

An entry is `### 2026-11-18 · Tune-up pass 3 (coordinator) · Claude Fable

- **Task**: Phase 3's pass: re-measure, read four debriefs, fix what converged, write HANDOFF for the morning.
- **Opened**: `docs/when/tune-up.md`, `build/gate-cold-times.txt`, `/tmp/cold3.out`, `docs/NAVIGATION-LOG.md`, `stacks/python/README.md`, `docs/when/hand-out-a-task.md`, `docs/HANDOFF.md`.
- **Complaints**: the cold gate is 15.5 min now (4,499 mutants) and refuses at the gate target each pass until Ghost rules (J-024); the four UI debriefs converge on one thing the brief should have said — the fast loop's interpreter has no tkinter — and on mutmut's unreliability under xvfb, which only one lane could have found.
- **Suggestions**: the two UI rules in the stack README (done); Core: a tune-up pass whose cold run is over target by mutation count alone should be able to end green.
