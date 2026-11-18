"""The work-order ledger (4.1, SP-011): the work_orders table, corrective orders opened from a fault and preventive ones
on their own, each closed only with a root-cause code from the leaf's closed list; the code is in
solarpunk/workorders/ledger.py. It imports the leaf alone (MOD-05): project closes a corrective order's fault."""
