"""README.md's roadmap held to the chain (P-01): each phase that TODO.md or docs/DONE.md names has one line
"- Phase N, <title>: <state>", and the state is the one the two files say: "done" when DONE.md holds the phase's
items and TODO.md none, "in progress" when both hold some, "not started" when TODO.md alone does. A README line that
says done while TODO.md still holds the phase's items, or open after they all moved to DONE.md, is the drift this
catches (Ghost, 2026-11-18: the README still called Phase 3 unfinished after its pass). A planted break shows the check
can fail."""
import re
import unittest

from test.support import ROOT

ITEM = re.compile(r"^### (\d+)\.\d+ ", re.MULTILINE)
LINE = re.compile(r"^- Phase (\d+), [^:\n]*: (.*)$", re.MULTILINE)


def phases(text: str) -> set[int]:
    """The phases whose items a chain file holds: "### 6.4 x" and "### 7.1 y" give {6, 7}."""
    return {int(phase) for phase in ITEM.findall(text)}


def expected(todo: str, done: str) -> dict[int, str]:
    """Each phase's state from the two files: 6 in both gives "in progress", 5 in DONE.md alone "done", 7 in TODO.md
    alone "not started"."""
    open_, closed = phases(todo), phases(done)
    found = {}
    for phase in open_ | closed:
        found[phase] = "in progress" if phase in open_ and phase in closed else ("not started" if phase in open_ else "done")
    return found


def problems(readme: str, todo: str, done: str) -> list[str]:
    """Every way the README's roadmap lines disagree with the chain; [] when they hold: a Phase 3 line saying "the demo
    is 3.4" while DONE.md holds all of Phase 3 gives ["Phase 3: the README says 'the demo is 3.4', the chain says done"]."""
    said: dict[int, list[str]] = {}
    for phase, state in LINE.findall(readme):
        said.setdefault(int(phase), []).append(state)
    found = []
    for phase, state in sorted(expected(todo, done).items()):
        lines = said.get(phase, [])
        if len(lines) != 1:
            found.append(f"Phase {phase}: {len(lines)} README lines, not one")
        elif not lines[0].startswith(state):
            found.append(f"Phase {phase}: the README says '{lines[0]}', the chain says {state}")
    return found


class TheReadme(unittest.TestCase):
    def test_the_roadmap_lines_match_the_chain(self) -> None:
        readme, todo, done = ((ROOT / name).read_text(encoding="utf-8") for name in ("README.md", "TODO.md", "docs/DONE.md"))
        self.assertEqual(problems(readme, todo, done), [])

    def test_the_planted_break_is_caught(self) -> None:
        todo = "### 6.4 Open\n### 7.1 Open\n"
        done = "### 3.5 Tune-up pass 3\n### 6.1 Done\n"
        readme = ("- Phase 3, the front end: the demo is 3.4, then a tune-up.\n- Phase 6, reports: done.\n"
                  "- Phase 7, security: not started; a design pass first.\n")
        self.assertEqual(problems(readme, todo, done), [
            "Phase 3: the README says 'the demo is 3.4, then a tune-up.', the chain says done",
            "Phase 6: the README says 'done.', the chain says in progress",
        ])
        self.assertEqual(problems("- Phase 7, security: not started.\n", todo, done)[0], "Phase 3: 0 README lines, not one")

    def test_a_held_roadmap_passes(self) -> None:
        readme = "- Phase 3, a: done.\n- Phase 6, b: in progress; more.\n- Phase 7, c: not started.\n"
        self.assertEqual(problems(readme, "### 6.4 x\n### 7.1 y\n", "### 3.5 z\n### 6.1 w\n"), [])


if __name__ == "__main__":
    unittest.main()
