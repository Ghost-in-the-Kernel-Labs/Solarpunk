"""Run: python3 -m solarpunk.cli --db fleet.db fleet load --demo prints "loaded 11 assets" and exits 0."""
import sys

from solarpunk.cli.main import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))
