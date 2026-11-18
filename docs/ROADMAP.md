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

What Ghost set on 2026-11-17, planned in full when Phase 1 closes:

- **The asset maintenance list (`docs/ASSET-MAINTENANCE-LIST.md`, `solarpunk/leaf/asset_types.json`).** One entry per
  asset type: what the asset is, the fields its feed answers with and the range each is supposed to fall in (an
  inverter answers `irradiance_w_m2`, `power_kw`, `temperature_c`; a tracker `angle_deg`; a meter `energy_kwh`,
  monotonic), the remote tests that can be run against it, and what a passing response is. The UI's type dropdown
  reads this list, the feed reader checks a response against it, and a remote test's `KINDS` names entries in it;
  `AssetKind` stays the id of an entry. A check holds the document and the JSON together (C-013).
- **The feed (`solarpunk/feed/`).** An asset is added by its IP address and port (`Asset.host`, `Asset.port`, in the
  leaf from 1.1); `ping(asset)` opens the endpoint and reads its data feed, one JSON line per sample in the leaf's
  `Sample` shape over plain TCP, and turns it into samples the telemetry table stores. A simulator
  (`python3 -m solarpunk.feed.simulate <asset> --port N --seed S`) serves the synthetic generator's output on a port,
  so the client, the remote tests and the UI are exercised here with no real inverter; a real asset's adapter is a
  later project's (§4).
- **Remote tests (`solarpunk/remote/`).** A remote test is a standalone module `solarpunk/remote/tests/<name>.py`
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
- **The mailer (`solarpunk/mailer/`).** On a new OUTAGE fault, a pushed error code or a failing remote test, one mail
  to the engineers `engineers_for` names, saying the asset, its location, the code or test and the instant, sent by
  `smtplib` from the standard library over the account's SMTP server (Outlook's own through Microsoft 365's SMTP, any
  SMTP host on Linux: one code path, SP-009); the server, port and sender live in a settings file the tests never
  read, and the tests use a local `smtpd`-style fake. A mail is also a row in a `mails` table, so what was sent and to
  whom is a query.
- **The clock (`solarpunk/schedule/`).** One `Job` (name, command, cadence) rendered to a crontab line on Linux and a
  `schtasks /Create` command on Windows, each against a golden; `install` and `remove` run the platform's tool and
  are the only functions that touch the host, so the tests never do; a Windows run is a by-hand Actions job (C-032).
  The scheduled job pings every asset with a feed, runs the whole remote-test suite (each test against every asset
  of its kinds), stores the results, stamps each asset's last status and the run's instant (`last_status`,
  `last_run_at` on the asset, shown on mouseover in Phase 3), and recomputes the site's KPIs. Open for Ghost: whether
  the job runs `python3 -m solarpunk.cli` or a frozen entry point.
- **The receiver (`solarpunk/receiver/`).** The one inbound surface: an asset pushes a line `<asset-id> <fault-code>`
  to the central server; the receiver refuses an unknown asset or code (SOL-04, SOL-05), assigns the fault in the
  ledger and sets the asset's status at once (SP-008), so degradation reaches the fleet view in real time, between
  scheduled runs.

### Phase 3: the native front end

A desktop UI on Windows and Linux, no browser and no web hook (Ghost, 2026-11-17): tkinter from the standard library
(P-17), `solarpunk/ui/`. The main screen is a scrollable list of every asset, each row a small solar-panel glyph
drawn on a canvas in the asset's `AssetStatus` colour (green passed the last scheduled run, yellow a remote test
failed on it, red an active OUTAGE fault) beside the asset's id and name; clicking a row opens the asset: its open
faults, the remote tests of its last run with the failing one named and its reason first, and a form to assign a
catalogue code or add a remote test. A second screen adds an asset: its id, its type from a dropdown read from the asset maintenance list, its IP address and port, and pings it.
Clicking an asset's icon opens its window, which also assigns its engineer: a dropdown of known engineer emails
plus a text field for a new one, and two buttons that read Save and Cancel; Save writes `assign_engineer`, Cancel
changes nothing. The UI calls project alone (its own MOD row when planned); every screen's data is a project call the tests exercise
headless, and the widgets are tested under a virtual display where the session has one, by hand on Windows where
it does not. Planned when Phase 2 closes.

### Phase 4: the work-order ledger

Corrective and preventive work orders (the CMMS half of the ghost): a work order opened from a fault or from a
`repeated` signal, its root-cause code from a closed list in the glossary, its closure closing the fault. Planned
when Phase 3 closes.
