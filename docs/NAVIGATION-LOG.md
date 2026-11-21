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

Last review: f3a5d95 (2026-11-20, the mid-Phase 12 tune-up commit)

## Entries

An entry is `### <date> · <task> · <who>`, then four bullets: **Task**, **Opened** (files, in order), **Complaints**,
**Suggestions**.

### 2026-11-20 · 12.6 the false-alarm baseline · Claude (strong-grade agent, carried by the coordinator)
- **Task**: 12.6 a false-alarm baseline on public field data.
- **Opened**: `CLAUDE.md`, `theGhost.md` (SP-036), `docs/journal/J-000-099.md` (J-099), `docs/ROADMAP.md`, `solarpunk/leaf/telemetry.py`, `solarpunk/leaf/clock.py`, `solarpunk/leaf/assets.py`, `solarpunk/leaf/codes.py`, `solarpunk/leaf/asset_types.json`, `solarpunk/telemetry/generate.py`, `solarpunk/telemetry/samples.py`, `solarpunk/remote/registry.py`, `solarpunk/remote/run.py`, `solarpunk/remote/results.py`, `solarpunk/fleet/registry.py`, `solarpunk/project/surface.py`, `docs/modules.json`, `solarpunk/cli/main.py`, `solarpunk.cmd`, `docs/paths/product.md`.
- **Complaints**: the brief's data-lake path, carried from J-099, was empty for these systems; the fast loop sits at its 30 s budget; irradiance on an inverter's sample forces a choice of station that neither the contract nor the brief makes.
- **Suggestions**: reachable not counting gaps as records; the thresholds J-100 names.
