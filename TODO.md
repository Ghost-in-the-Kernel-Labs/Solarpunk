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

## Phase 2: the feed, the remote tests, the clock

Lanes (P-15): 2.1 first (the list every other lane reads), then 2.2 to 2.6 in parallel, landed in this order; 2.7 after them (it joins them in project); 2.8 the pass.

## Phase 3: the native front end

Lanes (P-15): 3.1 to 3.3 in parallel after 2.7, landed in this order; 3.4 after them.

### 3.2 The asset window

Check: `solarpunk/ui/asset_window.py` (`AssetWindow(parent, conn, asset_id)`: the asset's fields; its open faults with code, meaning and opened instant; the remote tests of the last run, the failing one first with its reason; a form to assign a catalogue code (a dropdown of `CATALOGUE` for the asset's kind, an Assign button); the engineer: a dropdown of the fleet's known engineer emails plus a text field, and two buttons reading exactly `Save` and `Cancel` — Save calls `fleet.assign_engineer` and closes, Cancel closes and changes nothing); `test/solarpunk/test_ui_asset.py` green under a display, skipping without one; every mutant killed or explained.

### 3.3 The add-asset window

Check: `solarpunk/ui/add_asset.py` (`AddAssetWindow(parent, conn)`: id, name, site, parent (a dropdown of the site's assets), a type dropdown read from `solarpunk.leaf.asset_types.kinds()`, rated kW, location, engineer email, IP address and port; a Ping button that calls `feed.ping` and shows the first record or the `FeedError`; `Save` registers through `project` and closes, `Cancel` closes); the refusals of the fleet shown in the window, never swallowed; `test/solarpunk/test_ui_add.py` green under a display, skipping without one; every mutant killed or explained.

### 3.4 The demo

Check: `python3 -m solarpunk.ui --demo` builds a file store `demo.db` beside the current directory (removed and rebuilt each run): the OAHE fixture, one day of seed-7 telemetry, two closed faults and one open INV-001 outage, a simulator started on an ephemeral port for OAHE-INV-001 with the asset's host and port set to it, the remote suite run once (so the window opens with green, yellow and red rows and a last-run instant), then the fleet window; `DEMO.md` at the root with the Windows commands (`py -3.12 -m venv .venv`, the lockfile install, `py -m solarpunk.ui --demo`), what to click in what order, the five-minute talk track, and the clause report command; `test/solarpunk/test_demo.py` builds the demo store headless and asserts the three colours are present; `README.md`'s skeleton filled (what Solarpunk is, the commands, the roadmap's phases in five lines).

### 3.5 Tune-up pass 3

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 4: the work-order ledger

Planned when Phase 3 closes (`docs/ROADMAP.md` Phase 4).

### 4.1 Tune-up pass 4

Check: `docs/when/tune-up.md` followed in full; the phase planned in `docs/ROADMAP.md` and its items added before this pass, renumbered to the phase's end.
