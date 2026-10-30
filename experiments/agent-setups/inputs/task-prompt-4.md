Deliver issue #4 in this repository, using the development workflow that this repository's AGENTS.md describes.

## Issue #4: Limit abuse of sign-in and demo workspace creation

**Spec:** new (ACC)
**Owner:** zheng-jj
**Tier:** High

Done when the pull request that closes this issue is merged.

## What the team has decided

No human is available during this run. The requirements are ACC-3 in `workflow/specs/product/accounts.md` and the accounts notes in `workflow/specs/TECHNICAL-SPEC.md`, as they stand; build to them. The only other decisions:

1. The work is local only: no push, no pull request, no GitHub or web access. Commits on a local feature branch are allowed.
2. Do not write a session log or a usage report; the experiment records usage separately.
3. No new dependencies.

If the workflow calls for a human decision that the specs don't settle, choose the smallest option consistent with the issue and the specs, record the question and your choice in your final report, and continue without waiting.

## Environment

- The PostgreSQL test server is already running. Do not start, stop or remove Docker containers.
- Use the existing `.venv`. Do not install packages.

When the work is finished, end with a short report: what changed, the checks you ran and their results, and anything left open.
