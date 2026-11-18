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

Last review: ef77cfc (2026-11-18, Tune-up pass 1)

## Entries

An entry is `### 2026-11-18 · Tune-up pass 1 (coordinator) · Claude Fable

- **Task**: Phase 1's pass: re-measure, read eight debriefs, fix what converged.
- **Opened**: `docs/when/tune-up.md`, `build/gate-times.txt`, `docs/NAVIGATION-LOG.md`, `stacks/python/README.md`, `docs/paths/process.md`, `docs/when/long-run.md`, `docs/when/hand-out-a-task.md`, `scripts/commit.sh` (the cadence rule).
- **Complaints**: the Python stack's gate grew from 22 s to 125 s as the product grew (1,655 mutants), 2.45 min against a 10 min target — fine now, a trend to watch; the tune-up's may-change list keeps the contract's clarifying sentences (J-010, J-012, J-014) out of this pass, so they wait for 2.7, which is right but leaves the code as the only record for a phase.
- **Suggestions**: a mutmut cache kept warm between passes if the gate nears its target; a Core question whether a tune-up may add a sentence that states what the code already does under an invariant whose numbers do not move.
