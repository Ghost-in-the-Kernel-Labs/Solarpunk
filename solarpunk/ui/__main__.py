"""Run: python3 -m solarpunk.ui --db fleet.db opens the fleet window on that store, made if missing; python3 -m
solarpunk.ui --demo rebuilds demo.db in a throwaway folder of the system's temporary files, printing its path, removed on exit (solarpunk/ui/demo.py), starts the feed simulator for
OAHE-INV-001, runs the suite once and opens the fleet window on it. Either way a click on a row opens the asset window,
whose changes refresh the fleet window, "Add asset" above the list opens the add-asset window, "Reports" the
power-output report (6.3) and "Tests" the Tests window, every test's record and last 100 runs (13.7). Every window wears Solarpunk's icon; --shortcut puts a desktop shortcut wearing it, starting
in the current directory, and opens no window (9.7)."""
import argparse
import base64
import os
import shutil
import sqlite3
import sys
import tempfile
import tkinter
from collections.abc import Callable
from contextlib import closing
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from typing import TextIO

from solarpunk import project
from solarpunk.leaf.codes import AssetStatus
from solarpunk.ui import cells, demo, icon, shortcut, sign_in
from solarpunk.ui.add_asset import AddAssetWindow
from solarpunk.ui.app import FleetWindow
from solarpunk.ui.errors_window import ErrorsWindow
from solarpunk.ui.record_window import RecordWindow
from solarpunk.ui.runs_window import RunsWindow
from solarpunk.ui.tests_window import ManageTestsWindow
from solarpunk.ui.tickets_window import TicketsWindow
from solarpunk.ui.asset_window import AssetWindow
from solarpunk.ui.reports import ReportsWindow

PROG = "solarpunk.ui"
DEFAULT_DB = "solarpunk.db"
TITLE = "Solarpunk fleet"
DEMO_TITLE = "Solarpunk fleet — demo (OAHE, 2026-06-01)"
ADD_ASSET = "Add asset"
MANAGE_TESTS = "Manage tests"
REPORTS = "Reports"
TESTS = "Tests"
ERRORS = "Errors"
TICKETS = "Tickets"
STORE_LINE = "demo: store {path} rebuilt\n"
LEFT_LINE = "demo: folder {path} could not be removed and was left\n"
SIMULATOR_LINE = "demo: simulator on 127.0.0.1:{port}\n"
DEAD_LINE = "demo: dead feeds on 127.0.0.1:{port}\n"
ACCOUNT_LINE = "demo: account {email} password {password}\n"
RUN_LINE = "demo: run - {green} green, {yellow} yellow, {red} red\n"


def parse(argv: list[str]) -> argparse.Namespace:
    """The arguments: parse([]) is Namespace(db="solarpunk.db", demo=False); parse(["--db", "f.db", "--demo"]) is
    Namespace(db="f.db", demo=True); --shortcut makes the desktop shortcut and opens no window (9.7)."""
    parser = argparse.ArgumentParser(prog=PROG)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--shortcut", action="store_true")
    return parser.parse_args(argv)


def loop(root: tkinter.Tk) -> None:
    """Runs the window until it is closed: loop(root) returns when root is destroyed."""
    root.mainloop()


def run_line(report: project.RunReport) -> str:
    """The terminal's line for a run: statuses of eight GREEN, one YELLOW and one RED give
    "demo: run - 8 green, 1 yellow, 1 red\\n"."""
    found = list(report.statuses.values())
    return RUN_LINE.format(green=found.count(AssetStatus.GREEN), yellow=found.count(AssetStatus.YELLOW),
                           red=found.count(AssetStatus.RED))


def open_fleet(root: tkinter.Tk, conn: sqlite3.Connection, account: project.Account | None = None,
               revival: demo.Revival | None = None, now: Callable[[], datetime] = cells.wall_now) -> FleetWindow:
    """The fleet window wired to the others: a click opens AssetWindow(root, conn, id, on_change=refresh), the "Add asset"
    button in the window's toolbar opens AddAssetWindow(root, conn, on_saved) which refreshes after a save, "Manage tests"
    beside it the ManageTestsWindow over the remote tests' folder (9.8), and "Reports" after it opens ReportsWindow(root, conn) (6.3), "Tests" after that the RecordWindow(root, conn) (13.7), then "Errors" the fleet's ErrorsWindow, whose rows open a Runs window
    (10.7), then "Tickets" the TicketsWindow, a double click opening the ticket's asset window (11.2); Refresh stands
    at the toolbar's right (9.5). The account signed in (None in a store with none) is kept on the window and named in
    its status bar (12.3), and every asset window acts as it (12.4). The demo hands a revival (13.16), so its asset window
    offers "Bring the feed back (demo)" for a dead inverter; with none (any other store) the control does not exist. now is the
    instant every window stamps its acts at: the wall clock, or the demo's day (13.15)."""
    window = FleetWindow(root, conn)
    window.account = account
    window.account_label = ttk.Label(window.status_bar, text=cells.who_text(account))
    window.account_label.pack(side=tkinter.LEFT, padx=12)
    window.on_open_asset = lambda asset_id: AssetWindow(root, conn, asset_id, window.refresh, account, revival, now)  # 12.4, 13.16
    window.on_open_runs = lambda asset_id: RunsWindow(root, conn, asset_id, account, now)  # 10.3, 7.9
    bar = window.toolbar  # Refresh stands at its right since 9.5
    window.add_button = ttk.Button(bar, text=ADD_ASSET,
                                   command=lambda: AddAssetWindow(root, conn, lambda asset_id: window.refresh()))
    window.add_button.pack(side=tkinter.LEFT)
    window.tests_button = ttk.Button(bar, text=MANAGE_TESTS, command=lambda: ManageTestsWindow(root))
    window.tests_button.pack(side=tkinter.LEFT)  # 9.8: between Add asset and Reports
    window.reports_button = ttk.Button(bar, text=REPORTS, command=lambda: ReportsWindow(root, conn))
    window.reports_button.pack(side=tkinter.LEFT)
    window.record_button = ttk.Button(bar, text=TESTS, command=lambda: RecordWindow(root, conn))
    window.record_button.pack(side=tkinter.LEFT)  # 13.7: beside Reports
    window.errors_button = ttk.Button(bar, text=ERRORS, command=lambda: ErrorsWindow(root, conn, window.on_open_runs))
    window.errors_button.pack(side=tkinter.LEFT)  # 10.7
    window.tickets_button = ttk.Button(bar, text=TICKETS,
                                       command=lambda: TicketsWindow(root, conn, lambda asset_id: window.on_open_asset(asset_id), now))
    window.tickets_button.pack(side=tkinter.LEFT)  # 11.2
    return window


def run_demo(root: tkinter.Tk, out: TextIO) -> sqlite3.Connection:
    """Starts the simulator, rebuilds demo.db in a new folder of the system's temporary files, opens the fleet window on it
    titled "Solarpunk fleet — demo (OAHE, 2026-06-01)" and returns the open store; writes "demo: simulator on
    127.0.0.1:<port>", "demo: dead feeds on 127.0.0.1:<port>" (a port reserved for this run, 13.16), "demo: store /tmp/solarpunk-demo-k2j9/demo.db rebuilt" (the full path, to pass to --db from a
    second terminal), "demo: run - 9 green, 1 yellow, 1 red" and one "demo: account engineer@oahe.example password oahe-demo-engineer"
    line for each of the demo's two accounts (13.15), one line each, as it goes; the window is signed in as the engineer and
    stamps its acts on the demo's day (demo.demo_clock). The folder is removed by
    remove_demo_folder; a build that fails removes it here."""
    _server, port = demo.start_simulator(demo.simulator_samples())
    out.write(SIMULATOR_LINE.format(port=port))
    dead_port = demo.reserve_port()
    out.write(DEAD_LINE.format(port=dead_port))
    now = demo.demo_clock()
    revival = demo.Revival(dead_port, now)
    root.demo_revival = revival  # run_demo_window closes it with the window
    folder = Path(tempfile.mkdtemp(prefix="solarpunk-demo-"))
    try:
        state = demo.build_demo_store(folder / demo.DB_NAME, port, dead_port)
        out.write(STORE_LINE.format(path=state.db_path))
        out.write(run_line(state.run_report))
        for email, _name, _role, password in demo.ACCOUNTS:
            out.write(ACCOUNT_LINE.format(email=email, password=password))
        out.flush()
        conn = project.open_or_create(state.db_path)
        root.title(DEMO_TITLE)
        root.demo_fleet = open_fleet(root, conn, project.account_of(conn, demo.ENGINEER), revival, now)  # signed in, no prompt (13.15)
    except BaseException:
        revival.close()
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return conn


def demo_folder(conn: sqlite3.Connection) -> Path:
    """The folder holding the demo store: for a store at /tmp/solarpunk-demo-k2j9/demo.db it is /tmp/solarpunk-demo-k2j9."""
    return Path(conn.execute("PRAGMA database_list").fetchone()[2]).parent


def remove_demo_folder(folder: Path, out: TextIO) -> None:
    """Removes the demo's folder once the store is closed; never raises: where it cannot (Windows holding the file) it
    writes "demo: folder /tmp/solarpunk-demo-k2j9 could not be removed and was left" instead."""
    shutil.rmtree(folder, ignore_errors=True)
    if folder.exists():
        out.write(LEFT_LINE.format(path=folder))


def run_demo_window(root: tkinter.Tk, out: TextIO, run: Callable[[tkinter.Tk], None]) -> None:
    """run_demo, then run(root), then the store closed and its folder removed, whatever run does: after it returns,
    the path run_demo printed does not exist."""
    conn = run_demo(root, out)
    folder = demo_folder(conn)
    try:
        with closing(conn):
            run(root)
    finally:
        root.demo_revival.close()
        remove_demo_folder(folder, out)


def wear_icon(root: tkinter.Tk) -> None:
    """Gives every Solarpunk window the icon (9.7): the 64 and 32 px images as the default for the root and each
    window it opens, kept on the root so they are not collected."""
    root.icon_images = [tkinter.PhotoImage(master=root, data=base64.b64encode(icon.png(size))) for size in (64, 32)]
    root.iconphoto(True, *root.icon_images)


def main(argv: list[str], out: TextIO, run: Callable[[tkinter.Tk], None] = loop) -> int:
    """Opens the fleet window on the store (after a sign-in when the store holds an account, 12.3), or on the rebuilt
    demo store with --demo (signed in as its engineer without asking, 13.15), hands it to run, then exits 0:
    main(["--db", "f.db"], sys.stdout) shows f.db's assets; main(["--demo"], sys.stdout) shows demo.db's eleven, the store in a folder gone on exit."""
    args = parse(argv)
    if args.shortcut:
        for line in shortcut.make(Path.cwd(), os.environ, Path.home(), sys.platform == "win32"):
            out.write(line + "\n")
        return 0
    root = tkinter.Tk()
    wear_icon(root)
    if args.demo:
        run_demo_window(root, out, run)
        return 0
    with closing(project.open_or_create(args.db)) as conn:
        root.title(TITLE)
        sign_in.start(root, conn, lambda account: open_fleet(root, conn, account))  # 12.3
        run(root)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout))
