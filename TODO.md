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

Lanes (P-15): 7.1 (done, J-050), then 7.2 and 7.3 (SP-017, put ahead by Ghost), then 7.4 (it needs 7.1's `assigned_by`), then 7.5, then 7.6 the pass. Ghost's direction, SP-015.

## Phase 8: local tickets

Lanes (P-15): 8.1 first (the contract), then 8.2, then 8.3 the pass. Ghost's direction, SP-021 and
SP-022; the adapter and the windows moved to Phase 10 by SP-023, so the fleet window is reworked first.

### 8.3 Tune-up pass 8

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 9: the fleet window as an operations root

Lanes (P-15): 9.1 to 9.5 in order (each touches `solarpunk/ui/app.py`), then 9.6 the pass. Ghost's direction, SP-023,
from the 2026-11-18 advisor's review of the root window: the list says what colour an asset is, not why, nor what waits
on a person.

### 9.1 Headings and readable cells

The fleet list reads without a click (SP-023).

Check: the list has column headings (Asset, Name, Kind, Status, Last run, Failing); an instant reads "2026-06-01 13:00 UTC", not ISO; an asset with no endpoint reads "no feed" where one with an endpoint and no run reads "never run" (`AssetRow` gains whether it has an endpoint); no cell overruns its column with a 20-character name (the column widths from the text, not fixed x positions), the screenshot read back under xvfb; the pure half (headings, cell text) tested headless; the fast loop green.

### 9.2 The cause column

A red or yellow row says why (SP-023).

Check: a red row names its open outage's code and since when, a yellow row its open suggestion's code or else its failing test, a green row "—"; in the demo OAHE-INV-002 reads "INV-001 since 2026-06-01 11:30 UTC" and OAHE-SEN-001 "suggested SEN-001"; the cause comes from one project call that changes no status (`test/solarpunk/test_demo.py` goldens); the fast loop green.

### 9.3 The attention band

What waits on a person, counted at the top (SP-023).

Check: above the list, at most four counts: open outages, suggestions awaiting an engineer, open work orders; each equals the length of its project listing (the demo: 1, 1, 1, its outage's ticket the open work order since 8.2); clicking a count filters the list to its assets and clicking it again clears the filter; a count of zero is shown, not hidden; the fast loop green.

### 9.4 Sort and filter

Three red assets found among three hundred without scrolling (SP-023).

Check: pure `worst_first` (red, then yellow, then green, ties by id) and `matching(rows, text, status, kind)` tested headless; a search box (Ctrl+F) and status and kind boxes above the list, Esc clears them; a heading click sorts by its column; F5 refreshes and Enter opens the selected asset; the fast loop green.

### 9.5 The status bar

Which store, and when it last ran (SP-023).

Check: the summary line moves to a status bar at the window's foot with the store's file name and the fleet's last run instant ("demo.db, last run 2026-06-01 13:00 UTC"; an empty store "never run"); Refresh moves to the toolbar beside Add asset and Reports; the window opens sized to its content with a minimum size; the screenshot read back; the fast loop green.

### 9.6 Tune-up pass 9

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 10: tickets in the windows

Lanes (P-15): 10.1, then 10.2, then 10.3 the pass. Ghost's direction, SP-022; moved from Phase 8 (8.3, 8.4) by
SP-023, so the Tickets window and the attention band's tickets land in the reworked fleet window.

### 10.1 The adapter and the local tracker

The ticket ledger behind an interface every tracker implements, the local one first (SP-022).

Check: the module entry for the adapters approved by Ghost in `docs/modules.json` before any code; a sink (create, update, comment, transition) and a source (changes since a cursor) interface; an outbox table written in the same transaction as the ledger change and drained by the scheduled run, so a tracker that is down never blocks the ledger; the local adapter; a contract suite of tests every adapter must pass, run against the local one; the fast loop green.

### 10.2 Tickets in the windows and on the command line

The tickets where people work (SP-022).

Check: a Tickets window opened from the fleet window lists the open tickets ordered by the nearest target, a breach in red; the asset window shows its asset's ticket with Acknowledge, Comment and Resolve (Resolve taking a root cause from the closed list); `solarpunk ticket list|ack|comment|resolve`; each window's screenshot read back under xvfb; the fast loop green.

### 10.3 Tune-up pass 10

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 11: accounts and authentication

Lanes (P-15): 11.1, then 11.2 and 11.4 in parallel, then 11.3, then 11.5 the pass. Ghost's direction, SP-022.

### 11.1 Accounts

Who may act, stored without ever storing a password (SP-022).

Check: the module entry for accounts approved by Ghost in `docs/modules.json` before any code; an accounts table (email, name, role engineer, operator or admin, active, created) and a password check by `hashlib.scrypt` with a per-account salt and its parameters stored beside the hash; no password or hash in any log line, message, mail or test literal (a test's password assembled at runtime); an engineer address the fleet names with no engineer account is flagged by a query; the fast loop green.

### 11.2 Signing in

The windows and the command line know who is at them (SP-022).

Check: the windows open on a sign-in dialog and refuse to open the fleet window without a good one; the command line asks with `getpass` for a command that acts; a failed sign-in is recorded with its account and instant, never its password; the scheduled run acts as no person and attributes nothing to one; the window tests sign in a test account; the fast loop green.

### 11.3 Attribution from the account

Every act carries the signed-in account (SP-022, SP-015).

Check: assigning a fault, accepting or dismissing a suggestion and every ticket action take the signed-in account in place of a chosen address: an engineer acts as themself, an operator enters on a named engineer's word (recorded as entered by the operator), an admin who is not an engineer assigns nothing; the "Assigned by" dropdown is gone from the window; the CLI's `--by` is the signed-in account; a fault and a ticket record the account; the fast loop green.

### 11.4 Account administration

Accounts are made, reset and stopped, never deleted (SP-022).

Check: an admin creates an account, resets a password and deactivates an account (records keep its name; it cannot sign in); the first admin is made by `solarpunk account init` on the machine, once; `solarpunk account add|reset|deactivate|list`; the fast loop green.

### 11.5 Tune-up pass 11

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 12: the tests' record, at the root and per asset

Lanes (P-15): 12.1 and 12.2 first (SP-019: what a test is, and the suites), then 12.3 (a test's own reads) and 12.4 (reactions, which need suites; SP-020), then 12.5 (the surface every window reads), then 12.6, 12.7 and 12.8 in parallel, then 12.9 the pass. Moved after Phases 8 and 9 by SP-022 (now 8 and 11), and after Phase 10 by SP-023. Moved after Phase 8 by SP-018. Ghost's direction, SP-016.

### 12.1 What a test looks like

A remote test's contract written down and held by a check (SP-019), so a test is written to a page, not copied from
its neighbour.

Check: `docs/REMOTE-TESTS.md` states a remote test's contract: its module's fields (`KINDS`, `CLAUSES`, `SUGGESTS`, `run`) and what each must hold; that `run(asset, samples)` reads only what it is given (no store, no network, no clock) and returns a `Result`; the reason's shape (the first offending record with its instant, or a count when it passes); every threshold a named module constant with a comment saying why; a docstring with at least one passing and one failing case; its name in the asset maintenance list's `Tests:` line for each of its kinds; `scripts/checks/remote_tests.py` holds every module in `solarpunk/remote/tests/` to what a check can see (the fields, the docstring's cases, the maintenance-list lines, no import of a store, network or clock module), with a planted break under `test/fixtures/broken/remote_tests/`; `solarpunk test add`'s scaffold meets it but for `run`; the fast loop green.

### 12.2 The suites folder

Tests run in named suites, each with its own reach and cadence (SP-019); a suite is a Python module of declarations
(SP-020).

Check: a suite is a module in `solarpunk/remote/suites/` declaring `TESTS` (names the registry holds), `KINDS` and `SITES` (its reach) and `CADENCE` (a value of a closed set: every run, hourly, daily at an hour), and nothing else of its own; the registry finds every suite as it finds every test, refusing one with a test, kind or cadence it lacks, or with a function of its own; the scheduled run runs each suite due at its instant and stores its results as today, a result carrying its suite; `solarpunk suite list` prints each suite with its tests and cadence, `suite run NAME [--db PATH]` runs one now, `suite add NAME --test T [--kind K] [--cadence C]` writes one; the default suite `all` runs every test on every run, so a store with no other suite behaves as before; the fast loop green.

### 12.3 A test's own reads

A test that needs readings the stored samples cannot give (power once a second for a minute) declares them, and the
runner takes them; the test itself stays a pure judgement (SP-020).

Check: a test may declare `ACQUIRE`, a value of a closed set (`Burst(field, every_s, for_s)` first), held by the registry; the feed (`solarpunk/feed/`) gains a live-read mode answering one current reading per request, and the simulator serves it from its day; the runner, for a test with `ACQUIRE`, takes the reads through the feed (each read's instant kept) and hands them to `run`, which reads nothing else; a test without `ACQUIRE` judges the stored samples as today; a first burst test (power ripple over a minute) with its threshold and why; the tests use the simulator, never a real asset, and a burst's duration is shortened in them by a parameter, never by sleeping a minute; the fast loop green.

### 12.4 Reactions

What a failure does is declared per test from a closed vocabulary, checked at load, and printed (SP-020).

Check: a test declares `REACTIONS`, per kind a tuple of actions from a closed set (`Suggest(code)`, `Mail()`, `RunSuite(name)`, `OpenPreventive(note)`), replacing `SUGGESTS` (each test's rule becomes a `Suggest`, results unchanged); the registry refuses an unknown action, a code not of the kind's, a suite the folder lacks, and a chain where a suite started by a reaction would start itself, directly or through another, or run deeper than a stated limit; the scheduled run carries out each failing test's reactions, recording each; `solarpunk test list` prints each test's reactions; no action commands equipment; the fast loop green.

### 12.5 The record's surface and the timing

The scheduled run times each test, and project gives the three views the windows read; every result is kept (SP-016).

Check: the results table gains `duration_ms` (a store made before gains the column on opening, its old rows empty); the scheduled run and `solarpunk test run` store each test's duration; `project.tests_overview(conn)`, `project.test_log(conn, name, limit=100)` and `project.asset_log(conn, asset_id, limit=100, search=None)` (search matching the test name, "pass"/"fail" and words in the reason) are tested over a store holding more than 100 runs, newest first, nothing deleted; a result with no duration reads None, never 0; the fast loop green.

### 12.6 Last run in the asset window

Each test in the asset's diagnostics shows when it last ran and how long it took (SP-016).

Check: `solarpunk/ui/asset_window.py`'s diagnostics table has columns for the last-run instant and the duration, "never" for a test never run on the asset, "—" for a duration not recorded; `test/solarpunk/test_ui_asset.py` holds both; a screenshot read back under xvfb; the fast loop green.

### 12.7 The Tests window

The master list from the root of the window: every test, its run time, and its last 100 runs (SP-016).

Check: `solarpunk/ui/tests_window.py` opens from a "Tests" button in the fleet window; it lists `project.tests_overview` (name, kinds, assets, last run, duration, passes, failures) and, for the selected test, `project.test_log` (asset, instant, result, reason, duration), failures red; `test/solarpunk/test_ui_tests.py` builds it under xvfb over the demo store with its pure half headless; a screenshot read back; the fast loop green.

### 12.8 The asset's history

The asset's last 100 results, searchable and graphed (SP-016).

Check: `solarpunk/ui/history.py` opens from a "History" button in the asset window; a table of `project.asset_log` with a search box that narrows it; a canvas timeline, one row per test, one mark per run, green a pass and red a failure, the time axis in UTC, its geometry pure functions tested headless (as `solarpunk/ui/chart.py`'s are); `test/solarpunk/test_ui_history.py` under xvfb over a store with more than 100 runs of an asset; a screenshot read back; the fast loop green.

### 12.9 Tune-up pass 12

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 13: the network's security

Lanes (P-15): 13.1 alone, then the items its decisions call for, then the pass. Moved after Phase 6 by SP-013, after Phase 7 by SP-015 after the tests' record by SP-016, and after tickets and accounts by SP-022.

### 13.1 Network security: an engineering pass over the feed and the receiver

The feed and the receiver use plain TCP. The receiver accepts asset identifiers and fault codes, but the implementation
establishes neither an authenticated device identity nor an encrypted transport; it also defaults to localhost. That is
reasonable for the demonstration. A production deployment needs: authenticated asset connections; transport
encryption; authorization of fault submissions; replay protection; network segmentation and deployment controls. The
2026-11-18 advisor's research is the pass's starting point (`docs/ROADMAP.md` 13.1): the industry's addressing (host,
port, protocol, unit id, register map; Modbus TCP and SunSpec at the device), its security references (Modbus/TCP
Security, IEC 62351, IEC 62443, NERC CIP-003), and a sixth threat, spoofed telemetry from whatever answers at a feed's
host and port. Since SP-022 the pass also designs Phase 14's central server: its authenticated API, the accounts
and tokens on the wire, TLS, and whether the server may use a vetted dependency (Python's `http.server` is not for
production), with Phase 11's accounts as the identities.

Check: `docs/NETWORK-SECURITY.md` holds the pass: what the feed (`solarpunk/feed/`) and the receiver (`solarpunk/receiver/`) do on the wire today, a threat model for each, and for each of the five needs (authenticated asset connections, transport encryption, authorization of fault submissions, replay protection, network segmentation and deployment controls) a proposed decision in `docs/decisions.md` with the options weighed, what the standard library alone can carry and what would need a dependency (Ghost's approval, C-034); the items that build each decision Ghost puts in force are added to this phase before its pass (the pass renumbered to the phase's end). No code changes in this item: the design is Ghost's to rule on first.

### 13.2 Tune-up pass 13

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 14: the network

Lanes (P-15): 14.1, then the items it writes, then the pass. Ghost's direction, SP-022: a central server with many
clients, planned from Phase 13's decisions.

### 14.1 The server's plan

One Solarpunk server holds the store; the desktop windows on many machines and a future phone app are its clients over
one authenticated API (SP-022). Its items wait on Phase 13's decisions, so this item writes them.

Check: from the decisions Phase 13 puts in force, the items that build the server, its API, the desktop as its client and the app's surface are written into `docs/ROADMAP.md` and this phase, each with its check, before this phase's pass (renumbered to the phase's end); no code in this item.

### 14.2 Tune-up pass 14

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

