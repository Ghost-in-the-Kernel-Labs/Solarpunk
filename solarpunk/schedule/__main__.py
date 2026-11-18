"""Run: python3 -m solarpunk.schedule render solarpunk-kpi prints the job's crontab line and schtasks command;
python3 -m solarpunk.schedule render --golden test/solarpunk/goldens rewrites both goldens and prints their paths."""
import argparse
import sys
from pathlib import Path
from typing import TextIO

from solarpunk.schedule.jobs import crontab_line, demo_jobs, schtasks_command, write_goldens

NO_TARGET = "render needs a demo job's name or --golden <folder>"
UNKNOWN_JOB = "no demo job named {!r}"


def build_parser() -> argparse.ArgumentParser:
    """The parser: "render solarpunk-kpi" parses to name "solarpunk-kpi", golden None."""
    parser = argparse.ArgumentParser()
    render = parser.add_subparsers(dest="command", required=True).add_parser("render")
    render.add_argument("name", nargs="?")
    render.add_argument("--golden", type=Path)
    return parser


def main(argv: list[str], out: TextIO, err: TextIO) -> int:
    """Renders as argv says: main(["render", "solarpunk-clauses"], out, err) prints its two lines and returns 0; an
    unknown name prints the reason to err and returns 2."""
    args = build_parser().parse_args(argv)
    if args.golden is not None:
        for path in write_goldens(args.golden):
            print(path, file=out)
        return 0
    if args.name is None:
        print(NO_TARGET, file=err)
        return 2
    found = [job for job in demo_jobs() if job.name == args.name]
    if not found:
        print(UNKNOWN_JOB.format(args.name), file=err)
        return 2
    print(crontab_line(found[0]), file=out)
    print(schtasks_command(found[0]), file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))
