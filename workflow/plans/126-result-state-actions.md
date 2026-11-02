# 126: Result-state actions

Goal: label each tester current-build action from that tester's actual result state under [RES-1.5](../specs/product/results.md#res-1-see-the-tests-available-to-me).

Tier: High (user-scoped query). One requirement changed; <=400 runtime lines, estimate 25–60. Why: every action currently says Record result even after saving/submitting. Reuse existing result-entry route, immutable submitted read view and latest covering-build rule. No schema, dependency, new endpoint or state mutation.

Checkpoints:
1. Specs/plan recorded with 123 before source edits.
2. `fix: Reflect tester result state in round actions`: `src/rounds/tester.py`, `src/rounds/templates/rounds/tester_round.html`, `src/rounds/tests/test_tester.py`, `src/e2e/test_results.py`/`test_tester.py`. Red first: labels after draft/submission; second tester remains Record result; selected retest resets only selected cases; older result cannot label current build; Closed exposes none. Green: labels/URLs match signed-in tester and case/current-build pair, submitted view read-only, no GET writes and existing workspace denials/storage failures retained. Keep query bounded to authorized cases/round/coverage and select only needed status fields.
3. `docs: Explain current-build result actions`: `docs/UserGuide.md` after code exists, exact labels linked to existing result workflow. Run integrated full verification once candidate is complete; yield for coordinator freeze and independent verifier/security review.

Next: coordinator assigns after 125; full checks use existing disposable PostgreSQL/Chromium environment without concurrent DB runs. No open product decisions.
