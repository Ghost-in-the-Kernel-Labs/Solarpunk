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

Last review: f8c3ea1 (2026-11-17, Tune-up pass 0)

## Entries

An entry is `### <date> · <task> · <model>` and these lines:

- **Task**: what the agent was asked.
- **Opened**: the files it opened, in order.
- **Complaints**: what slowed or misled it.
- **Suggestions**: what it would change.

### 2026-11-17 · Phase 0 (0.1 to 0.6) as coordinator · Claude Fable

- **Task**: stamp Solarpunk, found it (0.1 to 0.5) and run Tune-up pass 0.
- **Opened**: `README.md` (Core's recipe), `CLAUDE.md`, `TODO.md`, `stacks/python/gate.sh`, `stacks/python/README.md`, `scripts/gate.sh`, `docs/HANDOFF.md`, `pyproject.toml`, `scripts/checks/imports.py`, `docs/GHOST-IN-THE-KERNEL.md`, `docs/FINDINGS.md`, `docs/GLOSSARY.md`, `docs/JOURNAL.md`, `theGhost.md`, `docs/DONE.md`, `docs/CONTRACT.md`, `scripts/checks/contract.py`, `docs/modules.json`, `docs/ROADMAP.md`, `docs/when/coordinate.md`, `docs/when/hand-out-a-task.md`, `docs/when/grades.md`, `scripts/commit.sh`, `scripts/save.sh`, `docs/when/tune-up.md`.
- **Complaints**: the Python starter's gate could not pass on a fresh stamp (F-003, F-004: ruff and the imports check read the fixtures; mutmut's copy cannot run the template's tests and is red with zero mutants), so 0.2's Check was unmeetable as written until Ghost pulled the leaf forward; `commit.sh` lands the whole recorded tree, so two items finished together needed a stash; the metrics table goes stale on any document edit after `--write`; `test/test_stacks.py` carries 19 TypeScript-only tests into a Python stamp; `test/test_contract.py` reads `docs/CONTRACT.md` by name while the template says to rename it; `scripts/score.py` placed every Phase 1 lane at mid though each builds a module from a contract.
- **Suggestions**: Core: exclude `test/fixtures` in the Python starter's ruff and imports check; set mutmut to the product and its tests and let a stamp's 0.2 Check say "once product code exists" or pull the leaf into 0.2 by default; drop another stack's tests from a stamp; either rename the contract in the test too or drop the "rename" sentence; a landing note in coordinate.md (done here, step 4).
