# The goal: where Solarpunk is going

Ghost, 2026-11-18, in his words. The roadmap (`docs/ROADMAP.md`) is the path; this is where it leads. A phase is
planned against this page: what it adds to one of the five areas below, and what it joins to another.

The goal of Solarpunk is to create a software system that fully integrates the following areas under a single
one-click solution: a substantially integrated solar asset quality and operations platform.

## 1. Asset and fleet intelligence

A proper hierarchy of portfolios, sites, blocks, inverters, strings, trackers, and other maintainable assets. Asset
history, operating status, performance baselines, and condition indicators.

## 2. SCADA and performance analytics

More sophisticated telemetry ingestion, normalization, anomaly detection, alarm correlation, and performance
comparisons. Potentially simulated integrations with multiple inverter or SCADA sources.

## 3. Maintenance execution

Preventive maintenance schedules, corrective work orders, assignment, priorities, SLA tracking, inspection checklists,
closeout evidence, and asset maintenance histories.

## 4. Quality management

Nonconformances, root-cause analysis, corrective and preventive actions, effectiveness verification, audit evidence,
document control, and ISO requirement traceability.

## 5. Management reporting

Availability, performance ratio, energy yield, MTBF, MTTR, maintenance backlog, recurring faults, contractor
performance, and quality trends. More importantly, relationships between these metrics.

## Where the repository stands today

A first slice of each area exists, built in Phases 1 to 5; the rest is unplanned and Ghost's to place on the roadmap.

- **Assets and fleet**: sites, inverters, strings, trackers, meters and sensors with a parent and a status colour. No
  portfolio or block level, no asset history view, no baselines or condition indicators.
- **SCADA and analytics**: synthetic five-minute telemetry, one feed format with a simulator, three remote tests. No
  anomaly detection, alarm correlation or second source.
- **Maintenance**: corrective and preventive work orders that close with a root-cause code. No schedules, assignment,
  priorities, SLA tracking, checklists or closeout evidence.
- **Quality**: a closed fault catalogue, root-cause codes, and the clause register tracing each claimed ISO 9001 and
  ISO 55000 clause to its test. No effectiveness verification, audit evidence store or document control.
- **Reporting**: availability, performance ratio, energy yield, MTBF and MTTR, repeated faults and repeated causes on
  the command line. No backlog, contractor or trend reporting, and nothing yet that relates one metric to another.
- **One click**: on Windows the single word `solarpunk` opens the window (`solarpunk --help` lists the rest).
