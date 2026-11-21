"""The remote tests themselves, one module each (SP-010): a module defines KINDS (the AssetKinds it runs against),
CLAUSES (the register clauses it evidences), REACTIONS (for each kind, what a failure does: a tuple of Fault(code),
Mail(), RunSuite(name) or OpenPreventive(note), the generic SIT-004 fault where none is named; SP-020) and run(asset, samples) -> Result. Adding a file adds a test; the registry
(solarpunk/remote/registry.py) finds it."""
