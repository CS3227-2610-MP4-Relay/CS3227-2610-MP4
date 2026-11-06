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
- PostgreSQL test service on port 55432 was unavailable at assignment; coordinator owns test-resource setup. If still unavailable, record the actual setup failure rather than calling it regression evidence.
- Yield this spec/plan checkpoint for coordinator scope check and commit; wait for the new HEAD/snapshot before tests or implementation. Independent review and delivery follow the integrated checks.
