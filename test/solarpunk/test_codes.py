"""The fault-code catalogue holds its shape: unique well-formed codes, each prefix its kind, lookups exact, outsiders refused."""
import unittest

from solarpunk.leaf import codes
from solarpunk.leaf.codes import CATALOGUE, AssetKind, FaultCode, Severity, UnknownFaultCode


class TheCatalogue(unittest.TestCase):
    def test_every_code_is_unique_and_well_formed(self) -> None:
        seen = [fault.code for fault in CATALOGUE]
        self.assertEqual(len(seen), len(set(seen)))
        for fault in CATALOGUE:
            prefix, number = codes.parse(fault.code)
            self.assertEqual(prefix, fault.kind.value, fault.code)
            self.assertGreaterEqual(number, 1, fault.code)

    def test_every_kind_has_at_least_one_code_and_a_meaning(self) -> None:
        for kind in AssetKind:
            rows = codes.codes_for(kind)
            self.assertGreaterEqual(len(rows), 1, kind)
            self.assertTrue(all(row.kind is kind and row.meaning.strip() for row in rows), kind)

    def test_codes_for_keeps_catalogue_order(self) -> None:
        self.assertEqual([f.code for f in codes.codes_for(AssetKind.TRACKER)], ["TRK-001", "TRK-002"])
        self.assertEqual([f.code for f in codes.codes_for(AssetKind.INVERTER)], ["INV-001", "INV-002", "INV-003", "INV-004"])

    def test_lookup_returns_the_row_itself(self) -> None:
        row = codes.lookup("INV-001")
        self.assertIs(row, CATALOGUE[3])
        self.assertIs(row.severity, Severity.OUTAGE)
        self.assertIs(row.kind, AssetKind.INVERTER)

    def test_lookup_refuses_an_unknown_and_a_malformed_code(self) -> None:
        with self.assertRaises(UnknownFaultCode) as unknown:
            codes.lookup("INV-999")
        self.assertEqual(str(unknown.exception), "INV-999 is not in the catalogue")
        for bad in ("inv-001", "INV001", "INV-1", "INVX-001", "", "INV-0011"):
            with self.assertRaises(UnknownFaultCode, msg=bad) as malformed:
                codes.lookup(bad)
            self.assertEqual(str(malformed.exception), f"{bad!r} is not of the shape AAA-000")

    def test_parse_splits_prefix_and_number(self) -> None:
        self.assertEqual(codes.parse("INV-001"), ("INV", 1))
        self.assertEqual(codes.parse("ZZZ-999"), ("ZZZ", 999))


class TheSeverity(unittest.TestCase):
    def test_only_an_outage_counts_against_availability(self) -> None:
        by_severity = {s: FaultCode("XXX-001", AssetKind.SITE, s, "x").counts_against_availability() for s in Severity}
        self.assertEqual(by_severity, {Severity.INFO: False, Severity.DERATE: False, Severity.OUTAGE: True})

    def test_severities_order_lowest_first(self) -> None:
        self.assertEqual([s.value for s in Severity], [1, 2, 3])
        self.assertLess(Severity.INFO.value, Severity.DERATE.value)
        self.assertLess(Severity.DERATE.value, Severity.OUTAGE.value)

    def test_the_catalogue_uses_every_severity(self) -> None:
        self.assertEqual({fault.severity for fault in CATALOGUE}, set(Severity))


class TheListing(unittest.TestCase):
    def test_one_line_per_row_in_order_with_the_four_fields(self) -> None:
        lines = codes.listing().splitlines()
        self.assertEqual(len(lines), len(CATALOGUE))
        self.assertTrue(lines[0].startswith("SIT-001 SITE OUTAGE Grid outage"))
        self.assertEqual(lines[-1], "SEN-001 SENSOR INFO " + CATALOGUE[-1].meaning)
        self.assertEqual([line.split(" ", 1)[0] for line in lines], [fault.code for fault in CATALOGUE])
        self.assertEqual([line.split(" ")[1] for line in lines], [fault.kind.name for fault in CATALOGUE])
