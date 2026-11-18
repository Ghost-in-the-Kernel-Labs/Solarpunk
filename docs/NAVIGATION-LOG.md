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

Last review: 9d4de1d (2026-11-18, Tune-up pass 4)

## Entries

An entry is `### 2026-11-18 · Tune-up pass 4 (coordinator) · Claude Fable

- **Task**: Phase 4's pass after its one lane; the last of the night.
- **Opened**: `docs/when/tune-up.md`, `build/gate-cold-times.txt`, `docs/NAVIGATION-LOG.md`, `docs/when/hand-out-a-task.md`, `docs/HANDOFF.md`.
- **Complaints**: the cold gate (14.2 min) refuses at its target each pass (J-024, still Ghost's question); one lane's debrief, so nothing converges — its two valid points are written where the next brief is read.
- **Suggestions**: a SOL-13 for root causes (an invariant: Ghost's); the brief rules name the armed metrics.

### 2026-11-18 · 5.1 the one-word command and the remote-test commands · Claude Fable

- **Task**: Ghost's requests in chat: `solarpunk` as one word on Windows, commands to run and add remote tests, a network-security item for the list.
- **Opened**: `README.md`, `DEMO.md`, `docs/modules.json`, `docs/paths/process.md`, `TODO.md`, `solarpunk/cli/main.py`, `solarpunk/ui/__main__.py`, `solarpunk/remote/registry.py`, `solarpunk/project/run.py`, `scripts/checks/todo.py`, `docs/when/handoff.md`.
- **Complaints**: CLAUDE.md's table has no row for product work (the CLI, a remote test, the UI): the product's modules are found only through `docs/modules.json`. Planning a phase (TODO, ROADMAP, DONE together) is learned from the last planning commit's diff, not from a row. The log's header line "An entry is" runs into the first entry's heading.
- **Suggestions**: a `docs/paths/product.md` workpath with a row per module; a line in the plan row naming the three files a new phase touches.
