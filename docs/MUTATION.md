# Mutation survivors explained

Each line names a surviving mutant and why no test can tell it from the original (C-018). Prefer killing; a line here is
for a mutant that is truly equivalent.

- `solarpunk.leaf.store.x_connect__mutmut_6`: `"PRAGMA foreign_keys = ON"` lowercased to `"pragma foreign_keys = on"`; SQLite reads pragma names and their boolean values in any case, so the connection behaves identically (foreign keys on, which test_fleet's `test_the_parent_references_assets` holds).
- `solarpunk.leaf.store.x_connect__mutmut_7`: `"PRAGMA foreign_keys = ON"` uppercased to `"PRAGMA FOREIGN_KEYS = ON"`; same reason: the pragma name is case-insensitive.
