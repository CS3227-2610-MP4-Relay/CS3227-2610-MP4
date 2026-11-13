# Slice 180: Distinct AI failure messages and logs

Goal: Tell users when AI drafting or feedback is busy, over their own or the shared allowance, or not set up, and log every feedback gateway refusal/failure at WARNING so production keeps it.

## Scope and decisions

- High tier (AI features). Human decisions (2026-11-13): scope is failure logs plus distinct user messages in both AI features; changing criteria in two requirements (RND-8, RES-4) is accepted, raising the one-requirement budget for this slice; estimate ~150–250 non-test `src/` lines within the 400-line budget. Hosted production AI check deferred: no release-gate or runbook steps. No retry-time display. Limits (20/user and 200/deployment per rolling hour; 1/2 in flight) unchanged. Exact messages as recorded in [RND-8.10](../specs/product/rounds.md#rnd-8-draft-test-cases-with-ai) and [RES-4.10](../specs/product/results.md#res-4-suggest-missing-details-in-a-draft-observation).
- Criteria: changed RND-8.4 and RES-4.4 (narrowed to the remaining generic-unavailable causes; RES-4.4 also links the feedback logging rule); added RND-8.10 and RES-4.10 (busy, own allowance, shared allowance, not set up). Four criteria in total.
- Gateway [limits](../specs/ai/llm-gateway.md#limits-and-accounting): `busy-or-quota` splits into `busy` (user slot in flight, or no free deployment slot), `slots-missing` (deployment slot rows not exactly `DEPLOYMENT_IN_FLIGHT`, a misconfiguration, generic message), `user-quota` and `deployment-quota`; provider 429 stays `quota`. Check order unchanged, so both quotas used gives `user-quota`. Quota refusals still roll back and count nothing. The fake-provider allowed-code rule inherits the new set. PLT-3.4's "busy/quota refusals" wording still covers all reservation refusals; unchanged.
- Code-to-message mapping lives in one shared helper used by both features (each supplies its own sentence ending and not-set-up wording); no duplicated mapping. Feedback logs `logger.warning("Feedback gateway %s: %s", type, code)` on Refused/Failed, like drafting; never text, prompts, request fields or exception text.
- Spec homes updated: `workflow/specs/ai/llm-gateway.md`, `workflow/specs/ai/test-drafting.md`, `workflow/specs/ai/observation-feedback.md`, `workflow/specs/product/rounds.md`, `workflow/specs/product/results.md`. TECHNICAL-SPEC and SECURITY-SPEC do not restate the codes; frozen plans unchanged.

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
