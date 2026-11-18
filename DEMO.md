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

- **OAHE-INV-001 green**: a feed simulator inside the demo serves its day of telemetry; every remote test passed.
- **OAHE-INV-002 red**: an open INV-001 outage (inverter offline) since 11:30, and its feed does not answer.
- **OAHE-SEN-001 yellow**: the irradiance sensor's feed does not answer, so its `reachable` test failed.
- The site, the strings, the trackers and the meter are green: they have no feed configured, so the suite leaves
  them alone and only their faults decide their colour.

The ledger also holds two closed faults: a grid curtailment on the site (12:00 to 13:00) and an over-temperature
derate on OAHE-INV-001 (10:00 to 10:45). The run is stamped 2026-06-01 13:00 UTC.

## What to click, in order

1. **Mouse over a row.** The tooltip gives the last status and the run's instant ("Last status: yellow at
   2026-06-01T13:00:00+00:00"); a string reads "never run".
2. **Click OAHE-INV-002.** The asset window shows the open INV-001 outage with its meaning, and the last run with
   `reachable` failing first, in red, with its reason.
3. **Close it, click OAHE-INV-001, and assign a fault.** Pick INV-004 (firmware update pending, INFO) and press
   Assign: the fleet window stays green, since an INFO fault is not an outage. Then assign INV-001: the fleet
   row turns red at once (the asset window refreshes the fleet window; Refresh does the same by hand).
4. **The engineer.** In the same window type an address into Engineer and press Save, or Cancel to leave it.
5. **Add asset** (the button above the list). The Type dropdown is read from the asset maintenance list. Fill an
   id such as OAHE-INV-005, a parent, the IP address 127.0.0.1 and a port, press Save: the new row appears in the
   fleet window. Then press **Ping**: with nothing listening on that port it says so, plainly.

## The five-minute talk track

1. **Line of sight (ISO 55000).** The site's purpose is energy delivered; that becomes a KPI contract
   (availability, performance ratio, energy yield, MTBF and MTTR, `docs/CONTRACT.md`); the code that computes each
   number cites the clause it serves; a test flags any break; the clause register shows the coverage.
2. **The closed catalogue and the ledger (ISO 9001 §8.7 and §10.2).** A fault can only be a code from the
   catalogue, on an asset the fleet holds; the ledger records when it opened and closed. Nonconforming output is
   named, controlled and corrected, never a free-text note.
3. **The blind mirror.** Each KPI is reimplemented from the contract text alone by an agent that never saw the
   code, and a test compares the two. Every number has a ten-row example you can check by hand.
4. **Show the clause report live:**

       python -I scripts\clauses.py

   Each ISO 9001 and ISO 55000 clause the project holds, the test that holds it, and held, failing or open.
5. **The mutation score.** Every product line is mutated and the tests must notice; each survivor is either killed
   or explained in `docs/MUTATION.md`. The tests are the audit.
6. **What is next.** The work orders (Phase 4: a fault opens a work order with a root-cause code, closing it
   closes the fault), the receiver pushing live faults into this window, the mailer writing to the engineer on a
   red or yellow, and the clock running the suite on a schedule (Task Scheduler here, cron on Linux).

## If something goes wrong

- **"No module named tkinter"**: reinstall CPython 3.12 from python.org with "tcl/tk and IDLE" ticked.
- **A port is busy**: run it again; the simulator picks a free port each time.
- **"demo.db" cannot be removed**: a demo window from an earlier run is still open; close it and run again.
- **The window is blank**: click Refresh.
- **The run takes a few seconds**: Windows waits a moment on each refused connection (two feeds do not answer).
