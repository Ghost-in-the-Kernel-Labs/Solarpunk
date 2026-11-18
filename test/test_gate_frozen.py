"""SP-017's gate, proven on a scratch repository: every step runs on a frozen copy of the tree taken before the first
step, so an edit to the working tree while the gate runs neither reaches a step nor fails the run, and leaves a record
that is stale for the edited tree; a step that hangs is refused by name once GHOST_STEP_TIMEOUT runs out; a step's
`note:` lines reach the terminal; no worktree outlives the run, red or green."""
import subprocess
import unittest
from pathlib import Path

from scripts.checks import gate_record
from test.support_git import gate, gated_repo, recorded


def worktrees(root: Path) -> int:
    """How many worktrees the scratch repository has: 1 when only its own is left."""
    listing = subprocess.run(["git", "-C", str(root), "worktree", "list"], capture_output=True, text=True, check=True)
    return len(listing.stdout.splitlines())


class TheFrozenCopy(unittest.TestCase):
    def test_an_edit_made_while_the_gate_runs_does_not_reach_it_and_the_record_is_the_tree_it_gated(self) -> None:
        root = gated_repo()
        frozen = gate_record.tree(root)
        result = gate(root, {"EDIT_ME": str(root / "notes.txt")})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((root / "notes.txt").read_text(), "edited\n")
        self.assertEqual(recorded(root), frozen)
        self.assertFalse(gate_record.matches(root), "the edited tree is not the one the gate passed on")
        self.assertEqual(worktrees(root), 1)

    def test_a_step_that_hangs_is_refused_by_name_and_the_copy_is_removed(self) -> None:
        root = gated_repo()
        result = gate(root, {"SLEEP_S": "30", "GHOST_STEP_TIMEOUT": "1"})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines()[-1], "gate: refused at the fast loop (timed out after 1 s)")
        self.assertIsNone(recorded(root))
        self.assertEqual(worktrees(root), 1)
        self.assertFalse((root / ".git" / "ghost" / "lock").exists())

    def test_a_steps_note_reaches_the_terminal_under_its_line(self) -> None:
        root = gated_repo()
        lines = gate(root, {"NOTE": "window tests not run (no xvfb-run)"}).stdout.splitlines()
        at = next(i for i, line in enumerate(lines) if line.startswith("== the fast loop: passed"))
        self.assertEqual(lines[at + 1], "note: window tests not run (no xvfb-run)")



class TheTestThreads(unittest.TestCase):
    def test_every_thread_a_test_starts_is_a_daemon(self) -> None:
        """A non-daemon thread a failing test leaves running keeps the interpreter alive after the summary (J-050): every
        `threading.Thread(` under test/ says daemon=True."""
        root = Path(__file__).resolve().parents[1]
        found = [f"{path.relative_to(root)}:{number}" for path in sorted((root / "test").rglob("*.py"))
                 for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                 if "threading.Thread(" in line and "daemon=True" not in line and "in line" not in line]
        self.assertEqual(found, [])

if __name__ == "__main__":
    unittest.main()
