# Prevent stale result forms overwriting newer drafts

Goal: enforce [RES-2.5](../specs/product/results.md#res-2-save-and-submit-an-outcome-with-observations) for every existing result-entry save action.

## Confirmed scope and decisions

- Standard slice #166; one requirement, RES-2; at most 400 changed production `src` lines excluding tests/migrations. Preserve existing access and conflict priority. No recovery subsystem, dependency, route or AI change.
- Why: a second tab can currently submit an obsolete outcome over a newer saved draft; the prior last-serialized-wins rule must change before implementation.
- Persist an integer revision, initialized to 1 by a small migration; form-only 0 represents no result. Increment on every successful save, including identical values, rather than hashing fields (which misses changes back to an earlier value). Use the existing round lock; no additional lock or service is needed. Revision is a concurrency marker, never authorization.
- Reject missing, malformed or stale revisions after existing domain conflicts and before field validation. Retain posted revision on invalid forms. Shared save semantics cover Save draft, Submit and save-and-open feedback; feedback generation remains unchanged.

## Intended checkpoints

1. `spec: Define stale result form protection (#166)` — this plan, `workflow/specs/product/results.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`. Read back changes and check builder scope, then yield for coordinator commit/new snapshot before code.
2. `fix: Reject stale result writes (#166)` — `src/rounds/models.py`, its migration, `results.py`, `tester.py`, `result_forms.py`, `templates/rounds/tester_result.html`; result service/view regressions and affected test callers; `src/e2e/test_results.py` / `test_feedback.py` where required. First write focused regressions and run them against unchanged production code, recording genuine red evidence. Then implement and run focused server and browser checks. Keep behavior and tests in one reviewable checkpoint.
3. `docs: Explain stale result form refusal (#166)` — `docs/UserGuide.md` and this plan's evidence/next step. Match exact built wording; run full Standard verification on the integrated candidate, then yield for independent verifier/security review and delivery by coordinator. Split further only if independent repairs warrant it.

## Verification and coverage

- RES-2.1/.5: fresh create/save/submit, revision advances on identical saves and changed-back values, missing/malformed/stale revisions, two tabs sharing a draft, and two initial empty forms. Assert complete row/domain snapshots remain unchanged on refusal.
- RES-2.2/.5/.11 and RES-4.9: all three actions, stale invalid values, corrected invalid re-render after another save, and invalid requests never advancing revision. Update existing synthetic POST/service helpers to supply deliberate current revisions while dedicated stale tests retain old revisions.
- RES-2.3–.8: preserve role/workspace/coverage/Closed/stale-build/submitted precedence, CSRF, privacy, no-store and storage rollback checks. A posted revision or identity cannot choose another tester's row.
- Real PostgreSQL races: two draft writers and save-versus-submit from one expected revision, both with and without a preexisting row; only first serialized eligible write persists. Preserve close/retest/submission races with revised expected outcomes.
- Playwright: two tabs load one saved draft; A saves Fail/new observation; B's old Pass Submit is refused; reload shows A's saved values; an intentional fresh edit/submission succeeds. Exercise stale Save draft and feedback actions plus the no-row case through real forms, using existing harness and no live AI calls.
- Required final command in Git Bash with existing main-checkout virtualenv: `ruff check . && ruff format --check . && pytest`. No installs authorized. Full checks and migration consistency run after implementation; report environmental failures exactly.

## Run evidence and next step

- Builder trigger: coordinator assignment for user-authorized `/slice 166 on separate worktree`; configured model `gpt-6.1-sol` / medium (coordinator-reported role adapter/spawn configuration), observed execution model unavailable pending attributable metadata. Supplied context: issue summary, confirmed scope/budget, paths, checkpoint base `351a2ce8472f8cc067698c8e29103d4473379a6b` and pre-run scope snapshot. No delegation and no Git mutations.
- Scope probe: refused to edit `AGENTS.md` because builder writes exclude it; no mutation attempted. This is instruction-following evidence, not observed native enforcement.
- Resource baseline attempted with `resource_usage.py snapshot`; unavailable because no attributable telemetry source was supplied (`select at least one --codex or --claude file`). Do not interpret missing usage as zero.
- Candidate: specs/plan only; production and tests unchanged. No implementation checks run yet. Next: coordinator reviews/commits this checkpoint and supplies fresh HEAD/snapshot before the implementation unit. Independent verifier and security-reviewer remain required for the later fixed candidate.
