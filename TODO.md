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

### 4.1 The work-order ledger

Check: `solarpunk/leaf/root_causes.py` holds the closed list of root-cause codes (`RootCause` enum: COMPONENT, FIRMWARE, GRID, WEATHER, SENSOR, COMMS, MAINTENANCE_OVERDUE, DESIGN, UNKNOWN, each with a one-line meaning) and `lookup_root_cause(code)` refuses any other; `solarpunk/workorders/` with `schema()` (the `work_orders` table: wo_id, asset_id, fault_id nullable, kind `corrective` or `preventive`, opened, closed nullable, root_cause nullable, note), `open_corrective(conn, asset_id, fault_id, opened, note)`, `open_preventive(conn, asset_id, opened, note)`, `close(conn, wo_id, root_cause, closed)` refusing a close without a root cause from the list (SOL-04's rule for causes), a close before opening and a double close, `open_orders`, `by_asset`, `repeated_causes(conn, period, at_least)`; project gains `open_work_order_from_fault`, `close_work_order` (which closes the order and, for a corrective order, its fault in the ledger in one call) and `work_orders_for(asset_id)`, and the asset detail shows the asset's open orders; `test/solarpunk/test_workorders.py` green; `test/solarpunk/iso/test_iso9001.py` gains the tagged test that holds `9001-10.2.1` (a work order closes only with a root-cause code from the closed list) and `docs/CLAUSE-REGISTER.md`'s row becomes held; every mutant killed or explained.

### 4.2 Tune-up pass 4

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.
