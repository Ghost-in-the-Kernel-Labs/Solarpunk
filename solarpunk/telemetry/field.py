"""Field telemetry (12.6, SP-036): one NREL PVDAQ system's export, read from a local copy outside the repository
(C-033), as leaf assets and samples. A folder holds the system's `<id>_system_metadata.json` and its CSV files, each a
`measured_on` column of local stamps then one column per channel. An inverter is a column named
`inverter_<n>_ac_power_(kw)_inv_<metric>`, its rated_kw the metadata's "AC capacity(kW)" for `*_inv_<n>`, None where
the metadata gives none; a weather station is each plane-of-array column `…_poa_irradiance_(w/m2)_o_<metric>`, in file
then column order, and inverter n's sample carries the irradiance of the station whose column names pad n
(`…_pad_<n>_…`), the site's first station where none does, at its instant. A stamp is the site's local clock: UTC is it
plus the metadata's timezone_code hours, a fixed offset. docs/FIELD-DATA.md has the mapping and why.
A missing row, an empty cell, a word or a register sentinel is a gap, never a zero (SOL-06); a stamp off the 5-minute
grid, or a second row for one stamp, is skipped and counted, never moved (gridding is 12.7's)."""
import csv
import json
import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from solarpunk.leaf.assets import Asset, site_id
from solarpunk.leaf.clock import SAMPLE_INTERVAL, OffTheGrid, on_grid
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample, gap

STAMP_COLUMN = "measured_on"
STAMP = "%Y-%m-%d %H:%M:%S"
POWER_COLUMN = re.compile(r"^inverter_(\d+)_ac_power_\(kw\)_inv_\d+$")
POA_COLUMN = re.compile(r"_poa_irradiance_\(w/m2\)_o_\d+$")
RATED_NAME = re.compile(r"_inv_(\d+)$")
# J-101: carrying pad 1's irradiance into inverter 2 during pad 1's outage gave three false night_power alarms (cause G);
# a station whose column names pad n is inverter n's (SP-039, call 5).
PAD_NAME = re.compile(r"_pad_(\d+)_")
RATING_KEY = "AC capacity(kW)"
# Register sentinels a logger writes for "no value"; none occurs in the window docs/FIELD-DATA.md names.
SENTINELS = frozenset({32767.0, -32768.0, 65535.0})
METADATA = "*_system_metadata.json"


class FieldError(ValueError):
    """Raised for a folder the loader cannot read as one PVDAQ system: FieldError("no *_system_metadata.json in x")."""


@dataclass(frozen=True)
class Channel:
    """One asset's column: Channel(<PV9068-INV-001>, "9068_ac_power_data.csv", "inverter_1_ac_power_(kw)_inv_150143")."""

    asset: Asset
    file: str
    column: str


@dataclass(frozen=True)
class Table:
    """One CSV file, its readings by UTC instant: rows[instant] is the row's cells by column; off_grid and duplicates
    count the rows skipped."""

    name: str
    rows: dict[datetime, dict[str, str]]
    off_grid: int
    duplicates: int


@dataclass(frozen=True)
class Export:
    """One system read: its id, its site's code, its assets (the site first), the channels that carry samples, its
    tables by file name, and the span of instants on the grid from the first row to the last, end exclusive."""

    system_id: int
    site: str
    assets: tuple[Asset, ...]
    channels: tuple[Channel, ...]
    tables: dict[str, Table]
    start: datetime
    end: datetime


def metadata(folder: Path) -> dict:
    """The folder's one system metadata file, parsed: a folder holding 9068_system_metadata.json gives its dict; none,
    or two, raises FieldError."""
    found = sorted(folder.glob(METADATA))
    if len(found) != 1:
        raise FieldError(f"{folder} holds {len(found)} {METADATA} files, not one")
    return json.loads(found[0].read_text(encoding="utf-8"))


def utc_of(stamp: str, hours: int) -> datetime:
    """A local stamp as UTC, timezone_code hours added: utc_of("2023-02-01 10:05:00", 7) is 2023-02-01T17:05Z."""
    local = datetime.strptime(stamp, STAMP).replace(tzinfo=timezone.utc)
    return local + timedelta(hours=hours)


def header(path: Path) -> list[str]:
    """A CSV file's column names: header(9068_irradiance_data.csv)[0] is "measured_on"; one without it raises
    FieldError."""
    with path.open(newline="", encoding="utf-8") as handle:
        names = next(csv.reader(handle), [])
    if STAMP_COLUMN not in names:
        raise FieldError(f"{path.name} has no {STAMP_COLUMN} column")
    return names


def table(path: Path, hours: int, wanted: tuple[str, ...]) -> Table:
    """One CSV file's wanted columns by instant: a row at 10:02 local is counted off_grid and skipped, a second row for
    one stamp counted a duplicate and skipped, the first kept."""
    # Invariant: SOL-06 (an instant off the grid is skipped and counted, never moved)
    rows: dict[datetime, dict[str, str]] = {}
    off_grid = duplicates = 0
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            moment = utc_of(row[STAMP_COLUMN], hours)
            try:
                on_grid(moment)
            except OffTheGrid:
                off_grid += 1
                continue
            if moment in rows:
                duplicates += 1
                continue
            rows[moment] = {column: row[column] for column in wanted}
    return Table(path.name, rows, off_grid, duplicates)


def ratings(meta: dict) -> dict[int, float]:
    """Each inverter's AC rating in kW by its number: an entry named "sco_inv_1" with "AC capacity(kW)" 1000 gives
    {1: 1000.0}; an entry without the key is left out."""
    found = {}
    for entry in meta.get("Inverters", {}).values():
        named = RATED_NAME.search(str(entry.get("name", "")))
        if named is not None and entry.get(RATING_KEY) is not None:
            found[int(named.group(1))] = float(entry[RATING_KEY])
    return found


def site_asset(meta: dict, site: str) -> Asset:
    """The system's site: Asset("PV9068-SIT-001", SITE, "PV9068", None, "SR_CO (PVDAQ 9068)", None, location
    "Kersey, CO")."""
    system = meta["System"]
    name = f"{system['public_name']} (PVDAQ {system['system_id']})"
    return Asset(site_id(site), AssetKind.SITE, site, None, name, None, location=meta.get("Site", {}).get("location"))


def channels(meta: dict, site: str, headers: dict[str, list[str]]) -> tuple[Channel, ...]:
    """The stations, in file then column order, then the inverters by number: 9068's two pads' raw POA columns are
    PV9068-SEN-001 and -002, its inverter_1 and inverter_2 PV9068-INV-001 and -002 rated as the metadata says."""
    rated = ratings(meta)
    stations, inverters = [], []
    for name in sorted(headers):
        for column in headers[name]:
            power = POWER_COLUMN.match(column)
            if power is not None:
                number = int(power.group(1))
                asset = Asset(f"{site}-INV-{number:03d}", AssetKind.INVERTER, site, site_id(site), column,
                              rated.get(number))
                inverters.append(Channel(asset, name, column))
            elif POA_COLUMN.search(column):
                asset = Asset(f"{site}-SEN-{len(stations) + 1:03d}", AssetKind.SENSOR, site, site_id(site), column, None)
                stations.append(Channel(asset, name, column))
    return tuple(stations) + tuple(sorted(inverters, key=lambda channel: channel.asset.asset_id))


def read(folder: Path, site: str | None = None) -> Export:
    """One system's export: read(the 9068 copy) has site "PV9068", the site and its two stations and two inverters as
    assets, and its span from the first stamp's instant to the last's plus five minutes; site names another code."""
    # Decision: SP-036 (the loader reads a local copy; C-033: nothing of it enters the repository)
    meta = metadata(folder)
    try:
        system_id, hours = int(meta["System"]["system_id"]), int(meta["System"]["timezone_code"])
    except (KeyError, TypeError, ValueError) as missing:
        raise FieldError(f"{folder}: the metadata has no system_id or timezone_code ({missing})") from missing
    code = site if site is not None else f"PV{system_id}"
    paths = {path.name: path for path in sorted(folder.glob("*.csv"))}
    found = channels(meta, code, {name: header(path) for name, path in paths.items()})
    tables = {}
    for name, path in paths.items():
        wanted = tuple(channel.column for channel in found if channel.file == name)
        if wanted:
            tables[name] = table(path, hours, wanted)
    instants = [moment for held in tables.values() for moment in held.rows]
    if not found or not instants:
        raise FieldError(f"{folder} holds no inverter power or plane-of-array irradiance reading")
    assets = (site_asset(meta, code),) + tuple(channel.asset for channel in found)
    return Export(system_id, code, assets, found, tables, min(instants), max(instants) + SAMPLE_INTERVAL)


def value(cell: str | None) -> float | None:
    """A cell as a reading, or None for a gap: "812.5" is 812.5; "", None, "NaN", "n/a" and 32767 are None (SOL-06)."""
    if cell is None or cell.strip() == "":
        return None
    try:
        number = float(cell)
    except ValueError:
        return None
    if not math.isfinite(number) or number in SENTINELS:
        return None
    return number


def reading(export: Export, channel: Channel, moment: datetime) -> float | None:
    """A channel's reading at an instant, None where its file has no row then or the cell is a gap."""
    row = export.tables[channel.file].rows.get(moment)
    return None if row is None else value(row.get(channel.column))


def instants(export: Export) -> Iterator[datetime]:
    """Every instant on the grid from the export's start to its end, end excluded."""
    moment = export.start
    while moment < export.end:
        yield moment
        moment += SAMPLE_INTERVAL


def station_for(export: Export, channel: Channel) -> Channel | None:
    """The station whose irradiance an inverter's samples carry: inverter_2's is the station whose column names pad 2
    (`…_pad_2_poa_irradiance_…`), the export's first station where no station names its pad, None with no station."""
    # Decision: SP-039 (inverter N reads pad N's station, the site's first otherwise)
    stations = [held for held in export.channels if held.asset.kind is AssetKind.SENSOR]
    power = POWER_COLUMN.match(channel.column)
    for held in stations:
        pad = PAD_NAME.search(held.column)
        if power is not None and pad is not None and int(pad.group(1)) == int(power.group(1)):
            return held
    return stations[0] if stations else None


def samples(export: Export, channel: Channel) -> tuple[Sample, ...]:
    """One asset's sample at every instant of the span: a station's reading as irradiance; an inverter's power with its
    station's irradiance at that instant (station_for); a missing reading gap(asset_id, at) (SOL-06): an inverter with
    power "812.0" and its station "905.1" at 17:05 gives Sample(id, 17:05, 905.1, 812.0, False)."""
    # Invariant: SOL-06 (every instant of the span present, a missing reading a gap, never a zero)
    asset_id = channel.asset.asset_id
    reference = station_for(export, channel)
    station = channel.asset.kind is AssetKind.SENSOR
    made = []
    for moment in instants(export):
        own = reading(export, channel, moment)
        if own is None:
            made.append(gap(asset_id, moment))
        elif station:
            made.append(Sample(asset_id, moment, own, None, False))
        else:
            sun = reading(export, reference, moment) if reference is not None else None
            made.append(Sample(asset_id, moment, sun, own, False))
    return tuple(made)
