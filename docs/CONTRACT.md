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
`gaps = 1`. Held by `solarpunk/leaf/kpi_defs.py` (`EXCLUDED_CODES`) and lane 1.4's golden.

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
decimals). Held by `solarpunk/leaf/kpi_defs.py` (`STC_IRRADIANCE_W_M2`) and lane 1.4's golden.

## SOL-09 Energy yield is metered first, estimated second

A site's energy yield over a period is the revenue meter's energy where the meter carried no
`MTR-001` over the period, and the sum of its inverters' `energy_kwh` (SOL-08) where it did; the
KPI reports which (`source` is `meter` or `inverters`), never a number alone. Held by lane 1.4's
golden and its two-source test.

## SOL-10 MTBF and MTTR are per asset kind, from closed faults

Over a period and one asset kind, from faults whose code's severity is OUTAGE and whose
`[opened, closed)` lies within the period:

    mttr_h = Σ (closed − opened) / count                    (None when count is 0)
    mtbf_h = (assets × period_hours − Σ (closed − opened)) / count

where `assets` is the number of assets of that kind in the fleet. An open fault (no `closed`) is
excluded from both and counted in `open`. Worked example: two inverters, a 24-hour period, two
closed outages of 2 h and 4 h: `mttr_h = 3.0`, `mtbf_h = (48 − 6) / 2 = 21.0`. Held by lane 1.4's
golden.

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
