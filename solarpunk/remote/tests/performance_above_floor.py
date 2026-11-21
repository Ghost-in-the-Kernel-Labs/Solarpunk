"""Performance above floor: in good sun, the inverter turns at least FLOOR of the energy its rating and the irradiance
promise into output: the performance ratio of SOL-08 over the window's daylight records alone. A ratio under the floor
is soiling, a string down, a failed MPPT input or a derate nobody logged: the condition that says a crew is worth
sending, where a calendar would send one regardless (docs/GOAL.md, "What to watch out for"). Daylight is irradiance at
or above DAYLIGHT_W_M2, so dawn and dusk, where the ratio swings on small numbers, do not decide it. Evidences ISO
55000 9.1 (the asset's performance is evaluated against what it should deliver)."""
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.kpi_defs import STC_IRRADIANCE_W_M2
from solarpunk.leaf.telemetry import Sample
from solarpunk.remote.results import Result, no_data, nothing_to_check

KINDS = (AssetKind.INVERTER,)
CLAUSES = ("55000-9.1",)
# SP-020's reactions (SP-015's rule table): the catalogue has no inverter code for output under the floor (soiling, a string down, an MPPT
# input lost); STR-002 is a string's, on a string asset. A gap for Ghost: until a code exists, no fault code of its own.
REACTIONS = {}  # the generic SIT-004 fault alone
# Below 200 W/m² the ratio swings on small numbers (dawn, dusk, heavy cloud), so those records do not decide it.
DAYLIGHT_W_M2 = 200.0
# A healthy plant runs 0.75 to 0.90; under 0.75 in good sun is a loss worth a look, not noise.
FLOOR = 0.75


def run(asset: Asset, samples: tuple[Sample, ...]) -> Result:
    """Passes when Σ power / Σ (rated × irradiance / 1000) over daylight records is at or above 0.75: rated 100 with
    (800 W/m², 72 kW) gives Result(True, "ratio 0.9 over 1 daylight records"); (800, 40) gives Result(False, "ratio 0.5
    under the floor 0.75 over 1 daylight records"); records with no daylight one among them give Result(True, "no
    daylight records") (an overcast day is judged, SP-039); gaps alone, or no samples, give no data,
    Result(False, "no records", no_data=True); rated_kw None gives Result(False, "no rating")."""
    if asset.rated_kw is None:
        return Result(False, "no rating")
    missing = nothing_to_check(samples)
    if missing is not None:
        return no_data(missing)  # Decision: SP-039 (nothing to check is not a pass)
    day = [s for s in samples if s.irradiance_w_m2 is not None and s.power_kw is not None
           and s.irradiance_w_m2 >= DAYLIGHT_W_M2]
    if not day:
        return Result(True, "no daylight records")
    produced = sum(sample.power_kw for sample in day)
    promised = sum(asset.rated_kw * sample.irradiance_w_m2 / STC_IRRADIANCE_W_M2 for sample in day)
    ratio = round(produced / promised, 4)
    if ratio < FLOOR:
        return Result(False, f"ratio {ratio} under the floor {FLOOR} over {len(day)} daylight records")
    return Result(True, f"ratio {ratio} over {len(day)} daylight records")
