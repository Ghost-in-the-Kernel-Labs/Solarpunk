"""The demo (3.4): the store solarpunk/ui/demo.py builds, headless, against a real simulator on an ephemeral port: all
three colours, OAHE-INV-001 GREEN with a last run, OAHE-INV-002 RED, OAHE-SEN-001 YELLOW on a failing reachable, the
trackers and the meter GREEN and untested, and the store rebuilt on a second call. The window half (__main__.py's
run_demo and open_fleet) under a display (xvfb-run -a .venv/bin/pytest test/solarpunk/test_demo.py), skipping with
"no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import io
import os
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind, AssetStatus
from solarpunk.remote import registry as remote_registry
from solarpunk.remote import results
from solarpunk.telemetry import generate as generator
from solarpunk.telemetry import samples as sample_table
from solarpunk.ui import cells, demo

ENGINEER = "site@oahe.example"  # SP-015: a fault names the engineer who assigned it; the fixtures' site engineer

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import __main__ as entry
    from solarpunk.ui.add_asset import AddAssetWindow
    from solarpunk.ui.asset_window import AssetWindow

INV1 = "OAHE-INV-001"
INV2 = "OAHE-INV-002"
SENSOR = "OAHE-SEN-001"
UNTESTED = ("OAHE-TRK-001", "OAHE-TRK-002", "OAHE-MTR-001")
RUN_AT = at(2026, 6, 1, 13)


def display_available() -> bool:
    """Whether a Tk window can open here: False with no DISPLAY (tkinter.Tk() raises TclError) or no tkinter at all."""
    if not HAS_TKINTER:
        return False
    try:
        tkinter.Tk().destroy()
    except tkinter.TclError:
        return False
    return True


class DemoFixture(unittest.TestCase):
    """A running simulator and a temporary folder, both gone when a test ends: self.port is the simulator's port."""

    def setUp(self) -> None:
        """Starts the simulator on the demo's day and makes the folder: self.path is <folder>/demo.db, not yet made."""
        self.server, self.port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.path = self.folder / demo.DB_NAME

    def opened(self) -> sqlite3.Connection:
        """The built store opened again, closed when the test ends: self.opened() reads what build_demo_store wrote."""
        conn = project.open_or_create(self.path)
        self.addCleanup(conn.close)
        return conn


class TheDemoStore(DemoFixture):
    def test_every_fault_names_its_engineer_and_the_outage_shows_cover_and_the_operator(self) -> None:
        demo.build_demo_store(self.path, self.port)
        conn = self.opened()
        faults = project.faults_listing(conn, False)
        self.assertEqual([f.assigned_by for f in faults], [demo.SITE_ENGINEER, demo.INVERTER_ENGINEER, demo.INVERTER_ENGINEER])
        (outage,) = project.faults_listing(conn, True)
        self.assertEqual((outage.asset_id, outage.recorded_by, project.is_cover(conn, outage)),
                         (demo.DOWN, demo.OPERATOR, True))

    def test_the_three_colours_and_who_wears_them(self) -> None:
        state = demo.build_demo_store(self.path, self.port)
        self.assertEqual((state.db_path, state.simulator_port), (self.path, self.port))
        rows = {row.asset_id: row for row in project.asset_rows(self.opened())}
        self.assertEqual(len(rows), 11)
        self.assertEqual({row.status for row in rows.values()}, set(AssetStatus))
        self.assertIs(rows[INV1].status, AssetStatus.GREEN)
        self.assertEqual((rows[INV1].last_run_at, rows[INV1].failing), (RUN_AT, "—"))
        self.assertIs(rows[INV2].status, AssetStatus.RED)
        self.assertIs(rows[SENSOR].status, AssetStatus.YELLOW)
        self.assertEqual(rows[SENSOR].failing, "reachable")
        # 9.2: each colour says why, from the same one call
        self.assertEqual([cells.cause_text(rows[a]) for a in (INV1, INV2, SENSOR)],
                         ["—", "INV-001 since 2026-06-01 11:30 UTC", "suggested SEN-001"])
        self.assertEqual([r.asset_id for r in rows.values() if r.status is not AssetStatus.GREEN], [INV2, SENSOR])
        self.assertEqual({a: s for a, s in state.run_report.statuses.items()}, {a: r.status for a, r in rows.items()})

    def test_the_trackers_and_the_meter_are_green_and_untested(self) -> None:
        demo.build_demo_store(self.path, self.port)
        conn = self.opened()
        for asset_id in UNTESTED:
            self.assertIs(project.asset_status(conn, asset_id), AssetStatus.GREEN)
            self.assertEqual(results.latest_for(conn, asset_id), ())

    def test_the_run_report(self) -> None:
        report = demo.build_demo_store(self.path, self.port).run_report
        # Every test of each pinged asset's kind, and a failed ping's reachable beside them for the two dead feeds (SP-017).
        per_run = (2 * len(remote_registry.tests_for(AssetKind.INVERTER)) + len(remote_registry.tests_for(AssetKind.SENSOR))
                   + 2)
        self.assertEqual((report.pinged, report.records, report.results, report.mails), (3, 0, per_run, 0))
        self.assertEqual(report.errors, tuple(f"{a}: 127.0.0.1:9 is unreachable" for a in (INV2, SENSOR)))

    def test_the_ledger_and_the_telemetry(self) -> None:
        demo.build_demo_store(self.path, self.port)
        conn = self.opened()
        faults = project.faults_listing(conn, False)
        self.assertEqual([(f.asset_id, f.code, f.opened, f.closed) for f in faults], [
            ("OAHE-SIT-001", "SIT-002", at(2026, 6, 1, 12), at(2026, 6, 1, 13)),
            (INV1, "INV-002", at(2026, 6, 1, 10, 5), at(2026, 6, 1, 10, 45)),
            (INV2, "INV-001", at(2026, 6, 1, 11, 30), None),
        ])
        self.assertEqual(conn.execute("SELECT count(*) FROM samples").fetchone()[0], 576)
        inverters = tuple(a for a in demo.demo_assets(self.port) if a.kind is AssetKind.INVERTER)
        seeded = generator.generate(inverters, project.day_period(demo.DAY), 7)
        stored = tuple(s for a in inverters for s in sample_table.in_period(conn, a.asset_id, project.day_period(demo.DAY)))
        self.assertEqual(stored, seeded)

    def test_the_simulator_runs_in_a_daemon_thread_on_its_own_free_port(self) -> None:
        before = set(threading.enumerate())
        server, port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        started = [thread for thread in threading.enumerate() if thread not in before]
        self.assertEqual([thread.daemon for thread in started], [True])
        self.assertNotEqual(port, self.port)
        self.assertEqual(server.server_address, ("127.0.0.1", port))

    def test_the_endpoints(self) -> None:
        assets = {asset.asset_id: asset for asset in demo.demo_assets(self.port)}
        self.assertEqual(len(assets), 11)
        self.assertEqual((assets[INV1].host, assets[INV1].port), ("127.0.0.1", self.port))
        self.assertEqual({(assets[a].host, assets[a].port) for a in (INV2, SENSOR)}, {("127.0.0.1", 9)})
        self.assertEqual({(assets[a].host, assets[a].port) for a in UNTESTED}, {(None, None)})
        self.assertEqual(assets["OAHE-STR-001"], next(a for a in project.demo_fleet() if a.asset_id == "OAHE-STR-001"))
        self.assertIs(assets["OAHE-MTR-001"].kind, AssetKind.METER)

    def test_the_simulator_serves_the_inverters_day(self) -> None:
        samples = demo.simulator_samples()
        self.assertEqual((len(samples), {s.asset_id for s in samples}), (288, {INV1}))
        self.assertEqual(samples, demo.simulator_samples())
        demo.build_demo_store(self.path, self.port)
        self.assertEqual(project.ping_asset(self.opened(), INV1), samples)

    def test_a_second_build_rebuilds_the_store(self) -> None:
        demo.build_demo_store(self.path, self.port)
        again = demo.build_demo_store(self.path, self.port)
        self.assertIs(again.run_report.statuses[INV2], AssetStatus.RED)
        with closing(project.open_or_create(self.path)) as conn:
            self.assertEqual(len(project.faults_listing(conn, False)), 3)
            self.assertEqual(conn.execute("SELECT count(*) FROM samples").fetchone()[0], 576)


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheRunLine(unittest.TestCase):
    def test_the_counts(self) -> None:
        statuses = {"A": AssetStatus.GREEN, "B": AssetStatus.GREEN, "C": AssetStatus.YELLOW, "D": AssetStatus.RED}
        report = project.RunReport(0, 0, 0, statuses, 0, ())
        self.assertEqual(entry.run_line(report), "demo: run - 2 green, 1 yellow, 1 red\n")


@unittest.skipUnless(display_available(), "no display")
class TheDemoWindow(DemoFixture):
    def setUp(self) -> None:
        """The demo run with the current directory set to the fixture's folder, put back when the test ends."""
        super().setUp()
        here = Path.cwd()
        os.chdir(self.folder)
        self.addCleanup(os.chdir, here)

    def test_main_demo_opens_the_three_colours_and_says_each_step(self) -> None:
        seen: list[tuple[str, str]] = []

        def look(root: "tkinter.Tk") -> None:
            """Records the title and the status line, then closes the window: look(root) leaves one entry in seen."""
            root.update()
            frame = root.winfo_children()[0]
            line = next(w for w in frame.winfo_children() if isinstance(w, tkinter.ttk.Label))
            seen.append((root.title(), line.cget("text")))
            root.destroy()

        out = io.StringIO()
        self.assertEqual(entry.main(["--demo"], out, look), 0)
        self.assertEqual(seen, [("Solarpunk fleet — demo (OAHE, 2026-06-01)", "11 assets: 9 green, 1 yellow, 1 red")])
        lines = out.getvalue().splitlines()
        self.assertRegex(lines[0], r"^demo: simulator on 127\.0\.0\.1:\d+$")
        self.assertEqual(lines[1:], ["demo: store demo.db rebuilt", "demo: run - 9 green, 1 yellow, 1 red"])
        self.assertTrue((self.folder / demo.DB_NAME).is_file())

    def test_a_click_opens_the_asset_window_and_add_asset_the_add_window(self) -> None:
        root = tkinter.Tk()
        self.addCleanup(root.destroy)
        conn = entry.run_demo(root, io.StringIO())
        self.addCleanup(conn.close)
        top = tkinter.Toplevel(root)
        fleet = entry.open_fleet(top, conn)
        root.update()
        fleet.canvas.event_generate("<Button-1>", x=100, y=28 + 5)
        root.update()
        opened = [w for w in top.winfo_children() if isinstance(w, AssetWindow)]
        self.assertEqual([w.asset_id for w in opened], [INV2])
        project.assign_fault(conn, INV1, "INV-001", at(2026, 6, 1, 14), ENGINEER)
        opened[0].on_change()
        self.assertEqual(fleet.status_line.cget("text"), "11 assets: 8 green, 1 yellow, 2 red")
        self.assertEqual(fleet.add_button.cget("text"), "Add asset")
        fleet.add_button.invoke()
        root.update()
        added = [w for w in top.winfo_children() if isinstance(w, AddAssetWindow)]
        self.assertEqual(len(added), 1)
