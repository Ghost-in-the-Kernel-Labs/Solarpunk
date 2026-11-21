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

Last review: 1a02a15 (2026-11-21, Tune-up pass 12)

## Entries

An entry is `### <date> · <task> · <who>`, then four bullets: **Task**, **Opened** (files, in order), **Complaints**,
**Suggestions**.

### 2026-11-21 · split `asset_window.py` (J-105) · Claude, coordinator
- **Task**: move the asset window's words and pure functions to their own module, no result changed.
- **Opened**: `docs/HANDOFF.md`, `TODO.md`, `solarpunk/ui/asset_window.py`, `solarpunk/ui/ticket_text.py`, `docs/paths/product.md`, `docs/modules.json`, `solarpunk/ui/demo.py`, `solarpunk/project/orchestrator.py`, `docs/when/handoff.md`, `docs/JOURNAL.md`.
- **Complaints**: the product row asks to render the changed window and read the screenshot, but names no command for it; I wrote a throwaway script over `demo.build_demo_store`, and first reached for `project.open_store`, which refuses a store that exists (`open_or_create` is the one).
- **Suggestions**: a small `scripts/` or test helper that renders a named window over the demo store to a PNG, so a refactor can diff its screenshots before and after.
