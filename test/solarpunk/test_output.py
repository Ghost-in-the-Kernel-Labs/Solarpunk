"""Power output (6.1, SOL-13): the contract's worked example as a golden, the refusals, the samples a row leaves out,
the site report over J-012's OAHE day (its energy the performance ratio's, SOL-08, computed apart), and the report
subcommand's lines and CSV."""
import io
import tempfile
import unittest
from pathlib import Path

from solarpunk import kpi, project
from solarpunk.cli import main as cli
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import Period, at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample, gap

INV1 = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 1", 100.0)
INV2 = Asset("OAHE-INV-002", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 2", 50.0)
QUARTER = Period(at(2026, 6, 1, 10), at(2026, 6, 1, 10, 15))
T0, T1, T2 = QUARTER.instants()
START = "2026-06-01T00:00:00+00:00"
END = "2026-06-02T00:00:00+00:00"


def reading(asset: Asset, moment, power: float) -> Sample:
    """A sample with a power and an irradiance beside it: reading(INV1, T0, 60.0).power_kw is 60.0."""
    return Sample(asset.asset_id, moment, 800.0, power, False)


# SOL-13's worked example: INV-001 60, 90 kW and a gap; INV-002 30, 45, 42 kW.
EXAMPLE = (reading(INV1, T0, 60.0), reading(INV1, T1, 90.0), gap(INV1.asset_id, T2),
           reading(INV2, T0, 30.0), reading(INV2, T1, 45.0), reading(INV2, T2, 42.0))


class TheContractsExample(unittest.TestCase):
    def test_each_inverter(self) -> None:
        self.assertEqual(kpi.inverter_output(INV1, EXAMPLE, QUARTER),
                         kpi.PowerOutput("OAHE-INV-001", 100.0, 12.5, 90.0, 0.125, 0.5, 2, 1))
        self.assertEqual(kpi.inverter_output(INV2, EXAMPLE, QUARTER),
                         kpi.PowerOutput("OAHE-INV-002", 50.0, 9.75, 45.0, 0.195, 0.78, 3, 0))

    def test_the_site_sums_and_takes_the_coincident_peak(self) -> None:
        self.assertEqual(kpi.site_output("OAHE-SIT-001", (INV1, INV2), EXAMPLE, QUARTER),
                         kpi.PowerOutput("OAHE-SIT-001", 150.0, 22.25, 135.0, 0.1483, 0.5933, 5, 1))


class WhatARowLeavesOut(unittest.TestCase):
    def test_other_assets_and_instants_outside_the_period(self) -> None:
        late = reading(INV1, at(2026, 6, 1, 10, 15), 99.0)
        self.assertEqual(kpi.inverter_output(INV1, (*EXAMPLE, late), QUARTER),
                         kpi.inverter_output(INV1, EXAMPLE, QUARTER))

    def test_only_gaps_give_no_peak_and_no_energy(self) -> None:
        gaps = tuple(gap(INV1.asset_id, moment) for moment in QUARTER.instants())
        self.assertEqual(kpi.inverter_output(INV1, gaps, QUARTER),
                         kpi.PowerOutput("OAHE-INV-001", 100.0, 0.0, None, 0.0, 0.0, 0, 3))
        self.assertEqual(kpi.site_output("OAHE-SIT-001", (INV1,), gaps, QUARTER).peak_kw, None)


class TheRefusals(unittest.TestCase):
    def test_no_rating_is_refused_never_read_as_zero(self) -> None:
        unrated = Asset("OAHE-INV-009", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 9", None)
        with self.assertRaisesRegex(ValueError, "OAHE-INV-009: no rated power"):
            kpi.inverter_output(unrated, EXAMPLE, QUARTER)

    def test_a_zero_rating_is_refused(self) -> None:
        zero = Asset("OAHE-INV-009", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 9", 0.0)
        with self.assertRaisesRegex(ValueError, "rated power 0.0 kW cannot divide a yield"):
            kpi.inverter_output(zero, EXAMPLE, QUARTER)


class TheReport(unittest.TestCase):
    def setUp(self) -> None:
        """A store file holding the demo fleet and J-012's seed-7 day."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "solarpunk.db")
        conn = project.open_or_create(self.db)
        project.load_fleet(conn, project.demo_fleet())
        project.generate_and_store(conn, "OAHE", project.day_period(at(2026, 6, 1).date()), 7)
        conn.close()

    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        """main over self.db: self.run_cli(["report", "OAHE", START, END])[0] is 0."""
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["--db", self.db, *argv], out, err)
        return code, out.getvalue(), err.getvalue()

    def test_the_sites_energy_is_the_performance_ratios(self) -> None:
        conn = project.open_or_create(self.db)
        self.addCleanup(conn.close)
        day = project.day_period(at(2026, 6, 1).date())
        found = project.power_report(conn, "OAHE", day)
        self.assertEqual(found.site.energy_kwh, project.kpis_for(conn, "OAHE", day).performance_ratio.energy_kwh)
        self.assertEqual([row.asset_id for row in found.inverters], ["OAHE-INV-001", "OAHE-INV-002"])
        self.assertEqual(found.site.records + found.site.gaps, 576)

    def test_the_subcommands_lines(self) -> None:
        code, out, err = self.run_cli(["report", "OAHE", START, END])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines()[0], "output OAHE-SIT-001 rated_kw=200.0 energy_kwh=1591.6242 peak_kw=187.22"
                                              " specific_yield=7.9581 capacity_factor=0.3316 records=559 gaps=17")
        self.assertEqual(len(out.splitlines()), 3)

    def test_the_csv(self) -> None:
        code, out, _ = self.run_cli(["report", "OAHE", START, END, "--csv"])
        lines = out.splitlines()
        self.assertEqual((code, lines[0]), (0, ",".join(cli.OUTPUT_FIELDS)))
        self.assertEqual(lines[2], "OAHE-INV-001,100.0,799.9658,94.35,7.9997,0.3333,279,9")

    def test_an_unknown_site_is_refused(self) -> None:
        self.assertEqual(self.run_cli(["report", "BIGS", START, END]), (2, "", "error: BIGS-SIT-001 is not in the fleet\n"))


if __name__ == "__main__":
    unittest.main()
