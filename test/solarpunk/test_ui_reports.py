"""The reports window (6.3): its numbers and geometry headless (solarpunk/ui/chart.py imports no tkinter, so the fast
loop's interpreter runs them), the project calls it makes headless (the curve, the CSV, the sites, the day it opens on),
and the window itself over the demo store under a display (xvfb-run -a .venv/bin/pytest test/solarpunk/test_ui_reports.py),
skipping "no tkinter" or "no display" as test_ui.py does (J-025)."""
import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path

from solarpunk import kpi, project
from solarpunk.leaf.clock import Period, at
from solarpunk.leaf.telemetry import Sample, gap
from solarpunk.remote import results
from solarpunk.ui import chart, demo

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import __main__ as entry
    from solarpunk.ui import reports

QUARTER = Period(at(2026, 6, 1, 10), at(2026, 6, 1, 10, 15))
DAY = Period(at(2026, 6, 1), at(2026, 6, 2))
# SOL-13's worked example: the site's row and INV-002's, and the site's curve.
SITE_ROW = kpi.PowerOutput("OAHE-SIT-001", 150.0, 22.25, 135.0, 0.1483, 0.5933, 5, 1)
INV2_ROW = kpi.PowerOutput("OAHE-INV-002", 50.0, 9.75, 45.0, 0.195, 0.78, 3, 0)
EXAMPLE = project.PowerReport(QUARTER, SITE_ROW, (INV2_ROW,), ((QUARTER.start, 90.0), (at(2026, 6, 1, 10, 5), 135.0),
                                                               (at(2026, 6, 1, 10, 10), 42.0)))


def display_available() -> bool:
    """Whether a Tk window can open here: False with no tkinter or no DISPLAY."""
    if not HAS_TKINTER:
        return False
    try:
        tkinter.Tk().destroy()
    except tkinter.TclError:
        return False
    return True


class TheChart(unittest.TestCase):
    def test_the_default_span_is_the_whole_utc_day(self) -> None:
        self.assertEqual(chart.default_span(date(2026, 6, 1)), ("2026-06-01T00:00:00+00:00", "2026-06-02T00:00:00+00:00"))

    def test_table_cells_and_summary(self) -> None:
        self.assertEqual(chart.table_values(INV2_ROW), ("OAHE-INV-002", "50.0", "9.75", "45.0", "0.195", "0.78", "3", "0"))
        self.assertEqual(chart.table_values(kpi.PowerOutput("X", 1.0, 0.0, None, 0.0, 0.0, 0, 3))[3], "—")
        self.assertEqual(chart.summary(EXAMPLE), "OAHE-SIT-001: 22.25 kWh over 0.25 h, peak 135.0 kW, 1 gaps")

    def test_the_axis_top_rounds_up_to_one_two_or_five(self) -> None:
        for peak, top in ((187.22, 200.0), (135.0, 200.0), (42.0, 50.0), (100.0, 100.0), (0.4, 0.5), (0.0, 1.0), (None, 1.0)):
            with self.subTest(peak=peak):
                self.assertAlmostEqual(chart.axis_top(peak), top)

    def test_the_hour_ticks(self) -> None:
        self.assertEqual([t.hour for t in chart.tick_hours(DAY)], [0, 3, 6, 9, 12, 15, 18, 21])
        self.assertEqual(chart.tick_hours(QUARTER), [QUARTER.start])
        self.assertEqual(chart.tick_hours(Period(at(2026, 6, 1, 10, 5), at(2026, 6, 1, 10, 30))), [])

    def test_x_and_y_put_the_axes_at_the_margins(self) -> None:
        self.assertEqual(chart.x_of(DAY.start, DAY, 720), chart.MARGIN)
        self.assertEqual(chart.x_of(at(2026, 6, 1, 12), DAY, 720), 360.0)
        self.assertEqual((chart.y_of(0, 200, 260), chart.y_of(100, 200, 260), chart.y_of(200, 200, 260)),
                         (216.0, 130.0, 44.0))

    def test_a_gap_breaks_the_line_and_is_never_a_zero(self) -> None:
        curve = ((at(2026, 6, 1, 10), 10.0), (at(2026, 6, 1, 10, 5), 20.0), (at(2026, 6, 1, 10, 15), 30.0))
        runs = chart.segments(curve, Period(at(2026, 6, 1, 10), at(2026, 6, 1, 10, 20)), 50.0)
        self.assertEqual([len(run) for run in runs], [2, 1])
        self.assertEqual(chart.segments((), DAY, 1.0), [])


class TheProjectCalls(unittest.TestCase):
    def setUp(self) -> None:
        """An in-memory store with the demo fleet and J-012's seed-7 day."""
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        project.load_fleet(self.conn, project.demo_fleet())
        project.generate_and_store(self.conn, "OAHE", DAY, 7)

    def test_the_curve_holds_only_instants_every_inverter_reported(self) -> None:
        found = project.power_report(self.conn, "OAHE", DAY)
        instants = [instant for instant, _ in found.curve]
        self.assertEqual(instants, sorted(instants))
        self.assertLessEqual(max(power for _, power in found.curve), found.site.peak_kw)
        # 288 instants less every instant either inverter has a gap at: 17 gaps, none at the same instant on both.
        self.assertEqual(len(found.curve), DAY.expected() - found.site.gaps)

    def test_a_one_inverter_gap_is_left_out_not_halved(self) -> None:
        inverters = tuple(a for a in project.demo_fleet() if a.asset_id in ("OAHE-INV-001", "OAHE-INV-002"))
        samples = tuple(Sample(inverter.asset_id, instant, 800.0, 40.0, False)
                        for inverter in inverters for instant in QUARTER.instants())
        self.assertEqual(kpi.site_curve(inverters, samples, QUARTER), tuple((i, 80.0) for i in QUARTER.instants()))
        dropped = (gap("OAHE-INV-002", QUARTER.start), *samples[:3], *samples[4:])
        self.assertEqual(kpi.site_curve(inverters, dropped, QUARTER), tuple((i, 80.0) for i in QUARTER.instants()[1:]))

    def test_the_csv_is_the_command_lines(self) -> None:
        lines = project.report_csv(project.power_report(self.conn, "OAHE", DAY)).splitlines()
        self.assertEqual(lines[0], ",".join(project.OUTPUT_FIELDS))
        self.assertEqual(lines[1], "OAHE-SIT-001,200.0,1591.6242,187.22,7.9581,0.3316,559,17")

    def test_the_sites_and_the_day(self) -> None:
        self.assertEqual(project.report_sites(self.conn), ("OAHE",))
        results.record(self.conn, "reachable", "OAHE-INV-001", at(2026, 6, 1, 13), results.Result(True, "ok"))
        self.assertEqual(project.report_day(self.conn), date(2026, 6, 1))


@unittest.skipUnless(display_available(), "no display")
class TheWindow(unittest.TestCase):
    def setUp(self) -> None:
        """The demo store built in a temporary folder with its simulator running, opened, and a hidden Tk root."""
        server, port = demo.start_simulator(demo.simulator_samples())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        demo.build_demo_store(self.folder / demo.DB_NAME, port)
        self.conn = project.open_or_create(self.folder / demo.DB_NAME)
        self.addCleanup(self.conn.close)
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def test_it_opens_on_the_demo_day_with_the_reports_rows_and_a_curve(self) -> None:
        window = reports.ReportsWindow(self.root, self.conn)
        found = project.power_report(self.conn, "OAHE", DAY)
        self.assertEqual(window.report, found)
        cells = [tuple(window.table.item(item, "values")) for item in window.table.get_children()]
        self.assertEqual(cells, [chart.table_values(row) for row in project.report_rows(found)])
        self.assertGreater(len(window.canvas.find_withtag("curve")), 0)
        self.assertEqual(window.error["text"], "")

    def test_a_refusal_is_shown_and_clears_the_report(self) -> None:
        window = reports.ReportsWindow(self.root, self.conn)
        window.start.set("2026-06-02T00:00:00+00:00")
        window.end.set("2026-06-01T00:00:00+00:00")
        window.show()
        self.assertIsNone(window.report)
        self.assertIn("is empty or reversed", str(window.error["text"]))
        self.assertEqual(window.table.get_children(), ())
        window.site.set("BIGS")
        window.end.set("2026-06-03T00:00:00+00:00")
        window.show()
        self.assertEqual(str(window.error["text"]), "BIGS-SIT-001 is not in the fleet")

    def test_save_writes_the_command_lines_csv(self) -> None:
        path = self.folder / "report.csv"
        window = reports.ReportsWindow(self.root, self.conn, ask_path=lambda: str(path))
        self.assertEqual(window.save(), str(path))
        self.assertEqual(path.read_text(encoding="utf-8"), project.report_csv(window.report))
        self.assertIsNone(reports.ReportsWindow(self.root, self.conn, ask_path=lambda: "").save())

    def test_the_fleet_window_has_a_reports_button_that_opens_it(self) -> None:
        fleet = entry.open_fleet(self.root, self.conn)
        before = len(self.root.winfo_children())
        fleet.reports_button.invoke()
        self.assertEqual(len(self.root.winfo_children()), before + 1)
        self.assertEqual(self.root.winfo_children()[-1].title(), reports.TITLE)


if __name__ == "__main__":
    unittest.main()
