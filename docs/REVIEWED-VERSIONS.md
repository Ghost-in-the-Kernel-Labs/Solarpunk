# Reviewed versions: the record of every dependency update

One row per update read in by `docs/DEPENDENCY-REVIEW.md` (C-035). "From" is the last version the
project reviewed before this one, so the next review reads the whole range from "To". Verdict is the
reviewer's (SAFE, UNSAFE, UNSURE); Reputation is CLEAN or CONCERN; Decision is `automatic`, or
`Ghost: <the question, and the answer>`; a large bundled package says `large-bundle` in Notes.
`test/test_reviewed_versions.py` holds the shape, and `scripts/checks/dependency_review.py` fails the
fast loop on any pin with no row (a lockfile entry, a workflow's action, a Dockerfile's image digest, a
vendored manifest's row). On adoption every pin already held gets an `unreviewed baseline` row (Kind
`baseline`, From, Verdict and Reputation `—`): the pin is the first review's old side, taken as held
and not as read. The template has no dependencies; its baseline rows are the workflow's action and
the Java starter's image, which a stamped project carries with them.

| Date | Package | From | To | Kind | Verdict | Reputation | Decision | Journal | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-07 | actions/checkout | — | 11d5960a326750d5838078e36cf38b85af677262 | baseline | — | — | unreviewed baseline | J-071 | v4.4.0, pinned in the workflow before the record; the first review reads from this pin |
| 2026-11-07 | gradle:8.14.3-jdk21-noble | — | sha256:21bd311ed01360c189b8870c6b6e988199ff10f72d445d02fb39d3cff9da91d7 | baseline | — | — | unreviewed baseline | J-071 | the Java starter's image, pinned before the record; the first review reads from this pin |
| 2026-11-17 | click | — | 8.5.1 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | coverage | — | 7.17.2 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | iniconfig | — | 2.3.1 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | libcst | — | 1.9.0 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | linkify-it-py | — | 2.2.0 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | markdown-it-py | — | 4.3.0 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | mdit-py-plugins | — | 0.7.0 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | mdurl | — | 0.1.2 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | mutmut | — | 3.8.1 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | packaging | — | 26.3 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | platformdirs | — | 4.14.5 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | pluggy | — | 1.7.0 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | pygments | — | 2.21.0 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | pytest | — | 9.2.0 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | pyyaml | — | 6.0.3 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | rich | — | 15.0.0 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | ruff | — | 0.17.4 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | setproctitle | — | 1.3.8 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | textual | — | 8.2.8 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
| 2026-11-17 | typing-extensions | — | 4.16.0 | baseline | — | — | unreviewed baseline | J-002 | pinned in requirements.lock before the record; the first review reads from this pin |
