# The asset maintenance list

One section per asset kind (`AssetKind`, `solarpunk/leaf/codes.py`): what the asset is, the fields its feed answers
with and the range each is supposed to fall in, the remote tests that can be run against it, and what a passing
response is. The same list is data in `solarpunk/leaf/asset_types.json`, loaded by `solarpunk/leaf/asset_types.py`;
the UI's type dropdown reads it, the feed reader checks a response against it, and a remote test's `KINDS` names
entries in it. `scripts/checks/asset_types.py` holds this document and the JSON together (`test/test_asset_types.py`,
C-013): every kind in both, every field row here in the JSON with the same unit, min and max, every test named here in
the JSON's tests.

Ranges include both ends. A max of `—` (null in the JSON) means the list sets no fixed ceiling: the loader's
`in_range` takes it as unbounded above. For an inverter's `power_kw` the ceiling is the asset's own rated value
(`Asset.rated_kw`), which the remote test `power_under_rated` holds; for a meter's `energy_kwh` there is none, since
the count only grows (`energy_monotonic`). A kind with no feed (a site, a string) has no fields and no tests.

## SITE

A solar plant: the point of interconnection and everything behind it. It has no feed of its own; its numbers are the
sum of its assets'.

No feed.

Tests: none.

Passing: a site has no remote test of its own; its status is its assets' statuses.

## INVERTER

Turns its strings' direct current into grid alternating current; the asset whose output the KPIs count.

| Field | Unit | Min | Max |
| --- | --- | --- | --- |
| irradiance_w_m2 | W/m2 | 0 | 1500 |
| power_kw | kW | 0 | — |
| temperature_c | °C | -40 | 90 |

Tests: `reachable`, `on_grid`, `irradiance_in_range`, `power_under_rated`, `night_power_near_zero`, `performance_above_floor`, `power_not_frozen`.

Passing: the endpoint answers within the timeout with a sample whose every field is in range, power at or under the
inverter's rated_kw, near zero at night, at least 0.75 of what its rating and the sun promise in daylight
(irradiance at or above 200 W/m²), and never the same non-zero value for half an hour (six records).

## STRING

A series chain of panels feeding one inverter input. It has no feed of its own; its current is read through its
inverter.

No feed.

Tests: none.

Passing: a string has no remote test of its own; a fault on it is raised from its inverter's data.

## TRACKER

A single-axis tracker turning a row of panels to follow the sun, stowing flat in high wind.

| Field | Unit | Min | Max |
| --- | --- | --- | --- |
| angle_deg | deg | -60 | 60 |

Tests: `reachable`, `on_grid`, `tracker_moving`.

Passing: the endpoint answers within the timeout with an angle in range that changes over the day.

## METER

The revenue meter at the point of interconnection: the energy the plant is paid for.

| Field | Unit | Min | Max |
| --- | --- | --- | --- |
| energy_kwh | kWh | 0 | — |

Tests: `reachable`, `on_grid`, `energy_monotonic`.

Passing: the endpoint answers within the timeout with an energy count at or above zero that never falls from one
sample to the next.

## SENSOR

A weather station: plane-of-array irradiance and temperature, the denominator of the performance ratio.

| Field | Unit | Min | Max |
| --- | --- | --- | --- |
| irradiance_w_m2 | W/m2 | 0 | 1500 |
| temperature_c | °C | -40 | 90 |

Tests: `reachable`, `on_grid`, `irradiance_in_range`.

Passing: the endpoint answers within the timeout with irradiance and temperature both in range.
