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

Last review: 75e2e42 (2026-11-18, Tune-up pass 2)

## Entries

An entry is `### 2026-11-18 · Tune-up pass 2 (coordinator) · Claude Fable

- **Task**: Phase 2's pass: re-measure, read seven debriefs, fix what converged, write the contract's sentences.
- **Opened**: `docs/when/tune-up.md`, `build/gate-cold.log`, `build/gate-times.txt`, `scripts/metrics.py` (its cold output), `stacks/python/gate.sh`, `test/solarpunk/test_project_run.py` (the 0.5 s tests), `pyproject.toml`, `stacks/python/README.md`, `docs/when/hand-out-a-task.md`, `docs/CONTRACT.md`.
- **Complaints**: two armed metrics had regressed by the end of Phase 2 — the fast loop to 41 s (every socket test waited on `serve_forever`'s default 0.5 s poll at shutdown) and the gate to 29 min (the stamped stack gate deletes mutmut's cache every run, against Core's own ruling of a warm cache per push); the cold gate still refuses at the gate target (12.7 min against 10) since a cache-off run over 3,195 mutants cannot be faster, so the pass cannot end green on its cold run and the rule needs Ghost's word.
- **Suggestions**: Core: the Python stack gate keeps the cache except on the cold run (done here); a decision on the cold run's minutes (exempt from the target, or a target of its own); the `poll_interval` lesson in the stack README (done).
