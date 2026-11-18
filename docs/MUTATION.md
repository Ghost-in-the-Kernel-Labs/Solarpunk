# Mutation survivors explained

Each line names a surviving mutant and why no test can tell it from the original (C-018). Prefer killing; a line here is
for a mutant that is truly equivalent.

- `solarpunk.leaf.store.x_connect__mutmut_6`: `"PRAGMA foreign_keys = ON"` lowercased to `"pragma foreign_keys = on"`; SQLite reads pragma names and their boolean values in any case, so the connection behaves identically (foreign keys on, which test_fleet's `test_the_parent_references_assets` holds).
- `solarpunk.leaf.store.x_connect__mutmut_7`: `"PRAGMA foreign_keys = ON"` uppercased to `"PRAGMA FOREIGN_KEYS = ON"`; same reason: the pragma name is case-insensitive.
- solarpunk.faults.ledger.x_schema__mutmut_2: the CREATE TABLE's first part lower-cased; the same table.
- solarpunk.faults.ledger.x_schema__mutmut_5: the CREATE TABLE's last part lower-cased; the same table.
- solarpunk.faults.ledger.x__select__mutmut_9: " order by fault_id" lower-cased; the same order.
- solarpunk.faults.ledger.x__select__mutmut_10: " ORDER BY FAULT_ID" upper-cased; the same order.
- solarpunk.faults.ledger.x__get__mutmut_9: " where fault_id = ?" lower-cased; the same row.
- solarpunk.faults.ledger.x__get__mutmut_10: " WHERE FAULT_ID = ?" upper-cased; the same row.
- solarpunk.faults.ledger.x_assign__mutmut_12: the open-clash WHERE lower-cased; the same rows.
- solarpunk.faults.ledger.x_assign__mutmut_13: the open-clash WHERE upper-cased; the same rows.
- solarpunk.faults.ledger.x_assign__mutmut_22: the INSERT lower-cased; the same insert.
- solarpunk.faults.ledger.x_assign__mutmut_23: the INSERT upper-cased; the same insert.
- solarpunk.faults.ledger.x_close__mutmut_17: the UPDATE lower-cased; the same update.
- solarpunk.faults.ledger.x_close__mutmut_18: the UPDATE upper-cased; the same update.
- solarpunk.faults.ledger.x_open_faults__mutmut_8: " where closed is null" lower-cased; the same rows.
- solarpunk.faults.ledger.x_open_faults__mutmut_9: " WHERE CLOSED IS NULL" upper-cased; the same rows.
- solarpunk.faults.ledger.x_by_asset__mutmut_8: " where asset_id = ?" lower-cased; the same rows.
- solarpunk.faults.ledger.x_by_asset__mutmut_9: " WHERE ASSET_ID = ?" upper-cased; the same rows.
- solarpunk.faults.ledger.x_by_code__mutmut_9: " where code = ?" lower-cased; the same rows.
- solarpunk.faults.ledger.x_by_code__mutmut_10: " WHERE CODE = ?" upper-cased; the same rows.
