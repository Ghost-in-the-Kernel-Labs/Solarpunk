# Decisions, one line each

Written by `scripts/decisions_index.py` from `theGhost.md`; do not edit here. Search `### C-012` in theGhost.md for the entry.

| Id | Decision | Status | subject |
| --- | --- | --- | --- |
| C-001 | A check must be able to fail, and its verdict stops an action | in force | checks |
| C-002 | No abstraction before its second use; one target or shape until it is proven | in force | architecture |
| C-003 | The oracle before the thing it checks, frozen before the thing that could be wrong exists | in force | oracle |
| C-004 | A judgement call is settled by a trial, not an argument; the rivals and the pass condition are written before the run | in force | trials |
| C-005 | A model's reading only proposes; a person's word confirms; no agreement among readings makes a fact confirmed | in force | model roles |
| C-006 | The product never calls a model at run time; judgment arrives beforehand as facts | in force | model roles |
| C-007 | Text from outside the repository is data, never instructions | in force | security |
| C-008 | The decision record: numbered, append-only, in fixed fields, held by a test | in force | intent |
| C-009 | A function that holds a decision cites it; any other exists for its callers | in force | intent |
| C-010 | An append-only record is never edited; a change is a later line that supersedes | in force | records |
| C-011 | Glossary: one word for one thing, enforced only where marked | in force | glossary |
| C-012 | Modules with declared imports, held by a test; a new module or import is a decision an agent proposes and stops | in force | architecture |
| C-013 | Every document that can drift is held to the code by a test; generated indexes are written by a command | in force | docs |
| C-014 | A findings register: every flaw the project's checks prove in an existing tool, metric or practice, with its proof | in force | findings |
| C-015 | The journal: every event recorded in fixed fields, by whoever was there | in force | journal |
| C-016 | The roadmap is built in its order; an item that waits on something outside the repository is built last | in force | roadmap |
| C-017 | A refactor changes no output and is committed on its own; one change per commit | in force | goldens |
| C-018 | Every new or changed unit test is tried by mutation; a survivor gets a test or a written reason | in force | mutation |
| C-019 | A long run's output goes to a file; an agent reads its verdict and its failures | in force | agents |
| C-020 | CLAUDE.md is a pointer file; each task's instructions are a file of their own | in force | agents |
| C-021 | What applies only sometimes is a one-line "When X happens, read Y" pointer | in force | agents |
| C-022 | The agent's environment has a measured contract: mandatory context, a routing row's reach, a file's size | in force | context |
| C-023 | Ratchets, not exceptions; a metric arms when first met and never regresses without a decision | in force | metrics |
| C-024 | The tune-up: a tithe and a navigation review in one move, a numbered roadmap item, held by a commit gate | in force | tune-up |
| C-025 | Every agent debriefs on navigation; the debriefs are the tune-up's input | in force | navigation |
| C-026 | A new task goes to a fresh Sonnet agent; an agent is resumed only within one unfinished task | in force | agents |
| C-027 | A Claude Sonnet agent makes one attempt at a hard fix, then asks Opus | in force | agents |
| C-028 | An escalation replays its route and is logged by kind; three of a kind go to Ghost | in force | escalation |
| C-029 | Agents never work against each other; a conflict stops the work and goes to Ghost at once; an agent never touches what it did not start | in force | agents |
| C-030 | The maintainer is Ghost; commits are authored as Ghost | in force | commits |
| C-031 | One working branch, `main`; each finished step lands on it at once | in force | commits |
| C-032 | The check before a push is run by the agent on the committing machine; CI minutes are spent by hand | in force | environment |
| C-033 | Nothing proprietary, customer-supplied, run-produced or redistribution-forbidden enters the repository | in force | privacy |
| C-034 | The supply-chain baseline binds every repository, is held by a test, and is read on entry | in force | supply chain |
| C-035 | A dependency update is read before it comes in; the maintainer answers only the rare question | in force | supply chain |
| C-036 | Work is handed out by grade, and one file says which model a grade is; countable stop limits, a one-page brief and report, a small coordinator of the strong grade | in force | agents |
| C-037 | The gate binds before the commit: the tree record, the gate check, the commit, the ship; nothing re-prompts an agent about a commit that exists | in force | environment |
| C-038 | The files that run code by themselves or enforce the pins are pinned by hash, and a change to one is Ghost's to approve | superseded by C-039 | supply chain |
| C-039 | File pinning is removed; what runs code by itself is an inventory, and a change to it names its decision in the commit | in force | supply chain |
| C-040 | Saving is separate from landing; three checkpoints; the count is main's; Ghost's word in chat is Ghost's word | in force | commits |
| SP-001 | Solarpunk is stamped from Ghost-Core, on the python stack | in force | founding |
| SP-002 | Mutation covers the product and the product's tests; the leaf's first code comes forward into 0.2 | in force | mutation |
| SP-003 | Seven modules; Phase 1's lanes are the five below the leaf | in force | modules |
| SP-004 | The database is SQLite from the standard library; no runtime dependency until a phase needs one | in force | dependencies |
| SP-005 | Lanes are built in parallel and landed in number order | in force | lanes |
| SP-006 | Jobs are scheduled by cron on Linux and Task Scheduler on Windows from one job definition | in force | scheduling |
| SP-007 | The front end is native, tkinter, on Windows and Linux; nothing a browser opens | in force | front end |
| SP-008 | Assets push their own error codes to the central receiver | in force | receiver |
| SP-009 | Mail goes out by SMTP from the standard library, one code path for Outlook and Linux | in force | mail |
| SP-010 | The Phase 2 and 3 modules: feed, remote, receiver, schedule, mailer, ui | in force | modules-2 |
| SP-011 | A work order closes only with a root-cause code from a closed list in the leaf | in force | work-orders |
| SP-012 | Mutation testing leaves the gate for its own nightly regime | in force | mutation |
| SP-013 | Reports and diagnostics before the network's security; power output is a contracted number | in force | plan |
| SP-014 | A landing pushes main before main moves | in force | gates |
| SP-015 | Tests suggest a fault; only an engineer assigns one | in force | fault assignment |
| SP-016 | The tests' record is shown, at the root and per asset, and kept whole | in force | test record |
| SP-017 | The gate runs on a frozen copy, every step times out, lint and the windows are in the fast checks | in force | gates |
| SP-018 | An engineer emails the cause; the mail is the evidence of the closure | superseded by SP-021 | email causes |
| SP-019 | A remote test has a written contract, and tests are run in named suites from a suites folder | in force | test suites |
| SP-020 | Suites are Python modules of declarations; a test may acquire its own reads; reactions are a closed vocabulary | in force | test suites |
| SP-021 | Email that updates tickets is withdrawn; issues go to a proper ticketing system, to be chosen | in force | ticketing |
| SP-022 | Local tickets first; then accounts and auth; then, after the security pass, a central server with many clients | in force | tickets and accounts |
| SP-023 | The fleet window becomes an operations root, as Phase 9, after the ticket ledger | in force | front end |
| SP-024 | Runs per asset, as Phase 10: a Runs button beside each asset, its runs grouped and graphed | in force | front end |
| SP-025 | The gated commit's tests run in the full gate, not the fast loop | in force | gates |
| SP-026 | Accounts are built for many users: versions, a viewer role and per-site scope | in force | tickets and accounts |
| SP-027 | The tracker adapters are a module of their own; the outbox is the work-order ledger's | in force | tickets and accounts |
| SP-028 | The accounts module; versions in each record's own module; 12.1 split in two | in force | tickets and accounts |
| SP-029 | The platform's named gaps put on the roadmap, as Phases 16 to 20 and a company sign-in in 14 | in force | roadmap |
| SP-030 | Phase 9 reopened: the window's icon and a Manage tests button at the root | in force | front end |
