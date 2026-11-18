# Findings: what the project's checks prove, written before the result they qualify

A finding is a flaw this repository's own checks prove in an existing tool, metric, document or
practice, with the evidence that proves it (C-014). Not a bug list for this codebase (a bug is a
journal entry of class failure-caught and a test) and not an opinion. Ids are never reused; a
resolved finding is marked, never deleted. A result that depends on a finding cites it.

| Id | Finding | Evidence | Qualifies | Status |
| --- | --- | --- | --- | --- |
| F-001 | The glossary governs `docs/REVIEWED-VERSIONS.md`, whose Package cells are third-party names that can carry a banned alias; a stamp fails its own fast loop at the first dependency review | Ghostreach F-005 (its stamp of 2026-11-13); this tree's `docs/GLOSSARY.md` "Not governed" line at stamp 59c211c | the stamp recipe (Ghost-Core owes the fix); here, the exemption added | resolved here, open in Core |
| F-002 | `scripts/ship.sh` is stamped at mode 100644 while every other script is 100755, so the only push to `main` cannot be run as `scripts/ship.sh` | Ghostreach F-006; `git ls-files -s scripts/ship.sh` at 59c211c | the stamp recipe (Ghost-Core owes the fix); here, the mode set in 0.2's commit | resolved here, open in Core |
