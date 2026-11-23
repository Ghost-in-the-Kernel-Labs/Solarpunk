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
    solarpunk test run --db <the demo's store path>   every remote test over every asset of that store, once, now
    solarpunk test add tracker_moving --clause 55000-9.1

`test add` writes `solarpunk\remote\tests\tracker_moving.py`, taking the test's asset kinds from the asset maintenance
list (`--kind TRACKER` names them by hand); the new test fails on every run until its `run` function is written, so
its assets turn yellow until then. To type `solarpunk` from any folder, add the `Solarpunk` folder to PATH (Settings,
"Edit environment variables for your account", Path, New); the store stays in the folder you typed it in. After the
demo window is closed its simulator is gone, so `solarpunk test run --db` on the demo's store shows OAHE-INV-001's feed as
unreachable: the feeds must be answering for a green run.

## What appears

The terminal prints one line per step:

    demo: simulator on 127.0.0.1:<a free port>
    demo: dead feeds on 127.0.0.1:<a free port>
    demo: store <the full path of the store> rebuilt
    demo: run - 9 green, 1 yellow, 1 red
    demo: account engineer@oahe.example password oahe-demo-engineer
    demo: account operator@oahe.example password oahe-demo-operator

The store is made in a new temporary folder, rebuilt every run and removed when the window closes; the store line is its
full path, which a second terminal passes to `--db`. The window is signed in as the engineer without asking and stamps
its acts on the demo's day (2026-06-01, 13:00 UTC plus the seconds since the demo started); a second terminal signs in
with `--as` and the password the account line printed. The window, titled "Solarpunk fleet —
demo (OAHE, 2026-06-01)", lists the eleven assets of the Oahe site near Pierre:

- **OAHE-INV-001 green**: a feed simulator inside the demo serves its day of telemetry; every remote test passed, `power_ripple` among them, judged on five quick reads the run took from the simulator.
- **OAHE-INV-002 red**: an open INV-001 outage (inverter offline) since 11:30 with no output from then, and its feed does not answer.
- **OAHE-SEN-001 yellow**: the irradiance sensor's feed does not answer, so its `reachable` test failed; its other
  two tests had nothing to check and read "no data", grey, never a pass (SP-039).
- The site, the strings, the trackers and the meter are green: they have no feed configured, so the suite leaves
  them alone and only their faults decide their colour.

The ledger also holds two closed faults: a grid curtailment on the site (12:00 to 13:00) and an over-temperature
derate on OAHE-INV-001 (10:05 to 10:45). The run is stamped 2026-06-01 13:00 UTC.

## The ISO walk: one requirement to its evidence and its fix

For a sceptical quality auditor: take ISO 55000 clause 9.1 (monitoring) through the test `reachable` on OAHE-INV-002, from the
requirement to the evidence of its failure, the corrective action under ISO 9001 clause 10.2.1, and the proof that it held.
Everything is clicked in the window (the audience watches it); the command-line equivalent for a second terminal stands
beside each step. In the second terminal `DB` is the store path the demo printed, and every acting command asks, hidden,
for the password the demo printed:

    python -m solarpunk.cli --db DB <command> --as engineer@oahe.example      (Windows: py -3.12 -m solarpunk.cli ...)

`--db` goes before the command here (the one word `solarpunk` sends a leading `--db` to the window). The window stamps its
acts on the demo's day; the terminal stamps the real clock unless given `--at`, so each terminal act below carries an `--at`
on the demo's day, each later than the one before (a ticket cannot move before its last move).

**1. The requirement.** *Say:* "Clause 9.1 asks that the asset's performance is monitored and the results kept. Here is the
clause, and the tests that are its evidence." *Click:* **Tests** in the fleet window; read the **Clauses** column:
`reachable` and `performance_above_floor` read `55000-9.1`. *Terminal:* `python -m solarpunk.cli clauses` prints
`55000-9.1    held     <the register's sentence>`, and `test list` the clause beside each test.

**2. The evidence.** *Say:* "Its feed stopped answering; the run at 13:00 recorded it, with time and reason." *Click:* the red
row OAHE-INV-002, then in its window the Diagnostics list: `reachable` **FAIL**, red, "2026-06-01 13:00 UTC", reason
"127.0.0.1:<the dead port> is unreachable" (its duration reads "—": a refused connection has no timed read). Beside it
`performance_above_floor` is red too: "ratio 0.6148 under the floor 0.75 over 71 daylight records". Its **Runs** link shows the
run: "9 results", "2 failed". *Terminal:* `test results --asset OAHE-INV-002 --failed` prints, among others,
`1  2026-06-01T13:00:00+00:00  reachable  fail  127.0.0.1:<port> is unreachable`.

**3. The nonconformity.** *Say:* "The failure raised its own fault, naming the test that found it, with no person in
between; nothing is a free-text note." *See:* in the window's **Open faults**: INV-001 (11:30, the outage an engineer
assigned), INV-005 "test:performance_above_floor" and SIT-004 "test:reachable", each with its root cause "not written". Say
plainly: INV-005's low ratio is the lost output of the INV-001 outage since 11:30, which the test measured truthfully, so it
is evidence and not noise; SIT-004 ("remote test failed: its cause is not yet known") is the fault this walk corrects.
*Terminal:* `fault list --open` prints `5 OAHE-INV-002 SIT-004 2026-06-01T13:00:00+00:00 open by test:reachable`.

**4. Corrective action.** *Say:* "A person owns it: a ticket on the failed result, acknowledged, commented, and it cannot
close without a root cause." *Click:* in the Diagnostics select the red `reachable` row and press **Open a ticket**; the
line at the foot says "Ticket 4 opened on the failed result: 1 failed result in it". *Terminal (the same):*
`ticket open --result 1 --as engineer@oahe.example --at 2026-06-01T13:30:00+00:00` prints
`4 opened on result 1 (1 failed results: 1)`.

The window's **Ticket** panel acts on the asset's nearest ticket, which is OAHE-INV-002's overdue INV-001 ticket (3), not the
one just opened, so the next acts on ticket 4 are made in the terminal:

    ... ticket ack 4 --as engineer@oahe.example --at 2026-06-01T13:35:00+00:00        4 acknowledged
    ... ticket comment 4 "Feed down since 11:30; datalogger link being traced." --as engineer@oahe.example --at 2026-06-01T13:40:00+00:00
                                                                                     4 comment 1 by engineer@oahe.example
    ... ticket resolve 4 --done "Reseated the uplink cable" --as engineer@oahe.example --at 2026-06-01T13:45:00+00:00
    error: fault 5 has no root cause written: an engineer writes it before its ticket closes

*Say:* "ISO 9001 10.2.1: no closure without the root cause. The refusal is the control." (The window's Resolve button
refuses the same way: on ticket 3 it reads "fault 3 has no root cause written: ...", and writes nothing.) *Click:* in the
asset window's Open faults select the SIT-004 row, type in **Root cause of the selected fault** "Datalogger uplink cable
unplugged during the 11:30 inverter outage" and press **Write**: the row's cause column now holds the words. *Terminal:*
`fault cause 5 "<the words>" --as engineer@oahe.example` does the same but takes no `--at` and stamps the real clock, so
write the cause in the window. Then the same resolve prints `4 closed`.

**5. Closing the loop.** *Say:* "The corrective action is done; now the proof that it held." *Click:* in OAHE-INV-002's window
press **Bring the feed back (demo)** (beside **Open a ticket**): all eight tests are listed and `reachable` reads **pass**,
"156 records"; `power_ripple` passes too. `performance_above_floor` still fails: the INV-001 outage is open, and it should.
Then **Tickets** in the fleet window, tick **Show closed**, select ticket 4: the trail pane reads (times of the window's acts
follow the demo's clock):

    Fault      fault 5  SIT-004  ... opened 2026-06-01T13:00:00+00:00  closed 2026-06-01T13:45:00+00:00
               assigned by test:reachable
    Causes     ... engineer@oahe.example  Datalogger uplink cable unplugged during the 11:30 inverter outage  (stands)
    Comments   2026-06-01T13:40:00+00:00  engineer@oahe.example  Feed down since 11:30; datalogger link being traced.
    Moves      open, acknowledged, in progress, resolved, closed, each with who and when
    Closeout   closed 2026-06-01T13:45:00+00:00  Reseated the uplink cable
    Results    result 1  reachable  2026-06-01T13:00:00+00:00  127.0.0.1:<port> is unreachable
                 clauses 55000-9.1
                 next result <id>  ...  pass  156 records

*Say:* "Clause, failed result, fault, cause, comments, closeout, and the next result of the same test passing: one chain."
*Terminal:* `ticket show 4 --as engineer@oahe.example --at 2026-06-01T14:00:00+00:00` prints the same trail; `test results
--asset OAHE-INV-002` lists the new `reachable` pass first. The trail shows the passing next result whether the feed comes
back before or after the resolve; it comes back after here, so the pass is the check made after the action.

## What to click, in order

1. **Read the band above the list.** "Open outages: 1", "Open work orders: 1": what waits
   on a person. Click one and the list keeps only its assets (the outage: OAHE-INV-002); click it again for all eleven.
   The status bar at the foot names the store and its last run ("demo.db, last run 2026-06-01 13:00 UTC") and who is signed in.
2. **Read the headings, then mouse over a row.** Each column is named (Asset, Name, Kind, Status, Cause, Last run, Failing),
   and the Cause says why a row is its colour: OAHE-INV-002 "INV-001 since 2026-06-01 11:30 UTC", OAHE-SEN-001
   "reachable" (its failing test);
   the tooltip gives the last status and the run's instant ("Last status: yellow at 2026-06-01 13:00 UTC"); a string,
   a tracker or the meter, having no endpoint the run can reach, reads "no feed", where an asset with one not yet run
   would read "never run". Click the Status heading to put the worst first (a second click turns it round); type
   in the search box (Ctrl+F) or pick a status or a kind to narrow the list, Esc to clear; Up and Down move the
   selection and Enter opens it; F5 rereads the store.
3. **Click OAHE-INV-002.** The asset window shows the open INV-001 outage with its meaning, and its diagnostics with
   `reachable` failing first, in red, with its reason, and each test's last run and how long it took.
   Its **Runs** link (the blue word at the row's end) opens its runs instead: one run at 13:00 UTC, "9 results",
   "2 failed", in red; below it the run's results: `performance_above_floor` and the ping's `reachable` failed, first and
   red ("127.0.0.1:<the dead port> is unreachable"), `power_ripple` "no data" in grey (its five quick reads failed), then
   the six that passed, the test's own `reachable` among them. Type "fail" or a test's name to narrow the list.
   Its **By test** tab draws the runs as a timeline: a row per test, a green, red or grey (no data) mark per run,
   the hours in UTC.
   OAHE-INV-001's **Power** tab draws its day: "288 samples: records 279, gaps 9; peak 94.35 kW", the line broken at
   each gap (10:40, 13:25, 17:35, 17:50), never drawn down to zero. The **Errors** tab counts an asset's faults (red)
   by code over the days chosen (the amber suggestions bar stays at zero in a store made since 7.7, where a test raises
   its fault itself): OAHE-SEN-001 "SEN-001: 1 fault, 0 suggestions".
4. **Close it, click OAHE-INV-001, and assign a fault.** Its eight diagnostics all pass, fed by the simulator (`power_ripple` on five quick reads). Pick
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
   is overdue too). A double click opens the asset window, whose **Ticket** panel acts on that asset's nearest ticket: it acknowledges,
   comments and resolves (what was done), which closes the ticket and its fault once the fault's root cause is written
   (9001-10.2.1); until then Resolve is refused. **Show closed** lists the closed tickets too, and a ticket selected
   there shows its whole trail (see the walk).

   **Tests** (beside Tickets) opens the Tests window: one row per remote test with its kinds, the count of assets it ran
   on, its last run and duration, passes, failures and no data. Select `reachable`: its log lists its newest runs, the
   failures (OAHE-SEN-001, and OAHE-INV-002's unreachable feed) in red, a duration "—" where none was timed. The last
   column, **Clauses**, names the ISO clauses each test is evidence for.
## The five-minute talk track

1. **One requirement to its evidence and its fix.** Do the walk above: it is the argument, and takes the five minutes
   by itself. What follows is the short form when there is less time.
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
   every remote test for the asset's kind: eight on an inverter, among them a daylight performance floor (the signal
   that says a crew is worth sending, not a calendar) and a frozen-reading check (a logger replaying its last value).
   Adding a test is adding one file: `solarpunk test add <name> --clause <id>`.
7. **The tests are the audit.** Every product line is mutation-tested nightly; each survivor is killed or explained in
   `docs/MUTATION.md`. Every decision has a number, a reason and the test that holds it (`theGhost.md`).
8. **What is next, decided today.** The network's security, from plain TCP towards what the industry uses (Modbus TCP
   with SunSpec at the device, mutual TLS, IEC 62443 zones).

## If something goes wrong

- **"No module named 'solarpunk'"**: the command was typed outside the clone, or the clone's `solarpunk` folder has
  become `Solarpunk` (Windows treats the two names as one; Python does not), which happens when the repository is
  cloned inside a folder already named `Solarpunk` and then moved up. Clone again straight onto the Desktop.
- **"No module named tkinter"**: reinstall CPython 3.12 from python.org with "tcl/tk and IDLE" ticked.
- **A port is busy**: run it again; the simulator picks a free port each time.
- **"could not be removed and was left"**: the demo could not delete its temporary folder (another program holds the file); delete the folder the line names.
- **The window is blank**: click Refresh.
- **The run takes a few seconds**: Windows waits a moment on each refused connection (two feeds do not answer).
