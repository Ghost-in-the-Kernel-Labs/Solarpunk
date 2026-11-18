"""The numbers the KPI contract fixes (Invariants: SOL-07, SOL-08, SOL-10, SOL-11): each lives here and nowhere else."""
from solarpunk.leaf.codes import Severity

STC_IRRADIANCE_W_M2 = 1000.0
EXCLUDED_CODES: frozenset[str] = frozenset({"SIT-001", "SIT-002", "SIT-003"})
UNRELIABLE_IRRADIANCE_CODE = "SEN-001"
METER_LOST_CODE = "MTR-001"
OUTAGE = Severity.OUTAGE
ROUND_TO = 4
