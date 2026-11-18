# TODO: the open items, in order

The roadmap as a chain: items are done in this order, never out of it, and an item that cannot be
done as written stops the chain and goes to Ghost (C-016). Each item's plan is its step in
`docs/ROADMAP.md` §6, by the same number; its check is copied here. A done item moves to
`docs/DONE.md` with its number kept. `test/test_todo.py` holds this file: headings in numeric order
under their phase, the first open item has a check, every phase ends with a tune-up pass (a reopened phase
of at most three new items with a tune-up commit, `docs/when/tune-up.md`), and
nothing is both here and done or done twice. An item that waits on something outside the repository (Ghost's choice
or approval, counsel, another project) carries a `Waits on:` line naming it in words, or one of the two kinds with a
shape for what a session lacks, `Waits on: environment (<host or tool>)` or `Waits on: reference (<what>)`
(`scripts/checks/todo.py`), and moves to the last phase, headed `## Phase W: waiting on Ghost`, keeping its number and adding a `Moved: from Phase N` line; a phase
whose every item waits takes its tune-up pass with it (the pass's `Waits on:` names those items), and the waiting
phase needs no pass of its own. When what it waits on arrives, Ghost moves the item back into the chain. An open
question a later item depends on is copied into that item's text, so the item reads whole where it stands.

## Phase 0: founding

## Phase 1: the fleet, its faults, its numbers

Lanes (P-15): 1.1 to 1.5 are built in parallel by separate workers and landed in this order; 1.6 and 1.8 in parallel after them, then 1.7.

## Phase 2: the feed, the remote tests, the clock

Lanes (P-15): 2.1 first (the list every other lane reads), then 2.2 to 2.6 in parallel, landed in this order; 2.7 after them (it joins them in project); 2.8 the pass.

## Phase 3: the native front end

Lanes (P-15): 3.1 to 3.3 in parallel after 2.7, landed in this order; 3.4 after them.

## Phase 4: the work-order ledger

Lanes (P-15): 4.1 alone, then 4.2 the pass.

## Phase 5: one word to run it

Lanes (P-15): 5.1 and 5.2 in order, then 5.3 the pass.

## Phase 6: reports and diagnostics

Lanes (P-15): 6.1 and 6.2 in parallel, landed in that order (done, J-041); 6.3 after 6.1 (done, J-043) and 6.4 after 6.2 (done, J-045); 6.5 the pass.

## Phase 7: faults suggested by tests, assigned by engineers

Lanes (P-15): 7.1 (done, J-050), then 7.2 and 7.3 (SP-017, put ahead by Ghost), then 7.4 (it needs 7.1's `assigned_by`), then 7.5, then 7.6 the pass. Ghost's direction, SP-015.

### 7.6 Tune-up pass 7

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 8: the cause by email

Lanes (P-15): 8.1 and 8.2 in parallel, then 8.3 (it needs both), then 8.4, then 8.5 the pass. Ghost's direction, SP-018.

### 8.1 The reply token

The mailer's mail about a fault carries a token that binds a reply to that fault, unforgeable without the settings'
key (SP-018).

Check: `solarpunk/mailer/` makes a token for a fault id from a key in the settings file (`hmac`, SHA-256, a short hex digest) and checks one, refusing a forged, altered or other fault's token; a mail about a fault carries `[Solarpunk F<id>-<token>]` in its subject and asks for a reply with the cause, a `CAUSE: <word>` line read first; no key is in the repository and the tests build theirs at runtime (the binding rules); the fast loop green.

### 8.2 The mailbox reader

Every mail an engineer sends back is read and kept whole, never deleted (SP-018).

Check: `solarpunk/mailer/` reads the unseen mail of the mailbox the settings name, by `imaplib` over TLS, and returns each (sender, date, subject, message id, text, the text part of a multipart mail); project stores each in an `inbound_mails` table, a message id once only, nothing deleted; the scheduled run reads the mailbox when the settings name one; the tests use a local fake IMAP server and never the settings file; the fast loop green.

### 8.3 The cause scan and its review queue

A good reply naming exactly one root cause closes the fault's work order with it, the mail its evidence; anything else
waits for review (SP-018).

Check: the leaf lists each root cause's synonyms beside its code (a closed list, held by a test that no synonym names two causes); `project` scans a stored mail: a bad token or a sender the fleet does not hold as an engineer goes to review; a `CAUSE: <word>` line wins; else exactly one cause named closes the fault's corrective work order with it (opening one from the fault first when it has none), decided by the sender, the mail linked to the closure as its evidence, which closes the fault (4.1); none or several go to review and the sender is mailed back asking which; the review queue is a query; each case a test, "not the firmware, it was the grid" among them (two causes: review); the fast loop green.

### 8.4 The cause in the windows and on the command line

The closure's cause and its mail where the asset is, and the review queue an operator resolves on the engineer's word
(SP-018, SP-015).

Check: the asset window shows a closed work order's root cause, who decided it and the mail that carried it; the review queue in a window from the fleet window, an operator resolving a mail by choosing the cause on the engineer's word (recorded as entered by the operator); `solarpunk mail read` runs the reader once, and `solarpunk mail review` lists the queue; a screenshot read back under xvfb; the fast loop green.

### 8.5 Tune-up pass 8

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 9: the tests' record, at the root and per asset

Lanes (P-15): 9.1 first (the surface every window reads), then 9.2, 9.3 and 9.4 in parallel, then 9.5 the pass. Moved after Phase 8 by SP-018. Ghost's direction, SP-016.

### 9.1 The record's surface and the timing

The scheduled run times each test, and project gives the three views the windows read; every result is kept (SP-016).

Check: the results table gains `duration_ms` (a store made before gains the column on opening, its old rows empty); the scheduled run and `solarpunk test run` store each test's duration; `project.tests_overview(conn)`, `project.test_log(conn, name, limit=100)` and `project.asset_log(conn, asset_id, limit=100, search=None)` (search matching the test name, "pass"/"fail" and words in the reason) are tested over a store holding more than 100 runs, newest first, nothing deleted; a result with no duration reads None, never 0; the fast loop green.

### 9.2 Last run in the asset window

Each test in the asset's diagnostics shows when it last ran and how long it took (SP-016).

Check: `solarpunk/ui/asset_window.py`'s diagnostics table has columns for the last-run instant and the duration, "never" for a test never run on the asset, "—" for a duration not recorded; `test/solarpunk/test_ui_asset.py` holds both; a screenshot read back under xvfb; the fast loop green.

### 9.3 The Tests window

The master list from the root of the window: every test, its run time, and its last 100 runs (SP-016).

Check: `solarpunk/ui/tests_window.py` opens from a "Tests" button in the fleet window; it lists `project.tests_overview` (name, kinds, assets, last run, duration, passes, failures) and, for the selected test, `project.test_log` (asset, instant, result, reason, duration), failures red; `test/solarpunk/test_ui_tests.py` builds it under xvfb over the demo store with its pure half headless; a screenshot read back; the fast loop green.

### 9.4 The asset's history

The asset's last 100 results, searchable and graphed (SP-016).

Check: `solarpunk/ui/history.py` opens from a "History" button in the asset window; a table of `project.asset_log` with a search box that narrows it; a canvas timeline, one row per test, one mark per run, green a pass and red a failure, the time axis in UTC, its geometry pure functions tested headless (as `solarpunk/ui/chart.py`'s are); `test/solarpunk/test_ui_history.py` under xvfb over a store with more than 100 runs of an asset; a screenshot read back; the fast loop green.

### 9.5 Tune-up pass 9

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.

## Phase 10: the network's security

Lanes (P-15): 10.1 alone, then the items its decisions call for, then the pass. Moved after Phase 6 by SP-013, after Phase 7 by SP-015 after Phase 8 by SP-016 and after Phase 9 by SP-018.

### 10.1 Network security: an engineering pass over the feed and the receiver

The feed and the receiver use plain TCP. The receiver accepts asset identifiers and fault codes, but the implementation
establishes neither an authenticated device identity nor an encrypted transport; it also defaults to localhost. That is
reasonable for the demonstration. A production deployment needs: authenticated asset connections; transport
encryption; authorization of fault submissions; replay protection; network segmentation and deployment controls. The
2026-11-18 advisor's research is the pass's starting point (`docs/ROADMAP.md` 10.1): the industry's addressing (host,
port, protocol, unit id, register map; Modbus TCP and SunSpec at the device), its security references (Modbus/TCP
Security, IEC 62351, IEC 62443, NERC CIP-003), and a sixth threat, spoofed telemetry from whatever answers at a feed's
host and port.

Check: `docs/NETWORK-SECURITY.md` holds the pass: what the feed (`solarpunk/feed/`) and the receiver (`solarpunk/receiver/`) do on the wire today, a threat model for each, and for each of the five needs (authenticated asset connections, transport encryption, authorization of fault submissions, replay protection, network segmentation and deployment controls) a proposed decision in `docs/decisions.md` with the options weighed, what the standard library alone can carry and what would need a dependency (Ghost's approval, C-034); the items that build each decision Ghost puts in force are added to this phase before its pass (the pass renumbered to the phase's end). No code changes in this item: the design is Ghost's to rule on first.

### 10.2 Tune-up pass 10

Check: `docs/when/tune-up.md` followed in full; the metrics table written; the navigation log's "Last review" set.
