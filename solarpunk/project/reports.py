"""The reports' surface (6.1, 6.3; SOL-13): a site's power output over a period recomputed from the stored samples,
with its summed power curve, as one PowerReport; the CSV that `solarpunk report --csv` prints and the reports window
saves, made here once so the two cannot disagree; the sites a report can be asked for and the day it opens on. Each
function is one call the window makes and a headless test makes too (SP-007)."""
import csv
import io
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone

from solarpunk import kpi
from solarpunk.fleet import registry
from solarpunk.leaf.assets import site_id
from solarpunk.leaf.clock import Period
from solarpunk.leaf.codes import AssetKind
from solarpunk.project.orchestrator import inverters_of, known, site_samples
from solarpunk.remote import results as result_table

OUTPUT_FIELDS = ("asset_id", "rated_kw", "energy_kwh", "peak_kw", "specific_yield", "capacity_factor", "records", "gaps")


@dataclass(frozen=True)
class PowerReport:
    """A site's power output over one period (SOL-13): the site's row, one per inverter in id order, and the site's summed
    power at each instant with a record; for OAHE, site.asset_id is "OAHE-SIT-001", inverters holds OAHE-INV-001 and
    OAHE-INV-002, and the curve's largest power is site.peak_kw."""

    period: Period
    site: kpi.PowerOutput
    inverters: tuple[kpi.PowerOutput, ...]
    curve: tuple[tuple[datetime, float], ...] = ()


def power_report(conn: sqlite3.Connection, site: str, period: Period) -> PowerReport:
    """The site's and each inverter's energy, peak, specific yield and capacity factor from the stored samples, with the
    site's curve: for a clean stored OAHE day each inverter's records are its non-gap samples and the site's energy is
    their sum; a site the fleet lacks raises UnknownAsset."""
    # Invariant: SOL-13 (the engine's numbers over the stored samples alone, so the report is recomputed, never kept)
    known(conn, site_id(site))
    inverters = inverters_of(registry.by_site(conn, site))
    samples = site_samples(conn, inverters, period)
    rows = tuple(kpi.inverter_output(inverter, samples, period) for inverter in inverters)
    return PowerReport(period, kpi.site_output(site_id(site), inverters, samples, period), rows,
                       kpi.site_curve(inverters, samples, period))


def report_rows(found: PowerReport) -> tuple[kpi.PowerOutput, ...]:
    """The report's rows, the site's first, then each inverter's in id order: three for OAHE."""
    return (found.site, *found.inverters)


def report_csv(found: PowerReport) -> str:
    """The report as CSV, one header naming OUTPUT_FIELDS and one row each, the site's first, an absent peak left empty:
    SOL-13's example site's row is "OAHE-SIT-001,150.0,22.25,135.0,0.1483,0.5933,5,1"."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(OUTPUT_FIELDS)
    for row in report_rows(found):
        writer.writerow(["" if getattr(row, field) is None else getattr(row, field) for field in OUTPUT_FIELDS])
    return out.getvalue()


def report_sites(conn: sqlite3.Connection) -> tuple[str, ...]:
    """The sites the fleet holds, by their short name in id order: ("OAHE",) for the demo fleet; () for an empty store."""
    return tuple(asset.site for asset in registry.by_kind(conn, AssetKind.SITE))


def report_day(conn: sqlite3.Connection) -> date:
    """The day a report opens on: the day of the store's last scheduled run, else today in UTC: 2026-06-01 for the demo,
    whose run is at 13:00 that day."""
    last = result_table.last_run_at(conn)
    return (last or datetime.now(timezone.utc)).date()
