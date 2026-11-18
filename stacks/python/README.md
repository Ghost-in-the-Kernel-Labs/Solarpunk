# The Python stack

Distilled from Neon Rain (R-001, R-015, R-017, R-018). Stamping a Python project copies `starter/`
to the repository root (a `starter/` path below is the same path at a stamped project's root) and writes `stacks/python/PRESENT`; `scripts/gate.sh` then runs
`stacks/python/gate.sh`. The core's own checks are already Python, so the stack adds the rules for
a project whose *product* is Python, which the maintainer cannot audit by eye the way he audits
Java or C#: **the tests are the audit** (Neon Rain R-015).

| Rule | What it is | Held by |
| --- | --- | --- |
| Toolchain | Python 3.12 in a venv made once per session; `pyproject.toml` is tool configuration only, not a package | `scripts/gate.sh` |
| Fast loop | `.venv/bin/pytest` (or the core's `scripts/fast.sh` while there is no product code), under 30 s; no data, no network | AGT-02 |
| Dependencies | `requirements.in` holds the direct dependencies with one line of reason each; `requirements.lock` is compiled from it with hashes; installed with `pip install --only-binary :all: --require-hashes -r requirements.lock`; never `pip install <name>` in a session | `starter/scripts/checks/imports.py`: an import not in the lock fails |
| Cooldown | the lock is compiled with `--exclude-newer` seven days back; a version younger than that does not enter | the compile command in `requirements.in`'s header |
| Mutation | mutmut over the product and the checks; every survivor killed or written up in `docs/MUTATION.md`; `scripts/survivors.py` refuses an unexplained one; `# pragma: no mutate` regions are Ghost's alone to grant (C-018) | `gate.sh` |
| Readability | type hints on every function (ruff ANN); no bare except; functions under 40 lines; no comprehension over three clauses; no `*args`/`**kwargs`; no decorator magic; no operator overloading; a docstring per function with a concrete input→output example | ruff plus `starter/scripts/checks/readability.py` |
| The blind mirror | a contract's numbers are reimplemented from the contract text alone by an agent that has not seen the code, and compared by a test; every number the maintainer is asked to trust has a ten-row example he can check by hand | the project's mirror test |
| Isolation | every script that reads supplied data runs with `python3 -I` | the recipes |
| Dependency updates | `docs/DEPENDENCY-REVIEW.md` (C-035). Fetch both sides without running anything: `pip download <name>==<version> --no-deps --no-binary :none: --only-binary :all: -d <archives>/old/` (wheels only; a sdist's setup.py is code), then `python3 -I scripts/review_scan.py --unpack <old>.whl <new>.whl "$REVIEW"` (a zip unpacked without links, special members, owners or modes; never `unzip` by hand); a `.pth`, `sitecustomize.py` or `usercustomize.py` the wheel adds or changes is a scan hit and never routine; the audit is `pip-audit -r requirements.lock` and OSV.dev on `PyPI:<name>`; provenance is the PyPI attestation (`https://pypi.org/pypi/<name>/<version>/json`, `urls[].attestations`), compared with the version before: the red flag is an attestation the prior version had that this version lacks, or a different publisher identity inside it (PyPI does not publish the uploader in a form a script can compare); the lock's `--exclude-newer` is the cooldown | `scripts/review_scan.py`, `scripts/checks/imports.py`, `docs/REVIEWED-VERSIONS.md` |
