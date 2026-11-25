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
is the one place this is decided; `INV-005` (output under the performance floor, a DERATE, raised by a failing
`performance_above_floor`) counts nothing against availability, its effect is the ratio itself. Held by `test/solarpunk/test_codes.py`
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
suggestion. A ticket also opens from a failed test result, not from the asset (7.9, SP-046): an engineer opens it on
one failed result (its asset, test and run), as the corrective work order on the fault telemetry raised for that result,
its priority from that fault code's severity; a passing, no-data or unknown result, or one with no such fault, is refused.
One ticket holds many failed results (the `ticket_results` table, a result in at most one ticket, rows only added): two
results are consecutive when they are the same test on the same asset with no other result of that test between their run
instants, and a failure in the run right after a failure of the same test on the same asset joins that failure's ticket,
a pass or no data ending the streak. Opening a ticket on a failed result already in a ticket shows that ticket and opens
no second one. The control is "Open a ticket" on a failed result in the asset window and the Runs window, and `solarpunk
ticket open --result ID`; the Tickets window and `ticket show` list a ticket's failed results. Its statuses are `open`, `acknowledged` (someone has taken it), `in progress` (work has started: the
response), `resolved` (the work is done, awaiting closure) and `closed` (closed once its fault's root cause is written,
which closes the fault, 4.1, SP-046). Only these moves are allowed; any other is refused:

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

    due        = start + target
    met        when it happened at or before due
    late       when it happened after due
    pending    when it has not happened and the instant is at or before due
    overdue    when it has not happened and the instant is after due

`start` is the ticket's opened instant, except for a ticket opened from a failed test result (7.9): its targets are counted
from the instant that result ran, the earliest failed result linked to it that ran at or before the ticket opened, since
the failure is when the clock began, not when someone clicked (13.15, SP-053). Both instants are kept (the ticket's
recorded opened instant is not moved, nothing back-filled); a ticket opened with its fault starts at its opened instant,
results that join it later changing nothing. Hand-checked: a P3 ticket opened at 13:05 on a result failed at 13:00 has
`start` 13:00, so its acknowledgement is due 13:00 + 24 h, 13:00 the next day (not 13:05), and its response 13:00 + 72 h;
`ticket show` and the Tickets window say those instants, and its opened instant stays 13:05. Held by
`solarpunk/project/tickets.py` (`target_start`) and `test/solarpunk/test_result_tickets.py`.

Worked example: an INV-001 outage (P1) is assigned and its ticket opened at 10:00 UTC; it is acknowledged at 10:40 and
put in progress at 14:30. Acknowledgement is due at 11:00 and happened at 10:40: `met`. Response is due at 14:00 and
happened at 14:30: `late`, by 30 minutes. At 13:00, before the response, the response target was `pending`; at 14:15 it
was `overdue`. A DERATE ticket (P2) opened at 10:00 and still open at 15:00 has its acknowledgement `overdue` (due 14:00)
and its response `pending` (due 10:00 the next day).

In the ledger (8.2), every work order is a ticket. A corrective one opens with its fault, in the same call that assigns
it, its priority from the fault's code; a preventive one, having no fault, is P3 (Claude's proposal, Ghost's to set). A
move out of `open` stamps the acknowledged instant, the first move into `in progress` the responded instant; `resolved`
stamps the resolved instant and needs closeout evidence (words saying what was done), and a move back to `in progress`
clears both. No instant may come before the ticket's opening. A fault's root cause is blank until an engineer writes it as free text (no list, no dropdown), each writing a new
row with who wrote it (and the operator, when entered on the engineer's word) and when, the latest superseding the
earlier without erasing it (7.8, SP-046). A ticket on a fault closes only once the fault's root cause is written, and
closes the fault if it is still open (4.1); a ticket with no fault (preventive) closes without one. Closing a ticket that has not reached `resolved` (the one-step close-out of 4.1)
is the allowed moves taken at the one instant: `open` to `in progress` to `resolved` to `closed`, an instant already
stamped kept. So a ticket closed at 13:00 that nobody acknowledged has its acknowledgement and response at 13:00, and
its targets read what that says. Comments carry their author and instant and are never edited or deleted. Every move,
the close included, is logged in the ticket's history with the status it moved to, its instant and the account that
made it, or none where nobody is signed in (SOL-16, SP-035): a row is only ever added, a refused or stale move adds
none, the history reads oldest first, and a store made before it gains the empty history on opening, nothing
back-filled. A ticket is
past a target when, at the instant asked, a target is `late` or `overdue`. Closing the fault alone (`solarpunk fault
close`) ends the downtime and leaves the ticket open, to be closed once its root cause is written.

The proof follows the action (13.21, SP-055): a ticket opened from a failed test result closes only after a later pass.
For every failed result linked to it, a passing result of the same test on the same asset must be stored strictly after
that failure's run instant and at or before the close's instant (SP-056: a close never precedes the pass that proves it; any result of the default suite `all`; the ping's `reachable` pass, "answered: N new records",
counts). The test is matched by name (SP-056): a failed `reachable` is proved by a `reachable` pass alone, never by a
`records_stored` pass, the script that judges the stored records. Until then resolving is refused, after the root-cause check (a ticket with neither is refused for the cause),
naming the test and the asset: "ticket 4 waits for a pass: reachable on OAHE-INV-002 has not passed since its failure at
2026-06-01T13:00:00+00:00". Nothing is written; the Tickets window's panel and `solarpunk ticket resolve` (exit 2) say the
same words as they say the root-cause refusal. A ticket with no linked result (an engineer's fault, a preventive order) is
unchanged. Hand-checked: a ticket opened from `reachable` on OAHE-INV-002 failed at 13:00, its cause written; resolving
at 13:20 is refused (no pass after 13:00); a later run with the feed still dead stores a `records_stored` pass and
another `reachable` failure, and resolving is still refused; a pass of `reachable` is stored at 13:25; resolving at 13:30
closes it. A
pass stored at 13:35 does not prove a close at 13:30 (refused as before), and one stored at 13:30 itself does. A
pass stored at 13:00 itself, or before, would not count. The demo's revival is stamped at the window's clock when that is
already after the latest move, comment or root cause stored on that asset's tickets, and one minute after that act only
when the clock is behind it (the terminal track's `--at` acts), so its pass always follows the last act and a Resolve
pressed after it closes at or after the pass. Held by
`solarpunk/project/causes.py` (`require_pass`), `solarpunk/project/revival.py` (`last_ticket_act`) and
`test/solarpunk/test_proof.py`.

When a remote tracker is joined behind an adapter (11.1), each field has one owner, and the other side's copy is for
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

A ticket change reaches a tracker by the outbox (11.1, SP-027): each change writes its event (create, update, comment,
transition) in its own commit, and a drain hands the events to the tracker oldest first, stamping each one taken; a
tracker that cannot be reached leaves them waiting and never stops a change in the ledger. A tracker's `create` is
idempotent: a work order delivered twice is one issue.
Solarpunk keeps what the KPIs and the clause register read; a tracker's change to a field Solarpunk owns is a proposal
Solarpunk's rules accept or refuse, never a write. Held by `solarpunk/leaf/tickets.py` (the statuses, the moves, the
priorities, the targets, the four states) and `test/solarpunk/test_tickets_contract.py`, which reads the three tables
above and the leaf and refuses any difference.

## SOL-15 A run, an error count and a power series are read from the store, never kept apart from it

What the Runs window shows (Phase 10, SP-024), defined before it is built. Nothing here is a new stored record: each
is a reading of the results, the faults, the suggestions and the samples the store already holds, made each time it is
asked for, so it cannot disagree with them; nothing is deleted to make it, and a window shows the newest 100 where
more are kept (SP-016).

**A run** of an asset is every result stored for it at one instant: one per remote test its kind runs, and the ping's
own `reachable` beside the test's own: a failure when the feed did not answer, and a pass, "answered: N new records"
(N the samples that ping stored, 0 included), when it did, both untimed and in suite `all` (SP-055, SP-056: `reachable`
is the live ping alone; the script that judges the stored records is `records_stored`, so one run holds a result of
each: one says what the feed did, the other what the stored samples showed; a store made before SP-056 keeps its old
`reachable` rows, read as the ping's history). A result is a pass, a failure or **no
data** (SP-039): a test with no stored record that is not a gap has nothing to check, so `records_stored` fails it, a
disconnection, and every other test returns no data, shown grey like "not run", never a pass and never a failure. A
day of real records with none of the kind a test needs (no daylight record, no night record) is judged, not no data.
A run **failed** when any of its results failed. An asset's runs are listed newest first; a run's results failures
first, then no data, then by test name.

**An error count** of an asset over a period is, per catalogue code, the faults opened on it inside the period and
the suggestions raised on it inside the period, counted apart and never added together (a fault is a
record raised by a test, a device or an engineer; a suggestion is one an older store holds, raised before 7.7 and
never since, SP-046). A suggestion counts whether it is open, accepted or dismissed (it was raised all the same), and
the fault an accepted one became counts once more as a fault. A fault
counts by its opening instant, a suggestion by its raising instant, the period half-open `[start, end)` (SOL-06). The
fleet's count of one code is the same, per asset, over every asset that has one.

**A power series** of an asset over a period is its samples inside the period in time order, each a power or a gap;
a gap is named and counted beside the series, never filled, joined across or read as zero (SOL-13's rule for the
curve). `records` counts the samples carrying a power, `gaps` the gap samples, as SOL-13 does.

Worked examples, over the demo store (`python3 -m solarpunk.ui --demo`, one run at 2026-06-01 13:00 UTC):

    OAHE-INV-002's run at 13:00     9 results, failed: performance_above_floor failed ("ratio 0.6148 under the floor
                                    0.75 over 71 daylight records": its stored power is 0 from its outage's start,
                                    11:30; raising INV-005, assigned by test:performance_above_floor) and reachable
                                    failed ("127.0.0.1:9 is unreachable", the ping; raising SIT-004, assigned by
                                    test:reachable); power_ripple no data; records_stored passed ("156 records"), and its
                                    five other tests passed
    OAHE-SEN-001's run at 13:00     4 results, failed: the ping's reachable and records_stored failed
                                    ("127.0.0.1:9 is unreachable", "no records"), irradiance_in_range and on_grid no data ("no records"), never a pass
    errors, OAHE-SEN-001, the day   faults: SEN-001 1 (open since 13:00); suggestions: none
    errors, OAHE-INV-002, the day   faults: INV-001 1 (open since 11:30), INV-005 1 and SIT-004 1 (open since 13:00); suggestions: none
    errors, OAHE-INV-001, the day   faults: INV-002 1 (10:05 to 10:45); suggestions: none
    INV-001 across the fleet        OAHE-INV-002: faults 1, suggestions 0; no other asset
    power, OAHE-INV-001, the day    288 samples: records 279, gaps 9 (the first at 04:25, one at 10:40)

Held by `test/solarpunk/test_runs_contract.py`, which reads each example's numbers from the demo store and finds each
example's line in this section, and by `solarpunk/project/runs.py` (10.2: `asset_runs`, `asset_power`,
`asset_code_counts`, `code_counts_by_asset`) with `test/solarpunk/test_runs.py`, which reads the same examples through it.

## SOL-16 An account acts within its role and its sites, and its password is never kept

Who may act, and where (12.1, SP-022, SP-026, SP-028). An **account** is an email (its name for every record), a
person's name, one **role**, whether it is **active**, when it was **created**, and its **site scope**: the sites it
may see and act on, or all. An admin's scope is all.

| Role | Acts |
| --- | --- |
| engineer | assigns faults, works tickets, within its sites |
| operator | enters an engineer's call-in and works tickets, within its sites |
| viewer | nothing: every write is refused, by name |
| admin | manages accounts; every site |

(12.1 holds the viewer and the site scope; 12.4 the acts of the others, "Every act is the account's" below.) An
account sees an asset, a fault, a suggestion and a ticket only when the asset's site is in its
scope, and acts on none outside it. An account that is not active is refused at its password and acts on nothing.
An engineer address the fleet names with no active engineer account is flagged by a query, so a fault assigned in its
name before accounts is not mistaken for an authenticated one.

**A password is never stored, logged, shown, mailed or written in a test.** It is checked by
`hashlib.scrypt(password, salt, n=16384, r=8, p=1, dklen=32)` with a fresh 16-byte salt per account; the stored line is
`scrypt$16384$8$1$<salt as hex>$<hash as hex>`, its parameters beside it so a later change of them reads the old lines
still, and a check compares hashes in constant time (`hmac.compare_digest`). A password is at least 12 characters.

Worked example, over the demo fleet (all of it site OAHE) with three accounts: `site@oahe.example` an engineer of OAHE,
`auditor@oahe.example` a viewer of all sites, `crew@bigs.example` an engineer of BIGS alone.

    site@oahe.example acknowledges OAHE-INV-002's ticket     allowed
    auditor@oahe.example lists the fleet                      11 assets
    auditor@oahe.example acknowledges it                      refused: "auditor@oahe.example is a viewer and acts on nothing"
    crew@bigs.example lists the fleet                         0 assets
    crew@bigs.example acknowledges it                         refused: "crew@bigs.example may not act on site OAHE"
    the fleet's engineers with no engineer account            inverter@oahe.example

Held by `solarpunk/accounts/` (the table, the password check), `solarpunk/project/access.py` (the role and the scope),
and `test/solarpunk/test_accounts.py`, which runs this example.

**A stale screen never overwrites another person's change** (12.2, SP-028). An asset, a fault, a suggestion (of an older
store) and a ticket each carry a **version**, 1 when made, its column in the table of the module that owns the record, raised by one
in the same write as every change to it: an asset's engineer; a fault's close; a
ticket's move, assignee, note, priority and close. A comment changes no ticket (comments are only ever added, so none
is lost). A write made from a screen names the version it read; one read at another version is refused with "<record>
changed by someone else since you read it; refresh" and writes nothing A
write that names no version (the scheduled run; the command line, which acts on what it reads in the same call) is not
checked. A store made before 12.2 gains the columns on opening, every record at version 1.

Worked example, over the same store: two screens read OAHE-INV-002's ticket (work order 1) at version 1.

    the first screen sets its assignee to "crew B"             allowed: version 2
    the second screen, read at version 1, acknowledges it      refused: "ticket 1 changed by someone else since you read it; refresh"
    the ticket after the refusal                               open, assignee crew B, version 2
    the second screen refreshes, reads version 2, acknowledges allowed: version 3

Held by `solarpunk/leaf/versions.py` (the rule and its words), each owning module's version column, and
`test/solarpunk/test_versions.py`, which runs this example.

**Signing in** (12.3, SP-032). A store that holds no active account asks nobody: anyone at the machine acts, and the
window says so. Once it holds one, the windows open on a sign-in and the fleet window opens only after a good one; a
command that acts takes `--as EMAIL` and asks its password with `getpass`; a command that reads, and the scheduled run,
which acts as no person and attributes nothing to one, ask nothing. A refusal says "that email and password do not
match an active account", whichever part was wrong. A failed sign-in is kept with the account it named, or "no such
account", and its instant; nothing of the password typed is kept.

**Every act is the account's** (12.4, SP-015, SP-022). In a store with an active account, an act is recorded as the
account signed in, never as an address chosen. An engineer assigns a fault as
themself: `assigned_by` its email, `recorded_by` empty. An operator enters one on an engineer's word
and names the engineer (`--for ENGINEER` at the command line, "On the word of" in the window): `assigned_by`
that engineer, `recorded_by` the operator; the engineer named is an active engineer account whose sites
hold the asset's, else "<email> is not an active engineer of site OAHE", and an engineer naming one is refused, as
they act as themself. A fault a failing remote test or a pushed code raises (SP-046) is assigned by no account: `assigned_by` is
`test:<name>` or `device`. Whoever assigns a fault, by any door, is in such
a store an active engineer account whose sites hold the asset's: the fleet need not also name the address, so a new
engineer acts once their account is made, and an address the fleet names with no such account is refused,
"inverter@oahe.example is not an active engineer of site OAHE"; a store with no active account keeps SP-015's rule, an
engineer the fleet names. An admin and a viewer assign and decide nothing ("admin@oahe.example is an admin and assigns
no fault"). A ticket is acknowledged, commented on and resolved by an engineer or an operator, as their own act, a
comment's author the account; an admin is refused ("admin@oahe.example is an admin and works no ticket"). Every move
of a ticket (acknowledge, start, resolve, reopen, close) is logged with the account that made it, an operator's as
their own, in a history only ever added to, so who acknowledged and who resolved stay on record, not only the last
move (SP-035); where nobody is signed in the move is logged as nobody's, and the asset window's ticket panel shows the
history one line per move, "nobody signed in" for those. Every act stays within the account's sites. `--by` and `--recorded-by` given where there are accounts are refused, "this
store has accounts: the signed-in account is used, so --by and --recorded-by are not taken", and the window shows an
engineer no picker; a store with no active account takes them as before, and the scheduled run attributes nothing.

Worked example, over the same store with `ops@oahe.example` an operator of OAHE:

    site@oahe.example assigns INV-001 on OAHE-INV-001          open by site@oahe.example
    ops@oahe.example assigns INV-002 --for site@oahe.example   open by site@oahe.example entered by ops@oahe.example
    ops@oahe.example assigns INV-003 --for crew@bigs.example   refused: "crew@bigs.example is not an active engineer of site OAHE"
    ops@oahe.example comments on its ticket                    the comment by ops@oahe.example

Worked example, a ticket's history and the engineer accounts (SP-035), over the same store with BIGS-INV-001 (site
BIGS, whose engineer the fleet names nowhere) loaded beside it; the panel's line for each move is on the right:

    ops@oahe.example acknowledges OAHE-INV-001's ticket at 11:40   2026-06-01 11:40 UTC · acknowledged · ops@oahe.example
    site@oahe.example resolves and closes it at 12:00              2026-06-01 12:00 UTC · in progress · site@oahe.example
                                                                   2026-06-01 12:00 UTC · resolved · site@oahe.example
                                                                   2026-06-01 12:00 UTC · closed · site@oahe.example
    a ticket acknowledged at 11:40 in a store with no account      2026-06-01 11:40 UTC · acknowledged · nobody signed in
    crew@bigs.example assigns INV-001 on BIGS-INV-001              open by crew@bigs.example
    a fault assigned as inverter@oahe.example, which the fleet names and no account holds
                                                                   refused: "inverter@oahe.example is not an active engineer of site OAHE"

Held by `solarpunk/project/attribution.py`, `solarpunk/project/engineers.py`, `permit_ticket_work` in
`solarpunk/project/access.py`, the ticket ledger's history in `solarpunk/workorders/`, `test/solarpunk/test_attribution.py`,
which runs the first example, and `test/solarpunk/test_ticket_moves.py`, which runs the second.

**An admin manages the accounts** (12.5, SP-022, SP-032). The first admin is made on the machine by `solarpunk account
init`, which asks a name, an email and a password, and only once: a store that holds an admin, active or not, refuses
it with "this store already has an admin: account init makes only the first; an admin adds the rest". Every other
change is an active admin's, signed in with `--as`: `account add` makes an account, `account reset` gives one a new
password (the old one then fails), `account deactivate` stops one. A store with no active account refuses them with
"this store has no active account: make the first admin with solarpunk account init", so no account is made where
nobody signed in; any other role is refused by name ("site@oahe.example is an engineer and does not manage accounts").
An account is never deleted: deactivating keeps its row and its email, so every record that names it keeps the name,
and it fails sign-in after. The last active admin is not deactivated, so the store is never locked out. Deactivating an account already deactivated is refused ("site@oahe.example is already deactivated"). `account add` and
`account reset` refuse, in one project call before any password is asked (`permit_new_account`, `permit_password_reset`,
as `account init` does with `permit_first_admin`), what needs none: no admin signed in, a blank name or email, a role
but an admin's with no `--site`, an email already held, an unknown email to reset. A new password
is asked twice and the two must match. `account list` reads: email, name, role, active, sites and created, never the
stored line. `solarpunk ticket show ID` prints a ticket's line and one line per
move, oldest first, whatever its status, to an account that sees its site (a viewer reads; `moves_for`).
