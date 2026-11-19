"""The tracker adapters (11.1, SP-022, SP-027): the sink and source every tracker implements (adapter.py), the local
tracker (local.py), and the delivery of one outbox event to a sink. It imports the leaf alone (MOD-05); project hands it
the outbox's events and stamps the ones a sink took."""
