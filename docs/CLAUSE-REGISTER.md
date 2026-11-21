# The clause register: each ISO 9001 or ISO 55000 clause this project speaks of, and the test that flags it

This register lists the requirements of ISO 9001:2015 and of the ISO 55000 family that this
project's checks can flag, one row per clause, each held by a test tagged with that clause
(`Clause: 9001-9.1.3` the first line of its docstring) (SOL-12). This project claims conformance to
nothing: the register says which requirements its checks can flag, and that is all. The
requirement column is in the project's own words; no sentence or clause title of either standard
is reproduced here, and the clause number is the only thing taken from it. The `55000-` clause
numbers are ISO 55001:2014's, the family's requirements document. A row whose test does not yet
exist is `open`, with `—` for its test; `held` means a test exists and is tagged. Whether a held
row's test passes today is the report's to say: `python3 -I scripts/clauses.py` prints each clause
`held`, `failing` or `open`. The check `scripts/checks/clauses.py` (run by `test/test_clauses.py`)
refuses a held row with no tagged test and a tagged test with no row.

| Clause | Requirement (our words) | Held by | Status |
| --- | --- | --- | --- |
| 9001-7.5.2 | Each recorded decision says why it was made and what keeps it true | test/solarpunk/iso/test_iso9001.py::test_every_decision_has_a_why_and_a_holder | held |
| 9001-7.5.3 | The list of fault codes is one controlled list: each code unique, each with its meaning written beside it | test/solarpunk/iso/test_iso9001.py::test_the_catalogue_is_one_list_with_a_meaning_per_code | held |
| 9001-8.7.1 | A code the catalogue does not hold is refused, never stored | test/solarpunk/iso/test_iso9001.py::test_an_unknown_code_is_refused | held |
| 9001-8.7.2 | A fault is kept as a record naming the asset, the catalogue code, when it opened and, for a failing remote test's own fault, the test that raised it | test/solarpunk/iso/test_iso9001.py::test_a_fault_records_its_asset_code_and_instant | held |
| 9001-9.1.1 | Every number the plant is judged by has a written method and an example a person checks by hand | test/solarpunk/iso/test_iso9001.py::test_every_kpi_has_a_worked_example | held |
| 9001-9.1.3 | A KPI says how many of its expected samples were missing and how it treated them | test/solarpunk/iso/test_iso9001.py::test_a_kpi_reports_its_gaps_beside_the_number | held |
| 9001-10.2.1 | A ticket on a fault closes only once the fault's root cause is written | test/solarpunk/iso/test_iso9001.py::test_a_ticket_on_a_fault_closes_only_once_its_root_cause_is_written | held |
| 9001-10.2.2 | Every flaw the project's checks prove is kept with its evidence and its status | test/solarpunk/iso/test_iso9001.py::test_every_finding_keeps_its_evidence | held |
| 55000-6.2.1 | The conditions a KPI excludes or distrusts are catalogue codes, fixed in one place | test/solarpunk/iso/test_iso55000.py::test_the_kpi_numbers_name_catalogue_codes | held |
| 55000-6.2.2 | An asset can name the engineer who services it, and a malformed address is refused | test/solarpunk/iso/test_iso55000.py::test_an_asset_names_its_engineer | held |
| 55000-7.5 | A reading that never arrived is stored as a gap carrying no values, never dropped or filled | test/solarpunk/iso/test_iso55000.py::test_a_missing_reading_is_stored_as_a_gap | held |
| 55000-9.1 | Only a fault that stops output counts against availability; a derate does not | test/solarpunk/iso/test_iso55000.py::test_only_an_outage_counts_against_availability | held |
