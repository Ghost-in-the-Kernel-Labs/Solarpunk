"""The work-order ledger (4.1, SP-011): the work_orders table, corrective orders opened from a fault and preventive ones
on their own, each closed; the root cause is the fault's, free text an engineer writes (7.8, SP-046), so the ledger
holds no list of causes; the ledger is in solarpunk/workorders/ledger.py. It imports the leaf alone (MOD-05): project closes a corrective order's fault."""
