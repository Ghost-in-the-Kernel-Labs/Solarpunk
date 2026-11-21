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

## Phase 7: faults suggested by tests, assigned by engineers

Lanes (P-15): 7.7, then 7.8, then 7.9, then 7.10 the tune-up commit. Reopened by SP-046 on Ghost's word, after running
the demo: telemetry assigns a fault, nothing is accepted or dismissed, an engineer writes the root cause as free text,
and a ticket opens from a failed test result, one ticket to many failed results.

### 7.7 Faults from telemetry

A failing test raises its fault itself; nobody accepts or dismisses it (SP-046).

Check: a failing remote test result raises a fault itself, with its rule table's code, or the catalogue's generic code (one new code in the leaf's catalogue: a remote test failed, its cause not yet known) where the table names none; a failure of a test on an asset in the run right after that test failed on that asset joins the earlier failure's fault, and a pass ends the streak; a no-data result raises none; accepting and dismissing a suggestion are gone from the windows, the command line and `project`, and no code updates a fault's or a suggestion's state in place (a later fact is a new row); a store made before 7.7 reads its suggestions and faults as they were; the clause register rows that name the old behaviour, and their tests, are reworded with it; the fast loop green.

### 7.8 The root cause, written by an engineer

A fault's root cause is blank until an engineer writes it, in words (SP-046).

Check: a fault carries a root cause, blank until an engineer writes it as free text (no list, no dropdown), kept as a new row with who and when, a later writing superseding an earlier one without erasing it; `solarpunk/leaf/root_causes.py` is retired (SP-011 superseded); a ticket on a fault closes only once the fault's root cause is written; the clause register's 9001-10.2.1 row and its test say so; the asset window shows a fault's root cause and a box to write it, and `solarpunk fault cause FAULT_ID TEXT` writes one; the fast loop green.

### 7.9 A ticket from a failed test

A ticket opens from the failed test run against an asset, not from the asset (SP-046).

Check: an "Open a ticket" control sits on a failed test result (its asset, test and run) in the asset window and the Runs window, and `solarpunk ticket open --result ID`, not on the asset; one ticket maps to many failed results: a failure in the run right after a failure of the same test on the same asset joins that failure's ticket, a pass ending the streak, and opening a ticket on a failed result already in a ticket's streak shows that ticket instead of opening a second; the ticket window lists its failed results; the fast loop green.

### 7.10 Tune-up commit 7

Check: `docs/when/tune-up.md` steps 1, 2, 5 and 6 (a reopened phase of three items or fewer); the metrics table written; the navigation log's "Last review" set.

## Phase 8: local tickets

Lanes (P-15): 8.1 first (the contract), then 8.2, then 8.3 the pass. Ghost's direction, SP-021 and
SP-022; the adapter and the windows moved to Phase 10 by SP-023 (Phase 11 since SP-024), so the fleet window is reworked first.

## Phase 9: the fleet window as an operations root

Lanes (P-15): 9.1 to 9.5 in order (each touches `solarpunk/ui/app.py`), then 9.6 the pass. Ghost's direction, SP-023,
from the 2026-11-18 advisor's review of the root window: the list says what colour an asset is, not why, nor what waits
on a person.

## Phase 9: the fleet window as an operations root

Lanes (P-15): 9.7, then 9.8, then 9.9 the tune-up commit. Reopened by SP-030 on Ghost's word, after running the window
on his own machine: no icon, and no way from the root to add a test.

## Phase 10: runs per asset

Lanes (P-15): 10.1 first (the contract section), then 10.2 (the surface every view reads), then 10.3 (the button and
the window), then 10.4, 10.5 and 10.6 in parallel, then 10.7 (the fleet's view), then 10.8 the pass. Ghost's direction,
SP-024: a Runs button beside each asset, its runs, and the runs grouped and graphed. It takes over the asset's history
that Phase 13 (then 12.5's `asset_log` and 12.8) planned, so nothing is built twice.

## Phase 11: tickets in the windows

Lanes (P-15): 11.1, then 11.2, then 11.3 the pass. Ghost's direction, SP-022; moved from Phase 8 (8.3, 8.4) by
SP-023, so the Tickets window and the attention band's tickets land in the reworked fleet window.

## Phase 12: accounts and authentication

Lanes (P-15): 12.1, then 12.2 (versions), then 12.3 and 12.5 in parallel, then 12.4, then 12.6 (a false-alarm baseline on field data), then 12.8 the pass; 12.7 waits (Phase W). Ghost's direction,
SP-022; 12.1 split in two by SP-028 (accounts, then versions); 12.6 added on Ghost's word, 2026-11-20 (J-098).

## Phase 13: the tests' record, at the root and per asset

Lanes (P-15): 13.1 and 13.2 first (SP-019: what a test is, and the suites), then 13.3 (a test's own reads) and 13.4 (reactions, which need suites; SP-020), then 13.5 (the surface every window reads), then 13.6 and 13.7 in parallel, then the human maintainability pass (SP-042): 13.8, then 13.9, 13.10 and 13.11 in parallel, then 13.12 the pass; the asset's history went to Phase 10 (SP-024). Moved after tickets and accounts by SP-022, after the fleet window and the ticket windows by SP-023, and after runs per asset (Phase 10) by SP-024. Moved after Phase 8 by SP-018. Ghost's direction, SP-016.

### 13.3 A test's own reads

A test that needs readings the stored samples cannot give (power once a second for a minute) declares them, and the
runner takes them; the test itself stays a pure judgement (SP-020).

Check: a test may declare `ACQUIRE`, a value of a closed set (`Burst(field, every_s, for_s)` first), held by the registry; the feed (`solarpunk/feed/`) gains a live-read mode answering one current reading per request, and the simulator serves it from its day; the runner, for a test with `ACQUIRE`, takes the reads through the feed (each read's instant kept) and hands them to `run`, which reads nothing else; a test without `ACQUIRE` judges the stored samples as today; a first burst test (power ripple over a minute) with its threshold and why; the tests use the simulator, never a real asset, and a burst's duration is shortened in them by a parameter, never by sleeping a minute; the fast loop green.

### 13.4 Reactions

What a failure does is declared per test from a closed vocabulary, checked at load, and printed (SP-020).

Check: a test declares `REACTIONS`, per kind a tuple of actions from a closed set (`Suggest(code)`, `Mail()`, `RunSuite(name)`, `OpenPreventive(note)`), replacing `SUGGESTS` (each test's rule becomes a `Suggest`, results unchanged); the registry refuses an unknown action, a code not of the kind's, a suite the folder lacks, and a chain where a suite started by a reaction would start itself, directly or through another, or run deeper than a stated limit; the scheduled run carries out each failing test's reactions, recording each; `solarpunk test list` prints each test's reactions; no action commands equipment; the fast loop green.

### 13.5 The record's surface and the timing

The scheduled run times each test, and project gives the three views the windows read; every result is kept (SP-016).

Check: the results table gains `duration_ms` (a store made before gains the column on opening, its old rows empty); the scheduled run and `solarpunk test run` store each test's duration; `project.tests_overview(conn)` and `project.test_log(conn, name, limit=100)` are tested (an asset's own runs are Phase 10's `asset_runs`, SP-024) over a store holding more than 100 runs, newest first, nothing deleted; a result with no duration reads None, never 0; the fast loop green.

### 13.6 Last run in the asset window

Each test in the asset's diagnostics shows when it last ran and how long it took (SP-016).

Check: `solarpunk/ui/asset_window.py`'s diagnostics table has columns for the last-run instant and the duration, "never" for a test never run on the asset, "—" for a duration not recorded; `test/solarpunk/test_ui_asset.py` holds both; a screenshot read back under xvfb; the fast loop green.

### 13.7 The Tests window

The master list from the root of the window: every test, its run time, and its last 100 runs (SP-016).

Check: `solarpunk/ui/tests_window.py` opens from a "Tests" button in the fleet window; it lists `project.tests_overview` (name, kinds, assets, last run, duration, passes, failures) and, for the selected test, `project.test_log` (asset, instant, result, reason, duration), failures red; `test/solarpunk/test_ui_tests.py` builds it under xvfb over the demo store with its pure half headless; a screenshot read back; the fast loop green.

### 13.8 Names of three characters or more

No variable, argument or loop name in `solarpunk/`, `scripts/` or `test/` is two characters or fewer, held by a check
(SP-042, part 1).

Check: `scripts/checks/names.py` refuses every binding (an assignment, an argument, a loop or comprehension target, an `except` name, a lambda argument) of two characters or fewer in the Python under `solarpunk/`, `scripts/` and `test/`, `_` and `self` excepted, naming file, line and name, with a planted break under `test/fixtures/broken/names/`; it runs in the fast loop; every such name renamed to what it holds; a refactor: every result unchanged, the fast loop and the window tests under xvfb green before and after.

### 13.9 Names and purpose comments reviewed

A person reading each module finds every name saying what it holds and every function's docstring saying what it is
for (SP-042, parts 1 and 3).

Check: each module of `solarpunk/` and each file of `scripts/` read for names longer than two characters that do not say what they hold and for docstrings that restate the code rather than say the function's purpose; each renamed or rewritten, module by module, each module's changes named in the journal; a refactor: every result unchanged, the fast loop and the window tests under xvfb green.

### 13.10 A README for people in each module

`solarpunk/README.md` maps the modules in plain words, and each module folder's `README.md` says what each of its files
does (SP-042, part 2).

Check: `solarpunk/README.md` names every module folder with a sentence or two on what it is for and how the parts fit (the leaf, project as the one door, the windows), written for a person new to the code; each folder under `solarpunk/` holding Python has a `README.md` naming each of its files with what it does; `scripts/checks/readmes.py` fails when a folder lacks its README or a file is missing from it, with a planted break under `test/fixtures/broken/readmes/`; the fast loop green.

### 13.11 The decision map

Each decision is mapped to the functions that hold it, and each function holding a decision cites it (SP-042, part 4).

Check: `scripts/decision_map.py` writes `docs/DECISION-MAP.md`, for each decision in `theGhost.md` the functions (file and name) whose `# Decision:` or `# Invariant:` line cites it, "no function" otherwise; the fast loop fails when the file is stale; `scripts/checks/decision_map.py` fails when an in-force decision whose `Held by` names a file under `solarpunk/` or `scripts/` is cited by no function, or a citation names a decision or invariant that does not exist, with a planted break under `test/fixtures/broken/decision_map/`; the missing citations added to the functions that hold each decision; the fast loop green.

### 13.12 Tune-up pass 13

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 14: the traceability matrix

Lanes (P-15): 14.1, then 14.2 and 14.3 in parallel, then 14.4, then 14.5, then 14.6, then 14.7 the pass. Ghost's direction, SP-044: the traceability matrix, ahead of quality management, with the network and the central server last.

### 14.1 The register's control column

Each register row names the product's control and where its evidence is stored, and every clause a remote test cites is a row (SP-044).

Check: `docs/CLAUSE-REGISTER.md` has the columns Clause, Requirement, Control (what in the product enforces it: a remote test by name, a rule by its function, or `—`), Evidence (the store table its records sit in, or `—` where the software alone holds it), Held by, Status; `scripts/checks/clauses.py` refuses a row missing a column, a Control naming a remote test that does not exist, and a remote test whose `CLAUSES` names a clause the register lacks, each with a planted break under `test/fixtures/broken/clauses/`; SOL-12 in `docs/CONTRACT.md` and `docs/REMOTE-TESTS.md` say so; the fast loop green.

### 14.2 Evidence that cannot be deleted

The evidence tables are append-only and each row is chained to the one before by hash, so a deleted or changed record is found (SP-044).

Check: a `docs/CONTRACT.md` section under a new SOL id names the evidence tables (remote results, faults, work orders, ticket moves and comments), which of their columns may change (a closure or a supersession is a new row or a column the section names), and a worked example of the chain by hand; no code in `solarpunk/` deletes from those tables or updates a column the section does not name, held by a check with a planted break; each new evidence row stores the hash of its content and of the row before it; `solarpunk evidence verify [--db PATH]` prints `evidence: intact, N rows` or the first broken row by table and id, exit 1; a store made before 14.2 is upgraded with its rows chained in order; the fast loop green.

### 14.3 Clause links for faults, work orders and KPIs

One declared table in the leaf says which clauses each fault code and KPI evidences (SP-044; root causes are free text since SP-046).

Check: a declared table in `solarpunk/leaf/` maps each fault-catalogue code and each KPI to zero or more clause ids, each a register row (a check, with a planted break); `project` resolves a record's clauses from it at read time and stores no copy; the register's Evidence column names the tables these links reach; the fast loop green.

### 14.4 The evidence query

For a clause, a site and a period, every record that evidences it and every asset with none, from a worked example first (SP-044).

Check: a `docs/CONTRACT.md` section with a worked example by hand: for a clause, a site and a period, each evidence record (remote results by the test's `CLAUSES`, faults, work orders and KPIs by 14.3's table) per asset of the site, and each asset the clause's control reaches with no record in the period listed as a gap; `project.evidence(conn, clause, site, start, end)` returns exactly the example's rows on the demo fleet; a clause the software alone holds returns its register status, not a gap; the fast loop green.

### 14.5 The matrix command and export

One command prints the matrix for a site and period and writes it to a file the operator names (SP-044).

Check: `solarpunk matrix --site SITE --from DATE --to DATE [--db PATH] [--csv FILE]` prints one row per register clause (clause, requirement, control, evidence records, assets with a gap) and 14.2's chain verdict; the CSV goes where the operator names it, never into the repository by default (C-033); the output's first line says the matrix claims conformance to nothing (SOL-12); a golden of the demo fleet's matrix; the fast loop green.

### 14.6 The matrix window

A Matrix button at the fleet window's root opens the matrix, and a clause opens its evidence and its gaps (SP-044).

Check: a Matrix button at the fleet window's root opens a window of 14.5's rows for a chosen site and period, a clause's row opening its evidence records and gaps; its words in a pure text module tested in the fast loop; rendered under xvfb and the screenshot read before landing; `DEMO.md` quotes its words; the fast loop green.

### 14.7 Tune-up pass 14

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 15: quality management

Lanes (P-15): 15.1, 15.2 and 15.3 in parallel, then 15.4 the pass. Ghost's direction, SP-029: inspection checklists and
evidence, CAPA effectiveness verification and document control, from `docs/GOAL.md` area 4. Renumbered by SP-044 (was Phase 18).

### 15.1 Inspection checklists and evidence

A ticket's work is done against a checklist, and what proves it is kept (SP-029).

Check: a checklist per asset kind and work type in a declared file, checked as the maintenance list is; a ticket of
that kind carries its checklist, each step done, failed or not applicable with who and when; resolving needs every step
answered; evidence (a note, a reading, a file's name and hash, never the file in the repository, C-033) attached to a
step and kept, never edited or deleted; the asset window's ticket panel shows the steps; clause register rows for ISO
9001 7.5 and 8.5; the fast loop green.

### 15.2 CAPA effectiveness verification

A corrective action is checked to have worked (SP-029).

Check: a contract section first: a closed corrective ticket is verified after a stated period by whether its fault's
code recurred on its asset (`repeated_causes`), with a worked example; a verification due is listed; a recurrence
reopens the question as a nonconformity, a quiet period marks the action effective; who verified and when are kept;
the clause register's ISO 9001 10.2 row names the test; the fast loop green.

### 15.3 Document control

The procedures the work follows are versioned, approved and current (SP-029).

Check: a register of controlled documents (a title, a version, an owner, an approval, a review date), each a document in
the repository or named by its hash outside it; a superseded version kept, never deleted; a document past its review
date listed; a checklist (15.1) names the document version it follows; clause register rows for ISO 9001 7.5.2 and
7.5.3; the fast loop green.

### 15.4 Tune-up pass 15

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 16: condition and maintenance planning

Lanes (P-15): 16.1 first (the contract section and the baselines), then 16.2 and 16.3 in parallel, then 16.4 the pass.
Ghost's direction, SP-029: asset condition baselines, preventive maintenance scheduling and condition-based maintenance,
from `docs/GOAL.md` areas 1 and 3.

### 16.1 Asset condition baselines

What normal looks like for each asset, so a reading can be judged against the asset's own past (SP-029).

Check: a contract section first: a baseline per asset and measure (power per irradiance band for an inverter, first),
the window it is learnt over, the records it needs before it holds, and its worked example over synthetic days; the
baseline recomputed from stored samples, never kept apart from them; a query giving each asset's reading beside its
baseline and the gap between them, with the records and gaps that explain it; an asset with too few records says so;
the fast loop green.

### 16.2 Preventive maintenance scheduling

Preventive work orders opened by a schedule, not by hand (SP-029).

Check: a schedule per asset kind (a task, an interval in days or in running hours) in the asset maintenance list,
checked against the list as the tests are; the scheduled run opens a preventive work order when one falls due, once,
never twice for one due date; a query of what is due and overdue; the work orders' tickets carry them to the Tickets
window; the fast loop green.

### 16.3 Condition-based maintenance

Maintenance decided by what the asset's condition shows (SP-029).

Check: a rule per measure that opens a preventive work order (or suggests one, SP-015) when a reading falls past its
baseline (16.1) by a stated margin for a stated time, its worked example in the contract; the work order names the
reading and the baseline that opened it; a rule never fires twice for one excursion; the over- and under-maintaining
counts of `docs/GOAL.md` (work done with no change in condition, condition worsening with no work) as a query; the fast
loop green.

### 16.4 Tune-up pass 16

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 17: anomaly detection and alarm correlation

Lanes (P-15): 17.1, then 17.2, then 17.3 the pass. Ghost's direction, SP-029, from `docs/GOAL.md` area 2. Deterministic
methods with worked examples; no model client (MOD-03) without a decision of its own.

### 17.1 Anomaly detection

A reading unlike the asset's own past or its neighbours' is flagged (SP-029).

Check: a contract section first: each method (a deviation from the 16.1 baseline beyond a stated band; a reading
unlike the same-kind assets of its site at the same instant), its parameters as named constants with why, and a worked
example; an anomaly is a suggestion (SP-015), never a fault, its reason naming the reading and what it was held
against; a test's planted anomaly found and a normal synthetic day not flagged; the fast loop green.

### 17.2 Alarm correlation

Many alarms with one cause are seen as one (SP-029).

Check: a contract section first: alarms (faults, suggestions, failed tests) grouped when they fall within a stated
window on assets of one parent chain (a site, an inverter and its strings), the group's likely root named (the highest
asset in the chain that alarmed), with a worked example; the asset and Runs windows show an alarm's group; a group is a
reading recomputed when asked, never stored apart; the fast loop green.

### 17.3 Tune-up pass 17

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 18: contractor performance management

Lanes (P-15): 18.1, then 18.2 the pass. Ghost's direction, SP-029, from `docs/GOAL.md` area 5. Renumbered by SP-044 (was Phase 19).

### 18.1 Contractors and their scorecard

Who does the work, and how well (SP-029).

Check: a contractor (a name, the sites and asset kinds it serves) set on a ticket; a scorecard per contractor over a
period: its tickets' acknowledgement and response targets met and late (SOL-14), its fixes that held (15.2), its open
backlog, each number beside the counts that explain it, a contract section and worked example first; a report window
and `solarpunk report contractors`; the fast loop green.

### 18.2 Tune-up pass 18

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 19: multiple inverter vendors

Lanes (P-15): 19.1, then 19.2 the pass. Ghost's direction, SP-029; after the network's security (Phase 21), which rules
how a device is reached. Renumbered by SP-044 (was Phase 20).

### 19.1 Vendor profiles

Inverters of more than one maker read as one fleet (SP-029, superseding in part ROADMAP §4's "no connection to a real
device").

Check: a vendor profile per maker (its register map over SunSpec models or its own, its units and scale factors, its
status and fault words mapped to the catalogue) in a declared file, checked as the maintenance list is; an asset names
its vendor; the feed normalizes every vendor's reading to the leaf's sample, and the simulator serves at least two
vendors' maps; a reading a profile cannot map is refused by name, never guessed; whether a real device is connected is a
decision of its own (Phase 21's); the fast loop green.

### 19.2 Tune-up pass 19

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 20: Azure

Lanes (P-15): 20.1 first (the guide), then 20.2, 20.3 and 20.4 in parallel, then 20.5 the pass. Ghost's direction,
SP-037: Azure as the place Solarpunk runs, by configuration and the standard library alone; what needs a dependency is
Phase 21's and 22's to decide. Renumbered by SP-044 (was Phase 21).

### 20.1 The Azure deployment guide

Solarpunk as it is, on an Azure virtual machine, with no code changed (SP-037).

Check: `docs/AZURE.md` says how to run Solarpunk on an Azure VM (Linux with cron, or Windows with Task Scheduler, from
the one job definition), where the store lives (a managed disk, with snapshots), how the VM reaches a plant's devices
(a site-to-site VPN or ExpressRoute into the plant network) and what the network security group opens (the receiver's
port, to named sources only), and how the mailer sends through Azure Communication Services Email's SMTP endpoint, by
settings alone; every claim about Azure carries the link to the page it was read from and the date it was read; a
check holds the document's links and its pointers; the fast loop green.

### 20.2 Secrets from Key Vault by managed identity

The mailer's SMTP credential read from Azure Key Vault, never from a file (SP-037, the supply-chain rules).

Check: with a vault and a secret name configured, the mailer's credential is fetched at send time through the VM's
managed identity (a token from the instance metadata endpoint, then the vault's REST API), with `urllib` alone; the
credential is never printed, logged, stored or put in a message; without the setting, the mailer reads its settings as
before; tested against a local stand-in for both endpoints, the real ones never called by a test; the fast loop green.

### 20.3 Reports and exports to Blob Storage

A report or an export written to an Azure Blob Storage container as well as to a file (SP-037).

Check: with a container configured, `solarpunk report` and the field baseline's output are also put to the container
through its REST API by managed identity, `urllib` alone; a failed upload says so and keeps the local file; tested
against a local stand-in; the fast loop green.

### 20.4 Health and alarms to Azure Monitor

The scheduled run's health and alarms sent to a Log Analytics workspace, so Azure can page someone when the run stops
(SP-037).

Check: with a data collection endpoint and rule configured, each scheduled run sends one health record (when it ran,
how many assets, how many failed) and one record per failing test through the Logs Ingestion API by managed identity,
`urllib` alone; a failed send never stops the run; `docs/AZURE.md` gives the alert rule for a run that stops
reporting; tested against a local stand-in; the fast loop green.

### 20.5 Tune-up pass 20

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 21: the network's security

Lanes (P-15): 21.1 alone, then 21.2 (company sign-in) and the items its decisions call for, then the pass. Moved after Phase 6 by SP-013, after Phase 7 by SP-015 after the tests' record by SP-016, and after tickets and accounts by SP-022. Renumbered by SP-044 (was Phase 14).

### 21.1 Network security: an engineering pass over the feed and the receiver

The feed and the receiver use plain TCP. The receiver accepts asset identifiers and fault codes, but the implementation
establishes neither an authenticated device identity nor an encrypted transport; it also defaults to localhost. That is
reasonable for the demonstration. A production deployment needs: authenticated asset connections; transport
encryption; authorization of fault submissions; replay protection; network segmentation and deployment controls. The
2026-11-18 advisor's research is the pass's starting point (`docs/ROADMAP.md` 21.1): the industry's addressing (host,
port, protocol, unit id, register map; Modbus TCP and SunSpec at the device), its security references (Modbus/TCP
Security, IEC 62351, IEC 62443, NERC CIP-003), and a sixth threat, spoofed telemetry from whatever answers at a feed's
host and port. Since SP-022 the pass also designs Phase 22's central server: its authenticated API, the accounts
and tokens on the wire, TLS, and whether the server may use a vetted dependency (Python's `http.server` is not for
production), with Phase 12's accounts as the identities.

Check: `docs/NETWORK-SECURITY.md` holds the pass: what the feed (`solarpunk/feed/`) and the receiver (`solarpunk/receiver/`) do on the wire today, a threat model for each, and for each of the five needs (authenticated asset connections, transport encryption, authorization of fault submissions, replay protection, network segmentation and deployment controls) a proposed decision in `docs/decisions.md` with the options weighed, what the standard library alone can carry and what would need a dependency (Ghost's approval, C-034); the items that build each decision Ghost puts in force are added to this phase before its pass (the pass renumbered to the phase's end). No code changes in this item: the design is Ghost's to rule on first.

### 21.2 Company sign-in

Enterprise authentication: an account signs in with the organisation's identity (Microsoft Entra ID, Google) as well as,
or instead of, a Solarpunk password (SP-026, SP-029).

Check: the pass of 21.1 holds a proposed decision for it (OpenID Connect against the organisation's identity provider,
or none; whether a dependency is needed, Ghost's approval, C-034); if Ghost puts one in force, an account of 12.1 is
linked to an outside identity by its email, a sign-in through it gives the same account and its role and sites, a
Solarpunk password stays for a machine with no provider, and the items that build it are written here before the pass;
no code until the decision; the fast loop green.

### 21.3 Tune-up pass 21

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 22: the network

Lanes (P-15): 22.1, then the items it writes, then the pass. Ghost's direction, SP-022: a central server with many
clients, planned from Phase 21's decisions. Renumbered by SP-044 (was Phase 15).

### 22.1 The server's plan

One Solarpunk server holds the store; the desktop windows on many machines and a future phone app are its clients over
one authenticated API (SP-022). Its items wait on Phase 21's decisions, so this item writes them.

Check: from the decisions Phase 21 puts in force, the items that build the server, its API, the desktop as its client and the app's surface are written into `docs/ROADMAP.md` and this phase, each with its check, before this phase's pass (renumbered to the phase's end); no code in this item.

### 22.2 Tune-up pass 22

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase W: waiting on Ghost

### 12.7 Known failures caught, on labelled field data

Moved: from Phase 12
Waits on: a public PV dataset that labels its failures with their times, its licence read, and Ghost's ruling on putting readings finer than five minutes on the grid (SP-036)

Each recorded failure in a labelled dataset is caught, or its miss explained, by the remote tests (J-099).

Check: the dataset, its licence and its labels written in `docs/FIELD-DATA.md`; the gridding rule a decision; per recorded failure, the check that caught it or why none did, in the journal; the fast loop green.

