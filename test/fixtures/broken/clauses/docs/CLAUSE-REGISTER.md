# A planted break of the clause register (test/test_clauses.py)

Two breaks: 9001-7.5.3 is held by a test that does not exist, and the test tagged 9001-10.2.2 has no row.
9001-8.7.1 holds, so the check is seen to pass a row that is right.

| Clause | Requirement (our words) | Held by | Status |
| --- | --- | --- | --- |
| 9001-7.5.3 | A planted row whose test is missing | test/solarpunk/iso/test_iso9001.py::test_missing | held |
| 9001-8.7.1 | A planted row that holds | test/solarpunk/iso/test_iso9001.py::test_present | held |
| 9001-9.1.3 | A planted open row | — | open |
