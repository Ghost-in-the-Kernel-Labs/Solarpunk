"""The ISO 55000 rows of docs/CLAUSE-REGISTER.md (clause numbers ISO 55001:2014's): one test per held row, its
docstring's first line `Clause: 55000-x.y` (SOL-12). Each asserts the thing in this repository that flags the
requirement; the words are the project's own."""
import unittest

from solarpunk.leaf import codes, kpi_defs
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import CATALOGUE, AssetKind, Severity
from solarpunk.leaf.telemetry import Sample, gap


class Iso55000(unittest.TestCase):
    def test_the_kpi_numbers_name_catalogue_codes(self) -> None:
        """Clause: 55000-6.2.1
        Every code the KPI contract's numbers exclude or distrust is a catalogue code of a site, sensor or meter."""
        named = set(kpi_defs.EXCLUDED_CODES) | {kpi_defs.UNRELIABLE_IRRADIANCE_CODE, kpi_defs.METER_LOST_CODE}
        self.assertEqual(len(named), 5)
        for code in named:
            self.assertIn(codes.lookup(code).kind, (AssetKind.SITE, AssetKind.SENSOR, AssetKind.METER), code)

    def test_an_asset_names_its_engineer(self) -> None:
        """Clause: 55000-6.2.2
        An asset carries the address of the engineer who services it, and an address of the wrong shape is refused."""
        asset = Asset("OAHE-INV-003", AssetKind.INVERTER, "OAHE", None, "Inverter 3", 100.0,
                      engineer_email="field@example.com")
        self.assertEqual(asset.engineer_email, "field@example.com")
        with self.assertRaises(ValueError):
            Asset("OAHE-INV-003", AssetKind.INVERTER, "OAHE", None, "Inverter 3", 100.0, engineer_email="not an address")

    def test_a_missing_reading_is_stored_as_a_gap(self) -> None:
        """Clause: 55000-7.5
        A reading that never arrived is a sample marked as a gap with no values; a gap carrying values is refused."""
        missing = gap("OAHE-INV-003", at(2026, 6, 1, 10, 20))
        self.assertEqual((missing.gap, missing.irradiance_w_m2, missing.power_kw), (True, None, None))
        with self.assertRaises(ValueError):
            Sample("OAHE-INV-003", at(2026, 6, 1, 10, 20), 812.0, None, True)

    def test_only_an_outage_counts_against_availability(self) -> None:
        """Clause: 55000-9.1
        Of the catalogue's rows, exactly the OUTAGE ones count against availability; a derate or a notice never does."""
        for fault in CATALOGUE:
            self.assertEqual(fault.counts_against_availability(), fault.severity is Severity.OUTAGE, fault.code)
        self.assertTrue(any(fault.severity is Severity.DERATE for fault in CATALOGUE))
