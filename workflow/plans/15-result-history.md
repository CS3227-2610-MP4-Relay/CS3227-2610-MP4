# Slice 15: Review my earlier results

Goal: expose the signed-in tester's read-only per-round result history under [RES-3](../specs/product/results.md#res-3-review-my-earlier-results).

## Scope and decisions

- Human request: `/slice 15`, stacked on PR #87; starting commit `2550cc168ce1e1a9d5bf8e77aca9229bddfed388`, branch `feat/15-result-history`, parent `feat/13-submit-results`.
- High tier: a new owner-scoped route and user-scoped query require full verification plus independent verifier and security-reviewer reports.
- Human explicitly confirmed both drafts and submissions, clearly labelled, private to the signed-in tester in Open and Closed rounds. Product behaviour lives in RES-3; architecture and controls live in the linked technical/security specs.
- Seven new criteria in one requirement. No changes to other requirements' criteria; no models/migrations, dependencies, services, AI, coordinator review, editing, filtering or pagination.
- Estimate: 100–180 changed non-test application lines; stop and report before the forecast exceeds 180. The slice's hard limit remains 400. Count tracked and untracked application changes, excluding tests/migrations, across all checkpoints.
- Why: saved rows already retain original case/build references and frozen linked criteria, but testers currently cannot read older-build or Closed-round results.

## Incremental checkpoints

Only the coordinator changes Git state. Builder yields each unit for scope review, commit and a fresh snapshot before resuming.

1. **Specs and plan** — `workflow/specs/product/results.md`, relevant sections of `workflow/specs/TECHNICAL-SPEC.md` and `workflow/specs/SECURITY-SPEC.md`, and this plan. Read changes back and run `git diff --check`; yield before code.
2. **History route and server regressions** — `src/rounds/tester.py`, `src/accounts/urls.py`, tester round/history templates, and focused `src/rounds/tests/` coverage. Write criterion-marked tests and record missing-behaviour failures before implementation. Cover navigation, empty and mixed records/order, original case/build/criteria after retest/close, UTC timestamp and draft omission, owner/workspace isolation, malformed cross-round/coverage rows, forged selectors, read-only methods/CSRF, no-store, storage failures and escaped isolated text. Reuse existing helpers, fixtures and error handling. Run focused new tests and existing tester/result regressions plus targeted Ruff; yield with source size.
3. **Browser journey** — `src/e2e/test_results.py` using the existing synthetic loopback harness. Follow real navigation through saved draft/submission history, retest and closure with separate tester sessions; verify labels, retained original build/context, private visibility and read-only page. Criterion-mark assertions and run affected browser tests. If the journey already passes because checkpoint 2 supplies its behaviour, record that reason and how assertions detect defects instead of manufacturing a red result. Yield separately.
4. **Guides and integrated verification** — `docs/UserGuide.md`, `docs/DeveloperGuide.md` and this plan. Match built wording, link canonical contracts and read changed sections back. Run full `ruff check . && ruff format --check . && pytest` in Git Bash with the existing venv/test PostgreSQL/Chromium, without installation or `.env` access. Report exact outcomes; yield the integrated candidate for coordinator freeze, independent review and authorized draft delivery.

## Current checkpoint and next step

Read-only discovery found no conflicts: RES-1/2's history exclusions describe their own scope; existing published-case freezing and result references support RES-3 without a schema change. Checkpoint 1 records the contract before implementation. Await coordinator scope check/commit and a fresh snapshot before checkpoint 2. No application or browser checks run during this specs checkpoint; the coordinator is checking the unchanged baseline separately.

Resource measurements, agent model/context, candidate identities and check evidence belong in coordinator handoffs/session logs; missing telemetry is unavailable. No human test, review, merge or release approval is inferred. No open product decision remains.
