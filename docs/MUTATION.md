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
- solarpunk.telemetry.samples.x_schema__mutmut_2: lowercases `CREATE TABLE samples (`; SQL keywords and SQLite identifiers are case-insensitive, the table is the same.
- solarpunk.telemetry.samples.x_schema__mutmut_5: lowercases `asset_id TEXT NOT NULL`; SQLite reads the type and constraint case-insensitively and reports the type as TEXT either way.
- solarpunk.telemetry.samples.x_schema__mutmut_8: lowercases `at TEXT NOT NULL`; the same column, as above.
- solarpunk.telemetry.samples.x_schema__mutmut_11: lowercases `irradiance_w_m2 REAL NULL`; the same column, as above.
- solarpunk.telemetry.samples.x_schema__mutmut_14: lowercases `power_kw REAL NULL`; the same column, as above.
- solarpunk.telemetry.samples.x_schema__mutmut_17: lowercases `gap INTEGER NOT NULL`; the same column, as above.
- solarpunk.telemetry.samples.x_schema__mutmut_20: lowercases `PRIMARY KEY (asset_id, at)`; the same key.
- solarpunk.telemetry.samples.x_schema__mutmut_21: uppercases the key's column names; SQLite column names are case-insensitive, the same key.
- solarpunk.telemetry.generate.x_reading__mutmut_2: `rng.random() < 0.02` to `<=`; random() returns multiples of 2**-53 and the double 0.02 is not one, so equality never happens.
- `solarpunk.leaf.clock.x_on_grid__mutmut_4`: `+ microsecond / 1_000_000` to `-`; whole seconds lie on the 300 s grid only at second 0 (60·minute + second is a multiple of 300 only when second is a multiple of 60), and any nonzero microsecond leaves a fraction in (0, 1) either way, so the same instants are refused with the same message (built from the instant, not the sum); checked over every minute and second with 306 microsecond values, 1 101 600 cases, no disagreement.
- `solarpunk.leaf.clock.x_on_grid__mutmut_5`: `minute * 60 + second` to `- second`; 60·minute − second is a multiple of 300 only when second is 0, as with `+`; same reason and check as mutmut_4.
- `solarpunk.leaf.clock.x_on_grid__mutmut_9`: `/ 1_000_000` to `/ 1000001`; the fraction stays in (0, 1) for every nonzero microsecond and 0 for none, so on-grid-ness and the message are unchanged; same check as mutmut_4.
