"""The remote tests themselves, one module each (SP-010): a module defines KINDS (the AssetKinds it runs against),
CLAUSES (the register clauses it evidences) and run(asset, samples) -> Result. Adding a file adds a test; the registry
(solarpunk/remote/registry.py) finds it."""
