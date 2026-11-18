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
