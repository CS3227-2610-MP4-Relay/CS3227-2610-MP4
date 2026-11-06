# Slice 157: result conflict navigation

Give authorized testers a route from result-entry conflicts back to their round or home ([PLT-4.14](../specs/product/platform.md#plt-4-shared-application-presentation)).

Why: A stale result submission correctly returns 409, but reloading the same URL cannot reach the current build and the refusal page currently offers no navigation.

## Scope and decisions

- Standard tier; PLT-4 is the single changed requirement, with PLT-4.7 clarified for this error-page exception and PLT-4.14 defining its navigation. Preserve RES-2.3–2.8 and existing access controls. Budget: at most 400 non-test source lines; aim for at most eight changed criteria.
- Only result-entry conflicts gain navigation. Preserve exact messages, 409 status, no-store, authorization precedence, write serialization and stored rows. No rejected-edit retention, automatic recovery, new service, credential or dependency.
- Shared renderer changes require independent verifier and security-reviewer reports on the coordinator's fixed candidate. Builder does not delegate or change Git state.

## Commit checkpoints

1. `spec: Define result conflict navigation (#157)` — product/platform.md and this plan. Read back changed sections and run builder scope/diff checks. Yield before implementation.
2. `fix: Add navigation to result entry conflicts (#157)` — src/rounds/tester.py, views.py, templates/rounds/conflict.html, src/rounds/tests/test_results.py, src/e2e/test_results.py and docs/UserGuide.md; adjust only these paths unless a necessary in-scope helper is identified. First add criterion-marked server/browser regressions and record missing-navigation failures before implementation. Then pass optional authorized navigation context to the shared renderer, reuse existing link styling, and document built labels through the maintain-docs skill. Yield with focused checks and full Standard verification.

## Verification and next steps

- Server: exercise stale/Closed GET and POST plus submitted POST; check exact destinations and single links, unchanged messages/status/cache headers and unchanged domain rows. Keep denied access fixed and other shared conflict callers unchanged.
- Browser: update the existing retest/close journey to leave each conflict using visible controls, reach the current build after retest, and return to the Closed round/home after closure. Do not use page.goto to recover from conflicts. Existing harness covers preserved earlier/unselected results; retain those assertions.
- Run focused result server and browser checks red before green, then `ruff check . && ruff format --check . && pytest` in the configured test environment. Record actual commands, results and environment limitations; no live provider calls.
- Initial candidate: f8adaad43506733793df05371dce01ecdb7c55f3, coordinator scope snapshot `%TEMP%/relay-157-builder-plan.json`. Trigger: coordinator's /slice 157 assignment; model identifier unavailable in runtime. Supplied context: confirmed narrow scope, relevant criteria, paths, tier and commit checkpoints.
- First checkpoint is specs/plan only. Await coordinator commit/new snapshot and environment status before implementing. No open product decision. Builder-local usage baseline unavailable: resource_usage.py requires an explicit session JSONL source that has not been supplied; do not count missing usage as zero. Coordinator reports its 13:26:09 UTC baseline includes descendant discovery. Test environment supplied: PostgreSQL 17 at 127.0.0.1:55432 with relay_test role/database, existing Chromium and root .venv; do not run test suites concurrently with other agents.
