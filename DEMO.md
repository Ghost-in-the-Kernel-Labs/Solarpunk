# The Solarpunk demo

One command builds a small solar site in a file, runs its remote tests once, and opens the fleet window with green,
yellow and red rows. Everything below is plain Python from python.org: nothing to install for the product itself.

## Run it on Windows

Install CPython 3.12 from python.org first, with "tcl/tk and IDLE" ticked (it is ticked by default). Then, in a
Command Prompt or PowerShell:

    git clone https://github.com/Ghost-in-the-Kernel-Labs/Solarpunk
    cd Solarpunk
    py -3.12 -m venv .venv
    .venv\Scripts\pip install --only-binary :all: --require-hashes -r requirements.lock
    .venv\Scripts\python -m solarpunk.ui --demo

The `pip install` brings in the tools only (pytest, ruff, mutmut); the product needs none of them, so the plain
`py -m solarpunk.ui --demo` from the `Solarpunk` folder works without the venv too.

## One word: `solarpunk`

The folder holds `solarpunk.cmd`, so in the `Solarpunk` folder (the one that holds `README.md`):

    solarpunk --demo                              the demo
    solarpunk                                     the window on solarpunk.db in this folder, made if missing
    solarpunk --help                              every command, one line each
    solarpunk test list                           the remote tests, each with its asset kinds and clauses
    solarpunk test run --db demo.db               every remote test over every asset of that store, once, now
    solarpunk test add tracker_moving --clause 55000-9.1

`test add` writes `solarpunk\remote\tests\tracker_moving.py`, taking the test's asset kinds from the asset maintenance
list (`--kind TRACKER` names them by hand); the new test fails on every run until its `run` function is written, so
its assets turn yellow until then. To type `solarpunk` from any folder, add the `Solarpunk` folder to PATH (Settings,
"Edit environment variables for your account", Path, New); the store stays in the folder you typed it in. After the
demo window is closed its simulator is gone, so `solarpunk test run --db demo.db` shows OAHE-INV-001's feed as
unreachable: the feeds must be answering for a green run.

## What appears

The terminal prints one line per step:

    demo: simulator on 127.0.0.1:<a free port>
    demo: store demo.db rebuilt
    demo: run - 9 green, 1 yellow, 1 red

`demo.db` is made in the folder you ran from, removed and rebuilt every run. The window, titled "Solarpunk fleet —
demo (OAHE, 2026-06-01)", lists the eleven assets of the Oahe site near Pierre:

- **OAHE-INV-001 green**: a feed simulator inside the demo serves its day of telemetry; every remote test passed, `power_ripple` among them, judged on five quick reads the run took from the simulator.
- **OAHE-INV-002 red**: an open INV-001 outage (inverter offline) since 11:30, and its feed does not answer.
- **OAHE-SEN-001 yellow**: the irradiance sensor's feed does not answer, so its `reachable` test failed; its other
  two tests had nothing to check and read "no data", grey, never a pass (SP-039).
- The site, the strings, the trackers and the meter are green: they have no feed configured, so the suite leaves
  them alone and only their faults decide their colour.

The ledger also holds two closed faults: a grid curtailment on the site (12:00 to 13:00) and an over-temperature
derate on OAHE-INV-001 (10:00 to 10:45). The run is stamped 2026-06-01 13:00 UTC.

## What to click, in order

1. **Read the band above the list.** "Open outages: 1", "Open work orders: 1": what waits
   on a person. Click one and the list keeps only its assets (the outage: OAHE-INV-002); click it again for all eleven.
   The status bar at the foot names the store and its last run ("demo.db, last run 2026-06-01 13:00 UTC").
2. **Read the headings, then mouse over a row.** Each column is named (Asset, Name, Kind, Status, Cause, Last run, Failing),
   and the Cause says why a row is its colour: OAHE-INV-002 "INV-001 since 2026-06-01 11:30 UTC", OAHE-SEN-001
   "reachable" (its failing test);
   the tooltip gives the last status and the run's instant ("Last status: yellow at 2026-06-01 13:00 UTC"); a string,
   a tracker or the meter, having no endpoint the run can reach, reads "no feed", where an asset with one not yet run
   would read "never run". Click the Status heading to put the worst first (a second click turns it round); type
   in the search box (Ctrl+F) or pick a status or a kind to narrow the list, Esc to clear; Up and Down move the
   selection and Enter opens it; F5 rereads the store.
3. **Click OAHE-INV-002.** The asset window shows the open INV-001 outage with its meaning, and its diagnostics with
   `reachable` failing first, in red, with its reason.
   Its **Runs** link (the blue word at the row's end) opens its runs instead: one run at 13:00 UTC, "8 results",
   "1 failed", in red; below it the run's results, the ping's failed `reachable` first ("127.0.0.1:9 is unreachable"),
   then the seven that passed, the test's own `reachable` among them. Type "fail" or a test's name to narrow the list.
   Its **By test** tab draws the runs as a timeline: a row per test, a green, red or grey (no data) mark per run,
   the hours in UTC.
   OAHE-INV-001's **Power** tab draws its day: "288 samples: records 279, gaps 9; peak 94.35 kW", the line broken at
   each gap (10:40, 13:25, 17:35, 17:50), never drawn down to zero. The **Errors** tab counts an asset's faults (red)
   and suggestions (amber) by code over the days chosen: OAHE-SEN-001 "SEN-001: 1 fault, 0 suggestions".
4. **Close it, click OAHE-INV-001, and assign a fault.** Its seven diagnostics all pass, fed by the simulator (`power_ripple` on five quick reads). Pick
   INV-004 (firmware update pending, INFO) and press Assign without an engineer: it is refused, since only an engineer
   assigns a fault (SP-015). Choose inverter@oahe.example under "Assigned by" (and an operator under "Entered by" if it
   was called in) and press Assign: the fleet window stays green, since an INFO fault is not an outage. Then assign
   INV-001: the fleet row turns red at once (the asset window refreshes the fleet window; Refresh does the same by
   hand). OAHE-INV-002's open outage shows who assigned it: inverter@oahe.example, entered by the operator, marked
   cover, since that engineer is not INV-002's own.
5. **A fault a test raises (SP-046).** Close it and click OAHE-SEN-001, the yellow weather station. Its `reachable` failed,
   first and in red; `irradiance_in_range` and `on_grid` read "no data" in grey, since with no record there was
   nothing to check, which is never a pass (SP-039), and so raise nothing. The failure's rule raises SEN-001 (readings
   unreliable) itself, under "Open faults", assigned by `test:reachable`: nobody accepts or dismisses it, and a later
   failure of the same test joins it. Where a test's rule names no code the fault is SIT-004, "Remote test failed: its
   cause is not yet known": so OAHE-INV-002's lost link raises SIT-004 beside its INV-001 (SP-047: a lost link is not a dead inverter). A store made before 7.7 lists its suggestions under "Earlier suggestions", read only.
6. **The engineer.** In the same window type an address into Engineer and press Save, or Cancel to leave it. If
   someone changed the asset since the window drew it, the save is refused ("changed by someone else since you read
   it; refresh") and **Refresh** beside the message redraws it; the ticket panel has its own.
7. **Add asset** (the button above the list). The Type dropdown is read from the asset maintenance list. Fill an
   id such as OAHE-INV-005, a parent, the IP address 127.0.0.1 and a port, press Save: the new row appears in the
   fleet window. Then press **Ping**: with nothing listening on that port it says so, plainly. **Manage tests**
   (beside it) lists every test script with its kinds, clauses and the codes a failure suggests; a script that cannot
   load is listed in red with its reason. **Open folder** shows the scripts, **New test** writes one to fill in, and
   **Reload** finds a script dropped into the folder.
8. **Reports** (beside Manage tests). The power-output report for OAHE over the demo day: the site's row first (1591.6 kWh,
   peak 187.2 kW, 7.96 kWh per kW of rating, capacity factor 0.33), then each inverter's, each with its records and
   gaps, and the site's power curve over the day in UTC. The line breaks where an inverter has a gap, never dropping to
   the other's share. **Save as CSV** writes the same file as `solarpunk report OAHE <start> <end> --csv`. Swap the
   start and end and press Show: the refusal is shown in red.

   **Errors** (beside Reports) counts one code across the fleet: INV-001 over the demo day is one row, OAHE-INV-002 with
   "1 fault" and "0 suggestions", worst first; a click on a row opens that asset's Runs window.
   **Tickets** (beside Errors) lists the open tickets, the nearest target first: OAHE-INV-002's, opened 11:30, in red,
   its acknowledgement "OVERDUE, due 2026-06-01 12:30 UTC" (the demo's run is at 13:00; on a later clock the response
   is overdue too). A double click opens the asset window, whose **Ticket** panel acknowledges, comments (By an
   engineer) and resolves (what was done and a root cause), which closes the fault.

   **Tests** (beside Tickets) opens the Tests window: one row per remote test with its kinds, the count of assets it ran
   on, its last run and duration, passes, failures and no data. Select `reachable`: its log lists its newest runs, the
   failures (OAHE-SEN-001, and OAHE-INV-002's unreachable feed) in red, a duration "—" where none was timed.
## The five-minute talk track

2. **Line of sight (ISO 55000).** The site's purpose is energy delivered; that becomes a KPI contract
   (availability, performance ratio, energy yield, MTBF and MTTR, `docs/CONTRACT.md`); the code that computes each
   number cites the clause it serves; a test flags any break; the clause register shows the coverage.
3. **The closed catalogue and the ledger (ISO 9001 §8.7 and §10.2).** A fault can only be a code from the
   catalogue, on an asset the fleet holds; the ledger records when it opened and closed. Nonconforming output is
   named, controlled and corrected, never a free-text note.
4. **The blind mirror.** The first four KPIs (SOL-07 to SOL-10) are reimplemented from the contract text alone by an
   agent that never saw the code, and a test compares the two. Every number, power output included (SOL-13), has a
   worked example in the contract a person can check by hand, held as a golden.
5. **Show the clause report live:**

       python -I scripts\clauses.py

   Each ISO 9001 and ISO 55000 clause the project holds, the test that holds it, and held, failing or open.
6. **Reports and diagnostics (click Reports, then an inverter).** The power-output report is recomputed from the
   stored telemetry every time, never kept: energy, peak, kWh per kW of rating, capacity factor, each beside its gaps.
   The curve breaks where an inverter missed a reading rather than drawing it as lost output. The asset window lists
   every remote test for the asset's kind: seven on an inverter, among them a daylight performance floor (the signal
   that says a crew is worth sending, not a calendar) and a frozen-reading check (a logger replaying its last value).
   Adding a test is adding one file: `solarpunk test add <name> --clause <id>`.
7. **The tests are the audit.** Every product line is mutation-tested nightly; each survivor is killed or explained in
   `docs/MUTATION.md`. Every decision has a number, a reason and the test that holds it (`theGhost.md`).
8. **What is next, decided today.** Tests raise their faults themselves, by their rules, the record saying which test (SP-046; an
   engineer still assigns one by hand, the record saying which engineer and which operator entered it, SP-015); a Tests window at the root and each asset's
   last 100 results, searchable and graphed, every result kept as evidence (SP-016); then the network's security, from
   plain TCP towards what the industry uses (Modbus TCP with SunSpec at the device, mutual TLS, IEC 62443 zones).

## If something goes wrong

- **"No module named 'solarpunk'"**: the command was typed outside the clone, or the clone's `solarpunk` folder has
  become `Solarpunk` (Windows treats the two names as one; Python does not), which happens when the repository is
  cloned inside a folder already named `Solarpunk` and then moved up. Clone again straight onto the Desktop.
- **"No module named tkinter"**: reinstall CPython 3.12 from python.org with "tcl/tk and IDLE" ticked.
- **A port is busy**: run it again; the simulator picks a free port each time.
- **"demo.db" cannot be removed**: a demo window from an earlier run is still open; close it and run again.
- **The window is blank**: click Refresh.
- **The run takes a few seconds**: Windows waits a moment on each refused connection (two feeds do not answer).
