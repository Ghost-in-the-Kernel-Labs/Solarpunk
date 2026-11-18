"""The remote tests (lane 2.3): standalone modules under tests/, each with KINDS, CLAUSES and run; registry.py finds
them, results.py holds the results table, run.py runs one test or the whole suite and gives each asset's status. It
imports the leaf alone (MOD-05, SP-010) and never opens a socket: a test receives the samples the feed stored."""
