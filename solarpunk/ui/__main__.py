"""Run: python3 -m solarpunk.ui --db fleet.db opens the fleet window on that store, made if missing; --demo is TODO
3.4's and for now prints "demo: see TODO 3.4" and exits 2."""
import argparse
import sys
import tkinter
from collections.abc import Callable
from contextlib import closing
from typing import TextIO

from solarpunk import project
from solarpunk.ui.app import FleetWindow

PROG = "solarpunk.ui"
DEFAULT_DB = "solarpunk.db"
TITLE = "Solarpunk fleet"
DEMO_PENDING = "demo: see TODO 3.4\n"
DEMO_EXIT = 2


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


def main(argv: list[str], out: TextIO, run: Callable[[tkinter.Tk], None] = loop) -> int:
    """Opens the fleet window on the store and hands it to run, then exits 0: main(["--db", "f.db"], sys.stdout) shows
    f.db's assets; main(["--demo"], out) writes "demo: see TODO 3.4" and returns 2 without opening a window."""
    args = parse(argv)
    if args.demo:
        out.write(DEMO_PENDING)
        return DEMO_EXIT
    with closing(project.open_or_create(args.db)) as conn:
        root = tkinter.Tk()
        root.title(TITLE)
        FleetWindow(root, conn)
        run(root)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout))
