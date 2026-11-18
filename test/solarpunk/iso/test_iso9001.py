"""The ISO 9001 rows of docs/CLAUSE-REGISTER.md: one test per held row, its docstring's first line `Clause: 9001-x.y.z`
(SOL-12). Each asserts the thing in this repository that flags the requirement; the words are the project's own."""
import re
import unittest
from pathlib import Path

from solarpunk.leaf import codes
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import CATALOGUE, Severity, UnknownFaultCode
from solarpunk.leaf.faults import Fault
from solarpunk.leaf.clock import Period
from solarpunk.leaf.telemetry import Sample, gap
from solarpunk.kpi import availability

ROOT = Path(__file__).resolve().parents[3]
ENTRY = re.compile(r"^### ([A-Z]{1,3}-\d{3}): .*?(?=^### |^## |\Z)", re.MULTILINE | re.DOTALL)
SECTION = re.compile(r"^## (SOL-\d{2}) .*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
FORMULA = re.compile(r"^    \w+\s+= ", re.MULTILINE)
FINDING = re.compile(r"^\| (F-\d{3}) \|(.*)\|\s*$", re.MULTILINE)


def decisions(text: str) -> dict[str, str]:
    """theGhost.md's entries by id, fenced examples left out: "### SP-001: x\\n- **Why:** y\\n" gives {"SP-001": ...}."""
    prose = re.sub(r"^```.*?^```", "", text, flags=re.MULTILINE | re.DOTALL)
    return {match.group(1): match.group(0) for match in ENTRY.finditer(prose)}


def sections_with_a_formula(contract: str) -> dict[str, str]:
    """The contract's SOL sections that state a formula (an indented `name = ...` line): SOL-07, SOL-08, SOL-10."""
    return {match.group(1): match.group(0) for match in SECTION.finditer(contract) if FORMULA.search(match.group(0))}


class Iso9001(unittest.TestCase):
    def test_a_kpi_reports_its_gaps_beside_the_number(self) -> None:
        """Clause: 9001-9.1.3
        A KPI says how many of its expected samples were missing: the contract's SOL-07 example, with one gap at 10:40,
        reports gaps 1 beside availability 0.7, never the number alone."""
        period = Period(at(2026, 6, 1, 10), at(2026, 6, 1, 11))
        faults = (Fault(1, "OAHE-SIT-001", "SIT-002", at(2026, 6, 1, 10, 5), at(2026, 6, 1, 10, 15)),
                  Fault(2, "OAHE-INV-001", "INV-001", at(2026, 6, 1, 10, 10), at(2026, 6, 1, 10, 30)))
        samples: tuple[Sample, ...] = (gap("OAHE-INV-001", at(2026, 6, 1, 10, 40)),)
        result = availability(period, faults, samples)
        self.assertEqual((result.value, result.gaps), (0.7, 1))

    def test_every_decision_has_a_why_and_a_holder(self) -> None:
        """Clause: 9001-7.5.2
        Each entry in theGhost.md carries a non-empty Why and Held by line."""
        entries = decisions((ROOT / "theGhost.md").read_text())
        self.assertIn("SP-001", entries)
        for rid, entry in entries.items():
            self.assertRegex(entry, r"(?m)^- \*\*Why:\*\* \S", rid)
            self.assertRegex(entry, r"(?m)^- \*\*Held by:\*\* \S", rid)

    def test_the_catalogue_is_one_list_with_a_meaning_per_code(self) -> None:
        """Clause: 9001-7.5.3
        The fault-code catalogue holds each code once, each with a written meaning, and the lookup is the list itself."""
        seen = [fault.code for fault in CATALOGUE]
        self.assertEqual(len(seen), len(set(seen)))
        for fault in CATALOGUE:
            self.assertTrue(fault.meaning.strip(), fault.code)
            self.assertIs(codes.lookup(fault.code), fault)
        self.assertEqual(len(codes.listing().splitlines()), len(CATALOGUE))

    def test_an_unknown_code_is_refused(self) -> None:
        """Clause: 9001-8.7.1
        A well-formed code outside the catalogue and a malformed one are both refused by the lookup and by a fault."""
        for outsider in ("INV-999", "inv-1", ""):
            with self.assertRaises(UnknownFaultCode, msg=outsider):
                codes.lookup(outsider)
        with self.assertRaises(UnknownFaultCode):
            Fault(1, "OAHE-INV-003", "INV-999", at(2026, 6, 1, 10), None)

    def test_a_fault_records_its_asset_code_and_instant(self) -> None:
        """Clause: 9001-8.7.2
        A fault keeps the asset, the catalogue code and its opening instant, and its code leads back to the catalogue row."""
        fault = Fault(7, "OAHE-INV-003", "INV-001", at(2026, 6, 1, 10, 10), None)
        self.assertEqual((fault.asset_id, fault.code, fault.opened), ("OAHE-INV-003", "INV-001", at(2026, 6, 1, 10, 10)))
        self.assertIs(fault.catalogue_row().severity, Severity.OUTAGE)
        self.assertIsNone(fault.duration())

    def test_every_kpi_has_a_worked_example(self) -> None:
        """Clause: 9001-9.1.1
        Every section of docs/CONTRACT.md that states a formula also gives a worked example a person checks by hand."""
        sections = sections_with_a_formula((ROOT / "docs" / "CONTRACT.md").read_text())
        self.assertGreaterEqual(set(sections), {"SOL-07", "SOL-08", "SOL-10"})
        for sid, text in sections.items():
            self.assertIn("Worked example", text, sid)

    def test_every_finding_keeps_its_evidence(self) -> None:
        """Clause: 9001-10.2.2
        Each row of docs/FINDINGS.md has evidence and a status of open or resolved."""
        rows = FINDING.findall((ROOT / "docs" / "FINDINGS.md").read_text())
        self.assertGreaterEqual(len(rows), 1)
        for fid, rest in rows:
            cells = [cell.strip() for cell in rest.split("|")]
            self.assertEqual(len(cells), 4, fid)
            self.assertTrue(cells[1], fid)
            self.assertRegex(cells[3], r"^(open|resolved)\b", fid)
