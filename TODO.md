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

### 1.9 Tune-up pass 1

Check: `docs/when/tune-up.md` followed in full: the full gate twice, the navigation log reviewed and its "Last review" set, the metrics table written, the stamped TypeScript-only tests under `test/test_stacks.py` pruned or their skip explained.

## Phase 2: the feed, the remote tests, the clock

Lanes (P-15): 2.1 first (the list every other lane reads), then 2.2 to 2.6 in parallel, landed in this order; 2.7 after them.

### 2.1 The asset maintenance list

Check: `docs/ASSET-MAINTENANCE-LIST.md` with one section per `AssetKind` (what the asset is; the fields its feed answers with and each field's expected range; the remote tests that apply; what a passing response is) and `solarpunk/leaf/asset_types.json` holding the same as data (`kind`, `description`, `fields` as name → {unit, min, max}, `tests`); `solarpunk/leaf/asset_types.py` loads it (`asset_type(kind)`, `kinds()`, `fields_of(kind)`) and refuses a kind the list lacks; `scripts/checks/asset_types.py` holds document and JSON together (every kind in both, every field named in the document present in the JSON) with a planted break under `test/fixtures/broken/asset_types/` rejected by `test/test_asset_types.py` (C-013); `test/solarpunk/test_asset_types.py` green; every mutant killed or explained.

### 2.2 The feed and its simulator

Check: `solarpunk/feed/` with `ping(asset, timeout_s) -> tuple[Sample, ...]` (opens `asset.host:asset.port` over TCP, reads newline-delimited JSON records `{"asset_id", "at", "irradiance_w_m2", "power_kw", "gap"}` until the server closes, refuses a record whose fields are outside the maintenance list's ranges or whose `at` is off the grid, SOL-06), `FeedError(ValueError)` for an unreachable, slow or malformed feed, and `simulate.py` (`python3 -m solarpunk.feed.simulate OAHE-INV-001 --port 5020 --seed 7 --day 2026-06-01` serves the generator's samples for that day, one record per line, then closes; `--once` answers one connection and exits); `test/solarpunk/test_feed.py` starts the simulator on an ephemeral port in a thread and pings it, and covers each refusal; every mutant killed or explained.

### 2.3 The remote tests and their registry

Check: `solarpunk/remote/` with `registry.py` (`discover()` finds every module under `solarpunk/remote/tests/` and returns its `KINDS`, `CLAUSES`, `run`; refuses a module missing one), `results.py` (`schema()` the `results` table: test_name, asset_id, run_at, passed, reason; `record`, `latest_for(asset_id)`, `last_run_at()`), `run.py` (`run_test(name, asset, samples) -> Result`; `run_suite(conn, assets, samples_by_asset, run_at)` runs every discovered test against every asset of its kinds, records each result, and returns the per-asset `AssetStatus`: RED when the asset carries an open OUTAGE fault, YELLOW when a result in this run failed, GREEN otherwise), and three standalone tests under `solarpunk/remote/tests/`: `reachable.py` (INVERTER, METER, SENSOR, TRACKER: the feed answered at least one record), `on_grid.py` (every kind with a feed: every record's instant on the grid and inside the maintenance list's ranges), `power_under_rated.py` (INVERTER: no record's power exceeds `rated_kw`), each with `KINDS`, `CLAUSES` (naming register clauses) and `run`; `python3 -m solarpunk.remote.run <test> <asset-id>` runs one against one asset's stored samples and prints pass or fail with the reason; `test/solarpunk/test_remote.py` green, with a test per remote test's pass and fail; every mutant killed or explained.

### 2.4 The receiver

Check: `solarpunk/receiver/` with `handle(conn, line) -> Fault` (a line `<asset-id> <fault-code>`: refuses an asset the fleet lacks, SOL-05, and a code the catalogue lacks, SOL-04, with one `ReceiverError` naming which; else assigns the fault through the ledger and returns it) and `serve(conn, host, port, once=False)` (a TCP listener reading one line per connection and answering `ok <fault_id>` or `refused <reason>`); `python3 -m solarpunk.receiver --db <path> --port 5030` runs it; `test/solarpunk/test_receiver.py` starts it on an ephemeral port in a thread, pushes a good line and two bad ones, and sees the fault in the ledger and the asset's status RED; every mutant killed or explained.

### 2.5 The clock

Check: `solarpunk/schedule/` with `Job(name, command, cadence)` (cadence one of `hourly`, `daily@HH:MM`, `every:N` minutes), `crontab_line(job)` and `schtasks_command(job)` rendering it, each compared with `test/solarpunk/goldens/schedule-crontab.txt` and `schedule-schtasks.txt`; `install(job)` and `remove(job)` the only functions that run the platform's tool (`crontab` or `schtasks`), never called by a test; `python3 -m solarpunk.schedule render <name>` prints both renderings; `test/solarpunk/test_schedule.py` green; every mutant killed or explained.

### 2.6 The mailer

Check: `solarpunk/mailer/` with `Mail(to, subject, body)`, `compose_degradation(asset, fault_or_result, engineers) -> Mail` (the asset, its location, the code or the failing test and its reason, the instant), `send(mail, settings)` over `smtplib` to `settings.host:settings.port` with STARTTLS when `settings.starttls` and a credential read from the one environment variable `settings.password_variable` names (never printed; absent → no login), `schema()` the `mails` table and `record`; `Settings` read from a JSON file path the caller gives, never from the repository; `test/solarpunk/test_mailer.py` green against a local fake SMTP server on an ephemeral port (the standard library's `smtpd` is gone in 3.12: a small `socketserver` fake speaking enough SMTP for one message), and a test that no credential value appears in any log line or exception; every mutant killed or explained.

### 2.7 Tune-up pass 2

Check: `docs/when/tune-up.md` followed in full; the six readings of J-010 written into `docs/CONTRACT.md` SOL-07 to SOL-10 as sentences (a tune-up may not change invariants' meaning: the sentences say what the code already does, with the worked examples unchanged — anything that would change a number is a question for Ghost instead); the metrics table written; the navigation log's "Last review" set.

## Phase 3: the native front end

Lanes (P-15): 3.1 to 3.3 in parallel after 2.7, landed in this order; 3.4 after them.

### 3.1 The fleet window

Check: `solarpunk/ui/` with `app.py` (`FleetWindow(root, conn)`: a scrollable list of every asset in id order, each row a 24×16 solar-panel glyph drawn on a `tkinter.Canvas` in the asset's `AssetStatus` colour (green, yellow, red: `glyph.py` draws it; `colour_of(status)`), the id, the name and the kind; a mouseover tooltip with the last status and the last run's instant from `results.latest_for`; a click opens 3.2's window; a Refresh button that rereads the store) and `__main__.py` (`python3 -m solarpunk.ui --db <path>` opens it; `--demo` is 3.4's); `test/solarpunk/test_ui.py` green under a display (`xvfb-run -a .venv/bin/pytest test/solarpunk/test_ui.py`), skipping with the message "no display" where `tkinter.Tk()` raises `TclError`; the data every widget shows comes from one `project` call the tests also call headless; every mutant killed or explained.

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
