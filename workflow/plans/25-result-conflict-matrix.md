# Slice 25: Result conflicts in the access matrix (#25, final part)

Goal: close the open items of the frozen [route access matrix plan](25-route-access-matrix.md#open-issues) so every route, role and workspace, and every overlapping RES-2.4, RES-2.5 and RES-4.5 conflict, is tested; the PR closes #25. RES-4.6's "changed" 409 and RES-2.5's concurrency 409s stay with their own tests.

Tier: High (role and workspace permission tests), so the verifier and security reviewer both run. Base: `045c33c`, branch `25-result-conflict-matrix`. Owner: zheng-jj. Budget: test-only plus one spec sentence; no change under `src/` outside tests, no new criterion IDs.

## Decisions

Confirmed by the human (zheng-jj): "continue working through other unblocked issues"; the coordinator chose #25's remaining work. If the matrix finds an authorization or state defect, stop and report it with evidence; application code is not fixed here.

- **Result entry overlaps** (`accounts:tester-result`): the Closed-versus-submitted/stale decision is resolved by [RES-2.4 and RES-2.5](../specs/product/results.md#res-2-save-and-submit-an-outcome-with-observations): Closed 409, then stale-build 409, then submitted 409. `RESULT_ROWS` adds Closed with a submitted row, Closed with a formerly current build, Open with a submitted row on a formerly current build (stale wins), and Closed with both (catches an implementation that special-cases the stale-and-submitted overlap ahead of Closed). The stale comment calling this an open decision is removed.
- **Feedback overlaps** (`accounts:tester-feedback`): the matrix already runs draft, missing, submitted and stale-draft rows in every state, so Closed against each is covered. Under [RES-4.5](../specs/product/results.md#res-4-suggest-missing-details-in-a-draft-observation)'s priority it adds a submitted row and a missing row on a formerly current build (stale wins over both); Closed with each comes from the state parameter. Submitted and missing cannot overlap.
- **Gateway calls** (review round 1): test settings turn live calls off, so `gateway.complete` refuses before writing any call record and neither the snapshot nor `block_llm_network` sees a call. The matrix wraps `ai.gateway.complete` (still refusing) to count calls per request: 1 only for a feedback or `ai:draft` POST that passes every check, otherwise 0, on every route.
- Every refusal keeps the matrix's unchanged-snapshot check. Marks: the existing ones, plus RES-2.5 on the submitted overlaps.
- **Tester home Draft titles (RND-1.6, second half):** no matrix check. `src/rounds/tests/test_tester.py::test_home_orders_only_own_available_rounds_for_both_testers` already lists a Draft round of the tester's workspace beside Open and Closed ones (the positive control) and another workspace's rounds, for two testers, and `src/rounds/tests/test_views.py::test_tester_home_shows_no_draft_round` covers a Draft-only workspace; a matrix copy would catch nothing more.
- **Accounts routes methods:** the [accounts routes](../specs/TECHNICAL-SPEC.md#accounts-routes) now say a route accepts exactly the methods listed, so HEAD gets 405 on every route but `/`, as the built views do (`require_GET`, `require_POST`, `require_http_methods`). This states existing behaviour; the matrix no longer rests on an assumption.

## Checkpoints

1. `spec:` then `plan:`: `workflow/specs/TECHNICAL-SPEC.md`, this plan. Checks: `git diff --check`; changed sections read back.
2. `test:`: `src/relay/tests/test_access_matrix.py` only. Guard tests over built behaviour, so red evidence is by mutation of temporary application-code edits, each restored and confirmed with `git diff --exit-code`: submission checked before Closed, and before the stale build, in `rounds/results.py`; the feedback checks' order in `ai/feedback_views.py` if separate. Checks: `pytest -q -p no:cacheprovider src/relay/tests/test_access_matrix.py`, `ruff check` and `ruff format --check` on the file.

Then the coordinator runs full verification, the verifier and the security reviewer.

## Open issues

The earlier plan's first open item is done: the routes it waited for (`rounds:results`, the RND-8 drafting routes `ai:draft` and `ai:use-draft`, `accounts:tester-results` and `accounts:tester-feedback`) have rows, and `test_every_route_has_a_matrix_entry` requires a row for any future route, so this PR closes #25.

Left deliberately from the [earlier plan](25-route-access-matrix.md#open-issues):

- PATCH, DELETE and OPTIONS are not sent; PUT stands for an unlisted method, and each route's own tests send others.
- CSRF variants beyond a missing token and a foreign `Origin` are left to Django's own tests.
- The snapshot leaves out `Session` and the ACC-3 limit counters, which sign-in, sign-out and failed sign-ins change by design; ACC-1 and ACC-3 tests own them.

Out of scope, raised by the coordinator with the human for separate tracking: SECURITY-SPEC's stale opening status sentence, and `delete_criterion`'s link check without a round filter (application code), which can only over-refuse a delete through a directly stored cross-round link.

## Review round 1

Candidate `045c33c..70adac0`. Verifier: 0 High, 0 Medium, 3 Low, 3 Nit, 2 Info. Security reviewer: 0 High, 0 Medium, 1 Low, 1 Nit.

- Fixed: security L1, the matrix could not see gateway calls (see Decisions); verifier Nit 2, the `Situation` docstring now says the submitted row is on the own build, formerly current when `stale`; verifier L1, L2 and L3 in this plan (open issues, out-of-scope tracking, goal wording).
- Not adopted: verifier Nit 1, deriving each situation's refused methods and message from its flags, as the explicit values read as the spec's expectations; verifier Nit 3, the two ways own rows are created (`result_world` for entry, the feedback test for its draft rows), kept as each suits its matrix; security N1, asserting competing conflict texts are absent, as mutations a1 to b2 already catch priority changes.

## Next steps

- [x] Checkpoint 1: spec sentence and plan (`ea18693`, `5dbab3e`).
- [x] Checkpoint 2: matrix tests (`b6f757e`). `RESULT_ROWS` adds submitted, stale and stale-submitted in Open and Closed (`Situation` gains `stale` and `submitted` flags); feedback's `FEEDBACK_ROWS` adds "stale submitted" and "stale missing" in every state. `pytest -q -p no:cacheprovider src/relay/tests/test_access_matrix.py`: 781 passed (741 at base). Ruff clean. Mutations of `rounds/results.py` (and, for b, a temporary `feedback=True` flag from `ai/feedback_views.py`), each restored from a copy and checked with `git diff --exit-code`, run with `-k "tester_result or feedback"` against this matrix and a temporary copy of the `5dbab3e` matrix:

  | Mutation | This matrix | Base matrix |
  | --- | --- | --- |
  | (a1) entry checks submission before Closed | 3 failed: Closed submitted, Open and Closed stale-submitted | 150 passed |
  | (a2) entry checks submission before the stale build | 1 failed: Open stale-submitted | 150 passed |
  | (a3) entry refuses stale-submitted as stale before Closed | 1 failed: Closed stale-submitted | 150 passed |
  | (b1) feedback's draft and submitted checks before Closed | 6 failed: Closed missing and submitted, Open and Closed stale submitted and stale missing | 2 failed (Closed missing and submitted) |
  | (b2) feedback's draft and submitted checks before the stale build | 2 failed: Open stale submitted and stale missing | 150 passed |

- [x] Repair round 1: `src/relay/tests/test_access_matrix.py` and this plan. `pytest -q -p no:cacheprovider src/relay/tests/test_access_matrix.py`: 781 passed; every passing success POST of `ai:draft` and feedback asserts 1 call, so the count is not vacuous. Ruff clean. Mutations of `ai/feedback_views.py` or `ai/views.py`, restored from copies and checked with `git diff --exit-code`, run with `-k "feedback or ai or body"` against this matrix and a temporary copy of the `70adac0` matrix:

  | Mutation | This matrix | Matrix at `70adac0` |
  | --- | --- | --- |
  | (g1) feedback's first POST pass skips the submitted check, leaving it to the post-call recheck | 1 failed: Open submitted | 243 passed |
  | (g2) feedback makes a discarded gateway call before any check | 37 failed: every `tester_a` feedback row and every forged-ID feedback row | 243 passed |
  | (d1) drafting makes a discarded gateway call before the round and state checks | 35 failed: `ai:draft` for both coordinators in every state, its 15 forged URL-ID rows and its 14 forged body-ID rows | 243 passed |

- [ ] Full verification, review, draft PR closing #25.
