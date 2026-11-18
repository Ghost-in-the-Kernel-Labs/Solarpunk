"""Run: python3 -m solarpunk.receiver --db fleet.db --host 127.0.0.1 --port 5030 [--once] prints
"receiver: listening on 127.0.0.1:5030" and serves."""
import sys

from solarpunk.receiver.server import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout))
