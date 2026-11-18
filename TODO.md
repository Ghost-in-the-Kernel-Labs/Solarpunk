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

## Phase 4: the work-order ledger

Lanes (P-15): 4.1 alone, then 4.2 the pass.

## Phase 5: one word to run it

Lanes (P-15): 5.1 and 5.2 in order, then 5.3 the pass.

## Phase 6: reports and diagnostics

Lanes (P-15): 6.1 and 6.2 in parallel, landed in that order (done, J-041); 6.3 after 6.1 (done, J-043) and 6.4 after 6.2 (done, J-045); 6.5 the pass.

## Phase 7: faults suggested by tests, assigned by engineers

Lanes (P-15): 7.1, then 7.2 (it needs 7.1's `assigned_by`), then 7.3, then 7.4 the pass. Ghost's direction, SP-015.

### 7.2 Suggestions from the tests

A failing remote test raises a suggestion of a likely fault by its rule table, and a code an asset pushes is a
suggestion from the device; an engineer accepts or dismisses each, recorded with who (SP-015).

Check: each module under `solarpunk/remote/tests/` declares `SUGGESTS` (a mapping from each of its `KINDS` to a catalogue code or None), held by the registry; a `suggestions` table (asset, code, source test or "device", reason, run, state open/accepted/dismissed, by whom, fault id when accepted, dismissal reason); the scheduled run stores one open suggestion per failing test with a code, never two open of the same code on one asset; the receiver stores a pushed code as a suggestion from the device; `project.accept_suggestion(conn, id, engineer, recorded_by=None)` opens the fault through 7.1's `assign_fault`, linked, and `project.dismiss_suggestion(conn, id, engineer, reason)`; an open suggestion keeps the asset yellow and never red, and no KPI reads it; the rule table printed by `solarpunk test list`; the tests of each, and the fast loop green.

### 7.3 Suggestions in the asset window and on the command line

The engineer's view of what the tests suggest, where the asset is, and the same on the command line (SP-015).

Check: the asset window lists the asset's open suggestions (the device's first, then by run, newest first) with code, meaning, source and reason, and Accept and Dismiss, each taking the engineer from the known-engineer dropdown and an optional operator, Dismiss a reason; `solarpunk fault suggestions [--asset ID]`, `fault accept ID --by ENGINEER [--recorded-by OPERATOR]`, `fault dismiss ID --by ENGINEER --reason TEXT`; `test/solarpunk/test_ui_asset.py` and the CLI tests cover each; a screenshot of the demo's asset window read back under xvfb; the fast loop green.

### 7.4 Tune-up pass 7

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 8: the tests' record, at the root and per asset

Lanes (P-15): 8.1 first (the surface every window reads), then 8.2, 8.3 and 8.4 in parallel, then 8.5 the pass. Ghost's direction, SP-016.

### 8.1 The record's surface and the timing

The scheduled run times each test, and project gives the three views the windows read; every result is kept (SP-016).

Check: the results table gains `duration_ms` (a store made before gains the column on opening, its old rows empty); the scheduled run and `solarpunk test run` store each test's duration; `project.tests_overview(conn)`, `project.test_log(conn, name, limit=100)` and `project.asset_log(conn, asset_id, limit=100, search=None)` (search matching the test name, "pass"/"fail" and words in the reason) are tested over a store holding more than 100 runs, newest first, nothing deleted; a result with no duration reads None, never 0; the fast loop green.

### 8.2 Last run in the asset window

Each test in the asset's diagnostics shows when it last ran and how long it took (SP-016).

Check: `solarpunk/ui/asset_window.py`'s diagnostics table has columns for the last-run instant and the duration, "never" for a test never run on the asset, "—" for a duration not recorded; `test/solarpunk/test_ui_asset.py` holds both; a screenshot read back under xvfb; the fast loop green.

### 8.3 The Tests window

The master list from the root of the window: every test, its run time, and its last 100 runs (SP-016).

Check: `solarpunk/ui/tests_window.py` opens from a "Tests" button in the fleet window; it lists `project.tests_overview` (name, kinds, assets, last run, duration, passes, failures) and, for the selected test, `project.test_log` (asset, instant, result, reason, duration), failures red; `test/solarpunk/test_ui_tests.py` builds it under xvfb over the demo store with its pure half headless; a screenshot read back; the fast loop green.

### 8.4 The asset's history

The asset's last 100 results, searchable and graphed (SP-016).

Check: `solarpunk/ui/history.py` opens from a "History" button in the asset window; a table of `project.asset_log` with a search box that narrows it; a canvas timeline, one row per test, one mark per run, green a pass and red a failure, the time axis in UTC, its geometry pure functions tested headless (as `solarpunk/ui/chart.py`'s are); `test/solarpunk/test_ui_history.py` under xvfb over a store with more than 100 runs of an asset; a screenshot read back; the fast loop green.

### 8.5 Tune-up pass 8

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 9: the network's security

Lanes (P-15): 9.1 alone, then the items its decisions call for, then the pass. Moved after Phase 6 by SP-013, after Phase 7 by SP-015 and after Phase 8 by SP-016.

### 9.1 Network security: an engineering pass over the feed and the receiver

The feed and the receiver use plain TCP. The receiver accepts asset identifiers and fault codes, but the implementation
establishes neither an authenticated device identity nor an encrypted transport; it also defaults to localhost. That is
reasonable for the demonstration. A production deployment needs: authenticated asset connections; transport
encryption; authorization of fault submissions; replay protection; network segmentation and deployment controls. The
2026-11-18 advisor's research is the pass's starting point (`docs/ROADMAP.md` 9.1): the industry's addressing (host,
port, protocol, unit id, register map; Modbus TCP and SunSpec at the device), its security references (Modbus/TCP
Security, IEC 62351, IEC 62443, NERC CIP-003), and a sixth threat, spoofed telemetry from whatever answers at a feed's
host and port.

Check: `docs/NETWORK-SECURITY.md` holds the pass: what the feed (`solarpunk/feed/`) and the receiver (`solarpunk/receiver/`) do on the wire today, a threat model for each, and for each of the five needs (authenticated asset connections, transport encryption, authorization of fault submissions, replay protection, network segmentation and deployment controls) a proposed decision in `docs/decisions.md` with the options weighed, what the standard library alone can carry and what would need a dependency (Ghost's approval, C-034); the items that build each decision Ghost puts in force are added to this phase before its pass (the pass renumbered to the phase's end). No code changes in this item: the design is Ghost's to rule on first.

### 9.2 Tune-up pass 9

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.
