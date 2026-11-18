# Done: finished items of TODO.md, numbers kept

An item moves here from `TODO.md` when its check passes, keeping its number because other documents
cite it. Each line: the item, the date, the journal entries, and its check with a tick.

## Phase 0: founding

### 0.1 This project's ghost, named

Done 2026-11-17 (J-002; commit 7356c5f). Check: `docs/GHOST-IN-THE-KERNEL.md`'s "This project's ghost" section replaced by Solarpunk's; the STAMP comment gone; committed by `scripts/commit.sh --docs-only` with every staged path under `docs/` (the gate refuses at the stack until 0.2), so the item's move from `TODO.md` to `docs/DONE.md` rides in 0.2's commit. ✓

### 0.2 The stack wired

Done 2026-11-17 (J-002, SP-002). Check: `stacks/python/gate.sh` runs green under its image, mutation included, so `scripts/gate.sh` passes and records the tree; `stacks/python/PRESENT` present; its STAMP markers gone; each pin of the founding lockfile and image has its `unreviewed baseline` row in `docs/REVIEWED-VERSIONS.md` (`python3 -I scripts/checks/dependency_review.py --baseline J-nnn` prints them; `docs/DEPENDENCY-REVIEW.md`, "The record"); the first commit through the gate lands, carrying 0.1's move to `docs/DONE.md`. ✓ By SP-002 the leaf's first module, the fault-code catalogue, landed with it (19 of 19 mutants killed), since mutation with nothing to mutate is red.

### 0.3 The roadmap and TODO filled

Done 2026-11-17 (J-003). Check: `docs/ROADMAP.md` §1 to §6 written for Solarpunk (its STAMP line gone, Phase 1 planned in §6) and `TODO.md` holds Phase 1's items in order, each with its Check line, ending with its tune-up pass. ✓

### 0.4 The contract and the leaf module

Done 2026-11-17 (J-004). Check: `docs/CONTRACT.md` renamed and its first invariants written; `docs/modules.json`'s package and modules set; `test/test_contract.py` and `test/test_modules.py` green on the real folders. ✓ The file keeps its name (`test/test_contract.py` reads it by name) and is titled the KPI contract, prefix SOL-.

### 0.5 The founding decisions

Done 2026-11-17 (J-005). Check: `theGhost.md` holds Ghost's founding decisions for Solarpunk, a decision for each core decision it refuses among them, each with Ghost as its Source. Agents cannot author Ghost's decisions: an agent drafts the questions for Ghost in `docs/HANDOFF.md`, and a builder that reports "waiting on Ghost" has done its job. ✓ SP-002 to SP-005 in force by Ghost's word in chat; SP-006 to SP-009 proposed from Ghost's directions, waiting on his word (`docs/HANDOFF.md`); no core decision refused.

### 0.6 Tune-up pass 0

Done 2026-11-17 (J-006). Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set. ✓ Cold gate 0.72 min, warm gate 0.70 min, fast loop 18.7 s; Core unchanged since the stamp (same commit); one fix from the notes (coordinate.md, landing one item at a time).

## Phase 1: the fleet, its faults, its numbers

### 1.1 The asset registry

Done 2026-11-17 (J-007). Check: `solarpunk/fleet/` with `schema`, `register`, `load_fleet`, `get`, `by_site`, `by_kind`, `children`; `test/solarpunk/test_fleet.py` green, with a refusal test for each of a malformed id (SOL-05), a kind disagreeing with the id, a missing or foreign-site parent, and a duplicate; the OAHE fixture (the site and ten assets) in the test file; every mutant killed or explained (`stacks/python/gate.sh`). ✓ 35 tests; 136 of 136 fleet mutants killed; two leaf PRAGMA-case survivors explained in `docs/MUTATION.md`.

### 1.2 The fault ledger

Done 2026-11-17 (J-008). Check: `solarpunk/faults/` with `schema`, `assign`, `close`, `open_faults`, `by_asset`, `by_code`, `in_period`, `repeated`; `test/solarpunk/test_faults.py` green, with a refusal test for each of an unknown code (SOL-04), a naive instant (SOL-06), a second open fault of one code on one asset, a close before open and a double close; instants round-trip as aware UTC; every mutant killed or explained. ✓ 20 tests; every ledger mutant killed or explained (18 SQL letter-case survivors in `docs/MUTATION.md`).

### 1.3 Synthetic SCADA

Done 2026-11-17 (J-009). Check: `solarpunk/telemetry/` with `generate`, `schema`, `store`, `in_period`; `python3 -m solarpunk.telemetry.generate --seed 7` writes the one-day golden `test/solarpunk/goldens/telemetry-seed7.txt` byte-identically on two runs (SOL-02); `test/solarpunk/test_telemetry.py` green: every expected instant present (SOL-06), gaps carried as `gap()` samples, irradiance zero at night and 1000 at the peak; every mutant killed or explained. ✓ 34 tests; the seed-7 golden identical on two runs (288 lines, 9 gaps, 1000.0 at 13:00); nine telemetry survivors explained (SQL case; a `<` to `<=` on a draw that can never equal 0.02).

### 1.4 The KPI engine

Done 2026-11-17 (J-010). Check: `solarpunk/kpi/` with `availability`, `performance_ratio`, `energy_yield`, `mtbf_mttr` as pure functions citing their invariants (`# Invariant: SOL-07` …); `test/solarpunk/test_kpi.py` green, holding the contract's four worked examples as goldens (0.7 and gaps 1; 0.9133; the two-source yield; 3.0 and 21.0) and a ten-row hand-checkable table per KPI; every mutant killed or explained. ✓ 32 tests; the four goldens exact (Availability 0.7/12/2/3/1; PerformanceRatio 0.9133/11.4167/12.5/0; EnergyYield 11.2 meter and 11.4167 inverters; Reliability 21.0/3.0/2/0); every kpi mutant killed.

### 1.5 The clause register and its check

Done 2026-11-17 (J-011). Check: `docs/CLAUSE-REGISTER.md` with eight to twelve rows in the project's words, no sentence of either standard copied; `test/solarpunk/iso/test_iso9001.py` and `test/solarpunk/iso/test_iso55000.py` with one tagged test per row (`Clause: 9001-9.1.3` first in its docstring); `scripts/checks/clauses.py` fails the fast loop on a row with no tagged test or a tagged test with no row, and `test/test_clauses.py` rejects a planted break of each (C-013); `python3 -I scripts/clauses.py` prints each clause `held`, `failing` or `open`; the routing row for the register added to `docs/paths/process.md`. ✓ 12 rows: 9001 six held and two open, 55000 four held; the check refuses six shapes of mismatch and its two planted breaks are rejected; `python3 -I scripts/clauses.py` prints held/failing/open per clause and a count per standard.
