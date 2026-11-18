# TODO: the open items, in order

The roadmap as a chain: items are done in this order, never out of it, and an item that cannot be
done as written stops the chain and goes to Ghost (C-016). Each item's plan is its step in
`docs/ROADMAP.md` §6, by the same number; its check is copied here. A done item moves to
`docs/DONE.md` with its number kept. `test/test_todo.py` holds this file: headings in numeric order
under their phase, the first open item has a check, every phase ends with a tune-up pass (a reopened phase
of at most three new items with a tune-up commit, `docs/when/tune-up.md`), and
nothing is both here and done or done twice. An item that waits on something outside the repository (Ghost's choice
or approval, counsel, another project) carries a `Waits on:` line naming it in words, or one of the two kinds with a
shape for what a session lacks, `Waits on: environment (<host or tool>)` or `Waits on: reference (<what>)`
(`scripts/checks/todo.py`), and moves to the last phase, headed `## Phase W: waiting on Ghost`, keeping its number and adding a `Moved: from Phase N` line; a phase
whose every item waits takes its tune-up pass with it (the pass's `Waits on:` names those items), and the waiting
phase needs no pass of its own. When what it waits on arrives, Ghost moves the item back into the chain. An open
question a later item depends on is copied into that item's text, so the item reads whole where it stands.

## Phase 0: founding

## Phase 1: the fleet, its faults, its numbers

Lanes (P-15): 1.1 to 1.5 are built in parallel by separate workers and landed in this order; 1.6 and 1.8 in parallel after them, then 1.7.

### 1.7 The thin CLI

Check: `python3 -m solarpunk.cli` with `fleet`, `fault`, `telemetry`, `kpi`, `clauses` subcommands, each one call into project; `test/solarpunk/test_cli.py` green; `solarpunk/cli/` imports project alone (MOD-02, `test/test_modules.py`).

### 1.8 The leaf's own tests

Check: `test/solarpunk/test_leaf.py` holds the leaf's refusals and numbers (clock: `utc`, `on_grid`, `Period`, `at`; telemetry: `Sample`, `gap`; assets: `Asset`'s host/port pairing, port bound and email shape, `parse_asset_id`, `site_id`; faults: `Fault`'s refusals, `covers`, `duration`; store: `connect`, `apply`), so `rm -rf mutants && .venv/bin/mutmut run && .venv/bin/mutmut results | python -I scripts/survivors.py` prints `survivors: every one explained` on the whole tree.

### 1.9 Tune-up pass 1

Check: `docs/when/tune-up.md` followed in full: the full gate twice, the navigation log reviewed and its "Last review" set, the metrics table written, the stamped TypeScript-only tests under `test/test_stacks.py` pruned or their skip explained.
