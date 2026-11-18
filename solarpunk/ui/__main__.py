"""Run: python3 -m solarpunk.ui --db fleet.db opens the fleet window on that store, made if missing; python3 -m
solarpunk.ui --demo rebuilds demo.db in the current directory (solarpunk/ui/demo.py), starts the feed simulator for
OAHE-INV-001, runs the suite once and opens the fleet window on it. Either way a click on a row opens the asset window,
whose changes refresh the fleet window, "Add asset" above the list opens the add-asset window and "Reports" the
power-output report (6.3)."""
import argparse
import sqlite3
import sys
import tkinter
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from tkinter import ttk
from typing import TextIO

from solarpunk import project
from solarpunk.leaf.codes import AssetStatus
from solarpunk.ui import demo
from solarpunk.ui.add_asset import AddAssetWindow
from solarpunk.ui.app import FleetWindow
from solarpunk.ui.asset_window import AssetWindow
from solarpunk.ui.reports import ReportsWindow

PROG = "solarpunk.ui"
DEFAULT_DB = "solarpunk.db"
TITLE = "Solarpunk fleet"
DEMO_TITLE = "Solarpunk fleet — demo (OAHE, 2026-06-01)"
ADD_ASSET = "Add asset"
REPORTS = "Reports"
STORE_LINE = "demo: store {name} rebuilt\n"
SIMULATOR_LINE = "demo: simulator on 127.0.0.1:{port}\n"
RUN_LINE = "demo: run - {green} green, {yellow} yellow, {red} red\n"


def parse(argv: list[str]) -> argparse.Namespace:
    """The arguments: parse([]) is Namespace(db="solarpunk.db", demo=False); parse(["--db", "f.db", "--demo"]) is
    Namespace(db="f.db", demo=True)."""
    parser = argparse.ArgumentParser(prog=PROG)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--demo", action="store_true")
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


def open_fleet(root: tkinter.Tk, conn: sqlite3.Connection) -> FleetWindow:
    """The fleet window wired to the others: a click opens AssetWindow(root, conn, id, on_change=refresh), the "Add asset"
    button packed above the list opens AddAssetWindow(root, conn, on_saved) which refreshes after a save, and "Reports"
    beside it opens ReportsWindow(root, conn) (6.3)."""
    window = FleetWindow(root, conn)
    window.on_open_asset = lambda asset_id: AssetWindow(root, conn, asset_id, window.refresh)
    bar = ttk.Frame(root)
    bar.pack(fill=tkinter.X, before=window.frame)
    window.add_button = ttk.Button(bar, text=ADD_ASSET,
                                   command=lambda: AddAssetWindow(root, conn, lambda asset_id: window.refresh()))
    window.add_button.pack(side=tkinter.LEFT)
    window.reports_button = ttk.Button(bar, text=REPORTS, command=lambda: ReportsWindow(root, conn))
    window.reports_button.pack(side=tkinter.LEFT)
    return window


def run_demo(root: tkinter.Tk, out: TextIO) -> sqlite3.Connection:
    """Starts the simulator, rebuilds demo.db in the current directory, opens the fleet window on it titled "Solarpunk
    fleet — demo (OAHE, 2026-06-01)" and returns the open store; writes "demo: simulator on 127.0.0.1:<port>", "demo:
    store demo.db rebuilt" and "demo: run - 8 green, 1 yellow, 1 red", one line each, as it goes."""
    _server, port = demo.start_simulator(demo.simulator_samples())
    out.write(SIMULATOR_LINE.format(port=port))
    state = demo.build_demo_store(Path.cwd() / demo.DB_NAME, port)
    out.write(STORE_LINE.format(name=demo.DB_NAME))
    out.write(run_line(state.run_report))
    out.flush()
    conn = project.open_or_create(state.db_path)
    root.title(DEMO_TITLE)
    open_fleet(root, conn)
    return conn


def main(argv: list[str], out: TextIO, run: Callable[[tkinter.Tk], None] = loop) -> int:
    """Opens the fleet window on the store, or on the rebuilt demo store with --demo, hands it to run, then exits 0:
    main(["--db", "f.db"], sys.stdout) shows f.db's assets; main(["--demo"], sys.stdout) shows demo.db's eleven."""
    args = parse(argv)
    root = tkinter.Tk()
    if args.demo:
        with closing(run_demo(root, out)):
            run(root)
        return 0
    with closing(project.open_or_create(args.db)) as conn:
        root.title(TITLE)
        open_fleet(root, conn)
        run(root)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout))
