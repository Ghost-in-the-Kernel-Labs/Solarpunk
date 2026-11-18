"""The remote tests themselves, one module each (SP-010): a module defines KINDS (the AssetKinds it runs against),
CLAUSES (the register clauses it evidences), SUGGESTS (its rule table: for each kind, the catalogue code a failure
suggests to an engineer, or None; SP-015) and run(asset, samples) -> Result. Adding a file adds a test; the registry
(solarpunk/remote/registry.py) finds it."""
