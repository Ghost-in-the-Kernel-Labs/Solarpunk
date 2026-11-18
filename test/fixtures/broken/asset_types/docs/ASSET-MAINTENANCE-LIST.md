# A planted break of the asset maintenance list (test/test_asset_types.py)

Two breaks: METER has a section here and no entry in the JSON, and TRACKER's field angle_deg is named here and absent
from its JSON entry. INVERTER holds, so the check is seen to pass a section that is right.

## SITE

No feed.

Tests: none.

## INVERTER

| Field | Unit | Min | Max |
| --- | --- | --- | --- |
| power_kw | kW | 0 | — |

Tests: `reachable`.

## STRING

No feed.

Tests: none.

## TRACKER

| Field | Unit | Min | Max |
| --- | --- | --- | --- |
| angle_deg | deg | -60 | 60 |

Tests: `reachable`.

## METER

| Field | Unit | Min | Max |
| --- | --- | --- | --- |
| energy_kwh | kWh | 0 | — |

Tests: `reachable`.

## SENSOR

No feed.

Tests: none.
