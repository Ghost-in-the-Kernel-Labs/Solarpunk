"""scripts/ship.sh, the only push (C-037, C-031), proven on a scratch clone of a bare remote: it ships a HEAD whose tree is
the gate's record as a fast-forward, prints one line, and refuses a stale record, a remote main that moved and an
uncommitted change, pushing nothing; a remote with no main takes the first ship. And no document or script names a raw
push but the ship itself and process.md's mention of it. And scripts/commit.sh --ship (SP-014): main moves only once
origin has taken the commit, so a refused push never leaves main ahead of origin."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from test.support import ROOT
from test.support_git import git_out, record, repo_with, run_commit

SHIP = ROOT / "scripts" / "ship.sh"
IDENTITY = ["-c", "user.name=Ghost", "-c", "user.email=g@example.invalid"]
AUTHOR = "Ghost <118085043+ghost-in-the-kernel@users.noreply.github.com>"
COMMITTER = "Claude <noreply@anthropic.com>"


def git(cwd: Path, args: list[str]) -> str:
    """git's output in cwd, stripped: git(clone, ["rev-parse", "HEAD"]) gives HEAD's SHA."""
    return subprocess.run(["git", "-C", str(cwd), *IDENTITY, *args], capture_output=True, text=True, check=True).stdout.strip()


def commit(clone: Path, name: str) -> None:
    """One commit in the clone that adds the file name, holding its own name."""
    (clone / name).write_text(name)
    git(clone, ["add", "-A"])
    git(clone, ["commit", "-q", "-m", name])


def remote_and_clone(seeded: bool = True) -> tuple[Path, Path]:
    """A bare remote and a clone of it holding a copy of scripts/ship.sh, committed; with seeded, main is on the remote."""
    top = Path(tempfile.mkdtemp(prefix="ghost-core-ship-"))
    remote, clone = top / "remote.git", top / "clone"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(clone)], check=True)
    git(clone, ["remote", "add", "origin", str(remote)])
    (clone / "scripts").mkdir()
    (clone / "scripts" / "ship.sh").write_text(SHIP.read_text())
    commit(clone, "start")
    if seeded:
        git(clone, ["push", "-q", "origin", "main"])  # the scratch remote's seed, before any record exists
    return remote, clone


def ship(clone: Path) -> subprocess.CompletedProcess:
    """The clone's scripts/ship.sh, run as an agent runs it."""
    return subprocess.run(["bash", "scripts/ship.sh"], cwd=clone, capture_output=True, text=True)


class TheShip(unittest.TestCase):
    def test_a_recorded_head_ships_as_a_fast_forward(self) -> None:
        remote, clone = remote_and_clone()
        commit(clone, "work")
        record(clone)
        result = ship(clone)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, f"ship: {git(clone, ['rev-parse', '--short', 'HEAD'])} → origin/main\n")
        self.assertEqual(git(remote, ["rev-parse", "main"]), git(clone, ["rev-parse", "HEAD"]))

    def test_the_first_ship_to_a_remote_with_no_main(self) -> None:
        remote, clone = remote_and_clone(seeded=False)
        record(clone)
        self.assertEqual(ship(clone).returncode, 0)
        self.assertEqual(git(remote, ["rev-parse", "main"]), git(clone, ["rev-parse", "HEAD"]))

    def test_a_stale_or_absent_record_is_refused(self) -> None:
        remote, clone = remote_and_clone()
        before = git(remote, ["rev-parse", "main"])
        commit(clone, "work")
        absent = ship(clone)
        self.assertEqual((absent.returncode, absent.stdout), (1, "ship: refused at the record (gate first: no tree recorded; run scripts/gate.sh)\n"))
        record(clone)
        commit(clone, "after the gate")
        stale = ship(clone)
        self.assertEqual(stale.returncode, 1)
        self.assertRegex(stale.stdout, r"^ship: refused at the record \(gate first: HEAD's tree \w{10} is not the tree the gate passed on, \w{10}\)\n$")
        self.assertEqual(git(remote, ["rev-parse", "main"]), before)

    def test_a_remote_main_that_moved_is_refused(self) -> None:
        remote, clone = remote_and_clone()
        other = remote.parent / "other"
        subprocess.run(["git", "clone", "-q", str(remote), str(other)], check=True)
        commit(other, "theirs")
        git(other, ["push", "-q", "origin", "main"])
        commit(clone, "mine")
        record(clone)
        result = ship(clone)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "ship: refused at the fast-forward (fetch and rebuild: main moved; rebase onto origin/main, run scripts/gate.sh and commit again)\n")
        self.assertEqual(git(remote, ["log", "-1", "--format=%s", "main"]), "theirs")

    def test_an_uncommitted_change_is_refused(self) -> None:
        remote, clone = remote_and_clone()
        commit(clone, "work")
        record(clone)
        (clone / "loose.txt").write_text("not committed")
        result = ship(clone)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stdout.startswith("ship: refused at the working tree (uncommitted changes"), result.stdout)


class TheOnlyPush(unittest.TestCase):
    def test_no_document_or_script_names_a_raw_push_but_the_ship_and_the_save(self) -> None:
        """The grep of TODO 3.8's check, widened by 4.10: the save pushes a session branch, never main (C-040). DONE.md's
        lines that quote those checks verbatim are a record of them, not a push."""
        found = subprocess.run(["grep", "-rn", "git push", "docs", "scripts", "README.md", "CLAUDE.md"], cwd=ROOT, capture_output=True, text=True).stdout
        files = {line.split(":", 1)[0] for line in found.splitlines() if not line.startswith("docs/DONE.md:") or "Check: " not in line}
        # commit.sh --ship pushes main itself, before main moves, so main is never left ahead of origin (SP-014).
        self.assertEqual(files, {"scripts/ship.sh", "scripts/save.sh", "scripts/commit.sh", "docs/paths/process.md"}, found)
        code = "\n".join(line for line in (ROOT / "scripts" / "save.sh").read_text().splitlines() if not line.startswith("#"))
        self.assertIn("git push -q -u origin HEAD", code)
        self.assertNotIn("refs/heads/main", code)
        self.assertNotIn("--force", code)
        shipped = (ROOT / "scripts" / "commit.sh").read_text()
        self.assertIn('git push -q origin "$commit:refs/heads/main"', shipped)
        self.assertNotIn("--force", shipped)

def with_remote(root: Path) -> Path:
    """A bare remote for the scratch repository, added as origin and seeded with its main: with_remote(repo_with(1))
    holds the same main as the repository."""
    remote = root.parent / f"{root.name}-remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    git_out(root, ["remote", "add", "origin", str(remote)])
    git_out(root, ["push", "-q", "origin", "main"])
    return remote


class TheShippedCommit(unittest.TestCase):
    """--ship (SP-014): main moves only once origin has taken the commit, so it is never left ahead of origin."""

    def ship(self, root: Path, subject: str) -> subprocess.CompletedProcess:
        """A change committed through --ship with the gate recorded first: self.ship(root, "x").returncode is 0."""
        (root / "next.txt").write_text(subject)
        record(root)
        return run_commit(root, ["-a", "-m", subject, "--ship"])

    def test_a_shipped_commit_is_on_origin_and_main_together(self) -> None:
        root = repo_with(1)
        remote = with_remote(root)
        result = self.ship(root, "6.1 a change")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        head = git_out(root, ["rev-parse", "HEAD"])
        self.assertEqual(git_out(remote, ["rev-parse", "main"]), head)
        self.assertEqual(result.stdout.splitlines()[-1], f"ship: {head[:7]} → origin/main")
        self.assertEqual(git_out(root, ["log", "-1", "--format=%an <%ae>/%cn <%ce>"]), f"{AUTHOR}/{COMMITTER}")

    def test_a_remote_that_moved_refuses_and_main_stays_where_it_was(self) -> None:
        root = repo_with(1)
        remote = with_remote(root)
        moved = git_out(remote, ["commit-tree", "main^{tree}", "-p", "main", "-m", "elsewhere"])
        git_out(remote, ["update-ref", "refs/heads/main", moved])
        before = git_out(root, ["rev-parse", "HEAD"])
        result = self.ship(root, "6.1 a change")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertRegex(result.stdout.splitlines()[-1], r"^commit: refused at the ship \(origin/main moved past \w{10}: ")
        self.assertEqual((git_out(root, ["rev-parse", "HEAD"]), git_out(remote, ["rev-parse", "main"])), (before, moved))

    def test_ship_from_another_branch_is_refused(self) -> None:
        root = repo_with(1)
        with_remote(root)
        git_out(root, ["checkout", "-q", "-b", "claude/work"])
        result = self.ship(root, "work")
        self.assertEqual(result.stdout.splitlines()[-1],
                         "commit: refused at staging (--ship lands main alone; HEAD is on claude/work)")

