"""A sample is one SCADA reading of one asset at one instant; a gap is a sample with no values (Invariant: SOL-06)."""
from dataclasses import dataclass
from datetime import datetime

from solarpunk.leaf.clock import on_grid

IRRADIANCE_START_W_M2 = 50.0


@dataclass(frozen=True)
class Sample:
    """One reading: Sample("OAHE-INV-003", 10:05 UTC, 812.0, 78.4, False); a gap is Sample(id, at, None, None, True)."""

    asset_id: str
    at: datetime
    irradiance_w_m2: float | None
    power_kw: float | None
    gap: bool

    def __post_init__(self) -> None:
        """The instant on the grid; a gap carries no values: Sample(id, 10:02, …) raises OffTheGrid."""
        on_grid(self.at)
        if self.gap and (self.irradiance_w_m2 is not None or self.power_kw is not None):
            raise ValueError(f"a gap at {self.at.isoformat()} carries values")


def gap(asset_id: str, at: datetime) -> Sample:
    """The gap sample for an expected instant with no reading: gap("OAHE-INV-003", 10:20).gap is True."""
    return Sample(asset_id, at, None, None, True)
