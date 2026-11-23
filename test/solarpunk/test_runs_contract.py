"""SOL-15 held to the demo store (10.1, SP-024): each worked example's numbers are read from the store as the section
defines them (a run is the results at one instant, an error count is faults and suggestions by code counted apart, a
power series is samples with their gaps named), and each example's line is found in the section, so the contract and
the store cannot drift apart before 10.2 builds the surface. The readings here use the tables directly: they are the
definitions' check, not the surface."""
import sqlite3
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from solarpunk import project
from solarpunk.ui import demo
from test.support import ROOT

DAY_START, DAY_END = "2026-06-01T00:00:00+00:00", "2026-06-02T00:00:00+00:00"
RUN_AT = "2026-06-01T13:00:00+00:00"


def section() -> str:
    """SOL-15's text, to the end of the contract or the next section."""
    contract = (ROOT / "docs" / "CONTRACT.md").read_text(encoding="utf-8")
    start = contract.index("## SOL-15")
    following = contract.find("\n## ", start + 1)
    return contract[start:] if following < 0 else contract[start:following]


def run_of(conn: sqlite3.Connection, asset_id: str, at: str) -> list[tuple[str, bool, str]]:
    """The run at one instant: (test, verdict, reason) for every result stored then, failures first, then no data (the
    verdict None, SP-039), then by test; a pass is True, a failure False."""
    rows = conn.execute("SELECT test_name, passed, reason, no_data FROM results WHERE asset_id = ? AND run_at = ?",
                        (asset_id, at))
    found = [(name, None if empty else bool(passed), reason) for name, passed, reason, empty in rows]
    return sorted(found, key=lambda r: ({False: 0, None: 1, True: 2}[r[1]], r[0]))


def errors_of(conn: sqlite3.Connection, asset_id: str) -> tuple[Counter, Counter]:
    """The day's faults and suggestions on an asset by code, counted apart, every suggestion's state counted."""
    faults = Counter(code for (code,) in conn.execute(
        "SELECT code FROM faults WHERE asset_id = ? AND opened >= ? AND opened < ?", (asset_id, DAY_START, DAY_END)))
    suggestions = Counter(code for (code,) in conn.execute(
        "SELECT code FROM suggestions WHERE asset_id = ? AND raised_at >= ? AND raised_at < ?",
        (asset_id, DAY_START, DAY_END)))
    return faults, suggestions


class TheExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """The demo store, built once in a temporary folder with its simulator, then opened."""
        server, port = demo.start_simulator(demo.simulator_samples())
        cls.addClassCleanup(server.server_close)
        cls.addClassCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(folder.cleanup)
        cls.dead = demo.build_demo_store(Path(folder.name) / demo.DB_NAME, port).dead_port
        cls.conn = project.open_or_create(Path(folder.name) / demo.DB_NAME)
        cls.addClassCleanup(cls.conn.close)
        cls.text = " ".join(section().split())

    def has(self, line: str) -> None:
        """The example's line is in the section, its spacing aside."""
        self.assertIn(" ".join(line.split()), self.text)

    def test_the_down_inverters_run(self) -> None:
        run = run_of(self.conn, demo.DOWN, RUN_AT)
        self.assertEqual(len(run), 9)
        self.assertEqual(run[0], ("performance_above_floor", False, "ratio 0.6148 under the floor 0.75 over 71 daylight records"))
        self.assertEqual(run[1], ("reachable", False, f"127.0.0.1:{self.dead} is unreachable"))
        self.assertIn(("reachable", True, "156 records"), run)
        self.assertEqual(sum(passed is True for _, passed, _ in run), 6)  # 13.15: zero output fails performance_above_floor
        self.has("OAHE-INV-002's run at 13:00 9 results, failed: performance_above_floor failed (\"ratio 0.6148 under the floor")

    def test_the_sensors_run(self) -> None:
        run = run_of(self.conn, demo.SENSOR, RUN_AT)
        self.assertEqual([(name, passed) for name, passed, _ in run],
                         [("reachable", False), ("reachable", False), ("irradiance_in_range", None), ("on_grid", None)])
        self.assertEqual({reason for name, passed, reason in run if passed is False},
                         {f"127.0.0.1:{self.dead} is unreachable", "no records"})
        self.assertEqual({reason for name, passed, reason in run if passed is None}, {"no records"})
        self.has("OAHE-SEN-001's run at 13:00 4 results, failed: two reachable failed")
        self.has("irradiance_in_range and on_grid no data (\"no records\"), never a pass")

    def test_the_error_counts(self) -> None:
        self.assertEqual(errors_of(self.conn, demo.SENSOR), (Counter({"SEN-001": 1}), Counter()))  # SP-046: a fault, no suggestion
        self.assertEqual(errors_of(self.conn, demo.DOWN), (Counter({"INV-001": 1, "INV-005": 1, "SIT-004": 1}), Counter()))  # SP-047, SP-054
        self.assertEqual(errors_of(self.conn, demo.FED), (Counter({"INV-002": 1}), Counter()))
        self.has("errors, OAHE-SEN-001, the day faults: SEN-001 1 (open since 13:00); suggestions: none")
        self.has("errors, OAHE-INV-002, the day faults: INV-001 1 (open since 11:30), INV-005 1 and SIT-004 1 (open since 13:00); suggestions: none")
        self.has("errors, OAHE-INV-001, the day faults: INV-002 1 (10:05 to 10:45); suggestions: none")

    def test_one_code_across_the_fleet(self) -> None:
        per_asset = Counter(asset for (asset,) in self.conn.execute(
            "SELECT asset_id FROM faults WHERE code = 'INV-001' AND opened >= ? AND opened < ?", (DAY_START, DAY_END)))
        suggested = self.conn.execute("SELECT count(*) FROM suggestions WHERE code = 'INV-001'").fetchone()[0]
        self.assertEqual((per_asset, suggested), (Counter({demo.DOWN: 1}), 0))
        self.has("INV-001 across the fleet OAHE-INV-002: faults 1, suggestions 0; no other asset")

    def test_the_power_series(self) -> None:
        rows = self.conn.execute("SELECT at, power_kw, gap FROM samples WHERE asset_id = ? AND at >= ? AND at < ?"
                                 " ORDER BY at", (demo.FED, DAY_START, DAY_END)).fetchall()
        gaps = [at for at, _, gap in rows if gap]
        self.assertEqual((len(rows), sum(power is not None for _, power, _ in rows), len(gaps)), (288, 279, 9))
        self.assertEqual(gaps[0][11:16], "04:25")
        self.assertIn("2026-06-01T10:40:00+00:00", gaps)
        self.assertTrue(all(power is None for _, power, gap in rows if gap))
        self.has("power, OAHE-INV-001, the day 288 samples: records 279, gaps 9 (the first at 04:25, one at 10:40)")

    def test_a_planted_break_is_caught(self) -> None:
        with self.assertRaises(AssertionError):
            self.has("OAHE-INV-002's run at 13:00 8 results, failed")
        with self.assertRaises(AssertionError):
            self.has("power, OAHE-INV-001, the day 288 samples: records 288, gaps 0")


if __name__ == "__main__":
    unittest.main()
