"""The thin CLI (lane 1.7) over a store file: each subcommand's printed lines pinned, J-012's OAHE day driven through it
end to end, every refusal printed as "error: ..." with exit 2, and the clauses report run as a subprocess (MOD-02)."""
import io
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from solarpunk import project
from solarpunk.cli import main as cli
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind

ROOT = Path(__file__).resolve().parents[2]
SITE_EMAIL = "site@oahe.example"
INVERTER_EMAIL = "inverter@oahe.example"
START = "2026-06-01T00:00:00+00:00"
END = "2026-06-02T00:00:00+00:00"

# The OAHE example fleet, copied from test/solarpunk/test_fleet.py, never imported (MOD-05): project.demo_fleet's rows.
OAHE: tuple[Asset, ...] = (
    Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None, location="Pierre, SD",
          engineer_email=SITE_EMAIL),
    Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 1", 100.0, "10.0.0.1", 5020,
          "Pad A", INVERTER_EMAIL),
    Asset("OAHE-INV-002", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 2", 100.0, "10.0.0.2", 5020, "Pad B"),
    Asset("OAHE-STR-001", AssetKind.STRING, "OAHE", "OAHE-INV-001", "String 1", 50.0),
    Asset("OAHE-STR-002", AssetKind.STRING, "OAHE", "OAHE-INV-001", "String 2", 50.0),
    Asset("OAHE-STR-003", AssetKind.STRING, "OAHE", "OAHE-INV-002", "String 3", 50.0),
    Asset("OAHE-STR-004", AssetKind.STRING, "OAHE", "OAHE-INV-002", "String 4", 50.0),
    Asset("OAHE-TRK-001", AssetKind.TRACKER, "OAHE", "OAHE-SIT-001", "Tracker 1", None, "10.0.0.11", 502),
    Asset("OAHE-TRK-002", AssetKind.TRACKER, "OAHE", "OAHE-SIT-001", "Tracker 2", None, "10.0.0.12", 502),
    Asset("OAHE-MTR-001", AssetKind.METER, "OAHE", "OAHE-SIT-001", "Revenue meter", None, "10.0.0.21", 1),
    Asset("OAHE-SEN-001", AssetKind.SENSOR, "OAHE", None, "Irradiance sensor", None, "10.0.0.31", 65535),
)
# A second site, so a listing that forgot its site, or sorted by kind rather than id, would be caught.
BIGS: tuple[Asset, ...] = (
    Asset("BIGS-SIT-001", AssetKind.SITE, "BIGS", None, "Big Stone", None),
    Asset("BIGS-INV-001", AssetKind.INVERTER, "BIGS", "BIGS-SIT-001", "Inverter 1", 50.0),
)
OAHE_LIST = [
    "OAHE-INV-001  INV  Inverter 1  green",
    "OAHE-INV-002  INV  Inverter 2  green",
    "OAHE-MTR-001  MTR  Revenue meter  green",
    "OAHE-SEN-001  SEN  Irradiance sensor  green",
    "OAHE-SIT-001  SIT  Oahe  green",
    "OAHE-STR-001  STR  String 1  green",
    "OAHE-STR-002  STR  String 2  green",
    "OAHE-STR-003  STR  String 3  green",
    "OAHE-STR-004  STR  String 4  green",
    "OAHE-TRK-001  TRK  Tracker 1  green",
    "OAHE-TRK-002  TRK  Tracker 2  green",
]
STATUS_IDS = ["OAHE-INV-001", "OAHE-INV-002", "OAHE-MTR-001", "OAHE-SEN-001", "OAHE-SIT-001", "OAHE-STR-001",
              "OAHE-STR-002", "OAHE-STR-003", "OAHE-STR-004", "OAHE-TRK-001", "OAHE-TRK-002"]
SITE_FAULT = "1 OAHE-SIT-001 SIT-002 2026-06-01T12:00:00+00:00 2026-06-01T13:00:00+00:00"
OUTAGE_OPEN = "2 OAHE-INV-001 INV-001 2026-06-01T12:30:00+00:00 open"
OUTAGE_CLOSED = "2 OAHE-INV-001 INV-001 2026-06-01T12:30:00+00:00 2026-06-01T14:30:00+00:00"


def kpi_lines(availability: str, inverters: str, energy_yield: str, faults_open: int, inverter_status: str) -> list[str]:
    """J-012's OAHE day as the kpi subcommand prints it, the parts that differ given: kpi_lines(...)[0] is the
    availability argument, [-11] "status OAHE-INV-001 " plus inverter_status."""
    kinds = [f"reliability {kind} mtbf_h=None mttr_h=None count=0 open=0" for kind in ("SIT", "INV", "STR", "TRK")]
    kinds[1] = inverters
    return [
        availability,
        "availability OAHE-INV-002 1.0 expected=288 excluded=12 down=0 gaps=8",
        "performance_ratio 0.9202 energy_kwh=1591.6242 reference_kwh=1729.735 unreliable=17",
        energy_yield,
        *kinds,
        "reliability MTR mtbf_h=None mttr_h=None count=0 open=0",
        "reliability SEN mtbf_h=None mttr_h=None count=0 open=0",
        f"faults_open {faults_open}",
        f"status OAHE-INV-001 {inverter_status}",
        *[f"status {asset_id} green" for asset_id in STATUS_IDS[1:]],
    ]


class Cli(unittest.TestCase):
    """A test case with a store file of its own, removed when it ends."""

    def setUp(self) -> None:
        """A fresh folder; self.db is a store path in it that does not exist yet."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = str(Path(folder.name) / "solarpunk.db")

    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        """main over self.db: self.run_cli(["fleet", "load", "--demo"]) is (0, "loaded 11 assets\\n", "")."""
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["--db", self.db, *argv], out, err)
        return code, out.getvalue(), err.getvalue()

    def ok(self, argv: list[str]) -> list[str]:
        """The lines a successful call prints, asserting exit 0 and nothing on stderr: self.ok(["fault", "list"]) is []
        on a fresh store."""
        code, out, err = self.run_cli(argv)
        self.assertEqual((code, err), (0, ""))
        return out.splitlines()

    def refused(self, argv: list[str], message: str) -> None:
        """Asserts the call exits 2 with "error: <message>" alone on stderr and nothing on stdout."""
        self.assertEqual(self.run_cli(argv), (2, "", f"error: {message}\n"))

    def oahe_day(self) -> None:
        """The demo fleet loaded and 2026-06-01's seed-7 telemetry stored through the CLI, each printing its count."""
        self.assertEqual(self.ok(["fleet", "load", "--demo"]), ["loaded 11 assets"])
        self.assertEqual(self.ok(["telemetry", "generate", "OAHE", "2026-06-01", "--seed", "7"]), ["stored 576 samples"])


class TheFleet(Cli):
    def test_the_demo_fleet_is_the_oahe_example(self) -> None:
        self.assertEqual(project.demo_fleet(), OAHE)

    def test_load_then_list_across_two_calls(self) -> None:
        self.assertEqual(self.ok(["fleet", "load", "--demo"]), ["loaded 11 assets"])
        self.assertEqual(self.ok(["fleet", "list"]), OAHE_LIST)
        self.assertEqual(self.ok(["fleet", "list", "--site", "OAHE"]), OAHE_LIST)

    def test_list_is_in_id_order_and_filters_by_site(self) -> None:
        self.ok(["fleet", "load", "--demo"])
        conn = project.open_or_create(self.db)
        project.load_fleet(conn, BIGS)
        conn.close()
        bigs = ["BIGS-INV-001  INV  Inverter 1  green", "BIGS-SIT-001  SIT  Big Stone  green"]
        self.assertEqual(self.ok(["fleet", "list", "--site", "BIGS"]), bigs)
        self.assertEqual(self.ok(["fleet", "list"]), bigs + OAHE_LIST)

    def test_a_second_load_is_refused(self) -> None:
        self.ok(["fleet", "load", "--demo"])
        self.refused(["fleet", "load", "--demo"], "OAHE-SIT-001 is already registered")

    def test_load_needs_demo(self) -> None:
        code, out, err = self.run_cli(["fleet", "load"])
        self.assertEqual((code, out), (2, ""))
        self.assertIn("the following arguments are required: --demo", err)


class TheStoreFile(Cli):
    def test_a_new_file_gets_every_table_and_reopens_with_its_rows(self) -> None:
        project.open_or_create(self.db).close()
        conn = project.open_or_create(self.db)
        names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid")]
        conn.close()
        self.assertEqual(names, ["assets", "faults", "samples", "results", "mails", "work_orders"])  # every module's table (2.7, 4.1)

    def test_a_file_missing_a_table_is_not_taken_as_a_store(self) -> None:
        conn = sqlite3.connect(self.db)
        conn.execute("CREATE TABLE assets (x)")
        conn.execute("CREATE TABLE faults (x)")
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(sqlite3.OperationalError, "table assets already exists"):
            project.open_or_create(self.db)


class TheFaults(Cli):
    def test_assign_close_and_list(self) -> None:
        self.ok(["fleet", "load", "--demo"])
        self.assertEqual(self.ok(["fault", "assign", "OAHE-SIT-001", "SIT-002", "2026-06-01T12:00:00+00:00"]),
                         ["1 OAHE-SIT-001 SIT-002 2026-06-01T12:00:00+00:00 open"])
        self.assertEqual(self.ok(["fault", "close", "1", "2026-06-01T13:00:00+00:00"]), [SITE_FAULT])
        self.assertEqual(self.ok(["fault", "assign", "OAHE-INV-001", "INV-001", "2026-06-01T12:30:00+00:00"]),
                         [OUTAGE_OPEN])
        self.assertEqual(self.ok(["fault", "list"]), [SITE_FAULT, OUTAGE_OPEN])
        self.assertEqual(self.ok(["fault", "list", "--open"]), [OUTAGE_OPEN])
        self.assertEqual(self.ok(["fleet", "list", "--site", "OAHE"])[0], "OAHE-INV-001  INV  Inverter 1  red")

    def test_every_refusal_is_an_error_line_and_exit_2(self) -> None:
        self.ok(["fleet", "load", "--demo"])
        self.refused(["fault", "assign", "OAHE-INV-009", "INV-001", "2026-06-01T10:00:00+00:00"],
                     "OAHE-INV-009 is not in the fleet")
        self.refused(["fault", "assign", "OAHE-INV-001", "INV-999", "2026-06-01T10:00:00+00:00"],
                     "INV-999 is not in the catalogue")
        self.refused(["fault", "assign", "OAHE-INV-001", "INV-001", "2026-06-01T10:00:00"],
                     "2026-06-01T10:00:00 is not UTC")
        self.refused(["fault", "assign", "OAHE-INV-001", "INV-001", "soon"], "Invalid isoformat string: 'soon'")
        self.refused(["fault", "close", "9", "2026-06-01T10:00:00+00:00"], "fault 9 is not in the ledger")
        self.assertEqual(self.ok(["fault", "list"]), [])

    def test_a_fault_id_must_be_a_number(self) -> None:
        code, out, err = self.run_cli(["fault", "close", "one", "2026-06-01T10:00:00+00:00"])
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("usage: "))
        self.assertIn("invalid int value: 'one'", err)


class TheKpis(Cli):
    def test_j012s_day_while_the_outage_is_open(self) -> None:
        self.oahe_day()
        self.ok(["fault", "assign", "OAHE-SIT-001", "SIT-002", "2026-06-01T12:00:00+00:00"])
        self.ok(["fault", "close", "1", "2026-06-01T13:00:00+00:00"])
        self.ok(["fault", "assign", "OAHE-INV-001", "INV-001", "2026-06-01T12:30:00+00:00"])
        self.assertEqual(self.ok(["kpi", "OAHE", START, END]), kpi_lines(
            "availability OAHE-INV-001 0.5217 expected=288 excluded=12 down=132 gaps=9",
            "reliability INV mtbf_h=None mttr_h=None count=0 open=1",
            "energy_yield 1591.6242 source=inverters", 1, "red"))

    def test_j012s_day_closed_with_a_meter_reading(self) -> None:
        self.oahe_day()
        self.ok(["fault", "assign", "OAHE-SIT-001", "SIT-002", "2026-06-01T12:00:00+00:00"])
        self.ok(["fault", "close", "1", "2026-06-01T13:00:00+00:00"])
        self.ok(["fault", "assign", "OAHE-INV-001", "INV-001", "2026-06-01T12:30:00+00:00"])
        self.assertEqual(self.ok(["fault", "close", "2", "2026-06-01T14:30:00+00:00"]), [OUTAGE_CLOSED])
        self.assertEqual(self.ok(["kpi", "OAHE", START, END, "--meter-kwh", "900"]), kpi_lines(
            "availability OAHE-INV-001 0.9348 expected=288 excluded=12 down=18 gaps=9",
            "reliability INV mtbf_h=46.0 mttr_h=2.0 count=1 open=0",
            "energy_yield 900.0 source=meter", 0, "green"))

    def test_a_bad_period_or_site_is_refused(self) -> None:
        self.oahe_day()
        self.refused(["kpi", "OAHE", END, START], f"period {END} .. {START} is empty or reversed")
        self.refused(["kpi", "OAHE", START, "2026-06-02T00:00:00"], "2026-06-02T00:00:00 is not UTC")
        self.refused(["kpi", "BIGS", START, END], "BIGS-SIT-001 is not in the fleet")

    def test_a_bad_day_is_refused(self) -> None:
        self.refused(["telemetry", "generate", "OAHE", "June", "--seed", "7"], "Invalid isoformat string: 'June'")


class TheParser(Cli):
    def test_the_store_defaults_to_solarpunk_db_here(self) -> None:
        self.assertEqual(cli.build_parser().parse_args(["fleet", "list"]).db, "solarpunk.db")

    def test_help_exits_0_with_the_usage_and_the_instant_format(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(cli.main(["--help"], out, err), 0)
        self.assertTrue(out.getvalue().startswith("usage: python3 -m solarpunk.cli "))
        self.assertIn("\nInstants are UTC: 2026-06-01T10:00:00+00:00.\n", out.getvalue())
        self.assertEqual(err.getvalue(), "")

    def test_a_missing_subcommand_is_a_usage_error(self) -> None:
        for argv in ([], ["fleet"], ["fault"], ["telemetry"], ["telemetry", "generate", "OAHE", "2026-06-01"]):
            with self.subTest(argv=argv):
                code, out, err = self.run_cli(argv)
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("usage: python3 -m solarpunk.cli "))
                self.assertIn("error: the following arguments are required", err)

    def test_python_dash_m_runs_main(self) -> None:
        argv = [sys.executable, "-m", "solarpunk.cli", "--db", self.db, "fleet", "load", "--demo"]
        done = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False, env=dict(os.environ))
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "loaded 11 assets\n", ""))


class TheClauses(Cli):
    def test_it_runs_the_report_isolated_from_the_root_and_passes_it_through(self) -> None:
        done = subprocess.CompletedProcess([], 3, stdout="report\n", stderr="warning\n")
        with mock.patch.object(cli.subprocess, "run", return_value=done) as run:
            self.assertEqual(self.run_cli(["clauses"]), (3, "report\n", "warning\n"))
        run.assert_called_once_with([sys.executable, "-I", "scripts/clauses.py"], cwd=ROOT, capture_output=True,
                                    text=True, check=False)
        self.assertFalse(Path(self.db).exists())

    @unittest.skipUnless((ROOT / "scripts" / "clauses.py").exists(), "mutmut's copy holds no scripts/")
    def test_the_real_report_runs(self) -> None:
        code, out, err = self.run_cli(["clauses"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("\n9001: ", out)
