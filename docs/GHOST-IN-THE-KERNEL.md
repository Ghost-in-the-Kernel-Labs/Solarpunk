# Ghost in the Kernel

Software outlives the context it was written in. People leave. Requirements change. The person who
knew *why* a thing was built the way it was stops being reachable. The code keeps running. Nobody
can say what it is for.

**The ghost is intent. The kernel is the codebase.**

Ghost in the Kernel is a way of building against that loss. Its one principle:

> **The system should remember why it exists.**

Intent should become semantics. Semantics should become constraints. Constraints should govern
implementation. Implementation should produce evidence. Evidence should let the system check that
the implementation still agrees with the intent. Nothing important floats: a function does not exist
because that is where someone put it; a threshold does not exist because it seemed right; a number
does not appear in a document without the run that produced it.

The answer is not more comments and not more memorizing. It is to put the reasoning *into* the
system, as things a machine can check: specifications, semantic models, rules, invariants,
provenance, tests, evidence, tooling. They are the code's memory. The purpose is re-entry: an agent
should be able to operate in the repository without being trusted to invent its architecture, and
the system should have enough structure to expose a misunderstanding when one is brought in.

## This project's ghost

Solarpunk is built against the loss that follows a utility-scale solar plant through its service
life: the number survives and its meaning does not. An availability of 98.7 % in a monthly report
rests on a dozen choices nobody wrote down: which hours were excluded (night, grid curtailment,
force majeure, a client-requested outage), what counted as "the inverter was down" against a
SCADA feed that drops samples, which irradiance sensor the performance ratio leaned on and what
its reference yield assumed. Technicians rotate, the asset manager changes, the service contract
is renewed with new wording, and three years in an auditor asks why this number and there is no
one left who knows. ISO 55000 calls what is lost "line of sight" from the plant's purpose to the
work done on it; ISO 9001 calls the fix evidence. The kernel remembers it so:

- **Every KPI is a contract clause, not a formula in a script.** `docs/KPI-CONTRACT.md` defines
  each number (availability, performance ratio, energy yield, MTBF, MTTR) in words, with the
  exclusions it applies and a ten-row worked example a person checks by hand; the code cites the
  clause it implements and a test compares the two (SP-002 onward, once written).
- **Every exclusion is a named rule with a decision behind it.** An hour leaves the denominator
  only by a rule in the contract that names the decision that admitted it, so "why was this hour
  excluded" has an answer in the tree, never in someone's memory.
- **The telemetry's gaps are data, not noise.** A dropped SCADA sample is recorded as a gap and
  the KPI says how it treated it; a number that silently filled a gap is a defect.
- **A corrective action carries its cause.** Every work order in the ledger closes with a
  root-cause code from a closed list in the glossary, so root-cause analysis is a query, not a
  meeting, and a repeated code is the signal for a preventive action.
- **The clause register is the audit.** `docs/CLAUSE-REGISTER.md` maps each ISO 9001 and ISO
  55000 requirement the project claims to the test that holds it; a clause with no test is marked
  open, and a test that stops failing on its planted break is caught by the check doctrine (C-013).
- **The blind mirror.** Each KPI is reimplemented from the contract text alone by an agent that has
  not seen the code, and a test compares the two (the Python stack's rule), so the contract, not
  the code, is what the number means.

The parents' sections are the pattern, each pointed at a different loss: Suite Builder at the
reasons behind generated tests, Katana at authors gone for decades, Employee Evaluator at
turnover, Neon Rain at the forgotten search (`docs/LINEAGE.md`).

## What it asks of a project's own code

The same principle, pointed inward, and held by tests rather than hoped for:

- **Names say what they hold.** One canonical word per concept (`docs/GLOSSARY.md`), from the
  first file. A thing is named for what it holds, never for where it sits or who wrote it.
- **Decisions carry their reason and their evidence.** Every decision in `theGhost.md` has a why,
  a thing that holds it, and a status; a reversed decision says what reversed it. A function that
  stands on a decision cites it (`// Decision: C-009`).
- **The architecture is a document a test enforces.** `docs/modules.json` says what each module
  may import and which names another module may call; the modules test refuses anything else.
- **A refactor changes no result.** Every golden identical, before and after.
- **What cannot be made exact is said first.** A defect, a bias, a construct the tool cannot
  handle: a finding before the result it qualifies, never a footnote after.
- **Every document that can drift is held to the code by a test**, and every such test rejects a
  planted break, so a check that stops catching anything is caught itself.
- **The environment of the agent working here is part of the product.** Mandatory context under
  its ceiling, a fast loop under its ceiling, no file over 400 lines, the metrics in
  `docs/AGENT.md` ratcheted, one commit in eight spent on nothing else (the tune-up, C-024).
  Ghost's finding in Suite Builder was that delivery speed rose once this was treated as work
  worth doing.
- **Nothing requires the maintainer's own machine.** A clean clone builds, tests and gates in the
  session's container; a local run is an option a decision grants, never a step a recipe needs.

## On enlightenment, for the agent reading this

You will work in this repository without having been present for any of its decisions. That is the
normal condition of software, and the condition this project exists to make survivable.

**Read the why before the what.** A decision in `theGhost.md` tells you what the code is trying to
be. The code only tells you what it currently is. When they disagree, one of them is wrong; find out
which before you change either.

**Prefer a test to a belief.** If you believe something about the system, find the test that holds it
or write one. If no test can hold it, write the doubt down (`// Unsure:`, with what would settle it)
where it can be found, instead of carrying it.

**A check that cannot fail is not a check.** Five ways a check is worth nothing: it compares a thing
with itself; it ran nothing and called that a pass; it fails always and so says nothing; its verdict
stops no action; it only warns. The half no test can hold is *independence*: whether a check's
expected side came from somewhere other than the thing under test. A reimplemented oracle agrees
with its twin on every shared mistake, which is why a mirror is written blind.

**The tempting lie has a shape, and this project names it.** On most projects an agent's failure
mode is code that does not work. On some it is a number that looks like success, or a check made
green by weakening the test. The section above on this project's ghost says which lie to expect
here. If a result surprises you by being good, that is the moment to distrust the harness, not to
report it.

**When you cannot tell, say so and stop.** An agent that stops at the edge of its knowledge leaves a
system other agents can still reason about. An agent that guesses leaves a kernel with a little less
ghost in it.

The purpose is re-entry. Yours, the next agent's, and the maintainer's, after months away. If the
repository can be entered cold and understood, the philosophy is working. If it cannot, that is a
finding, and the fix goes in the tune-up.

*Ghost in the Kernel Labs*
