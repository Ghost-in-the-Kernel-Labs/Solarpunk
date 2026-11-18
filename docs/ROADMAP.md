# Roadmap: the plan, not the decision log

A plan, in phases. Each phase's steps are items with a check that fails before the work and passes
after; each phase ends with a numbered tune-up pass (C-024). When a phase is built, its section
shrinks to a ten-line header and the decisions it produced live in `theGhost.md`. `TODO.md` is this
plan as a chain: the open items, in order, with the checks copied; `docs/DONE.md` is what is
finished.

## 1. The product in three sentences

Solarpunk manages a fleet of utility-scale solar assets the way an ISO 55000 asset manager and an ISO
9001 quality manager would audit one: every asset in a registry, every fault a catalogue code assigned
to an asset in a database, every KPI a contract clause with a hand-checkable example, and every
quality claim a test that flags. The thesis to hold: a number whose meaning is written where the
number is computed survives the people who defined it. The thesis to refuse: a dashboard, a report or
a certificate that states a number the repository cannot recompute from its own data.

## 2. Principles

The core's principles, copied from Ghost-Core when this project was stamped; add this project's own below them.

- **P-01 The check before the thing it checks.** Every document arrives with its check and the
  check's planted break, in the same commit (C-003, C-013).
- **P-02 A refactor changes no result.** Every test green before and after, every generated file
  identical (C-017).
- **P-03 Findings before claims.** What a check proves about a parent or a practice is a row in
  `docs/FINDINGS.md` before it is a sentence anywhere else (C-014).
- **P-04 One shape until proven.** One check framework, one test runner, one fast loop; a second
  arrives when the first has failed a stated test (C-002).
- **P-05 Numbered decisions, test-checked supersession** (C-008).
- **P-06 Plans shrink into decisions.** A built phase becomes a ten-line header.
- **P-07 The routing table is the front door** (C-020, C-021).
- **P-08 One canonical word per concept, from the first file** (C-011).
- **P-09 Ratchets only where there is debt** (C-023).
- **P-10 Proven by a run, not on paper.** "Done" never means "on paper" (C-004).
- **P-11 The agent's environment is a first-class deliverable**, funded at one commit in eight (C-022, C-024).
- **P-12 Cloud-primary.** Nothing requires the maintainer's own machine (AGT-01).
- **P-13 CI minutes are spent by hand** (C-032).
- **P-14 Core checks run with nothing installed.** Python 3 standard library, `-I` (C-022).
- **P-15 Lanes do not touch.** A phase's items are lanes, each one module folder and one test file, built in
  parallel by separate workers and landed in number order through one gate (SP-005, MOD-05).
- **P-16 The standard is a list of tests.** A clause of ISO 9001 or ISO 55000 this project speaks of is a row
  in the clause register and a tagged test that flags; the project claims conformance to nothing (SOL-12).
- **P-17 No runtime dependency until a phase needs one.** The product is standard library (SQLite, tkinter,
  `datetime`); a dependency enters with a decision and a review (SP-004, C-034).


## 3. Settled facts

| Id | Fact | Source | Implication |
| --- | --- | --- | --- |
| F-01 | SCADA at utility-scale sites commonly logs at 5-minute intervals; irradiance at STC is 1000 W/m² | the KPI contract's choices (SOL-06, SOL-08), stated as this project's, not an industry claim | `SAMPLE_INTERVAL_S = 300`, `STC_IRRADIANCE_W_M2 = 1000.0` live in the leaf |
| F-02 | mutmut runs the tests in a copy holding Python alone; exits red with zero mutants | J-002, F-004 | mutation covers `solarpunk/` and `test/solarpunk/` (SP-002) |
| F-03 | This session has no Docker and no Windows; GitHub Actions minutes are scarce | AGT-01, C-032 | Windows behaviour is tested by generated artefacts against goldens; a Windows run is a by-hand job |
| F-04 | `sqlite3` and `tkinter` ship with CPython on Windows and Linux | the standard library | the database and the native UI add no dependency (P-17) |

## 4. What is deliberately not built

- A web front end, a REST service, or anything a browser opens: the UI is native (tkinter) on Windows and
  Linux (Ghost, 2026-11-17).
- A connection to a real SCADA, CMMS or revenue meter: telemetry is synthetic and deterministic; an adapter is a
  later project's.
- A claim of conformance or certification to ISO 9001 or ISO 55000: the register says which requirements the
  checks can flag, in the project's words; the standards' text is not reproduced (SOL-12).
- A model client: `docs/modules.json`'s `forbidden` list; a judge, if ever, is a decision first (MOD-03).

## 5. The meta-architecture

The core's table, copied from Ghost-Core when this project was stamped; add this project's contract and modules.

| Document | What it holds | Test |
| --- | --- | --- |
| `CLAUDE.md` | the routing table, the when list, the binding rules | `test/test_claude_md.py` (words, rows, pointers) |
| `theGhost.md` | the decisions | `test/test_ghost.py` |
| `docs/GLOSSARY.md` | the words | `test/test_glossary.py` |
| `docs/journal/` | what happened | `test/test_journal.py` |
| `TODO.md`, `docs/DONE.md`, this file | the plan as a chain | `test/test_todo.py` |
| `docs/HANDOFF.md` | what waits on whom | `test/test_journal.py` (open conflicts), `test/test_registers.py` (raised escalations) |
| `docs/FINDINGS.md`, `docs/ESCALATIONS.md` | the registers | `test/test_registers.py` |
| `docs/NAVIGATION-LOG.md` | the debriefs and the last review | `test/test_navigation.py` |
| `docs/AGENT.md` | the environment contract and the metrics | `test/test_metrics.py` |
| `docs/CONTRACT.md`, `docs/modules.json` | the kernel contract and the import graph | `test/test_contract.py`, `test/test_modules.py` |
| `docs/when/*.md`, `docs/paths/*.md` | what to do in a situation; a workpath's rows | `test/test_pointers.py` |
| `docs/SUPPLY-CHAIN.md` | the baseline and where this repository stands | `test/test_supply_chain.py` |
| `docs/CONTRACT.md` (the KPI contract, `SOL-nn`) | the KPI definitions with worked examples; the leaf holds them in code | `test/test_contract.py`, `test/solarpunk/` |
| `docs/CLAUSE-REGISTER.md` | each claimed ISO 9001 / 55000 clause and the tagged test that flags it | `scripts/checks/clauses.py` (lane 1.5) |


## 6. Phases

Each phase's items are lanes (P-15): a lane names its module folder and its test file, and no two lanes
of one phase name the same file, so workers build them at once; the coordinator lands them in number
order, each through `scripts/gate.sh --fast` and `scripts/commit.sh`. An item's plan is its paragraph
here; its check is copied into `TODO.md`.

### Phase 0: founding

- 0.1 this project's ghost, named (done, J-002)
- 0.2 the stack wired; by SP-002 the leaf's fault-code catalogue landed with it (done, J-002)
- 0.3 the roadmap and TODO filled: §1 to §6 and Phase 1's items
- 0.4 the contract and the leaf module: `docs/CONTRACT.md` SOL-01 to SOL-12, `docs/modules.json`'s seven
  modules, the leaf's asset, clock, telemetry, fault, KPI-number and store files
- 0.5 the founding decisions, Ghost's: SP-003 to SP-007 drafted from Ghost's rulings of 2026-11-17 for his word
- 0.6 Tune-up pass 0

### Phase 1: the fleet, its faults, its numbers

- **1.1 The asset registry (`solarpunk/fleet/`, `test/solarpunk/test_fleet.py`).** `schema()` returns the `assets`
  table (asset_id primary key, kind, site, parent_id referencing assets, name, rated_kw, host, port, location,
  engineer_email: every field of the leaf's `Asset`); `assign_engineer(conn, asset_id, email)` and
  `engineers_for(conn, asset_id)` (the asset's engineer, then its parent's, then its site's: who is written to); `register(conn, asset)`
  refuses a malformed id (SOL-05), a kind that disagrees with the id's prefix, a parent that does not exist or
  whose site differs, and a duplicate; `by_site`, `by_kind`, `children`, `get` return leaf `Asset`s in id order;
  `load_fleet(conn, assets)` registers a tuple in order. An eleven-row example fleet (the site OAHE and ten assets at it: two inverters,
  four strings, two trackers, a meter, a sensor) is a fixture the other lanes' tests may copy, never import.
- **1.2 The fault ledger (`solarpunk/faults/`, `test/solarpunk/test_faults.py`).** `schema()` returns the `faults`
  table (fault_id integer primary key, asset_id text, code, opened, closed nullable; no foreign key to assets,
  MOD-05: project checks the asset exists); `assign(conn, asset_id, code, opened)` refuses a code `lookup`
  refuses (SOL-04), a naive instant (SOL-06) and a second open fault of the same code on the same asset;
  `close(conn, fault_id, closed)` refuses closing before opening and closing twice; `open_faults`, `by_asset`,
  `by_code`, `in_period(conn, period)` return leaf `Fault`s; `repeated(conn, period, at_least)` returns (asset_id,
  code, count) for codes assigned at least N times, the preventive-action signal. Instants are stored as ISO 8601
  UTC text and read back as aware datetimes.
- **1.3 Synthetic SCADA (`solarpunk/telemetry/`, `test/solarpunk/test_telemetry.py`).** `generate(assets, period,
  seed)` returns leaf `Sample`s for every inverter at every expected instant (SOL-06): irradiance a clear-sky bell
  over the day (zero before 06:00 and after 20:00 UTC, peak 1000 W/m² at 13:00, from `math`, no numpy), power
  `rated_kw × irradiance / 1000 × 0.92` with `random.Random(seed)` jitter of ±3 %, and gaps at a seeded 2 % of
  instants as `gap()` samples; the same seed gives byte-identical output (a golden of one day for one inverter,
  regenerated by `python3 -m solarpunk.telemetry.generate --seed 7`, SOL-02). `schema()` returns the `samples`
  table; `store(conn, samples)` and `in_period(conn, asset_id, period)`.
- **1.4 The KPI engine (`solarpunk/kpi/`, `test/solarpunk/test_kpi.py`).** Pure functions over leaf types, no
  database: `availability(period, faults) -> Availability(value, expected, excluded, down, gaps)` per SOL-07;
  `performance_ratio(assets, samples) -> PerformanceRatio(value, energy_kwh, reference_kwh, unreliable)` per
  SOL-08; `energy_yield(site, meter_kwh, samples, faults) -> EnergyYield(kwh, source)` per SOL-09;
  `mtbf_mttr(kind, assets, period, faults) -> Reliability(mtbf_h, mttr_h, count, open)` per SOL-10; each
  rounded to `ROUND_TO`. The contract's worked examples are the goldens, one test each, and a ten-row table per
  KPI in `test/solarpunk/test_kpi.py` a person checks by hand. The blind mirror (`stacks/python/README.md`) is
  1.6's.
- **1.5 The clause register and its check (`docs/CLAUSE-REGISTER.md`, `scripts/checks/clauses.py`,
  `scripts/clauses.py`, `test/solarpunk/iso/test_iso9001.py`, `test/solarpunk/iso/test_iso55000.py`,
  `test/test_clauses.py`).** The register: one row per claimed clause, `| Clause | Requirement (our words) | Held
  by | Status |`, clauses as `9001-9.1.3`, `55000-6.2.2`; a first set of eight to twelve clauses drawn from
  ISO 9001 §7.5 (documented information), §8.7 (nonconforming outputs), §9.1 (monitoring and measurement),
  §10.2 (nonconformity and corrective action) and ISO 55001 §6.2 (asset management objectives and planning),
  §7.5 (information requirements), §9.1 (performance evaluation). The tests: one function per clause, its
  docstring's first line `Clause: 9001-9.1.3`, asserting the thing in this repository that flags the
  requirement (the catalogue is closed; a fault carries a code; a KPI reports its gaps; a worked example exists
  for every number). The check: every register row names a test that exists and is tagged with that clause; every
  tagged test has a row; a row with no test is `open`. The command `python3 -I scripts/clauses.py` runs the two
  files and prints each clause `held`, `failing` or `open`, so a standard in the list can be flagged against on
  demand. No sentence of either standard is copied; each requirement is in the project's words.
- **1.6 The orchestrator and the mirror (`solarpunk/project/`, `test/solarpunk/test_project.py`,
  `test/solarpunk/test_mirror.py`).** Lands after 1.1 to 1.5: `open_store(path)` applies every module's schema;
  `assign_fault` checks the asset exists before the ledger takes it; `kpis_for(site, period)` reads the fleet, the
  faults and the samples and calls the engine; the blind mirror, written by a worker who reads `docs/CONTRACT.md`
  and never `solarpunk/kpi/`, recomputes the four worked examples and agrees.
- **1.7 The thin CLI (`solarpunk/cli/`, `test/solarpunk/test_cli.py`).** `python3 -m solarpunk.cli fleet load|list`,
  `fault assign|close|list`, `telemetry generate`, `kpi <site> <start> <end>`, `clauses`: argument parsing and
  one call into project each; no logic (MOD-02).
- **1.8 The leaf's own tests (`test/solarpunk/test_leaf.py`).** The leaf's refusals and numbers tested directly, so its
  mutants are killed in the leaf's own file and no lane inherits survivors it may not fix (every Phase 1 lane reported
  them, J-007).
- **1.9 Tune-up pass 1.**

### Phase 2: the feed, the remote tests, the clock

What Ghost set on 2026-11-17; the lanes, 2.1 first and the rest in parallel (P-15):

- **2.1 The asset maintenance list (`docs/ASSET-MAINTENANCE-LIST.md`, `solarpunk/leaf/asset_types.json`).** One entry per
  asset type: what the asset is, the fields its feed answers with and the range each is supposed to fall in (an
  inverter answers `irradiance_w_m2`, `power_kw`, `temperature_c`; a tracker `angle_deg`; a meter `energy_kwh`,
  monotonic), the remote tests that can be run against it, and what a passing response is. The UI's type dropdown
  reads this list, the feed reader checks a response against it, and a remote test's `KINDS` names entries in it;
  `AssetKind` stays the id of an entry. A check holds the document and the JSON together (C-013).
- **2.2 The feed (`solarpunk/feed/`).** An asset is added by its IP address and port (`Asset.host`, `Asset.port`, in the
  leaf from 1.1); `ping(asset)` opens the endpoint and reads its data feed, one JSON line per sample in the leaf's
  `Sample` shape over plain TCP, and turns it into samples the telemetry table stores. A simulator
  (`python3 -m solarpunk.feed.simulate <asset> --port N --seed S`) serves the synthetic generator's output on a port,
  so the client, the remote tests and the UI are exercised here with no real inverter; a real asset's adapter is a
  later project's (§4).
- **2.3 Remote tests (`solarpunk/remote/`).** A remote test is a standalone module `solarpunk/remote/tests/<name>.py`
  with `KINDS` (the `AssetKind`s it runs against), `CLAUSES` (the register clauses it evidences, `9001-9.1.1` …),
  and `run(asset, samples) -> Result(passed, reason)`; it is executed on its own against one asset of a defined
  kind (`python3 -m solarpunk.remote.run <test> <asset-id>`) and by the scheduled job against every asset of its
  kinds. Each test is its own roadmap lane, written in parallel by its own worker from a one-page brief; the first
  set: reachable within a timeout; a sample on the grid; irradiance in range; power under rated; night power near
  zero; tracker angle moving by day; meter energy monotonic. The registry (`solarpunk/remote/registry.py`) finds
  every module in the folder, so a test is added by adding a file; a run stores one `results` row per (test, asset,
  instant) with pass or fail and the reason. The clause register (1.5) counts a remote test's `CLAUSES` as
  evidence beside the repository's tagged tests, so ISO 9001 and ISO 55000 coverage is one report over both
  (`scripts/clauses.py`). The leaf's `AssetStatus` rule: RED when the asset carries an open OUTAGE fault, YELLOW when
  the latest run has a failing remote test, GREEN otherwise.
- **2.6 The mailer (`solarpunk/mailer/`).** On a new OUTAGE fault, a pushed error code or a failing remote test, one mail
  to the engineers `engineers_for` names, saying the asset, its location, the code or test and the instant, sent by
  `smtplib` from the standard library over the account's SMTP server (Outlook's own through Microsoft 365's SMTP, any
  SMTP host on Linux: one code path, SP-009); the server, port and sender live in a settings file the tests never
  read, and the tests use a local `smtpd`-style fake. A mail is also a row in a `mails` table, so what was sent and to
  whom is a query.
- **2.5 The clock (`solarpunk/schedule/`).** One `Job` (name, command, cadence) rendered to a crontab line on Linux and a
  `schtasks /Create` command on Windows, each against a golden; `install` and `remove` run the platform's tool and
  are the only functions that touch the host, so the tests never do; a Windows run is a by-hand Actions job (C-032).
  The scheduled job pings every asset with a feed, runs the whole remote-test suite (each test against every asset
  of its kinds), stores the results, stamps each asset's last status and the run's instant (`last_status`,
  `last_run_at` on the asset, shown on mouseover in Phase 3), and recomputes the site's KPIs. Open for Ghost: whether
  the job runs `python3 -m solarpunk.cli` or a frozen entry point.
- **2.4 The receiver (`solarpunk/receiver/`).** The one inbound surface: an asset pushes a line `<asset-id> <fault-code>`
  to the central server; the receiver refuses an unknown asset or code (SOL-04, SOL-05), assigns the fault in the
  ledger and sets the asset's status at once (SP-008), so degradation reaches the fleet view in real time, between
  scheduled runs.

- **2.7 The scheduled run and the UI's project surface (`solarpunk/project/`).** The job the clock runs: ping every asset
  with an endpoint, store the samples, run the remote suite with the ledger's open-outage flags, stamp each status, mail
  the engineers of every RED or YELLOW asset when a settings path is given; `asset_status` becomes the three-colour rule
  (RED an open outage, YELLOW a failing latest result, GREEN otherwise). And the one surface the three Phase 3 windows
  call, so the UI lanes never edit the orchestrator: rows for the fleet window, a detail for the asset window, the
  engineers, the kinds and codes for the dropdowns, register and ping for the add-asset window.
- **2.8 Tune-up pass 2**, which also writes J-010's six readings into the contract as sentences.

### Phase 3: the native front end

A desktop UI on Windows and Linux, no browser and no web hook (Ghost, 2026-11-17; SP-007): tkinter from the standard
library (P-17), `solarpunk/ui/`, calling project alone (a `ui` module row in `docs/modules.json`, mayImport project).

- **3.1 The fleet window (`solarpunk/ui/app.py`, `glyph.py`, `__main__.py`).** A scrollable list of every asset, each
  row a small solar-panel glyph on a canvas in the asset's `AssetStatus` colour (green: the last scheduled run's remote
  tests passed; yellow: one failed; red: an open OUTAGE fault), the id, name and kind; mouseover shows the last status
  and the run's instant; a click opens the asset window; Refresh rereads the store. Every widget's data is one project
  call the tests also make headless; the widgets are tested under a virtual display (`xvfb-run`) and skip without one.
- **3.2 The asset window (`solarpunk/ui/asset_window.py`).** The asset's fields, its open faults with their meanings,
  the last run's remote tests with the failing one and its reason first, a form to assign a catalogue code, and the
  engineer assignment: a dropdown of known engineer emails plus a text field, with `Save` and `Cancel`.
- **3.3 The add-asset window (`solarpunk/ui/add_asset.py`).** Id, name, site, parent, the type from a dropdown read
  from the asset maintenance list, rated kW, location, engineer email, IP address and port; Ping reads the feed once
  and shows the first record or the error; Save registers through project; the fleet's refusals are shown, never
  swallowed.
- **3.4 The demo (`python3 -m solarpunk.ui --demo`, `DEMO.md`).** A rebuilt file store with the OAHE fixture, a day of
  telemetry, closed and open faults, a simulator for one inverter and one run of the remote suite, so the window opens
  with all three colours and a last-run instant; `DEMO.md` holds the Windows commands, the click order, the talk track
  and the clause report; `README.md` filled.
- **3.5 Tune-up pass 3.**

### Phase 4: the work-order ledger

The CMMS half of the ghost: a corrective action carries its cause.

- **4.1 The work-order ledger (`solarpunk/workorders/`, `solarpunk/leaf/root_causes.py`).** A work order is opened from a
  fault (corrective) or from a `repeated` signal or a schedule (preventive), carries the asset, the fault where there is
  one, who opened it and a note, and closes only with a root-cause code from a closed list in the leaf — so root-cause
  analysis is a query (`repeated_causes`) and ISO 9001 10.2.1 is held by a test. Closing a corrective order closes its
  fault, in project, in one call. The asset window lists the asset's open orders (a later item).
- **4.2 Tune-up pass 4.**

### Phase 5: one word to run it

Ghost's directions of 2026-11-18, after the demo ran on his Windows machine.

- **5.1 The one-word command and the remote-test commands (`solarpunk.cmd`, `solarpunk/cli/`, `solarpunk/remote/scaffold.py`).**
  On Windows `solarpunk` opens the window and `solarpunk --demo` the demo; `solarpunk test run` runs every remote
  test over every asset of the store once, `solarpunk test list` names the tests, and `solarpunk test add <name>`
  scaffolds a new one beside the others, failing until its `run` is written, so no asset is green on a test nobody
  wrote. The launcher is a batch file that only chooses between `solarpunk.ui` and `solarpunk.cli`; the logic is
  project's and remote's (MOD-02).
- **5.2 The help list (`solarpunk/cli/main.py`, `solarpunk.cmd`).** `solarpunk --help` (or `-h`, or `help`) lists every
  command with a line of what it does, the window's first; the list is a constant a test holds to the parser.
- **5.3 Tune-up pass 5.** Ghost's word: the pass runs once the two commands land.

### Phase 6: reports and diagnostics

Ghost's direction of 2026-11-18, before the demo: reports on the fleet's power output and diagnostics for the solar
units, ahead of the network's security (SP-013). It adds to two of `docs/GOAL.md`'s areas, management reporting (5) and
SCADA analytics (2), and joins them to the asset view (1).

- **6.1 The power-output report (`solarpunk/kpi/output.py`, `test/solarpunk/test_output.py`).** Per inverter and per
  site over a period, energy, peak, specific yield (kWh/kWp) and capacity factor, each beside its records and gaps
  (SOL-13, with a worked example); `project.power_report(conn, site, period)` recomputes it from the stored samples;
  `solarpunk report SITE START END [--csv]` prints it or writes it as CSV.
- **6.2 The inverter diagnostics (`solarpunk/remote/tests/`, `test/solarpunk/test_diagnostics.py`).** Four remote
  tests, one file each, found by the registry (SP-010): `irradiance_in_range` (inverter and weather station),
  `night_power_near_zero`, `performance_above_floor` (the daylight performance ratio at or above 0.75: the condition
  that says a crew is worth sending, GOAL's "What to watch out for") and `power_not_frozen` (one non-zero power six
  records in a row is a logger replaying its last value). Each names its threshold beside its reason. The tracker's
  `tracker_moving` and the meter's `energy_monotonic` wait on the feed carrying `angle_deg` and `energy_kwh`, which its
  wire does not yet (the 2026-11-18 advisor's finding).
- **6.3 The reports window (`solarpunk/ui/reports.py`).** A site and a period chosen, the power-output table of 6.1 and
  the site's power curve drawn on a tkinter canvas (no dependency, P-17), with a Save as CSV button; opened from the
  fleet window. Its data is `project.power_report`, the call its tests also make headless.
- **6.4 The diagnostics in the asset window (`solarpunk/ui/asset_window.py`).** The asset's latest result of every
  remote test that runs on its kind, failing first, each with its reason and the threshold it names.
- **6.5 Tune-up pass 6.**

### Phase 7: faults suggested by tests, assigned by engineers

Ghost's direction of 2026-11-18 (SP-015): a remote test's rules name a likely fault, and an engineer, the one who
examines the asset and replaces the part, assigns it; the record says which engineer, and which operator entered it
when it was called in. It adds to `docs/GOAL.md`'s quality management (4: who decided is a record) and maintenance (3).

- **7.1 Who assigned it (`solarpunk/leaf/faults.py`, `solarpunk/faults/`, `solarpunk/project/`, `solarpunk/cli/`,
  `solarpunk/ui/asset_window.py`).** A fault carries `assigned_by` (an engineer address the fleet holds) and
  `recorded_by` (the operator who entered it on the engineer's word, or none); `project.assign_fault` refuses an
  address the fleet does not hold and reports when the engineer is not the asset's own chain (cover); a store made
  before gains the two columns on opening, its old faults read `assigned_by` "unrecorded". `solarpunk fault assign`
  takes `--by ENGINEER` (required) and `--recorded-by OPERATOR`; the asset window's Assign takes the engineer from a
  dropdown of known engineers; the demo's faults name an engineer; `fault list` prints who.
- **7.2 The gate's reliability (`scripts/gate.sh`, `scripts/fast.sh`, `stacks/python/gate.sh`; SP-017).** The gate runs on
  a frozen copy of the tree it records; every step and the fast loop time out; ruff and the window tests (under xvfb
  where installed) are in the fast checks, and the stack gate says on the terminal when the window tests could not run.
- **7.3 Counts that follow from the registry (`test/`; SP-017).** The tests take the number of remote tests, their
  results per run and the commands from the registry and the parser, so adding a remote test or a command is one file.
- **7.4 Suggestions from the tests (`solarpunk/remote/`, `solarpunk/project/`, `solarpunk/receiver/`).** Each remote
  test names the likely catalogue code for a failure on each kind it runs on (`SUGGESTS`, a rule table Ghost reviews:
  `reachable` on an inverter suggests INV-001, a frozen power suggests no code until the catalogue has one); the
  scheduled run stores a suggestion for every failing test with a code (asset, code, test, reason, run); a code pushed
  to the receiver is a suggestion marked as pushed by the device (SP-008 in part superseded). An engineer accepts a
  suggestion into a fault linked to it, or dismisses it with a reason; both record who. An open suggestion keeps the
  asset yellow; only a fault turns it red or counts in a KPI.
- **7.5 Suggestions in the asset window and on the command line (`solarpunk/ui/asset_window.py`, `solarpunk/cli/`).**
  The asset window lists open suggestions (the device's first, then by run) with Accept and Dismiss, each taking the
  engineer and, for a call-in, the operator; `solarpunk fault suggestions|accept|dismiss`.
- **7.6 Tune-up pass 7.**

### Phase 8: the cause by email

Ghost's direction of 2026-11-18 (SP-018): an engineer replies to the mailer's mail with the cause; the reply is scanned,
and when it names exactly one root cause the fault's work order closes with it, the mail kept as the closure's evidence.
It joins maintenance execution (3: closeout evidence) to quality management (4: root cause, ISO 9001 10.2).

- **8.1 The reply token (`solarpunk/mailer/`).** Each mail about a fault carries a token in its subject, an HMAC of the
  fault's id under a key in the settings file (`hmac` from the standard library), and asks for a reply with the cause,
  a `CAUSE: <word>` line read first; a token is checked without the store, and a forged or altered one refused.
- **8.2 The mailbox reader (`solarpunk/mailer/`, `solarpunk/project/`).** `imaplib` reads the unseen mail of the
  settings' mailbox at each scheduled run; every mail is stored whole in an `inbound_mails` table and never deleted; the
  tests use a local fake IMAP server, as the mailer's use a fake SMTP one.
- **8.3 The cause scan and its review queue (`solarpunk/leaf/root_causes.py`, `solarpunk/project/`).** The synonyms of
  each root cause in the leaf (a closed list, as the causes are); a mail with a good token from an engineer the fleet
  holds: `CAUSE: <word>` wins, else exactly one cause named closes the fault's corrective work order with it (opening
  the order first when the fault has none), decided by that engineer, the mail linked as its evidence; none, several, a
  bad token or a stranger's address go to the review queue, and the engineer is mailed back asking which.
- **8.4 The cause in the windows and on the command line (`solarpunk/ui/`, `solarpunk/cli/`).** The asset window shows
  a closed order's cause with its mail; a review queue an operator resolves on the engineer's word (recorded as such);
  `solarpunk mail read` runs the reader once.
- **8.5 Tune-up pass 8.**

### Phase 9: the tests' record, at the root and per asset

Ghost's direction of 2026-11-18 (SP-016): the tests that run against the fleet are shown with what they have done, at
the root of the window and on each asset, the last 100 runs reviewable, an asset's history searchable and graphed; every
result kept. It adds to `docs/GOAL.md`'s SCADA analytics (2) and quality management (4: audit evidence).

- **9.1 The record's surface and the timing (`solarpunk/remote/`, `solarpunk/project/`).** Each test's run is timed and
  its duration stored beside its result (a `duration_ms` column a store made before gains, empty for its old rows);
  project gives `tests_overview` (each test: kinds, assets it runs on, last run, last duration, passes and failures),
  `test_log(name, limit=100)` (its newest runs across the fleet) and `asset_log(asset_id, limit=100, search=None)` (the
  asset's newest results, filtered by test, result and words in the reason). Nothing is deleted.
- **9.2 Last run in the asset window (`solarpunk/ui/asset_window.py`).** The diagnostics table gains each test's last-run
  instant (and duration); a test never run reads "never".
- **9.3 The Tests window (`solarpunk/ui/tests_window.py`).** "Tests" beside "Reports" in the fleet window: every remote
  test with its kinds, asset count, last run, duration and pass/fail counts; selecting one shows its last 100 runs
  (asset, instant, result, reason, duration), failures red.
- **9.4 The asset's history (`solarpunk/ui/history.py`).** From the asset window, "History": the asset's last 100 results
  in a table with a search box (test, result, words in the reason), and a timeline drawn on a canvas, one row per test,
  one mark per run, green a pass and red a failure, its time axis in UTC; the pure half headless, as `chart.py` is.
- **9.5 Tune-up pass 9.**

### Phase 10: the network's security

Ghost's item of 2026-11-18: the demonstration's network is not a production one. Moved after reports and
diagnostics by SP-013, after fault assignment by SP-015, after the tests' record by SP-016, and after email causes by SP-018.

- **10.1 Network security: an engineering pass over the feed and the receiver.** Both speak plain TCP with no device
  identity; the receiver defaults to localhost, which suits the demonstration alone. The pass is a document first
  (the wire today, the threats, a proposed decision for each of: authenticated asset connections, transport
  encryption, authorization of fault submissions, replay protection, network segmentation and deployment
  controls); the code follows the decisions Ghost puts in force. The 2026-11-18 advisor's research is its starting
  point: a module has no endpoint, an inverter, logger, meter, weather station or tracker controller does; the
  industry addresses a device by host, port, protocol, unit id and register map (Modbus TCP on 502 with SunSpec
  models at the device, DNP3 on 20000 or IEC 60870-5-104 on 2404 from the plant to the utility, OPC UA on 4840 to the
  historian); the security references are Modbus/TCP Security (mutual TLS on 802), IEC 62351, IEC 62443 zones and
  conduits, and NERC CIP-003 for a large US plant. It adds a sixth threat to the five: the feed client trusts whatever
  answers at the host and port (spoofed telemetry).
- **10.2 Tune-up pass 10.**
