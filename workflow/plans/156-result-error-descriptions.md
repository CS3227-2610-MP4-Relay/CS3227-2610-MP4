# Slice 156: Accessible result field errors

Goal: Make result-entry server validation errors available in their fields' accessible descriptions under [RES-2.13](../specs/product/results.md#res-2-save-and-submit-an-outcome-with-observations).

## Scope and decisions

- Standard tier; one requirement (RES-2), at most 400 changed source lines excluding tests and migrations. Expected implementation: under 10 template lines and approximately 60–100 focused test lines; no dependencies, schema changes or new controls.
- Why: Django marks invalid result controls and references error IDs, but the custom template does not render those IDs, leaving the accessible description empty.
- Reuse the existing field error messages, styling, form validation and browser harness. Give each field's error group its referenced ID only when errors exist. Preserve non-field errors.
- No guide change is expected: visible product wording and user actions stay the same.

## Commit checkpoints

1. `spec: Define accessible result validation errors (#156)` — this plan and `workflow/specs/product/results.md`; confirm the new stable criterion and read back both changed sections before yielding. No implementation at this checkpoint.
2. `fix: Associate result fields with validation errors (#156)` — `src/rounds/templates/rounds/tester_result.html`, `src/rounds/tests/test_results.py` and `src/e2e/test_feedback.py`. Before the template fix, run focused regression assertions for invalid Outcome and Observation independently and together, across save/submit/feedback; confirm failures arise from unresolved error references or missing accessible descriptions. Check initial/valid forms and successful correction have no stale error association. Retain existing no-write and unsaved-value checks. Browser coverage must assert the computed accessible description for the existing Fail/empty-Observation journey and exercise Outcome server validation with native validation bypassed only by the test when needed.

## Checks and next step

- Map server and browser regression tests to RES-2.13; retain applicable RES-2.2 and RES-4.9 markers.
- Run focused server/browser tests red before implementation and green afterwards, then `ruff check . && ruff format --check . && pytest` using the parent checkout's existing virtual environment in Git Bash.
- Coordinator owns test-resource setup; record setup failures separately from regression evidence.
- After integrated checks, yield the implementation checkpoint for coordinator freeze and independent review, followed by delivery.

## Checkpoint evidence

- Spec/plan committed before code as `047ff0714a33f6ef531d98369e818061e4369c54`; implementation resumed against coordinator snapshot `builder-2.json`.
- Environment deviation: coordinator supplied an ignored settings adapter importing `relay.settings.test`, changing only PostgreSQL port to 55436 and test database to `test_relay_156` to avoid concurrent test collisions. Commands use the parent checkout's existing virtual environment and adapter directory in `PYTHONPATH`; pytest resolves this worktree's `src` through `pytest.ini`. Existing Chromium runs without installation or sandbox escalation.
- Before the template edit, `pytest src/rounds/tests/test_results.py::test_field_error_references_resolve_once_to_own_errors src/e2e/test_feedback.py::test_result_errors_describe_fields_and_clear_after_correction src/e2e/test_feedback.py::test_invalid_result_keeps_persisted_baseline_and_native_validation_guard --ds=slice156_settings -q --tb=short` produced **20 failed in 108.26s**: nine server cases found zero elements for the referenced error ID; eleven browser cases found an empty computed accessible description. These were application assertion failures, not setup failures.
- Minimal repair: render one error group per invalid field, with the ID already referenced by Django's widget; keep escaped messages and existing error styling.
- Focused green: `pytest src/rounds/tests/test_results.py src/e2e/test_feedback.py --ds=slice156_settings -q --tb=short` produced **125 passed in 143.82s**. This covers RES-2.13's per-field and simultaneous error associations across all actions, clean initial/corrected forms, the existing unsaved-value journey and unchanged persisted rows on refusal.
- First integrated command stopped at Ruff `FURB167` on the new server test's `re.S` alias. Replaced it with equivalent `re.DOTALL`; the resumed command passed `ruff check .` and `ruff format --check .` (147 files). No tests or checks were weakened.
- Full pytest result: **1 failed, 3015 passed, 5 skipped in 1403.41s**. The sole failure was `src/relay/tests/test_database.py::test_postgresql_synthetic_roundtrip`, whose fixed-environment assertion requires `test_relay_test`; the temporary adapter instead supplied `test_relay_156`. All result and browser tests passed.
- Coordinator removed the adapter's test-name override, retaining isolated port 55436 and restoring canonical `test_relay_test`. On that repaired environment, `pytest src/relay/tests/test_database.py --ds=slice156_settings -q --tb=short` produced **1 passed in 2.41s**. No repository code or test expectation changed for this harness repair. The local full run is not green, and its environment differs from the repaired adapter; final-head CI full verification remains required. Coordinator requested no duplicate 23-minute local full run.
- Implementation checkpoint ready for coordinator freeze and independent verification; delivery awaits final-head CI results.

## Independent review and delivery

- Fixed candidate: `f8adaad43506733793df05371dce01ecdb7c55f3..cf154b73e393b8bbd9d2a55475916eb9588ac72a`, captured in private `review-candidate.json`. Verifier scope and unchanged-manifest checks passed; no code, criterion, scope or documentation defect was found. No security-specialist trigger applied to this template-only behavior change.
- Verifier independently ran the nine new server cases, nine new browser cases and database-contract check on the repaired adapter: **19 passed in 34.05s**. Ruff and formatting passed independently. This focused result does not replace full verification.
- At the review checkpoint, canonical full verification remained pending. Delivery requires the latest draft-PR head's `verify` and `site` jobs to succeed after the summary commit; actual hosted results belong on that PR. Merge, release and human manual/log review remain human decisions.
- [Session log](../../logs/Whimsyturtle/042-fix-accessible-result-errors.md) records agent identities, review limits, usage and environment repairs.
