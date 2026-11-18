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

Last review: a595275 (2026-11-18, Tune-up pass 6)

## Entries

An entry is `### <date> · <task> · <agent>` and four lines: **Task**, **Opened** (files, in order), **Complaints**,
**Suggestions**.

### 2026-11-18 · 7.1, who assigned a fault · Claude

- **Task**: SP-015's first step: an engineer on every fault, an operator when called in, cover shown.
- **Opened**: `docs/paths/product.md` (the fleet-and-faults row), `solarpunk/leaf/faults.py`, `solarpunk/faults/ledger.py`, `solarpunk/project/orchestrator.py`, `solarpunk/receiver/server.py`, `solarpunk/cli/main.py`, `solarpunk/ui/asset_window.py`, `solarpunk/ui/demo.py`.
- **Complaints**: the product workpath's new row sent me to the right four files first; a rule added to `project.assign_fault` reached forty-five callers, and nothing lists the tests that build their own fleets (each needed an engineer the fleet holds); a failing test that leaves a server thread running hangs the fast loop after its summary, with no timeout to say so.
- **Suggestions**: a timeout on `scripts/fast.sh`'s run, so a hang is a red line, not a stall.
