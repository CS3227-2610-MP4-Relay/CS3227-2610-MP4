# Slice 180: Distinct AI failure messages and logs

Goal: Tell users when AI drafting or feedback is busy, over their own or the shared allowance, or not set up, and log every feedback gateway refusal/failure at WARNING so production keeps it.

## Scope and decisions

- High tier (AI features). Human decisions (2026-11-13): scope is failure logs plus distinct user messages in both AI features; changing criteria in two requirements (RND-8, RES-4) is accepted, raising the one-requirement budget for this slice; estimate ~150–250 non-test `src/` lines within the 400-line budget. Hosted production AI check deferred: no release-gate or runbook steps. No retry-time display. Limits (20/user and 200/deployment per rolling hour; 1/2 in flight) unchanged. Exact messages as recorded in [RND-8.10](../specs/product/rounds.md#rnd-8-draft-test-cases-with-ai) and [RES-4.10](../specs/product/results.md#res-4-suggest-missing-details-in-a-draft-observation).
- Criteria: changed RND-8.4 and RES-4.4 (narrowed to the remaining generic-unavailable causes; RES-4.4 also links the feedback logging rule); added RND-8.10 and RES-4.10 (busy, own allowance, shared allowance, not set up). Four criteria in total.
- Gateway [limits](../specs/ai/llm-gateway.md#limits-and-accounting): `busy-or-quota` splits into `busy` (user slot in flight, or no free deployment slot), `slots-missing` (deployment slot rows not exactly `DEPLOYMENT_IN_FLIGHT`, a misconfiguration, generic message), `user-quota` and `deployment-quota`; provider 429 stays `quota`. Check order unchanged, so both quotas used gives `user-quota` (superseded by repair round 1: quotas are now checked before free deployment slots). Quota refusals still roll back and count nothing. The fake-provider allowed-code rule inherits the new set. PLT-3.4's "busy/quota refusals" wording still covers all reservation refusals; unchanged.
- Code-to-message mapping lives in one shared helper used by both features (each supplies its own sentence ending and not-set-up wording); no duplicated mapping. Feedback logs `logger.warning("Feedback gateway %s: %s", type, code)` on Refused/Failed, like drafting; never text, prompts, request fields or exception text.
- Spec homes updated: `workflow/specs/ai/llm-gateway.md`, `workflow/specs/ai/test-drafting.md`, `workflow/specs/ai/observation-feedback.md`, `workflow/specs/product/rounds.md`, `workflow/specs/product/results.md`. TECHNICAL-SPEC and SECURITY-SPEC do not restate the codes; frozen plans unchanged (superseded by repair round 2, which changes the TECHNICAL-SPEC call-slot wording and adds a SECURITY-SPEC residual naming `busy`).

## Commit checkpoints and checks

1. `spec: Distinguish busy, quota and not-set-up AI failures (#180)` (the five spec files; `Why:` issue #180, users cannot tell temporary limits from setup problems, and feedback failures leave no production log) and `plan: Record distinct AI failure messages slice (#180)` (this plan). Check: read back, `check_scope.py builder --base a93430a`.
2. `feat: Split gateway reservation refusal codes (#180)` — `src/ai/gateway.py` (`_reserve` returns the refusal code; `complete` returns it; `_checked_result` code set), `src/ai/tests/test_gateway.py` (each refusal, order with both quotas used, `slots-missing`, boundaries, no records; marks RND-8.10/RES-4.10 where they were RND-8.4), plus any other test asserting `busy-or-quota`. Focused: `pytest src/ai/tests/test_gateway.py`. Red first: new-code assertions fail against the old `busy-or-quota`.
3. `feat: Show distinct drafting failure messages (#180)` — shared mapping helper (in `src/ai/`), `src/ai/drafting.py`, `src/ai/views.py`, `src/ai/tests/test_views.py` (each code to message, `slots-missing`/other refusals/failures generic, WARNING logs), `src/e2e/test_rounds.py` (its unmocked drafting call now shows the not-set-up message) and a criterion-marked browser case in `src/e2e/test_drafting.py` for one RND-8.10 message. Focused: those test files.
4. `feat: Show distinct feedback failure messages and log them (#180)` — `src/ai/feedback_views.py`, `src/ai/tests/test_feedback_views.py` (replace the `busy-or-quota` row; each code, WARNING log with type/code and no source text), `src/e2e/test_feedback.py` (one RES-4.10 message). Focused: those test files.
5. `docs: Describe distinct AI failure messages (#180)` — `docs/UserGuide.md` drafting (~line 175) and feedback (~line 297) paragraphs, exact product wording. Then full verification `ruff check . && ruff format --check . && pytest`.

## Open issues

- None.

## Checkpoint and next step

- Committed: specs `e9ba5d8`, plan `2c79077`, gateway split `16d2256`, drafting messages `37ef0dc`, feedback messages and logging `ef1ce09`.
- The shared mapping is `src/ai/failures.py`, used by both features. Checkpoints 3 and 4 were implemented as one assigned batch with disjoint files and separate red/green runs: drafting red with `views.py` temporarily at HEAD (10 failed), then one run with drafting green and feedback red (11 failed), then feedback green.
- An unchanged race test failed intermittently while another session shared the test database; clean runs passed. Focused and full runs use `--basetemp` in a session scratchpad because the default pytest temp directory was access-denied.
- Checkpoint 5: User Guide drafting and feedback failure messages; full verification. The first full run found one stale expectation in `src/relay/tests/test_access_matrix.py`: its unmocked drafting POST, with live calls off, now shows RND-8.10's not-set-up message. Correcting it is a separate test-only repair from the docs. Committed as `8c04035` (test repair), `f0f1d81` (docs) and `548247f` (plan).

## Repair round 1

Independent verifier and security-reviewer findings on `548247f`, checked by the builder:

- **A (security Low; human decision 2026-11-13, "check quotas first"):** with the old order, a user at their own quota could poll free `busy` against `user-quota` refusals to watch deployment-wide in-flight state. New order: user slot in flight (`busy`), slot rows (`slots-missing`), user quota, deployment quota, free deployment slot (`busy`). Every refusal rolls back the whole reservation transaction. This also fixes verifier finding 3: `busy` and `slots-missing` left a newly created user slot row, so "records nothing" was not exactly true. A user under both quotas can still see free deployment-slot `busy` refusals, as any allowed caller can.
- **B (verifier 2, security info 1):** an unexpected gateway exception logs two fixed WARNINGs in each feature. The code is kept; both contracts now state the exception path exactly, and tests will pin those records.
- **C (verifier 4):** `not-configured` is detected after reservation, so it counts toward quota and yields to busy or allowance refusals, while `live-off` precedes every limit. One sentence added to RND-8.10 and RES-4.10; no behaviour change, no new IDs.
- **D (nit):** rename `failures.NOT_SET_UP` (a set of codes) to `NOT_SET_UP_CODES`.
- **E (info):** SECURITY-SPEC's #22 residual gap (a shared allowance used up makes drafting unavailable to everyone) stays true after the reorder; no change.

Planned commits:

1. `spec: Check AI quotas before deployment slots (#180)`: `llm-gateway.md`, `test-drafting.md`, `observation-feedback.md`, `rounds.md`, `results.md`, plus this plan note, or a separate `plan:` commit.
2. `fix: Check quotas before free slots and roll back every refusal (#180)`: `src/ai/gateway.py`, `src/ai/tests/test_gateway.py`. Red first with the new order: at quota while slots are busy gives `user-quota`; deployment quota used while slots are busy gives `deployment-quota`; a first call's refusal leaves no user slot row.
3. `test: Pin AI exception-path log records (#180)` and `refactor: Rename not-set-up code set (#180)`, or one coherent commit: `src/ai/failures.py`, `src/ai/tests/test_views.py`, `src/ai/tests/test_feedback_views.py`. The User Guide changes only if a statement becomes inaccurate. Then full verification.

Results:

- Specs committed as `ed2cfaf` and this note as `8e8efb2`.
- Gateway red, run against the old order: `pytest src/ai/tests/test_gateway.py -k "check_order or rolls_back_everything"` gave 4 failed, 7 passed. The failures were `[user-quota-first]`, `[deployment-quota-first]`, and first-call `[busy]` and `[slots-missing]`, which left a user slot row.
- Gateway green: `_reserve` now wraps `_try_reserve` in one transaction and rolls back on any refusal; `src/ai/tests/test_gateway.py` gave 313 passed.
- The new exception-path log tests (`test_an_unexpected_gateway_exception_logs_two_fixed_warnings` in both view test files) passed before any code change. They pin existing, intentionally kept behaviour, so no red run was possible. They fail if either fixed line changes, is dropped or is duplicated.
- The rename is behaviour-neutral. `test_views.py` and `test_feedback_views.py` gave 156 passed.
- The User Guide is unchanged: its busy and allowance meanings stay accurate under the new order.
- Committed as `4a34b9e` (gateway reorder and tests), `ca45a19` (rename and exception log tests) and `8a1b734` (plan).

## Repair round 2

Re-reviews of `8a1b734` found no blocking defects. This is the last allowed round, with no behaviour change.

- **Decision 1 (human, 2026-11-13):** SECURITY-SPEC "Resource use and cached results" records the accepted residual. A user whose quotas both allow a call can learn from a free `busy` refusal whether the deployment is full.
- **Decision 2 (human, 2026-11-13):** in the TECHNICAL-SPEC call-slot model, user slot rows are created at the first *reserved* call, matching the rollback rule.
- **Finding 3:** RND-8.10 and RES-4.10 now say live-off is detected before any *gateway* limit, without "always". The features' own earlier checks still come first.
- **Finding 5:** the two exception-path log tests filter `ai` and `ai.*` loggers only, so `aiohttp` records are excluded.
- **Finding 6:** `test_three_racing_users_share_two_deployment_slots` also asserts the refusal is `Refused("busy")` and that each quota scope keeps exactly 2 records. This proves that a real `busy` refusal leaves no committed records; the check order itself is pinned by `test_reservation_refusals_follow_check_order` and `test_a_first_call_refusal_rolls_back_everything`. The test's comment ("The refusal comes after both quota inserts") overstates this in the same way and is left unchanged.

Evidence as reported:

- Round 1 full verification: 3279 passed, 5 skipped, 254 subtests passed.
- The coordinator found ruff clean at `8a1b734`.
- The coordinator ran `pytest src/ai/tests/test_gateway.py -k "check_order or rolls_back_everything or racing"` at `8a1b734`: 13 passed, 300 deselected.
- CI succeeded on `548247f` and `8e8efb2`. On `ef1ce09` it failed only on the access-matrix expectation, later fixed in `8c04035`.
- Committed as `ec4a246` (specs) and `7d88b27` (tests). Final full verification, run by the coordinator at `7d88b27` (2026-11-13 02:48–03:05 UTC): `ruff check . && ruff format --check . && pytest -q -p no:cacheprovider --basetemp=<scratchpad>` gave "All checks passed!", "152 files already formatted" and "3279 passed, 5 skipped, 254 subtests passed". Next: reviewers inspect `8a1b734` to the final head, then hosted CI.
