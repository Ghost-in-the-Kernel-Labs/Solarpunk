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

Lanes (P-15): 6.1 and 6.2 in parallel, landed in that order (done, J-041); 6.3 after 6.1 and 6.4 after 6.2, in parallel; 6.5 the pass.

### 6.3 The reports window

A window that shows 6.1's power-output report: a site and a period chosen, the table, the site's power curve on a
tkinter canvas, and Save as CSV; opened from the fleet window (SP-013).

Check: `solarpunk/ui/reports.py` opens from a button in the fleet window; it takes a site and a day (or a start and end),
shows one row per `project.power_report` row (the site's first: energy, peak, specific yield, capacity factor, records,
gaps), draws the site's summed power over the period as a line on a canvas with its axes labelled in kW and UTC hours,
and writes the same CSV as `solarpunk report --csv` through a save dialog; a refusal (an unknown site, a reversed period)
is shown, never swallowed; `test/solarpunk/test_ui_reports.py` builds it under xvfb (skipped without one) over the demo
store and asserts the table's rows equal the report's; the curve's points are a function tested headless; the fast loop
green.

### 6.4 The diagnostics in the asset window

The asset window shows the latest result of every remote test that runs on the asset's kind, failing first, each with
its reason, so the diagnostics of 6.2 are read where the asset is (SP-013).

Check: `solarpunk/ui/asset_window.py` lists, for the asset's kind, every remote test the registry holds with its latest
result (pass, fail or not yet run) and reason, failing first, from one project call the tests make headless;
`test/solarpunk/test_ui_asset.py` asserts the demo's OAHE-INV-001 shows all seven inverter tests passing and OAHE-SEN-001
its failing `reachable` first; the fast loop green.

### 6.5 Tune-up pass 6

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 7: the network's security

Lanes (P-15): 7.1 alone, then the items its decisions call for, then the pass. Moved after Phase 6 by SP-013.

### 7.1 Network security: an engineering pass over the feed and the receiver

The feed and the receiver use plain TCP. The receiver accepts asset identifiers and fault codes, but the implementation
establishes neither an authenticated device identity nor an encrypted transport; it also defaults to localhost. That is
reasonable for the demonstration. A production deployment needs: authenticated asset connections; transport
encryption; authorization of fault submissions; replay protection; network segmentation and deployment controls. The
2026-11-18 advisor's research is the pass's starting point (`docs/ROADMAP.md` 7.1): the industry's addressing (host,
port, protocol, unit id, register map; Modbus TCP and SunSpec at the device), its security references (Modbus/TCP
Security, IEC 62351, IEC 62443, NERC CIP-003), and a sixth threat, spoofed telemetry from whatever answers at a feed's
host and port.

Check: `docs/NETWORK-SECURITY.md` holds the pass: what the feed (`solarpunk/feed/`) and the receiver (`solarpunk/receiver/`) do on the wire today, a threat model for each, and for each of the five needs (authenticated asset connections, transport encryption, authorization of fault submissions, replay protection, network segmentation and deployment controls) a proposed decision in `docs/decisions.md` with the options weighed, what the standard library alone can carry and what would need a dependency (Ghost's approval, C-034); the items that build each decision Ghost puts in force are added to this phase before its pass (the pass renumbered to the phase's end). No code changes in this item: the design is Ghost's to rule on first.

### 7.2 Tune-up pass 7

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.
