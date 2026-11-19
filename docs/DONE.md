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

### 1.6 The orchestrator and the mirror

Done 2026-11-18 (J-012). Check: `solarpunk/project/` with `open_store`, `assign_fault` (refuses an asset the fleet lacks), `kpis_for`; `test/solarpunk/test_project.py` green over the OAHE fixture end to end; `test/solarpunk/test_mirror.py`, written from `docs/CONTRACT.md` alone by a worker whose brief forbids `solarpunk/kpi/`, agrees with the engine on all four worked examples; every mutant killed or explained. ✓ 29 tests (19 end to end, 10 mirror); the mirror, written from the contract alone, agreed with the engine on all four worked examples and six variations; 185 of 185 project mutants killed.

### 1.8 The leaf's own tests

Done 2026-11-18 (J-013). Check: `test/solarpunk/test_leaf.py` holds the leaf's refusals and numbers (clock: `utc`, `on_grid`, `Period`, `at`; telemetry: `Sample`, `gap`; assets: `Asset`'s host/port pairing, port bound and email shape, `parse_asset_id`, `site_id`; faults: `Fault`'s refusals, `covers`, `duration`; store: `connect`, `apply`), so `rm -rf mutants && .venv/bin/mutmut run && .venv/bin/mutmut results | python -I scripts/survivors.py` prints `survivors: every one explained` on the whole tree. ✓ 36 tests; the whole tree's mutation run clean, every survivor explained (three equivalent `on_grid` arithmetic mutants proven by brute force over 1,101,600 instants).

### 1.7 The thin CLI

Done 2026-11-18 (J-014). Check: `python3 -m solarpunk.cli` with `fleet`, `fault`, `telemetry`, `kpi`, `clauses` subcommands, each one call into project; `test/solarpunk/test_cli.py` green; `solarpunk/cli/` imports project alone (MOD-02, `test/test_modules.py`). ✓ five subcommands, each one project call; `fleet load --demo` loads the OAHE eleven; every cli mutant killed; `project.open_or_create` reopens a file store.

### 1.9 Tune-up pass 1

Done 2026-11-18 (J-015). Check: `docs/when/tune-up.md` followed in full: the full gate twice, the navigation log reviewed and its "Last review" set, the metrics table written, the stamped TypeScript-only tests under `test/test_stacks.py` pruned or their skip explained. ✓ cold gate 2.35 min, warm 2.45 min, fast loop 21.3 s; eight debriefs reviewed, four converging complaints fixed in the stack README, the brief rules, process.md and long-run.md; the 19 TypeScript-only skips explained in HANDOFF (a Core fix, not a pruning here).

## Phase 2: the feed, the remote tests, the clock

### 2.1 The asset maintenance list

Done 2026-11-18 (J-016). Check: `docs/ASSET-MAINTENANCE-LIST.md` with one section per `AssetKind` (what the asset is; the fields its feed answers with and each field's expected range; the remote tests that apply; what a passing response is) and `solarpunk/leaf/asset_types.json` holding the same as data (`kind`, `description`, `fields` as name → {unit, min, max}, `tests`); `solarpunk/leaf/asset_types.py` loads it (`asset_type(kind)`, `kinds()`, `fields_of(kind)`) and refuses a kind the list lacks; `scripts/checks/asset_types.py` holds document and JSON together (every kind in both, every field named in the document present in the JSON) with a planted break under `test/fixtures/broken/asset_types/` rejected by `test/test_asset_types.py` (C-013); `test/solarpunk/test_asset_types.py` green; every mutant killed or explained. ✓ six kinds in document and JSON, the check both ways with its two planted breaks; the loader refuses an unknown kind or field (SOL-03); no new survivor.

### 2.4 The receiver

Done 2026-11-18 (J-017). Check: `solarpunk/receiver/` with `handle(conn, line) -> Fault` (a line `<asset-id> <fault-code>`: refuses an asset the fleet lacks, SOL-05, and a code the catalogue lacks, SOL-04, with one `ReceiverError` naming which; else assigns the fault through the ledger and returns it) and `serve(conn, host, port, once=False)` (a TCP listener reading one line per connection and answering `ok <fault_id>` or `refused <reason>`); `python3 -m solarpunk.receiver --db <path> --port 5030` runs it; `test/solarpunk/test_receiver.py` starts it on an ephemeral port in a thread, pushes a good line and two bad ones, and sees the fault in the ledger and the asset's status RED; every mutant killed or explained. ✓ 19 tests; `serve` and `make_server` take the store's path, not a connection, since a SQLite connection is per thread; every receiver mutant killed.

### 2.5 The clock

Done 2026-11-18 (J-018). Check: `solarpunk/schedule/` with `Job(name, command, cadence)` (cadence one of `hourly`, `daily@HH:MM`, `every:N` minutes), `crontab_line(job)` and `schtasks_command(job)` rendering it, each compared with `test/solarpunk/goldens/schedule-crontab.txt` and `schedule-schtasks.txt`; `install(job)` and `remove(job)` the only functions that run the platform's tool (`crontab` or `schtasks`), never called by a test; `python3 -m solarpunk.schedule render <name>` prints both renderings; `test/solarpunk/test_schedule.py` green; every mutant killed or explained. ✓ the three demo jobs rendered both ways against goldens; install and remove one subprocess.run each over a tested pure command builder, and the only mutants with no test (22) are inside them, as the design intends.

### 2.6 The mailer

Done 2026-11-18 (J-019). Check: `solarpunk/mailer/` with `Mail(to, subject, body)`, `compose_degradation(asset, fault_or_result, engineers) -> Mail` (the asset, its location, the code or the failing test and its reason, the instant), `send(mail, settings)` over `smtplib` to `settings.host:settings.port` with STARTTLS when `settings.starttls` and a credential read from the one environment variable `settings.password_variable` names (never printed; absent → no login), `schema()` the `mails` table and `record`; `Settings` read from a JSON file path the caller gives, never from the repository; `test/solarpunk/test_mailer.py` green against a local fake SMTP server on an ephemeral port (the standard library's `smtpd` is gone in 3.12: a small `socketserver` fake speaking enough SMTP for one message), and a test that no credential value appears in any log line or exception; every mutant killed or explained. ✓ 26 tests against a socketserver SMTP fake; the credential value appears in no log, exception or row; every mailer mutant killed.

### 2.2 The feed and its simulator

Done 2026-11-18 (J-021). Check: `solarpunk/feed/` with `ping(asset, timeout_s) -> tuple[Sample, ...]` (opens `asset.host:asset.port` over TCP, reads newline-delimited JSON records `{"asset_id", "at", "irradiance_w_m2", "power_kw", "gap"}` until the server closes, refuses a record whose fields are outside the maintenance list's ranges or whose `at` is off the grid, SOL-06), `FeedError(ValueError)` for an unreachable, slow or malformed feed, and `simulate.py` (`python3 -m solarpunk.feed.simulate OAHE-INV-001 --port 5020 --seed 7 --day 2026-06-01` serves the generator's samples for that day, one record per line, then closes; `--once` answers one connection and exits); `test/solarpunk/test_feed.py` starts the simulator on an ephemeral port in a thread and pings it, and covers each refusal; every mutant killed or explained. ✓ 44 tests including the real `-m solarpunk.feed.simulate --once` as a subprocess; the simulator imports telemetry (SP-010 amended, J-021); every feed mutant killed.

### 2.3 The remote tests and their registry

Done 2026-11-18 (J-022). Check: `solarpunk/remote/` with `registry.py` (`discover()` finds every module under `solarpunk/remote/tests/` and returns its `KINDS`, `CLAUSES`, `run`; refuses a module missing one), `results.py` (`schema()` the `results` table: test_name, asset_id, run_at, passed, reason; `record`, `latest_for(asset_id)`, `last_run_at()`), `run.py` (`run_test(name, asset, samples) -> Result`; `run_suite(conn, assets, samples_by_asset, run_at)` runs every discovered test against every asset of its kinds, records each result, and returns the per-asset `AssetStatus`: RED when the asset carries an open OUTAGE fault, YELLOW when a result in this run failed, GREEN otherwise), and three standalone tests under `solarpunk/remote/tests/`: `reachable.py` (INVERTER, METER, SENSOR, TRACKER: the feed answered at least one record), `on_grid.py` (every kind with a feed: every record's instant on the grid and inside the maintenance list's ranges), `power_under_rated.py` (INVERTER: no record's power exceeds `rated_kw`), each with `KINDS`, `CLAUSES` (naming register clauses) and `run`; `python3 -m solarpunk.remote.run <test> <asset-id>` runs one against one asset's stored samples and prints pass or fail with the reason; `test/solarpunk/test_remote.py` green, with a test per remote test's pass and fail; every mutant killed or explained. ✓ 36 tests; three standalone tests found by the registry; `python3 -m solarpunk.remote.run reachable OAHE-INV-001 --db <path>` prints pass or fail; every remote mutant killed.

### 2.7 The scheduled run and the UI's project surface

Done 2026-11-18 (J-023). Check: `solarpunk/project/` gains `scheduled_run(conn, run_at, settings_path=None) -> RunReport` (for every asset with an endpoint: `feed.ping` and store its samples, a `FeedError` recorded as a failing `reachable` result; then `remote.run_suite` over every asset with the open-outage flags from the ledger; a `Mail` composed and sent for each asset whose status is RED or YELLOW when a settings path is given, recorded in the `mails` table; the report: assets pinged, records stored, results written, statuses per asset, mails sent) and `asset_status` now reading RED on an open OUTAGE fault, YELLOW when the asset's latest results hold a failure, GREEN otherwise; the surface every Phase 3 window calls, so no UI lane touches `orchestrator.py`: `asset_rows(conn)` (id, name, kind, status, last run instant, failing test or `—`), `asset_detail(conn, asset_id)` (the asset, its open faults with meanings, the latest results failing first, the engineer chain), `known_engineers(conn)`, `register_asset(conn, asset)`, `codes_for_kind(kind)`, `kinds()`, `ping_asset(conn, asset_id)`, and `LedgerError` re-exported; `test/solarpunk/test_project.py` extended (a scheduled run over the OAHE fixture with a simulator on an ephemeral port gives one asset YELLOW on a planted failure and one RED on an open outage; `open_or_create` reopens a file store); every mutant killed or explained. ✓ the run over the OAHE inverters with a simulator, a dead port and a fake SMTP server gives GREEN, YELLOW and RED and two mails; every project mutant killed.

### 2.8 Tune-up pass 2

Done 2026-11-18 (J-024). Check: `docs/when/tune-up.md` followed in full; the six readings of J-010 written into `docs/CONTRACT.md` SOL-07 to SOL-10 as sentences (a tune-up may not change invariants' meaning: the sentences say what the code already does, with the worked examples unchanged — anything that would change a number is a question for Ghost instead); the metrics table written; the navigation log's "Last review" set. ✓ cold gate 12.7 min (refused at the gate target: Ghost's question), warm gate 1.48 min with mutmut's cache kept, fast loop 26 s after the socket tests stopped waiting on the 0.5 s poll; seven debriefs reviewed; the contract's sentences for SOL-07 to SOL-10 written.

## Phase 3: the native front end

### 3.1 The fleet window

Done 2026-11-18 (J-025). Check: `solarpunk/ui/` with `app.py` (`FleetWindow(root, conn)`: a scrollable list of every asset in id order, each row a 24×16 solar-panel glyph drawn on a `tkinter.Canvas` in the asset's `AssetStatus` colour (green, yellow, red: `glyph.py` draws it; `colour_of(status)`), the id, the name and the kind; a mouseover tooltip with the last status and the last run's instant from `results.latest_for`; a click opens 3.2's window; a Refresh button that rereads the store) and `__main__.py` (`python3 -m solarpunk.ui --db <path>` opens it; `--demo` is 3.4's); `test/solarpunk/test_ui.py` green under a display (`xvfb-run -a .venv/bin/pytest test/solarpunk/test_ui.py`), skipping with the message "no display" where `tkinter.Tk()` raises `TclError`; the data every widget shows comes from one `project` call the tests also call headless; every mutant killed or explained. ✓ 20 tests under xvfb (8 widget tests skip without a display, the rest run headless); every view string and colour from a pure function; ten display-only survivors recorded in `docs/MUTATION.md`.

### 3.2 The asset window

Done 2026-11-18 (J-026). Check: `solarpunk/ui/asset_window.py` (`AssetWindow(parent, conn, asset_id)`: the asset's fields; its open faults with code, meaning and opened instant; the remote tests of the last run, the failing one first with its reason; a form to assign a catalogue code (a dropdown of `CATALOGUE` for the asset's kind, an Assign button); the engineer: a dropdown of the fleet's known engineer emails plus a text field, and two buttons reading exactly `Save` and `Cancel` — Save calls `fleet.assign_engineer` and closes, Cancel closes and changes nothing); `test/solarpunk/test_ui_asset.py` green under a display, skipping without one; every mutant killed or explained. ✓ 24 tests under xvfb; the 101 layout-only window mutants proven survivors by a by-hand xvfb loop, one pytest run per mutant, and recorded as the display-only class.

### 3.3 The add-asset window

Done 2026-11-18 (J-027). Check: `solarpunk/ui/add_asset.py` (`AddAssetWindow(parent, conn)`: id, name, site, parent (a dropdown of the site's assets), a type dropdown read from `solarpunk.leaf.asset_types.kinds()`, rated kW, location, engineer email, IP address and port; a Ping button that calls `feed.ping` and shows the first record or the `FeedError`; `Save` registers through `project` and closes, `Cancel` closes); the refusals of the fleet shown in the window, never swallowed; `test/solarpunk/test_ui_add.py` green under a display, skipping without one; every mutant killed or explained. ✓ 24 tests under xvfb (16 headless); Ping enabled after a successful Save and reading the feed through project; every form-parsing mutant killed, the widget mutants the display-only class.

### 3.4 The demo

Done 2026-11-18 (J-028). Check: `python3 -m solarpunk.ui --demo` builds a file store `demo.db` beside the current directory (removed and rebuilt each run): the OAHE fixture, one day of seed-7 telemetry, two closed faults and one open INV-001 outage, a simulator started on an ephemeral port for OAHE-INV-001 with the asset's host and port set to it, the remote suite run once (so the window opens with green, yellow and red rows and a last-run instant), then the fleet window; `DEMO.md` at the root with the Windows commands (`py -3.12 -m venv .venv`, the lockfile install, `py -m solarpunk.ui --demo`), what to click in what order, the five-minute talk track, and the clause report command; `test/solarpunk/test_demo.py` builds the demo store headless and asserts the three colours are present; `README.md`'s skeleton filled (what Solarpunk is, the commands, the roadmap's phases in five lines). ✓ `python3 -m solarpunk.ui --demo` under xvfb prints the simulator's port, the rebuilt store and `9 green, 1 yellow, 1 red`, then opens the window; `test_demo.py` builds the store headless; DEMO.md 81 lines with the Windows commands, the click order and the talk track.

### 3.5 Tune-up pass 3

Done 2026-11-18 (J-030). Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set. ✓ cold gate 15.5 min over 4,499 mutants (refused at its target: Ghost's question, J-024), warm 1.07 min, fast loop 25.8 s; four debriefs reviewed; the two UI rules written into the stack README and the brief rules.

## Phase 4: the work-order ledger

### 4.1 The work-order ledger

Done 2026-11-18 (J-031). Check: `solarpunk/leaf/root_causes.py` holds the closed list of root-cause codes (`RootCause` enum: COMPONENT, FIRMWARE, GRID, WEATHER, SENSOR, COMMS, MAINTENANCE_OVERDUE, DESIGN, UNKNOWN, each with a one-line meaning) and `lookup_root_cause(code)` refuses any other; `solarpunk/workorders/` with `schema()` (the `work_orders` table: wo_id, asset_id, fault_id nullable, kind `corrective` or `preventive`, opened, closed nullable, root_cause nullable, note), `open_corrective(conn, asset_id, fault_id, opened, note)`, `open_preventive(conn, asset_id, opened, note)`, `close(conn, wo_id, root_cause, closed)` refusing a close without a root cause from the list (SOL-04's rule for causes), a close before opening and a double close, `open_orders`, `by_asset`, `repeated_causes(conn, period, at_least)`; project gains `open_work_order_from_fault`, `close_work_order` (which closes the order and, for a corrective order, its fault in the ledger in one call) and `work_orders_for(asset_id)`, and the asset detail shows the asset's open orders; `test/solarpunk/test_workorders.py` green; `test/solarpunk/iso/test_iso9001.py` gains the tagged test that holds `9001-10.2.1` (a work order closes only with a root-cause code from the closed list) and `docs/CLAUSE-REGISTER.md`'s row becomes held; every mutant killed or explained. ✓ every clause of the register held: 9001 eight, 55000 four; 4,720 mutants, every survivor explained.

### 4.2 Tune-up pass 4

Done 2026-11-18 (J-032). Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set. ✓ cold gate 14.2 min (refused at its target: Ghost's question), warm 1.08 min, fast loop 26.2 s; the one debrief's points written into the brief rules.

## Phase 5: one word to run it

### 5.1 The one-word command and the remote-test commands

Done 2026-11-18 (J-033). Check: `solarpunk.cmd` in the repository root: `solarpunk` runs `py -m solarpunk.ui` with every argument as typed (`solarpunk --demo` the demo, `solarpunk --db fleet.db` another store), and a first word that is one of the command line's subcommands runs `py -m solarpunk.cli`; `test/test_launcher.py` holds its routing words to the parser's own. `python3 -m solarpunk.cli test list` prints each remote test with its kinds and clauses; `test run [--db PATH] [--at INSTANT]` is the scheduled run once over every asset of the store, printing the counts, each asset's status and each feed that did not answer; `test add <name> --clause <id> [--kind <KIND>]` scaffolds `solarpunk/remote/tests/<name>.py` (`solarpunk/remote/scaffold.py`), its kinds from the asset maintenance list unless named, its `run` failing until written, refusing a taken name, an unknown kind and a missing clause; `test/solarpunk/test_scaffold.py` and `test/solarpunk/test_cli_tests.py` green; README.md and DEMO.md give the commands. ✓ fast loop 903 tests green, ruff clean; the launcher has not been run on Windows from here (no Windows shell in the session), and the new product lines have not been through mutmut (the next full gate's).

### 5.2 The help list

Done 2026-11-18 (J-035). Check: `python3 -m solarpunk.cli help` prints every command with one line of what it does, the window's four first (`solarpunk`, `solarpunk --demo`, `solarpunk --db PATH`, `solarpunk --help`), and opens no store; `solarpunk.cmd` sends `--help`, `-h` and `help` to it; `test/solarpunk/test_cli_tests.py` holds the list to the parser (every command exactly one line, no line for a command the parser lacks) and `test/test_launcher.py` the launcher's flags. ✓ fast loop 908 tests green, ruff clean; not run on Windows from here.

### 5.3 Tune-up pass 5

Done 2026-11-18 (J-039). Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set. ✓ cold gate 9.95 min over 4,910 mutants (the last with mutation in the gate; the first cold run refused on three survivors, killed by J-037's test), warm 0.80 min on the gate without mutation (SP-012), fast loop 23.1 s; the one debrief reviewed; the log's header line restored.

## Phase 6: reports and diagnostics

### 6.1 The power-output report

Done 2026-11-18 (J-041). Check: `docs/CONTRACT.md` SOL-13 states energy, peak, specific yield and capacity factor per inverter and per site with a worked example; `solarpunk/kpi/output.py` computes them over leaf samples, refusing an unrated or zero-rated inverter (SOL-03); `project.power_report(conn, site, period)` recomputes them from the store; `python3 -m solarpunk.cli report SITE START END [--csv]` prints a line per row or CSV, and `solarpunk.cmd` routes `report`; `test/solarpunk/test_output.py` holds the worked example as a golden and the site's energy equal to the performance ratio's (SOL-08) over J-012's day. ✓ fast loop green; the OAHE seed-7 day reports 1591.6242 kWh, 7.9581 kWh/kWp, capacity factor 0.3316, peak 187.22 kW; not run on Windows from here.

### 6.2 The inverter diagnostics

Done 2026-11-18 (J-041). Check: four remote tests under `solarpunk/remote/tests/`, found by the registry: `irradiance_in_range` (INVERTER, SENSOR), `night_power_near_zero`, `performance_above_floor` and `power_not_frozen` (INVERTER), each with its threshold named in the module and its reason naming the first offending record; the asset maintenance list and its JSON name the two new inverter tests; `test/solarpunk/test_diagnostics.py` holds each docstring's cases and edges, and a generated healthy day passes all four. ✓ fast loop green; the demo keeps its three colours (results per run 10 to 19); `tracker_moving` and `energy_monotonic` wait on the feed's wire, which carries irradiance and power alone.

### 6.3 The reports window

Done 2026-11-18 (J-043). Check: `solarpunk/ui/reports.py` opens from a button in the fleet window; it takes a site and a day (or a start and end), shows one row per `project.power_report` row (the site's first: energy, peak, specific yield, capacity factor, records, gaps), draws the site's summed power over the period as a line on a canvas with its axes labelled in kW and UTC hours, and writes the same CSV as `solarpunk report --csv` through a save dialog; a refusal (an unknown site, a reversed period) is shown, never swallowed; `test/solarpunk/test_ui_reports.py` builds it under xvfb (skipped without one) over the demo store and asserts the table's rows equal the report's; the curve's points are a function tested headless; the fast loop green. ✓ the window under xvfb over the demo store, a screenshot read back (the site's 1591.6242 kWh, peak 187.22 kW, the curve 06:00 to 20:00); the pure half in `solarpunk/ui/chart.py`, run by the fast loop without tkinter; the curve breaks at an instant one inverter missed (SOL-13's added sentence) rather than dropping to the other's share, which the first screenshot showed; 13 tests, 4 of them the window's; not run on Windows from here.

### 6.4 The diagnostics in the asset window

Done 2026-11-18 (J-045). Check: `solarpunk/ui/asset_window.py` lists, for the asset's kind, every remote test the registry holds with its latest result (pass, fail or not yet run) and reason, failing first, from one project call the tests make headless; `test/solarpunk/test_ui_asset.py` asserts the demo's OAHE-INV-001 shows all seven inverter tests passing and OAHE-SEN-001 its failing `reachable` first; the fast loop green. ✓ `project.asset_detail(...).diagnostics` (fail, then not run, then pass, each by name; a stored result of a test no longer in the folder kept); the window's "Diagnostics" table, a failure red and a test never run grey, the reason column 480 px and stretching; screenshots of OAHE-INV-001 (seven passes) and OAHE-SEN-001 (`reachable` FAIL first) read back under xvfb; a sensor that does not answer shows its other two tests passing over 0 readings, put to Ghost (HANDOFF item 5); not run on Windows from here.

### 6.5 Tune-up pass 6

Done 2026-11-18 (J-049). Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set. ✓ cold gate 0.83 min, warm 0.80 min, fast loop 22.2 s, 9 of 9 metrics measured, none regressed (a first cold run refused on a tree edited while it ran, J-049); eight debriefs reviewed; the product workpath written (`docs/paths/product.md`, its row in CLAUDE.md, 1197 words); the renumbering line in the process workpath; the talk-track update of J-048 rides here.

## Phase 7: faults suggested by tests, assigned by engineers

### 7.1 Who assigned it

Done 2026-11-18 (J-050). Check: the leaf's `Fault` carries `assigned_by` and `recorded_by`; `solarpunk/faults/` stores them, and a store made before 7.1 gains both columns on opening with its old faults reading `assigned_by` "unrecorded"; `project.assign_fault(conn, asset_id, code, opened, assigned_by, recorded_by=None)` refuses an address the fleet does not hold (`project.known_engineers`) and reports cover when the engineer is not in `engineers_for(asset)`; `python3 -m solarpunk.cli fault assign ASSET CODE OPENED --by ENGINEER [--recorded-by OPERATOR]` (`--by` required) and `fault list` printing who; the asset window's Assign takes the engineer from a dropdown of known engineers and refuses none chosen; the demo's faults name an engineer; the receiver, until 7.2, refuses a push it cannot attribute rather than assign one unattributed; the tests of each, and the fast loop green. ✓ `UnknownEngineer`, `is_cover` and `check_fault` in project; `ledger.upgrade` run by `open_or_create`; the CLI line ends "by <engineer>[ entered by <operator>][ (cover)]"; the window's open faults gain "Assigned by", and Assign an "Assigned by" dropdown and an "Entered by" box; the demo's open outage on OAHE-INV-002 is assigned by INV-001's engineer, entered by the operator, cover; the receiver answers a good push "refused held for an engineer: <asset> <code> (SP-015)"; 6.4's diagnostics hid a failed `reachable` behind the suite's pass of the same run, fixed here (J-050); screenshots of OAHE-INV-002's window read back; not run on Windows from here.

### 7.2 The gate's reliability

Done 2026-11-18 (J-051). Check: `scripts/gate.sh` runs every step in a temporary `git worktree` holding the tree it took before its first step (`.venv` linked in), records that tree, still refuses a step that changes the copy, and is not disturbed by an edit to the working tree while it runs; every step runs under `timeout` (`GHOST_STEP_TIMEOUT`, default 600 s) and a timed-out step is refused by name; `scripts/fast.sh` runs under `timeout` (`GHOST_FAST_TIMEOUT`, default 300 s); `stacks/python/gate.sh --fast` runs ruff, and pytest under `xvfb-run -a` where it is installed, printing `note: window tests not run (no xvfb-run)` otherwise, a line the gate shows on the terminal; the receiver tests' server threads are daemon threads; `test/test_gates.py` holds each in a scratch repository; the fast loop green. ✓ held in `test/test_gate_frozen.py` (`test_gates.py` is at its line ceiling): an edit mid-run, a hung step refused "(timed out after 1 s)", a `note:` on the terminal, no worktree left, every test thread a daemon; the lock and record paths made absolute, since the copy moves the gate's working folder (a red run left the lock held until then); the real fast checks pass in the copy with the window tests run under xvfb and ruff, 1.00 min against 0.83; ruff caught a missing annotation in this item's own test on its first run.

### 7.3 Counts that follow from the registry

Done 2026-11-18 (J-052). Check: no test pins the number or the names of the remote tests, the results of a run, or the commands: `test/solarpunk/test_remote.py`, `test_project_run.py`, `test_demo.py`, `test_cli_tests.py`, `test_ui_asset.py` and `test_diagnostics.py` derive them from `solarpunk.remote.registry` and the parser; scaffolding a remote test into the folder (`solarpunk test add`, in a scratch copy) leaves those tests green; the fast loop green. ✓ a run's results are each tested asset's kind's tests plus one failed ping per dead feed, a formula over the registry; the folder's files give the list; the help test holds a line per command without a count; with `tracker_moving` and a sensor test scaffolded in a scratch copy the six files pass, after the proof found two assumptions more (a sensor's sole failure being `reachable`, and an "unknown" test name that a scaffold makes real), both replaced by the rule they stood for; `test_diagnostics.py` pinned nothing.

### 7.4 Suggestions from the tests

Done 2026-11-18 (J-053). Check: each module under `solarpunk/remote/tests/` declares `SUGGESTS` (a mapping from each of its `KINDS` to a catalogue code or None), held by the registry; a `suggestions` table (asset, code, source test or "device", reason, run, state open/accepted/dismissed, by whom, fault id when accepted, dismissal reason); the scheduled run stores one open suggestion per failing test with a code, never two open of the same code on one asset; the receiver stores a pushed code as a suggestion from the device; `project.accept_suggestion(conn, id, engineer, recorded_by=None)` opens the fault through 7.1's `assign_fault`, linked, and `project.dismiss_suggestion(conn, id, engineer, reason)`; an open suggestion keeps the asset yellow and never red, and no KPI reads it; the rule table printed by `solarpunk test list`; the tests of each, and the fast loop green. ✓ `solarpunk/remote/suggestions.py` (the table) and `solarpunk/project/suggest.py` (the joins), new files in existing modules; the registry refuses a rule for a kind the test does not run on, a kind with no rule, or a code not of the kind's; a run never suggests a code the asset already carries open (the demo's red OAHE-INV-002 gets none; its dead weather station waits with SEN-001); accepting opens the fault at the suggestion's instant; the receiver answers `ok suggestion <id>`; the rule table is Claude's proposal, for Ghost's review (HANDOFF item 6), with two catalogue gaps named; a Tk abort the change exposed in the window tests fixed by `test/solarpunk/conftest.py` (J-053); not run on Windows from here.

### 7.5 Suggestions in the asset window and on the command line

Done 2026-11-18 (J-054). Check: the asset window lists the asset's open suggestions (the device's first, then by run, newest first) with code, meaning, source and reason, and Accept and Dismiss, each taking the engineer from the known-engineer dropdown and an optional operator, Dismiss a reason; `solarpunk fault suggestions [--asset ID]`, `fault accept ID --by ENGINEER [--recorded-by OPERATOR]`, `fault dismiss ID --by ENGINEER --reason TEXT`; `test/solarpunk/test_ui_asset.py` and the CLI tests cover each; a screenshot of the demo's asset window read back under xvfb; the fast loop green. ✓ "Suggested faults" under Diagnostics, its rows by suggestion id, Accept and Dismiss using the window's "Assigned by" and "Entered by"; the window's tests in `test/solarpunk/test_ui_suggestions.py` (`test_ui_asset.py` near the line ceiling) and the CLI's in `test/solarpunk/test_suggestions.py`; a screenshot of OAHE-SEN-001 read back, its "Raised" column widened after it; DEMO.md's click order gains the step; not run on Windows from here.

### 7.6 Tune-up pass 7

Done 2026-11-18 (J-056). Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set. ✓ cold gate 1.02 min, warm 1.02 min, fast loop 26.9 s (the first pass run on 7.2's frozen copy, with the window tests and ruff in it), 9 of 9 metrics, none regressed; five debriefs reviewed; two facts written into the product workpath (what one run stores per asset; the Tk rule and `conftest.py`).

## Phase 8: local tickets

### 8.1 The ticket contract

Done 2026-11-18 (J-061). Check: `docs/CONTRACT.md` gains a ticket section: the statuses (open, acknowledged, in progress, resolved, closed) and every allowed move between them; priority from the fault's severity (OUTAGE, DERATE, INFO); for each priority an acknowledgement and a response target, Ghost's to set (Claude's proposal written beside them, marked as such), with a worked example of a ticket meeting one target and breaching the other; the fields a remote tracker would own (the working assignee, comments, scheduling) and those Solarpunk keeps (the code, who assigned, the root cause, the open and close instants the KPIs read); the leaf holds the statuses, the moves and the targets, tested against the section; the fast loop green. ✓ SOL-14: six moves, P1 1 h / 4 h, P2 4 h / 24 h, P3 24 h / 72 h (Claude's proposal, marked), four target states (met, late, pending, overdue) with the worked example as a golden; `solarpunk/leaf/tickets.py`; `test/solarpunk/test_tickets_contract.py` reads the contract's three tables against the leaf, with a planted break; status is Solarpunk's field, the tracker's change to it a proposal.

### 8.2 The ticket ledger

Done 2026-11-19 (J-063). Check: `solarpunk/workorders/` stores a ticket's status, priority, working assignee, acknowledged and responded instants, comments (each with its author and instant, never edited or deleted) and closeout evidence; a store made before gains the columns on opening; `project.assign_fault` opens the fault's corrective ticket in the same call, a suggestion never opens one; a move the contract forbids is refused; closing needs a root cause from the closed list and closes the fault (4.1); a ticket past a target is reported by a query; the KPIs are unchanged (the ISO and KPI tests unchanged); the fast loop green. ✓ Seven columns on `work_orders` and a `ticket_comments` table (`solarpunk/workorders/ledger.py`, `solarpunk/workorders/tickets.py`); `project.move_ticket`, `set_ticket_assignee`, `comment_on_ticket`, `ticket_comments`, `open_tickets`, `ticket_of`, `tickets_past_target` (`solarpunk/project/tickets.py`); a preventive order is P3 (Claude's proposal); the one-step close-out of 4.1 takes the allowed moves at its instant (SOL-14 says so); the demo's two closed faults close through their tickets with RC-GRID and RC-WEATHER; `test/solarpunk/test_tickets.py` (21 tests); the ISO and KPI tests unchanged; 1020 tests green.

### 8.3 Tune-up pass 8

Done 2026-11-19 (J-064). Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set. ✓ Cold gate 1.3 min, refused at the fast loop (36.7 s cold against 30); warm gate 1.13 min, fast loop 29.2 s, 9 of 9 measured, none regressed; the table written from the warm run; two debriefs read; the log wiped, Last review set.

## Phase 9: the fleet window as an operations root

### 9.1 Headings and readable cells

Done 2026-11-19 (J-065). Check: the list has column headings (Asset, Name, Kind, Status, Last run, Failing); an instant reads "2026-06-01 13:00 UTC", not ISO; an asset with no endpoint reads "no feed" where one with an endpoint and no run reads "never run" (`AssetRow` gains whether it has an endpoint); no cell overruns its column with a 20-character name (the column widths from the text, not fixed x positions), the screenshot read back under xvfb; the pure half (headings, cell text) tested headless; the fast loop green. ✓ A heading strip above the list in bold; `instant_text`, `never_text`, `column_xs`, `width_for` in `solarpunk/ui/app.py`; `AssetRow.has_feed` (default True, so rows made before keep their meaning); the tooltip in the same words; `test/solarpunk/test_ui_columns.py` (8 tests: a made-up 7 px measure headless, the real font under xvfb with "Central inverter 2-B"); the demo's screenshot read: nine "no feed", three runs at "2026-06-01 13:00 UTC", "Irradiance sensor" clear of its column; DEMO.md's click order updated.

### 9.2 The cause column

Done 2026-11-19 (J-066). Check: a red row names its open outage's code and since when, a yellow row its open suggestion's code or else its failing test, a green row "—"; in the demo OAHE-INV-002 reads "INV-001 since 2026-06-01 11:30 UTC" and OAHE-SEN-001 "suggested SEN-001"; the cause comes from one project call that changes no status (`test/solarpunk/test_demo.py` goldens); the fast loop green. ✓ `AssetRow` gains `outage` and `suggested` (defaults None), filled by the same `asset_rows` call; `solarpunk/ui/cells.py` holds `cause_text` and `instant_text` with no tkinter, so the fast loop tests them; a "Cause" column after Status; the demo goldens in `test/solarpunk/test_demo.py`; four cause tests in `test/solarpunk/test_ui_columns.py`; the screenshot read back.

### 9.3 The attention band

Done 2026-11-19 (J-068). Check: above the list, at most four counts: open outages, suggestions awaiting an engineer, open work orders; each equals the length of its project listing (the demo: 1, 1, 1, its outage's ticket the open work order since 8.2); clicking a count filters the list to its assets and clicking it again clears the filter; a count of zero is shown, not hidden; the fast loop green. ✓ `project.attention(conn)` gives the three listings (open OUTAGE faults, open suggestions, open tickets), each read once; `band_counts`, `band_assets`, `filtered`, `showing` in `solarpunk/ui/cells.py`, headless; three buttons above the headings, the filtering one pressed, the status line saying what it shows, the column widths kept from the whole fleet; `test/solarpunk/test_ui_band.py` (9 tests); the screenshots read back, unfiltered and filtered; DEMO.md's click order gains the band.

### 9.4 Sort and filter

Done 2026-11-19 (J-069). Check: pure `worst_first` (red, then yellow, then green, ties by id) and `matching(rows, text, status, kind)` tested headless; a search box (Ctrl+F) and status and kind boxes above the list, Esc clears them; a heading click sorts by its column; F5 refreshes and Enter opens the selected asset; the fast loop green. ✓ `solarpunk/ui/order.py` (`worst_first`, `sorted_by`, `matching`), the row's words moved to `solarpunk/ui/cells.py` so they are headless; a filter row under the band; a heading click sorts (Status worst first), a second turns it round, the heading marked ▲ or ▼ and measured with its mark; Up and Down move a highlighted selection, Enter opens it, a click selects too; Esc clears the search, the boxes and the band's filter; the status line says "2 of 11 shown" when the boxes narrow the list; `test/solarpunk/test_ui_sort.py` (8 tests); the screenshots read back, which found the mark overrunning the next heading.

### 9.5 The status bar

Done 2026-11-19 (J-070). Check: the summary line moves to a status bar at the window's foot with the store's file name and the fleet's last run instant ("demo.db, last run 2026-06-01 13:00 UTC"; an empty store "never run"); Refresh moves to the toolbar beside Add asset and Reports; the window opens sized to its content with a minimum size; the screenshot read back; the fast loop green. ✓ `project.store_name` and `project.fleet_last_run`; `cells.store_line`; a sunken status bar, the store on its left and the summary on its right; the window's own toolbar holds Refresh at its right and the program puts Add asset and Reports in it; the list as tall as the fleet, 6 to 20 rows, the window at least 820 by 420; `test/solarpunk/test_ui_statusbar.py` (6 tests); the demo test finds the summary in the status bar; the screenshot read back.

### 9.6 Tune-up pass 9

Done 2026-11-19 (J-072). Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set. ✓ The first cold gate refused at the Python stack's readability rule (`FleetWindow.__init__` 52 lines of 39), fixed forward by splitting it into `make_list`, `make_bars` and `lay_out`, the window tests green and the demo's screenshot identical to 9.5's pixel for pixel; then cold gate 1.10 min, warm 1.08 min, fast loop 21.1 s, slow tests 10.8 s, 9 of 9 measured, none regressed; five debriefs read; the window row brought up to date; the log wiped, Last review set.

## Phase 10: runs per asset

### 10.1 What a run and a count are

Done 2026-11-19 (J-073). Check: `docs/CONTRACT.md` gains a section: a run of an asset is the results stored at one instant for it (one per test, and the ping's failed `reachable`); an error count is the faults opened and the suggestions raised with a code on an asset in a period, faults and suggestions counted apart, a dismissed suggestion still counted, nothing deleted; a power series is the asset's samples in a period with its gaps named, never filled; each with a worked example over the demo store (OAHE-INV-002's run at 13:00, OAHE-SEN-001's one SEN-001 suggestion); the fast loop green. ✓ SOL-15, seven worked examples read from the demo store (INV-002's run of 8 results with two `reachable`, the sensor's of 4, three assets' error counts, INV-001 across the fleet, INV-001's day of power: 288 samples, 279 records, 9 gaps); `test/solarpunk/test_runs_contract.py` (6 tests) reads each example's numbers from the store and finds its line in the section, with a planted break.

### 10.2 The runs' surface

Done 2026-11-19 (J-074). Check: `project.asset_runs(conn, asset_id, limit=100, search=None)` gives the asset's runs newest first, each with its results, failures first, the search matching a test's name, "pass"/"fail" and words in a reason; `project.asset_power(conn, asset_id, period)` the asset's samples and its gap count; `project.asset_code_counts(conn, asset_id, period)` faults and suggestions by code; `project.code_counts_by_asset(conn, code, period)` each asset's faults and suggestions of one code; each held to 10.1's worked examples; over a store with more than 100 runs, newest first, nothing deleted; the fast loop green. ✓ `solarpunk/project/runs.py` (`Run`, `PowerSeries`, `CodeCount`, `AssetCount` and the four calls); two lane queries, `results.results_of` and `suggestions.raised_in`; a search keeps the runs holding a matching result, whole; `test/solarpunk/test_runs.py` (9 tests: SOL-15's examples, 120 runs with the newest 100 shown and all 120 kept, the counting rules, the refusals).

### 10.3 The Runs button and window

Done 2026-11-19 (J-075). Check: each row of the fleet list has a "Runs" cell that opens `solarpunk/ui/runs_window.py` for that asset (a click elsewhere on the row still opens the asset window); the window lists the asset's last 100 runs, newest first, a run with a failure in red, and selecting a run shows its results with their reasons; a search box narrows the list; an asset never run reads "no runs yet" (or "no feed"); `test/solarpunk/test_ui_runs.py` under xvfb over the demo store; the screenshot read back; the fast loop green. ✓ A blue, underlined "Runs" link past each row's last column (`app.runs_x`); `RunsWindow` (two tables: the runs, the chosen run's results, failures red), the newest run chosen on opening; its words in `solarpunk/ui/runs_text.py`, headless; a search that finds nothing names its words; `test/solarpunk/test_ui_runs.py` (8 tests); DEMO.md step 3; the screenshots read back.
