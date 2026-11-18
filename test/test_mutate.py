"""The mutation regime stands apart from the gate (SP-012): the Python stack's gate runs no mutmut, the regime's own
script runs it and the survivor check, and it refuses an argument it does not know before it runs anything."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "stacks" / "python" / "gate.sh"
MUTATE = ROOT / "stacks" / "python" / "mutate.sh"


def code_lines(path: Path) -> list[str]:
    """A script's lines that are not comments: code_lines(GATE)[0] is "set -euo pipefail"."""
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]


class TheRegime(unittest.TestCase):
    def test_the_gate_runs_no_mutation(self) -> None:
        for line in code_lines(GATE):
            with self.subTest(line=line):
                self.assertNotIn("mutmut", line)
                self.assertNotIn("survivors", line)

    def test_the_regime_runs_mutmut_then_refuses_an_unexplained_survivor(self) -> None:
        lines = code_lines(MUTATE)
        run = [index for index, line in enumerate(lines) if '"$bin/mutmut" run ' in line]
        check = [index for index, line in enumerate(lines) if "scripts/survivors.py" in line]
        self.assertEqual((len(run), len(check)), (1, 1))
        self.assertLess(run[0], check[0])
        self.assertIn("|| refuse", lines[check[0] + 1])

    def test_an_unknown_argument_is_refused_before_anything_runs(self) -> None:
        done = subprocess.run(["bash", str(MUTATE), "--warm"], capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 1)
        self.assertEqual(done.stdout, "mutate: refused at the arguments (unknown argument --warm; usage: "
                                      "stacks/python/mutate.sh [--cold])\n")
