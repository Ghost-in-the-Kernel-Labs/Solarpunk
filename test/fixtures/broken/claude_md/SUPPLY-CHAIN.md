# Supply chain (planted break: one rule on the act reworded, one missing)

## Rules on the act

- Never add or remove a dependency without a one-line reason in the decision log and Ghost's approval; never update one unread: an update comes in by `docs/DEPENDENCY-REVIEW.md` (C-035), routine ones automatically, the rest with a question for Ghost.
- Every GitHub Action is pinned to a tag. Every workflow starts with `permissions: contents: read`.
- Never use pull_request_target, self-hosted runners, toJSON(secrets), or scheduled triggers without approval.
- A fake key in a test is assembled at runtime from fragments, so no key-shaped literal exists in source.
