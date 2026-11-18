# The KPI contract

The contract precedes the code. It is the specification the leaf module is built from and that a
mirror could be written from blind: if something here is not precise enough to implement, that is a
defect in this document, and the fix is to make it precise, not to read the code. Each invariant is
one heading, `## SOL-nn title`, numbered in sequence and never reused; code cites one as
`# Invariant: SOL-03` and `test/test_contract.py` holds the two together in both directions: every
invariant is named somewhere in the leaf module, and the code names no invariant the document does
not have.

The leaf module (`docs/modules.json`'s `leaf`, the folder `solarpunk/leaf/`) holds this contract in
code: the types and the numbers every other module imports and that imports nothing of the project's
own. A threshold lives there and nowhere else; a threshold defined elsewhere fails the check. Every
number this contract defines comes with a worked example a person checks by hand; the example is the
golden the KPI lane's tests compare against (0.3's plan, lane 1.4), and the blind mirror reimplements
the number from this text alone (`stacks/python/README.md`).

Words: an **asset** is one thing in the fleet with an id (`docs/GLOSSARY.md`); a **sample** is one
SCADA reading of one asset at one instant; a **fault** is one catalogue code carried by one asset
over an interval; a **period** is the half-open interval `[start, end)` a KPI is computed over.

## SOL-01 The leaf module imports nothing of the project's own

Every other module may import it; it may import only the standard library (this project has no
runtime dependency; `requirements.lock` holds tools alone). Held by `test/test_modules.py`
(`mayImport: []`).

## SOL-02 Every number a document reports comes from a run the repository can repeat

A number without the command that produced it does not exist. A KPI reported anywhere in `docs/`
names the command and the seed that produced it. Held by the KPI lane's goldens, which are files a
command regenerates (C-017).

## SOL-03 What the kernel cannot make exact, it says first

A sample the generator could not produce, a fault with no catalogue code, a period with no
irradiance: each is a finding (`docs/FINDINGS.md`) or a refusal before it is output, never a silent
number. Held by `test/solarpunk/test_codes.py` (an unknown code is refused) and each lane's refusal
tests.

## SOL-04 Every fault carries a catalogue code

A fault's `code` is one of `solarpunk/leaf/codes.py`'s `CATALOGUE`; `lookup` refuses any other, and
the ledger stores no fault whose code `lookup` refuses. The catalogue is a closed list: a new code is
a change to the leaf, with its test, never a string written where the fault is raised. Held by
`test/solarpunk/test_codes.py`; the ledger's refusal test (lane 1.2).

## SOL-05 Identifiers have one shape each

An asset id is `<SITE>-<KIND>-<nnn>`: a site code of two to six capitals or digits, the kind's
three-letter prefix (`AssetKind.value`), a number of three digits; a site's own id is `<SITE>-SIT-001`.
A fault code is `AAA-000` (`CODE_SHAPE`). A malformed id is refused where it enters, never stored.
Example: `OAHE-INV-003` is the third inverter at site OAHE; `OAHE-INV-3`, `oahe-INV-003` and
`OAHE-INVERTER-003` are refused. Held by `solarpunk/leaf/assets.py` (`parse_asset_id`) and its test.

## SOL-06 Time is UTC and samples fall on the interval

Every instant is a timezone-aware `datetime` in UTC; a naive datetime is refused where it enters.
Samples are spaced `SAMPLE_INTERVAL_S` (300 s) apart, each on a multiple of the interval from the
hour; a sample off the grid is refused. An expected sample instant with no sample is a **gap**, and a
gap is stored as a sample whose values are `None` and whose `gap` is `True`, never dropped (the
ghost: "the telemetry's gaps are data, not noise"). Example: for `[10:00, 11:00)` the expected
instants are 10:00, 10:05, …, 10:55, twelve in all; with 10:20 missing, the period holds eleven
readings and one gap. Held by `solarpunk/leaf/clock.py` and its test.

## SOL-07 Availability is contractual, not raw

For one inverter over a period, in sample intervals:

    contractual = expected − excluded
    down        = intervals the inverter carried an OUTAGE fault not among the excluded
    availability = (contractual − down) / contractual        (1.0 when contractual is 0)

where `expected` is the period's sample count (SOL-06), `excluded` is the intervals that carried any
fault whose code is in `EXCLUDED_CODES` (`SIT-001` grid outage, `SIT-002` grid curtailment, `SIT-003`
client-requested outage: the plant's hours, not the service provider's), and an interval carries a
fault when the fault's `[opened, closed)` covers the interval's start instant. Night does not reduce
`expected`: the contract counts hours, and an inverter is expected to be up at night (its DC side
idle); a project that counts daylight hours only takes a decision that supersedes this invariant.
A gap interval counts as expected and as up unless a fault covers it: the KPI says how many gaps it
counted (`gaps`) beside the number, never silently.

Worked example, twelve intervals (one hour), one inverter: a grid curtailment `SIT-002` covers
intervals 1 and 2 (10:05, 10:10); the inverter carries `INV-001` (OUTAGE) over intervals 2 to 5
(10:10 to 10:25 inclusive); interval 8 is a gap. `expected = 12`, `excluded = 2` (1, 2),
`contractual = 10`, `down = 3` (3, 4, 5: interval 2 is excluded first), `availability = 7/10 = 0.7`,
`gaps = 1`. `gaps` counts every gap sample handed to the KPI (J-010). Held by `solarpunk/leaf/kpi_defs.py`
(`EXCLUDED_CODES`) and `test/solarpunk/test_kpi.py`'s golden.

## SOL-08 Performance ratio is yield over reference yield

For a set of inverters over a period, with their samples:

    energy_kwh      = Σ power_kw × (SAMPLE_INTERVAL_S / 3600)       over samples that are not gaps
    reference_kwh   = Σ rated_kw × (irradiance / STC_IRRADIANCE_W_M2) × (SAMPLE_INTERVAL_S / 3600)
    performance_ratio = energy_kwh / reference_kwh                  (None when reference_kwh is 0)

summed over the same samples; a sample with no irradiance (`None`) is left out of both sums and
counted in `unreliable`. `STC_IRRADIANCE_W_M2` is 1000.0. A period whose site carries `SEN-001`
(irradiance sensor out of range) over any interval reports its ratio with `unreliable` set to those
intervals' count, never without. Worked example: one inverter rated 100 kW, three samples at
irradiance 500, 1000, 0 W/m² producing 45, 92, 0 kW: `energy_kwh = (45 + 92 + 0) × 5/60 = 11.4167`,
`reference_kwh = 100 × (0.5 + 1.0 + 0.0) × 5/60 = 12.5`, `performance_ratio = 0.9133` (four
decimals). A sample enters both sums only with both an irradiance and a power; otherwise, a gap included, it is left out
and counted once in `unreliable`, and the intervals a `SEN-001` fault covers are added to `unreliable` as distinct
instants, so an instant both missing its irradiance and covered counts twice (J-010; a union is a later decision). A
sample whose asset is unknown to the fleet passed, or whose asset has no `rated_kw`, is refused (SOL-03), never read as
zero. Held by `solarpunk/leaf/kpi_defs.py` (`STC_IRRADIANCE_W_M2`) and `test/solarpunk/test_kpi.py`'s golden.

## SOL-09 Energy yield is metered first, estimated second

A site's energy yield over a period is the revenue meter's energy where the meter carried no
`MTR-001` over the period, and the sum of its inverters' `energy_kwh` (SOL-08) where it did; the
KPI reports which (`source` is `meter` or `inverters`), never a number alone. With no meter reading given the
source is `inverters`, 0.0 kWh when there are no samples (J-012); the meter is lost when any `MTR-001` fault on the
site's meter overlaps the span from the first sample to the last plus one interval; `site` selects the samples and the
faults by the site part of their asset ids (J-010). Held by `test/solarpunk/test_kpi.py`'s golden and its two-source
test.

## SOL-10 MTBF and MTTR are per asset kind, from closed faults

Over a period and one asset kind, from faults whose code's severity is OUTAGE and whose
`[opened, closed)` lies within the period (`opened` at or after the start and `closed` at or before the end: an
outage that crosses either edge is left out whole, not clipped, J-010):

    mttr_h = Σ (closed − opened) / count                    (None when count is 0)
    mtbf_h = (assets × period_hours − Σ (closed − opened)) / count

where `assets` is the number of assets of that kind in the fleet. An open fault (no `closed`) is
excluded from both and counted in `open` when it opened inside the period; `assets` counts the assets of that kind in
the fleet handed to the KPI, and a fault on an asset not among them is ignored. Worked example: two inverters, a
24-hour period, two closed outages of 2 h and 4 h: `mttr_h = 3.0`, `mtbf_h = (48 − 6) / 2 = 21.0`. Held by
`test/solarpunk/test_kpi.py`'s golden.

## SOL-11 A derate is not an outage

A fault of severity DERATE or INFO never reduces availability (SOL-07) and never enters MTBF or MTTR
(SOL-10); its effect, if any, shows in the performance ratio (SOL-08). `counts_against_availability`
is the one place this is decided. Held by `test/solarpunk/test_codes.py`
(`test_only_an_outage_counts_against_availability`).

## SOL-12 The clause register names a test for every claimed clause

`docs/CLAUSE-REGISTER.md` holds one row per ISO 9001 or ISO 55000 clause this project claims to
hold, in the project's own words (the standards' text is not reproduced), with the test that holds
it; a row's test is a test function tagged with that clause (`Clause: 9001-9.1.3` in its docstring),
and `python3 -I scripts/clauses.py` prints every claimed clause as `held`, `failing` or `open` from
the test run. A clause with no test is `open`, never silently absent. This project claims conformance
to nothing: the register says which requirements its checks can flag, and that is all. Held by
lane 1.5's check (`scripts/checks/clauses.py`).

## SOL-13 Power output is energy, peak, specific yield and capacity factor, from the samples

For one inverter over a period, from its samples in the period:

    energy_kwh      = Σ power_kw × (SAMPLE_INTERVAL_S / 3600)       over samples that are not gaps
    peak_kw         = max power_kw                                  (None when no sample carries a power)
    specific_yield  = energy_kwh / rated_kw                         (kWh per kW of rating)
    capacity_factor = energy_kwh / (rated_kw × period_hours)

and for a site, the same over all its inverters' samples with `rated_kw` the sum of their ratings and `peak_kw` the
coincident peak: the largest sum of power at one instant. `records` counts the samples that carried a power and `gaps`
the gap samples, beside the numbers, never without them; an inverter with no `rated_kw`, or a rating of 0, is refused
(SOL-03). The site's power curve (the reports window's) is the summed power at each instant where every inverter
has a record carrying a power; an instant where any inverter has a gap is left out, so the drawn line breaks there and
never shows a gap as a fall in output. The report is recomputed from the stored samples each time it is asked for,
never kept. Worked example: over
10:00 to 10:15 (0.25 h), OAHE-INV-001 rated 100 kW produces 60, 90 kW and a gap, and OAHE-INV-002 rated 50 kW produces
30, 45, 42 kW. INV-001: `energy_kwh = (60 + 90) × 5/60 = 12.5`, `peak_kw = 90.0`, `specific_yield = 12.5 / 100 =
0.125`, `capacity_factor = 12.5 / (100 × 0.25) = 0.5`, records 2, gaps 1. INV-002: `energy_kwh = 117 × 5/60 = 9.75`,
`peak_kw = 45.0`, `specific_yield = 0.195`, `capacity_factor = 9.75 / 12.5 = 0.78`. The site: `energy_kwh = 22.25`,
`rated_kw = 150`, `peak_kw = max(60 + 30, 90 + 45, 42) = 135.0`, `specific_yield = 22.25 / 150 = 0.1483`,
`capacity_factor = 22.25 / 37.5 = 0.5933` (four decimals), records 5, gaps 1. Held by `solarpunk/kpi/output.py` and
`test/solarpunk/test_output.py`'s golden.

## SOL-14 A ticket moves through five statuses, against two targets set by its priority

A ticket (SP-022) is the work an engineer-assigned fault needs; it opens when the fault is assigned, never from a
suggestion. Its statuses are `open`, `acknowledged` (someone has taken it), `in progress` (work has started: the
response), `resolved` (the work is done, awaiting closure) and `closed` (closed with a root cause from the closed list,
which closes the fault, 4.1). Only these moves are allowed; any other is refused:

| From | To |
| --- | --- |
| open | acknowledged |
| open | in progress |
| acknowledged | in progress |
| in progress | resolved |
| resolved | in progress |
| resolved | closed |

A move from `open` straight to `in progress` acknowledges and responds at the same instant. `resolved` back to
`in progress` is a fix that did not hold; `closed` is final. The acknowledged instant is the first move out of `open`,
the responded instant the first move into `in progress`; neither is ever moved again.

Its priority follows the fault's severity, and each priority has two targets measured from the ticket's opening: to be
acknowledged within, and to be responded to (work started) within. Acknowledgement and response are the times a
contractor can guarantee; resolution often is not in its hands, so it has no target here (SolarPower Europe's O&M
guidelines draw the same line, J-060). **The targets are Ghost's to set: the hours below are Claude's proposal, in
force for the code until he sets his own.**

| Severity | Priority | Acknowledge within | Respond within |
| --- | --- | --- | --- |
| OUTAGE | P1 | 1 h | 4 h |
| DERATE | P2 | 4 h | 24 h |
| INFO | P3 | 24 h | 72 h |

Each target, at an instant, is in one of four states:

    due        = opened + target
    met        when it happened at or before due
    late       when it happened after due
    pending    when it has not happened and the instant is at or before due
    overdue    when it has not happened and the instant is after due

Worked example: an INV-001 outage (P1) is assigned and its ticket opened at 10:00 UTC; it is acknowledged at 10:40 and
put in progress at 14:30. Acknowledgement is due at 11:00 and happened at 10:40: `met`. Response is due at 14:00 and
happened at 14:30: `late`, by 30 minutes. At 13:00, before the response, the response target was `pending`; at 14:15 it
was `overdue`. A DERATE ticket (P2) opened at 10:00 and still open at 15:00 has its acknowledgement `overdue` (due 14:00)
and its response `pending` (due 10:00 the next day).

When a remote tracker is joined behind an adapter (8.3), each field has one owner, and the other side's copy is for
display only:

| Field | Owner |
| --- | --- |
| fault code | Solarpunk |
| assigned by | Solarpunk |
| root cause | Solarpunk |
| opened and closed instants | Solarpunk |
| status | Solarpunk |
| working assignee | tracker |
| comments | tracker |
| scheduling | tracker |

Solarpunk keeps what the KPIs and the clause register read; a tracker's change to a field Solarpunk owns is a proposal
Solarpunk's rules accept or refuse, never a write. Held by `solarpunk/leaf/tickets.py` (the statuses, the moves, the
priorities, the targets, the four states) and `test/solarpunk/test_tickets_contract.py`, which reads the three tables
above and the leaf and refuses any difference.
