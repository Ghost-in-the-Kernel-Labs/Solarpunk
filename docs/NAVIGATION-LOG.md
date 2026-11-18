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

### 2026-11-18 · 6.1 and 6.2, the power-output report and the inverter diagnostics · Claude

- **Task**: SP-013's reordering, SOL-13 and its report, four remote tests, the records.
- **Opened**: `docs/ROADMAP.md`, `TODO.md`, `docs/GOAL.md`, `docs/paths/process.md`, `scripts/checks/todo.py`, `solarpunk/kpi/performance.py`, `docs/CONTRACT.md` (SOL-08), `solarpunk/project/orchestrator.py`, `solarpunk/cli/main.py`, `solarpunk/remote/tests/power_under_rated.py`, `solarpunk/remote/registry.py`, `solarpunk/leaf/asset_types.json`.
- **Complaints**: no routing row for product work again, a second voice for J-039's complaint (and an architecture advisor's); a new CLI command touches the help list, a hard-coded count in a test and two lines of `solarpunk.cmd`, found only by running the fast loop; the maintenance list's check reads a `Tests:` line as one line, which wrapping at 120 columns breaks with a message that does not say why.
- **Suggestions**: `docs/paths/product.md`, a row per module; the help count derived from the parser and the launcher's words generated or held by one list; the asset-types check to say "one line" when a Tests line wraps.

### 2026-11-18 · SP-014, the landing that pushes before main moves · Claude

- **Task**: `scripts/commit.sh --ship`, its tests, the decision and the documents that name the landing.
- **Opened**: `scripts/commit.sh`, `scripts/ship.sh`, `test/test_ship.py`, `test/test_gates.py`, `test/support_git.py`, `docs/paths/process.md`.
- **Complaints**: the raw-push test's allow-list lives in a test, so a new push site is found by running the loop, not by reading the gates row; the largest-file ratchet fired on a test file, where the move to a sibling file was the right answer but nothing says which file a gate test belongs in.
- **Suggestions**: name the push sites in process.md's gates row (it is where a builder starts); `test_ship.py` for anything that pushes, `test_gates.py` for the rest, said in that row.

### 2026-11-18 · 6.3, the reports window · Claude

- **Task**: the reports window over `project.power_report`, its curve, the CSV in project, the Reports button.
- **Opened**: `solarpunk/ui/app.py`, `solarpunk/ui/__main__.py`, `solarpunk/ui/demo.py`, `test/solarpunk/test_ui.py`, `solarpunk/project/surface.py`, `stacks/python/README.md` (the fast loop row, for tkinter), `docs/journal/J-000-099.md` (J-025).
- **Complaints**: that the widget tests need tkinter and xvfb and that the fast loop's interpreter has neither is written only in the stack README's long fast-loop cell and a journal entry; a fresh container's venv had no tkinter either, which nothing says. No product workpath again (third voice: J-039, J-041).
- **Suggestions**: a UI row in a product workpath naming `xvfb-run -a .venv/bin/python -m pytest test/solarpunk/test_ui*.py` and `apt-get install python3-tk` when the venv lacks it; the pure-half split (`glyph.py`, `chart.py`) written as the UI rule.

### 2026-11-18 · the README's roadmap held to the chain · Claude

- **Task**: the stale README fixed, and a test so it cannot fall behind TODO.md and DONE.md again.
- **Opened**: `README.md`, `TODO.md`, `docs/DONE.md`, `test/solarpunk/test_mirror.py` (to check the mirror's claim).
- **Complaints**: the README is the one document a visitor reads first and the only one in the meta-architecture table (`docs/ROADMAP.md` §5) with no test; the handoff's list of what a landing updates does not name it.
- **Suggestions**: a README row in §5's table naming `test/test_readme.py`, at the next tune-up.

### 2026-11-18 · 6.4, the diagnostics in the asset window · Claude

- **Task**: every remote test of an asset's kind in the asset window, with its latest result, failing first.
- **Opened**: `solarpunk/project/surface.py`, `solarpunk/ui/asset_window.py`, `solarpunk/remote/results.py`, `solarpunk/remote/registry.py`, `test/solarpunk/test_ui_asset.py`.
- **Complaints**: none new for finding my way: the surface and window split made this two files and a test; the UI's xvfb recipe was already in hand from 6.3. Reading a window is best done by a screenshot, and nothing says so: both of this phase's UI bugs were found by looking.
- **Suggestions**: a line in the UI rule: render the changed window under xvfb and read the screenshot before landing.

### 2026-11-18 · SP-015 and Phase 7 planned · Claude

- **Task**: Ghost's fault-assignment direction as a decision, three questions put, the phase written.
- **Opened**: `solarpunk/leaf/faults.py`, `solarpunk/leaf/codes.py` (the catalogue), `solarpunk/receiver/server.py`, `theGhost.md` (SP-008, the supersession template), `docs/ROADMAP.md`, `TODO.md`.
- **Complaints**: renumbering a phase touches four files by hand (ROADMAP, TODO, README, HANDOFF) and nothing points at all four; the decision template's partial-supersession pattern was found by grep, not by the header.
- **Suggestions**: a line in the process workpath's "The plan" row naming the four files a renumbering touches.

### 2026-11-18 · SP-016 and Phase 8 planned · Claude

- **Task**: Ghost's test-record direction as a decision, three questions put, the phase written, security renumbered again.
- **Opened**: `solarpunk/remote/results.py` (what is stored), `docs/ROADMAP.md`, `TODO.md`.
- **Complaints**: the second renumbering of the security phase in one day: each new phase put ahead of it touches four files and a decision's text that named the old number.
- **Suggestions**: an unnumbered "later" place for a phase that keeps being pushed back, or the waiting phase if it waits on nothing but order.
