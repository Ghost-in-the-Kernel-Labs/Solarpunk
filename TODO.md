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

### 0.6 Tune-up pass 0

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 1: the fleet, its faults, its numbers

Lanes (P-15): 1.1 to 1.5 are built in parallel by separate workers and landed in this order; 1.6 and 1.7 after them.

### 1.1 The asset registry

Check: `solarpunk/fleet/` with `schema`, `register`, `load_fleet`, `get`, `by_site`, `by_kind`, `children`; `test/solarpunk/test_fleet.py` green, with a refusal test for each of a malformed id (SOL-05), a kind disagreeing with the id, a missing or foreign-site parent, and a duplicate; the ten-asset OAHE fixture in the test file; every mutant killed or explained (`stacks/python/gate.sh`).

### 1.2 The fault ledger

Check: `solarpunk/faults/` with `schema`, `assign`, `close`, `open_faults`, `by_asset`, `by_code`, `in_period`, `repeated`; `test/solarpunk/test_faults.py` green, with a refusal test for each of an unknown code (SOL-04), a naive instant (SOL-06), a second open fault of one code on one asset, a close before open and a double close; instants round-trip as aware UTC; every mutant killed or explained.

### 1.3 Synthetic SCADA

Check: `solarpunk/telemetry/` with `generate`, `schema`, `store`, `in_period`; `python3 -m solarpunk.telemetry.generate --seed 7` writes the one-day golden `test/solarpunk/goldens/telemetry-seed7.txt` byte-identically on two runs (SOL-02); `test/solarpunk/test_telemetry.py` green: every expected instant present (SOL-06), gaps carried as `gap()` samples, irradiance zero at night and 1000 at the peak; every mutant killed or explained.

### 1.4 The KPI engine

Check: `solarpunk/kpi/` with `availability`, `performance_ratio`, `energy_yield`, `mtbf_mttr` as pure functions citing their invariants (`# Invariant: SOL-07` …); `test/solarpunk/test_kpi.py` green, holding the contract's four worked examples as goldens (0.7 and gaps 1; 0.9133; the two-source yield; 3.0 and 21.0) and a ten-row hand-checkable table per KPI; every mutant killed or explained.

### 1.5 The clause register and its check

Check: `docs/CLAUSE-REGISTER.md` with eight to twelve rows in the project's words, no sentence of either standard copied; `test/solarpunk/iso/test_iso9001.py` and `test/solarpunk/iso/test_iso55000.py` with one tagged test per row (`Clause: 9001-9.1.3` first in its docstring); `scripts/checks/clauses.py` fails the fast loop on a row with no tagged test or a tagged test with no row, and `test/test_clauses.py` rejects a planted break of each (C-013); `python3 -I scripts/clauses.py` prints each clause `held`, `failing` or `open`; the routing row for the register added to `docs/paths/process.md`.

### 1.6 The orchestrator and the mirror

Check: `solarpunk/project/` with `open_store`, `assign_fault` (refuses an asset the fleet lacks), `kpis_for`; `test/solarpunk/test_project.py` green over the OAHE fixture end to end; `test/solarpunk/test_mirror.py`, written from `docs/CONTRACT.md` alone by a worker whose brief forbids `solarpunk/kpi/`, agrees with the engine on all four worked examples; every mutant killed or explained.

### 1.7 The thin CLI

Check: `python3 -m solarpunk.cli` with `fleet`, `fault`, `telemetry`, `kpi`, `clauses` subcommands, each one call into project; `test/solarpunk/test_cli.py` green; `solarpunk/cli/` imports project alone (MOD-02, `test/test_modules.py`).

### 1.8 Tune-up pass 1

Check: `docs/when/tune-up.md` followed in full: the full gate twice, the navigation log reviewed and its "Last review" set, the metrics table written, the stamped TypeScript-only tests under `test/test_stacks.py` pruned or their skip explained.
