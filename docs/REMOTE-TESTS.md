# What a remote test is

A remote test is one Python module under `solarpunk/remote/tests/` that judges one asset's stored samples and says
pass, fail or no data (SP-019, TODO 13.1). It is written to this page, not copied from its neighbour. The registry
(`solarpunk/remote/registry.py`) finds it by its file, and `scripts/checks/remote_tests.py` holds every module to what
a check can see (`test/test_remote_tests.py`). `solarpunk test add <name> --clause <id>` scaffolds a module that meets
the page but for `run`. The shape to read first is `solarpunk/remote/tests/power_under_rated.py`.

## The module's fields

| Field | Holds | Held by |
| --- | --- | --- |
| `KINDS` | a non-empty tuple of `AssetKind`: the kinds the test runs on | the registry and the check |
| `CLAUSES` | a non-empty tuple of clause ids, each a row of `docs/CLAUSE-REGISTER.md`: what the test evidences | the registry and the check |
| `SUGGESTS` | a dict with one key per kind in `KINDS`: the catalogue code a failure suggests to an engineer, or `None`, with a comment saying why (SP-015) | the registry and the check |
| `run` | `run(asset, samples)`, below | the check (its shape), `test/solarpunk/test_diagnostics.py` (its results) |

The module opens with a docstring that says in a sentence what the test checks, why a failure matters and the clause
it evidences.

## What `run` may do

`run(asset: Asset, samples: tuple[Sample, ...]) -> Result` reads only what it is given: no store (`sqlite3`,
`solarpunk.leaf.store`), no network (`socket`, `urllib`, `http`, the feed, the receiver), no clock (`time`, a call to
`now`, `today` or `utcnow`), and no import of the project, the runner or the registry (MOD-05). The runner reads the
samples and the asset and hands them over; the same arguments give the same result on any day. The leaf clock's grid
arithmetic (`solarpunk.leaf.clock`, which does sums on an instant it is given and never reads the time) is allowed.
`run` returns a `Result` (`solarpunk/remote/results.py`) and nothing else.

## The three results

A test says one of three things (SP-039, J-107):

- **Pass**: `Result(True, reason)`, every record it could judge was fine.
- **Fail**: `Result(False, reason)`, a record broke the rule.
- **No data**: `no_data(reason)`, that is `Result(False, reason, no_data=True)`: the samples hold nothing to judge,
  which `nothing_to_check(samples)` says (`None` when one record is not a gap; "no records" or "no records: 3 gaps"
  otherwise). Shown grey. It is not a pass and it is not a failure, and a result that says both pass and no data is
  refused (`NotAVerdict`).

Every test calls `nothing_to_check` first and returns `no_data` for what it names, so an asset that sent nothing is
never green; the check looks for the call. `reachable` is the one exception in effect: a feed that answered nothing is
a disconnection, said once there as a failure (SP-039, call 4). A test with no rating to judge against says
`Result(False, "no rating")`. A record that has none of the fields a test needs is not no data: a day of real records is
judged (SP-039).

## The reason's shape

- A failure names the first offending record with its instant: `"2026-06-01T10:05:00+00:00: power 101.5 kW over rated
  100.0 kW + 1%"`, the instant as `sample.at.isoformat()`, then what was read and what it was held to.
- A pass gives a count: `"2 records at or under rated 100.0 kW + 1%"`.
- No data gives the words of `nothing_to_check`.

## Thresholds

Every threshold is a named module constant in capitals, with a comment (the line above it, or at the end of its own
line) saying why that value: `FLOOR = 0.75` under "A healthy plant runs 0.75 to 0.90". A function body holds no number
but 0, 1 and the digits of a `round`. A threshold's value changes by a decision, never as part of a tidy-up.

## The docstring

`run`'s docstring has at least one passing case and one failing case, written as results: `Result(True, "3 records")`
and `Result(False, "2026-06-01T10:05:00+00:00: ...")`, with the inputs that give them; and the no-data case where the
test judges records. They are the examples a reader checks the code against.

## The maintenance list

The test's name is in the `Tests:` line of the asset maintenance list, `docs/ASSET-MAINTENANCE-LIST.md`, for each kind
in its `KINDS`, and in the same kind's `tests` in `solarpunk/leaf/asset_types.json`: one line, the two files together
(`scripts/checks/asset_types.py`). A kind with the test in its `KINDS` and not on its line is a failure of the check.

## What the check sees and what it leaves

`scripts/checks/remote_tests.py` reads each module's source and loads it for `KINDS` and `SUGGESTS`. It sees: the
module docstring, the four fields and their shapes, the two cases in `run`'s docstring, the call to
`nothing_to_check`, the forbidden imports and clock calls, a commentless or bare threshold, and the list lines. It does
not see that `run` is right: each threshold's two sides and each reason's words are pinned by
`test/solarpunk/test_diagnostics.py` and `test/solarpunk/test_remote.py`. A planted break is
`test/fixtures/broken/remote_tests/`.
