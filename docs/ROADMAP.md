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

- A web front end, or anything a browser opens: the UI is native (tkinter) on Windows and Linux (Ghost, 2026-11-17).
  A REST service was here too until SP-022: a central server with an authenticated API is Phase 22, after the security
  pass (Phase 21; renumbered by SP-023, SP-024 and SP-044).
- A connection to a real SCADA, CMMS or revenue meter: telemetry is synthetic and deterministic; an adapter is a
  later project's. SP-029 puts vendor profiles on the roadmap (Phase 19), normalized and simulated; a real device
  connected stays a decision of its own.
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
- **7.7 Faults from telemetry (SP-046).** A failing test raises its fault itself, by its rule table's code or a
  generic one; a streak of failures is one fault; accept and dismiss are removed, and nothing changes a fault in place.
- **7.8 The root cause, written by an engineer (SP-046).** Blank until an engineer writes it as free text, kept as a new
  row with who and when; the closed list of SP-011 retired; a ticket closes only once the cause is written.
- **7.9 A ticket from a failed test (SP-046).** "Open a ticket" on a failed result, not the asset; a streak of
  failures shares one ticket, one ticket to many failed results.
- **7.10 Tune-up commit 7.**

### Phase 8: local tickets

Ghost's direction of 2026-11-18 (SP-021, SP-022): issues are tracked in Solarpunk's own ticket ledger, behind an adapter
interface so a tracker such as Jira is one adapter later. A ticket opens when an engineer assigns a fault, never from a
suggestion (the advisor's main defence against ticket spam, J-060). It adds to maintenance execution (3: priorities, SLA
tracking, assignment, closeout evidence).

- **8.1 The ticket contract (`docs/CONTRACT.md`, `solarpunk/leaf/`).** A ticket's statuses and the transitions between
  them, its priority from the fault's severity, the acknowledgement and response targets per priority (the timers a
  contractor can guarantee, SolarPower Europe's distinction) with a worked example of a breach, and which fields a
  remote tracker would own (the working assignee, comments) and which Solarpunk keeps (the code, who assigned, the
  root cause, the instants the KPIs read).
- **8.2 The ticket ledger (`solarpunk/workorders/`, `solarpunk/project/`).** A work order grows into a ticket: status,
  priority, working assignee, acknowledged and responded instants, comments, closeout evidence; assigning a fault opens
  its ticket; closing a ticket needs a root cause from the closed list and closes its fault (4.1); the KPIs unchanged.
- **8.3 Tune-up pass 8.**

### Phase 9: the fleet window as an operations root

Ghost's direction of 2026-11-19 (SP-023), from an advisor's review of the root window (2026-11-18): the fleet list shows
what colour each asset is, but not why, what waits on a person, or which store and run it shows. Most answers are in
the store already. Site KPIs at the root wait on a decision of their own (their period and baseline; a number beside
its counts and gaps), as do a "Run now" button (a worker thread and its own connection), grouping by site and parent
(with the question of `ttk.Treeview` over the drawn list), and over- and under-maintaining signals (schedules, not
built). It adds to operations visibility (1) and maintenance execution (3).

- **9.1 Headings and readable cells (`solarpunk/ui/app.py`).** Column headings; instants in UTC words; "no feed" for an
  asset with no endpoint beside "never run"; column widths from the text, so a long name does not overrun.
- **9.2 The cause column (`solarpunk/ui/app.py`, `solarpunk/project/surface.py`).** A red row names its open outage and
  since when, a yellow row its suggestion or failing test.
- **9.3 The attention band (`solarpunk/ui/app.py`, `solarpunk/project/`).** At most four counts above the list (open
  outages, suggestions awaiting an engineer, open work orders), each a filter; Phase 11 adds tickets past target.
- **9.4 Sort and filter (`solarpunk/ui/app.py`).** Worst first, a search box, status and kind boxes, keyboard
  shortcuts; the sorting and matching pure and tested headless.
- **9.5 The status bar (`solarpunk/ui/app.py`).** The store's name and the fleet's last run at the foot; Refresh to
  the toolbar; the window sized to its content.
- **9.6 Tune-up pass 9.**
- **9.7 The window's icon (SP-030).** The solar-panel glyph drawn as an image at runtime and set on every window.
- **9.8 Manage tests (SP-030).** A root button opening a window over the remote tests' folder: each script, a broken
  one with its reason, Open folder, New test (the scaffold), Reload; tests are Python scripts (SP-020).
- **9.9 Tune-up commit 9.** The reopened phase closed (three items, C-024).

### Phase 10: runs per asset

Ghost's direction of 2026-11-19 (SP-024): "a runs button. This is beside each asset, and when clicked brings up each run
associated with the asset, as well as a grouping of each run with a graph of each run grouping. For example, monitoring
asset power over time, or how many times each asset caused a specific error." Four groupings, chosen by Ghost: runs by
test, power over time, errors by code, and error counts across the fleet. It takes over the asset's history Phase 13
planned (its `asset_log` and its History window), so that is built once, here. It adds to SCADA analytics (2) and
quality management (4: a repeated cause seen before it is a pattern).

- **10.1 What a run and a count are (`docs/CONTRACT.md`).** A run of an asset (the results at one instant), an error
  count (faults and suggestions by code in a period, counted apart), a power series (samples and their named gaps),
  each with a worked example over the demo store.
- **10.2 The runs' surface (`solarpunk/project/`).** `asset_runs`, `asset_power`, `asset_code_counts`,
  `code_counts_by_asset`: one call per view, held to 10.1's examples; nothing deleted, the last 100 shown.
- **10.3 The Runs button and window (`solarpunk/ui/app.py`, `solarpunk/ui/runs_window.py`).** A "Runs" cell on each
  row of the fleet list; the window lists the asset's runs, failures red, a run's results on selection, a search box.
- **10.4 Runs by test.** A timeline, one row per test, one mark per run, green and red, UTC; the geometry pure.
- **10.5 Power over time.** The asset's power for a chosen day with `chart.py`, gaps drawn and counted, never joined.
- **10.6 Errors by code.** A bar per code for the asset over a period, faults and suggestions apart, counts written.
- **10.7 Error counts across the fleet.** From an "Errors" button beside Reports: one code, a bar per asset, worst
  first; a bar opens that asset's runs.
- **10.8 Tune-up pass 10.**

### Phase 11: tickets in the windows

The adapter and the windows of Ghost's local tickets (SP-022), moved from Phase 8 by SP-023 so they land in the
reworked fleet window.

- **11.1 The adapter and the local tracker.** A sink and source interface (create, update, comment, transition; changes
  since a cursor), an outbox written with the ledger change, the local adapter first, and a contract suite every adapter
  must pass. A new module is Ghost's to approve when the item starts (`docs/modules.json`).
- **11.2 Tickets in the windows and on the command line (`solarpunk/ui/`, `solarpunk/cli/`).** A Tickets window from the
  fleet window, ordered by the nearest target; the asset window's ticket with acknowledge, comment and resolve;
  `solarpunk ticket list|ack|comment|resolve`.
- **11.3 Tune-up pass 11.**

### Phase 12: accounts and authentication

Ghost's direction of 2026-11-18 (SP-022): every act is attributed to a signed-in account, so SP-015's "who" is
authenticated rather than chosen from a dropdown. On one machine first; the network is Phase 22.

- **12.1 Accounts (`docs/CONTRACT.md`, a module Ghost approves at the item's start).** Users with an email, a name, a
  role (engineer, operator, viewer, admin) and an active flag; passwords hashed with `hashlib.scrypt`, salted, never
  stored, logged or shown; an engineer address the fleet names with no account is flagged. Widened by SP-026: a viewer
  reads and acts on nothing; each account sees and acts on its own sites, or all; and an asset, a fault, a suggestion
  and a ticket carry a version (12.2). Built on one machine first, so the central server (Phase 22) inherits the rules
  rather than adding them. The module `accounts` imports the leaf alone (SP-028).
- **12.2 Versions (`solarpunk/fleet/`, `solarpunk/faults/`, `solarpunk/remote/`, `solarpunk/workorders/`; SP-028).** An
  asset, a fault, a suggestion and a ticket each carry a version in its own module's table, raised in the same write as
  the change; a write read at an older version is refused, so a stale screen never overwrites another person's change.
- **12.3 Signing in (`solarpunk/ui/`, `solarpunk/cli/`).** The windows open on a sign-in; the command line asks with
  `getpass`; a failed sign-in is recorded, never its password.
- **12.4 Attribution from the account (`solarpunk/project/`).** Assigning, accepting, dismissing and every ticket action
  take the signed-in account: an engineer acts as themself, an operator enters on a named engineer's word (recorded as
  such), an admin assigns nothing unless also an engineer; the "Assigned by" dropdown gives way to the account.
- **12.5 Account administration.** Create, reset a password, deactivate (never delete: records keep their names); the
  first admin made by a command on the machine.
- **12.6 A false-alarm baseline on public field data (`solarpunk/telemetry/`, `docs/FIELD-DATA.md`; SP-036).** Real
  5-minute telemetry from public PV systems (NREL PVDAQ, CC BY 4.0) is loaded from a local copy outside the repository
  (C-033), and every remote test that applies is run over it a day at a time, so how often each check fires on working
  plant is known and each alarm is explained: a real event, a data artefact or a threshold to change. No public dataset
  reachable from a session records its failures (J-099), so catching known failures is 12.7's. What is learned shapes
  the synthetic fixtures and the thresholds; the data itself never enters the repository.
- **12.7 Known failures caught, on labelled field data (waiting).** A dataset that labels its failures with their times;
  each one caught, or its miss explained. Waits on such a dataset and on a rule for readings finer than five minutes.
- **12.8 Tune-up pass 12.**
- **12.9 No data is not a pass (`solarpunk/remote/`, `solarpunk/project/`, `solarpunk/ui/`; SP-039).** Reopened Phase 12, on
  Ghost's word: a test with nothing to check is a disconnection, an error, said once by `reachable`; the others return a
  third result, "no data", grey and never a pass.
- **12.10 The field thresholds (`solarpunk/leaf/asset_types.json`, `solarpunk/remote/tests/`, `solarpunk/telemetry/`;
  SP-039).** The irradiance minimum -5 W/m2, an inverter's power minimum -2% of its rating, 1% over the rating allowed,
  inverter N's irradiance from pad N's station; the baseline re-run.
- **12.11 Four loose ends of accounts and tickets (`solarpunk/project/`, `solarpunk/cli/`; SP-039).** Deactivating twice
  refused, the password asked last, `ticket show`, the operator named on a dismissal.
- **12.12 Tune-up commit 12.** The reopened phase closed (three items, C-024).

### Phase 13: the tests' record, at the root and per asset

Ghost's directions of 2026-11-18 (SP-016, SP-019): what a test is and the suites it runs in, then the tests that run against the fleet are shown with what they have done, at
the root of the window and on each asset, the last 100 runs reviewable, an asset's history searchable and graphed; every
result kept. It adds to `docs/GOAL.md`'s SCADA analytics (2) and quality management (4: audit evidence).

- **13.1 What a test looks like (`docs/REMOTE-TESTS.md`, `scripts/checks/remote_tests.py`; SP-019).** The contract of a remote
  test: its module's fields (`KINDS`, `CLAUSES`, `SUGGESTS`, `run`), that `run` reads only the asset and samples it is
  given (no store, no network, no clock), the shape of its reason (the first offending record, or a count), its
  thresholds as named constants with why, its docstring's pass and fail cases, its line in the maintenance list; a check
  holds every module in the folder to it, with a planted break.
- **13.2 The suites folder (`solarpunk/remote/suites/`, `solarpunk/remote/`, `solarpunk/project/`, `solarpunk/cli/`; SP-019,
  SP-020).** A suite is a Python module of declarations (`TESTS`, `KINDS`, `SITES`, `CADENCE`), no logic; the scheduled
  run runs the suites due; `solarpunk suite list|run|add`; the default suite `all` is today's run.
- **13.3 A test's own reads (`solarpunk/feed/`, `solarpunk/remote/`; SP-020).** A test may declare `ACQUIRE`, such as
  `Burst(field="power_kw", every_s=1, for_s=60)`; the feed and its simulator gain a live-read mode, the runner takes
  the reads and hands them to the test's pure `run`; a test without `ACQUIRE` judges the stored samples as today.
- **13.4 Reactions (`solarpunk/remote/`, `solarpunk/project/`; SP-020).** A test's `REACTIONS` per kind from a closed
  vocabulary (raise a fault, SP-049; mail, run a follow-up suite, open a preventive work order), replacing `SUGGESTS`; checked at
  load, no unknown action or suite, no suite that starts itself; `solarpunk test list` prints them; nothing commands
  equipment.
- **13.5 The record's surface and the timing (`solarpunk/remote/`, `solarpunk/project/`).** Each test's run is timed and
  its duration stored beside its result (a `duration_ms` column a store made before gains, empty for its old rows);
  project gives `tests_overview` (each test: kinds, assets it runs on, last run, last duration, passes and failures),
  and `test_log(name, limit=100)` (its newest runs across the fleet); an asset's own runs are Phase 10's `asset_runs`
  (SP-024). Nothing is deleted.
- **13.6 Last run in the asset window (`solarpunk/ui/asset_window.py`).** The diagnostics table gains each test's last-run
  instant (and duration); a test never run reads "never".
- **13.7 The Tests window (`solarpunk/ui/record_window.py`; `tests_window.py` is 9.8's Manage tests window).** "Tests" beside "Reports" in the fleet window: every remote
  test with its kinds, asset count, last run, duration and pass/fail counts; selecting one shows its last 100 runs
  (asset, instant, result, reason, duration), failures red.
- **13.8 Names of three characters or more (`scripts/checks/names.py`; SP-042).** Ghost's human maintainability pass,
  placed last in the phase so it covers what 13.1 to 13.7 add: every binding of two characters or fewer renamed to
  what it holds, in the product, the scripts and the tests, and a check that keeps it so.
- **13.9 Names and purpose comments reviewed (SP-042).** Each module read for names that do not say what they hold and
  docstrings that restate the code; renamed or rewritten, results unchanged.
- **13.10 A README for people in each module (`solarpunk/README.md`, `scripts/checks/readmes.py`; SP-042).** A map of
  the modules for a person new to the code, and each folder's files said in plain words, held by a check.
- **13.11 The decision map (`scripts/decision_map.py`, `docs/DECISION-MAP.md`; SP-042).** Each decision with the
  functions that cite it; an in-force decision that shapes code and is cited by none, or a citation of nothing, fails.
- **13.12 Phase 7's loose ends (SP-047).** A failed `reachable` raises the generic SIT-004 where its table named an
  outage, since a lost link is not a dead inverter; `solarpunk test results` lists result ids for `ticket open
  --result`; the code 7.7 left unused removed.
- **13.13 Bursts in the demo and on request (SP-049).** The demo takes shortened bursts, so `power_ripple` shows a
  verdict; the command line takes them with `--acquire`; the 5 % threshold Ghost's.
- **13.14 The demo on a throwaway store (SP-052).** `--demo` builds its store in a temporary folder outside the
  repository, prints its path, deletes it on exit; `demo.db` leaves git.
- **13.15 The demo's people, day and outage (SP-053).** Accounts in the demo store, so every act names a person; acts
  stamped on the demo's day; OAHE-INV-002 at zero output during its outage; a result's ticket clock from the failure.
- **13.16 A dead feed brought back, and the tests re-run (SP-053).** A dead port per run, a demo-only control that
  revives an asset's feed and re-runs its tests, every test visible in the asset window.
- **13.17 The closed trail read back (SP-053).** One project call for a ticket's whole trail, shown by `ticket show`
  and the Tickets window; closed tickets listed; the Tests window shows clauses.
- **13.18 Output under the floor, its own fault (SP-054).** INV-005, an inverter derate, for a performance ratio under
  the floor, so a lost link keeps SIT-004.
- **13.19 Cheaper password hashing in the tests (SP-054).** A low scrypt cost in the tests alone, the product's held by
  a test, so the fast loop is under 30 s with every test in it.
- **13.20 The ISO walk, scripted and dry-run (SP-052, SP-053).** DEMO.md walks 55000-9.1 from requirement to evidence
  to corrective action, the register's sentence fixed, and a fresh dry run finds nothing missing.
- **13.21 Tune-up pass 13.** (The asset's history, 13.8 before SP-024, is Phase 10.)

### Phase 14: the traceability matrix

Ghost's direction of 2026-11-21 (SP-044): the ISO 9001 and ISO 55000 evidence matrix, each clause traced to its
requirement in our words, the product's control and the records that evidence it per site and period, gaps shown; it
claims conformance to nothing (SOL-12), and no real organisation's records enter the repository (C-033).

- **14.1 The register's control column.** Each register row names the product's control and where its evidence is
  stored, and every clause a remote test cites is a row.
- **14.2 Evidence that cannot be deleted.** The evidence tables are append-only and each row is chained to the one
  before by hash, so a deleted or changed record is found.
- **14.3 Clause links for faults, work orders and KPIs.** One declared table in the leaf says which clauses each fault
  code and KPI evidences (root causes are free text, SP-046).
- **14.4 The evidence query.** For a clause, a site and a period, every record that evidences it and every asset with
  none, from a worked example first.
- **14.5 Historical import (SP-048).** Years of readings load from a documented CSV into a store of their own, never
  into the repository; the simulator writes a multi-year file for the tests.
- **14.6 The historical run (SP-048).** The tests replay over a historical period day by day, resumable; failures raise
  faults marked historical; no ticket, mail or streak; a test that takes its own reads is "not replayable".
- **14.7 The replay's speed (SP-048).** Years of simulated history timed before any limit is proposed to Ghost.
- **14.8 The matrix command and export.** One command prints the matrix for a site and period, over a live or a
  historical store, and writes it to a file the operator names.
- **14.9 The matrix window.** A Matrix button at the fleet window's root opens the matrix, and a clause opens its
  evidence and its gaps.
- **14.10 Tune-up pass 14.**

### Phase 15: quality management

Ghost's direction of 2026-11-20 (SP-029), `docs/GOAL.md` area 4.

- **15.1 Inspection checklists and evidence.** A checklist per kind and work type carried by a ticket, each step
  answered by who and when, evidence kept and never edited; resolving needs every step answered.
- **15.2 CAPA effectiveness verification.** A closed corrective ticket verified after a period by whether its cause
  recurred, effective or reopened as a nonconformity.
- **15.3 Document control.** A register of controlled documents, versioned, approved, reviewed, a superseded version kept.
- **15.4 Tune-up pass 15.**

### Phase 16: condition and maintenance planning

Ghost's direction of 2026-11-20 (SP-029): the gaps `docs/GOAL.md` names in areas 1 and 3, put on the roadmap.

- **16.1 Asset condition baselines.** What normal is for each asset and measure, learnt from its stored samples, a
  reading shown beside its baseline with the gap and the counts that explain it; a contract section first.
- **16.2 Preventive maintenance scheduling.** A schedule per asset kind in the maintenance list; the scheduled run opens
  a preventive work order when one falls due, once; what is due and overdue as a query.
- **16.3 Condition-based maintenance.** A reading past its baseline by a margin for a time opens (or suggests) preventive
  work; the over- and under-maintaining counts of `docs/GOAL.md` as a query.
- **16.4 Tune-up pass 16.**

### Phase 17: anomaly detection and alarm correlation

Ghost's direction of 2026-11-20 (SP-029), `docs/GOAL.md` area 2. Deterministic methods with worked examples; no model
client (MOD-03) without a decision.

- **17.1 Anomaly detection.** A reading unlike the asset's own baseline or its same-kind neighbours, flagged as a
  suggestion (SP-015) with its reason.
- **17.2 Alarm correlation.** Alarms within a window on one parent chain grouped, the highest alarming asset named the
  likely root; a reading recomputed when asked.
- **17.3 Tune-up pass 17.**

### Phase 18: contractor performance management

Ghost's direction of 2026-11-20 (SP-029), `docs/GOAL.md` area 5.

- **18.1 Contractors and their scorecard.** A contractor on a ticket; its targets met and late, its fixes that held, its
  backlog, each beside its counts; a window and a report command.
- **18.2 Tune-up pass 18.**

### Phase 19: multiple inverter vendors

Ghost's direction of 2026-11-20 (SP-029), after the network's security rules how a device is reached.

- **19.1 Vendor profiles.** Each maker's register map, units and fault words in a declared profile, normalized to the
  leaf's sample by the feed; the simulator serves two makers; whether a real device is connected is a decision of its own.
- **19.2 Tune-up pass 19.**

### Phase 20: Azure

Ghost's direction of 2026-11-20 (SP-037): Solarpunk runs in Azure. What configuration and the standard library can do
comes here; what needs a dependency is decided where it belongs: sign-in with Entra ID is 21.1's option already; a
managed database (Azure SQL or PostgreSQL) for the central store is Phase 22's; reading telemetry from Azure IoT Hub or
Event Hubs is Phase 19's feed. The desktop windows stay on the engineers' machines.

- **20.1 The Azure deployment guide (`docs/AZURE.md`).** Today's Solarpunk on an Azure VM with no code changed: cron or
  Task Scheduler from the one job, the store on a managed disk, a VPN or ExpressRoute to the plant network, the network
  security group opening the receiver's port to named sources, email through Azure Communication Services' SMTP
  endpoint; each Azure claim linked and dated.
- **20.2 Secrets from Key Vault by managed identity (`solarpunk/mailer/`).** The SMTP credential fetched at send time,
  `urllib` alone, never written anywhere.
- **20.3 Reports and exports to Blob Storage.** The report and the baseline's output put to a container as well as a
  file.
- **20.4 Health and alarms to Azure Monitor.** A health record per scheduled run and a record per failing test through
  the Logs Ingestion API; the alert rule for a run that stops reporting.
- **20.5 Tune-up pass 20.**

### Phase 21: the network's security

Ghost's item of 2026-11-18: the demonstration's network is not a production one. Moved after reports and
diagnostics by SP-013, after fault assignment by SP-015, after the tests' record by SP-016, and after email causes by SP-018.

- **21.1 Network security: an engineering pass over the feed and the receiver.** Both speak plain TCP with no device
  identity; the receiver defaults to localhost, which suits the demonstration alone. The pass is a document first
  (the wire today, the threats, a proposed decision for each of: authenticated asset connections, transport
  encryption, authorization of fault submissions, replay protection, network segmentation and deployment
  controls); the code follows the decisions Ghost puts in force. The 2026-11-18 advisor's research is its starting
  point: a module has no endpoint, an inverter, logger, meter, weather station or tracker controller does; the
  industry addresses a device by host, port, protocol, unit id and register map (Modbus TCP on 502 with SunSpec
  models at the device, DNP3 on 20000 or IEC 60870-5-104 on 2404 from the plant to the utility, OPC UA on 4840 to the
  historian); the security references are Modbus/TCP Security (mutual TLS on 802), IEC 62351, IEC 62443 zones and
  conduits, and NERC CIP-003 for a large US plant. It adds a sixth threat to the five: the feed client trusts whatever
  answers at the host and port (spoofed telemetry). Since SP-022 it also designs the central server of Phase 22: its
  authenticated API, accounts and tokens on the wire, TLS, and whether the server may use a vetted dependency.
- **21.2 Company sign-in (SP-029).** Enterprise authentication: a proposed decision in the pass (OpenID Connect against
  Entra ID or Google, or none; a dependency, Ghost's approval); if put in force, an account of 12.1 linked to an outside
  identity by its email, the Solarpunk password kept for a machine with none.
- **21.3 Tune-up pass 21.**

### Phase 22: the network

Ghost's direction of 2026-11-18 (SP-022): one Solarpunk server holds the store; the desktop windows on many machines,
and later a phone app, are its clients over one authenticated API. Planned from Phase 21's decisions, so its items are
written when they are in force.

- **22.1 The server's plan.** The items that build the server, its API, the desktop as its client and the app's surface,
  each with its check, written from Phase 21's decisions.
- **22.2 Tune-up pass 22.**
