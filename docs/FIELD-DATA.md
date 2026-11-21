# Field data: the public PV telemetry the remote tests are measured on

TODO 12.6 (SP-036) runs every remote test that applies over real 5-minute telemetry from public PV plants, one UTC day at
a time, so how often each check fires on working plant is known and each alarm is explained. This file says where the
data comes from, under what licence, which systems and window, and how each column becomes an asset and a sample. The
data itself never enters the repository (C-033): it is a local copy outside the checkout, read by
`solarpunk field load PATH --db STORE`; the loader's tests read a hand-written sample of a few rows in the export's
exact format, real column names and invented values (`test/fixtures/pvdaq/`). The baseline's numbers are in the journal.

## Source and licence

- **Dataset**: Photovoltaic Data Acquisition (PVDAQ) Public Datasets, NREL, on the Open Energy Data Initiative (OEDI
  submission 4568). Authors: Chris Deline, Kirsten Perry, Michael Deceglie, Matthew Muller, William Sekulic, Dirk
  Jordan. DOI [10.25984/1846021](https://doi.org/10.25984/1846021).
- **Licence**: Creative Commons Attribution 4.0 International (CC BY 4.0),
  https://creativecommons.org/licenses/by/4.0/. The attribution the licence asks for is the line above; the changes
  made are the ones this file describes (local stamps converted to UTC, cells mapped to samples, missing readings made
  gaps). Nothing of the data is redistributed here: only column names, in the sample's header.
- **Host**: the files are read from the OEDI data lake, `oedi-data-lake.s3.amazonaws.com`, under
  `pvdaq/2023-solar-data-prize/<id>_OEDI/` (`data/` and `metadata/`); the catalogue page is on `data.openei.org`. These
  two systems are not under `pvdaq/csv/pvdata/` (that prefix is empty for them). `www.nrel.gov` and `developer.nrel.gov`
  are refused by the session's proxy and were not used.
- **Fetched**: only the window's rows, by HTTP range requests on each whole-history CSV (the files are sorted by time),
  with the file's header line; and each system's metadata JSON. About 63 MB in all.

## The systems and the window

Both are 2023 Solar Data Prize systems with 5-minute data, inverter-level AC power and plane-of-array irradiance:

| System | Name, place | Plant | Files read | Why |
| --- | --- | --- | --- | --- |
| 9068 | SR_CO, Kersey, CO; single-axis tracker; 4,738 kW DC | 2 inverters, rated 1,910 kW AC each in the metadata; 2 POA pyranometers (pad 1, pad 2) | `9068_ac_power_data.csv`, `9068_irradiance_data.csv`, `9068_system_metadata.json` | the brief's first choice; both pads' pyranometers read through the window |
| 9069 | Simon Solar Farm, Social Circle, GA; fixed tilt 20°; 38,687 kW DC | 40 inverters, five (1 to 5) rated 825 kW AC in the metadata, 35 without a rating; 13 POA channels (reference cells and pyranometers) and one GHI | `9069_electrical_ac.csv`, `9069_irradiance_data.csv`, `9069_system_metadata.json` | the brief's second; a large plant with many inverters to compare |

**Window**: local stamps 2023-01-31 00:00 to 2023-05-01 23:55; the baseline runs the UTC days 2023-02-01 to 2023-04-30
(89 days), winter into spring across the March equinox and both daylight-saving changes (below). The window was moved
from August to October 2022, first fetched, because 9068's two pyranometers read zero or nothing from August to mid
September 2022.

## The mapping

A system's local copy is one folder holding its `<id>_system_metadata.json` and its CSV files, as fetched. The loader
(`solarpunk/telemetry/field.py`) reads every CSV in the folder:

- **Site**: one asset `PV<id>-SIT-001` (`--site CODE` names another code, 2 to 6 capitals or digits), named
  "<public_name> (PVDAQ <id>)", its location the metadata's.
- **Inverters**: each column `inverter_<n>_ac_power_(kw)_inv_<metric>` is the inverter `PV<id>-INV-<nnn>` (kind
  INV), its power_kw the cell in kW as read. Its rated_kw is the metadata's `"AC capacity(kW)"` for the inverter
  named `*_inv_<n>`, None where the metadata gives none (never invented). `inverter_module_*` columns (9068's four power
  modules per inverter) are parts of an inverter, not inverters, and are not loaded.
- **Weather stations**: each plane-of-array column `…_poa_irradiance_(w/m2)_o_<metric>` is a station
  `PV<id>-SEN-<nnn>` (kind SEN), numbered in file then column order, its irradiance_w_m2 the cell in W/m² as read.
  The temperature-compensated duplicates (`…_poa_irradiance_temp_compensated_…`) and the GHI channel are not loaded.
- **The irradiance an inverter's sample carries** is, at the same instant, that of the station whose column names the
  inverter's pad (`…_pad_<n>_…` for `inverter_<n>_…`), the site's first station (`PV<id>-SEN-001`) where none does
  (SP-039): 9068's inverter 1 reads pad 1's pyranometer and inverter 2 pad 2's; 9069's stations name no pad, so all 40
  inverters read reference cell 01. The metadata links no inverter to a station (`source_id` is null), so the match is
  by name. The leaf's sample holds irradiance and power together, and the inverter tests compare the two; J-101's
  first-station mapping carried pad 1's outage into inverter 2's night (three false alarms, its cause G).
- **Not loaded**: the meters (9068's `meter_ac_power_*`, 9069's `meter_data.csv`): the leaf's sample has no energy
  field and a meter's power in power_kw would fail on_grid on the mapping itself; temperatures (the sample has no
  temperature field); DC, current, voltage, power-factor and tracker channels.
- Assets are registered as the fleet registers them, with no host and port, so the scheduled run (`solarpunk test run`)
  never pings or tests them; the baseline is `solarpunk field baseline`, which records nothing.

**Time.** A stamp is the site's local clock. UTC is the stamp plus the metadata's `timezone_code` hours (7 for 9068, 5
for 9069), a fixed offset. The clocks keep daylight saving, so after a change a converted instant is an hour late: 9068's
files move with the US change on 12 March 2023; at 9069 the power file moves on 12 March but the irradiance file only
about 26 March, so for two weeks its power and irradiance disagree by an hour. No test compares a reading with the clock,
and UTC midnight is night at both sites, so the hour moves no daylight reading into another day; the two-week
disagreement at 9069 is a data artefact the baseline names: from 12 to 26 March `night_power_near_zero` fires on
9069's producing inverters (on every one in J-101's counterfactual with a rating given), power an hour off against
irradiance (J-101). The offset stays fixed (SP-039, call 6; J-106: following daylight saving fixes no alarm the
baseline counts). A stamp repeated by an autumn change would be a duplicate, skipped and counted.

**Values.** A cell is a reading in the column's unit as read. A missing row, an empty cell, a word ("NaN", "n/a"), a
non-finite number or a register sentinel (32767, -32768, 65535) is a gap, never a zero (SOL-06); none of the sentinels
occurs in the window, and the export marks no value bad. Every instant on the grid from the first row to the last is a
sample of every asset, a gap where its file has no reading. A stamp off the 5-minute grid is skipped and counted, never
moved (gridding is 12.7's decision); so is a second row for one stamp. In this window neither occurs.

## Running it

From the repository root, with the copy outside it (each command reads only the folder it is given):

    python3 -m solarpunk.cli field load <copy>/9068 --db field.db
    python3 -m solarpunk.cli field load <copy>/9069 --db field.db
    python3 -m solarpunk.cli field baseline --from 2023-02-01 --to 2023-04-30 --db field.db

The baseline prints, per test and asset, the days run and the days alarmed, then each alarmed day with the test's
message. A store made this way is a run's output and stays outside the repository too.
