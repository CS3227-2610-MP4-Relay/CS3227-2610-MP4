# 144: trustworthy close response

Goal: make the close POST and its existing success notification commit together under [RND-6.5](../specs/product/rounds.md#rnd-6-close-a-round).

Why: the existing regression reproduces a 400 response after the close commits; a coordinator cannot tell from that response whether testing ended. Narrow the previously accepted session-save residual for this action, preserving the current redirect and once-only notification.

## Scope and decisions

- High tier: session persistence. One changed criterion, RND-6.5; retain RND-6.1 and existing permission, CSRF, locking, state and history requirements.
- Use the existing database session and Django messages locally in `close_round`: store unread messages and save the existing session before the close transaction commits, construct the redirect there, and prevent response middleware from repeating either save. Handle session `UpdateError` alongside storage failure; never resurrect a deleted session. Clear pending response-message work even when persistence/commit fails so the error response cannot requeue success.
- Preserve existing unread messages on success. Detailed implementation may use a small local helper to isolate message/session response bookkeeping; no global middleware or backend changes.
- No dependency, credential, service, schema, retry or recovery subsystem. No change to other actions or later GET message consumption. Operating burden: one session update joins the existing close transaction, holding its round lock for that update; no new deployment setup.
- Estimate before code: 30–65 production lines added/deleted, 140–230 test lines, 25–55 spec/plan lines and a short guide correction if needed; roughly 200–360 total changed lines. Production ceiling: 400 added/deleted lines. Stop and report any required expansion.

## Checkpoints

1. **Specs/plan**: this plan, `workflow/specs/product/rounds.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`. Read changed sections back, diff/whitespace check and builder scope check; yield for coordinator commit and new scope snapshot before code.
2. **Close fix and regressions**: `src/rounds/views.py`, `src/rounds/tests/test_messages.py`, relevant `test_close.py` or `test_close_services.py` only if necessary, and `src/e2e/test_round_lifecycle.py`/`test_review.py` as needed. First change failure expectations and run focused tests against unchanged production code to show the meaningful red. Then implement and run focused round tests and criterion-marked browser journeys. Retain permissions, CSRF, duplicate-close and retest/submit race checks. Yield a coherent implementation/test checkpoint for coordinator commit.
3. **User guide, if needed**: `docs/UserGuide.md` close-failure guidance must match the accepted implementation. Use the maintain-docs skill if changing it. Run final integrated `ruff check .`, `ruff format --check .`, `pytest` and affected Playwright tests using the configured test environment; report actual failures. Independent verifier/security review and delivery belong to the coordinator.

## Expected regression evidence

- Session persistence failure: 503 with no-store, round still Open, closing time unset, unchanged domain history, no persisted close message and no response-phase retry. Replace the old explicitly accepted 400/Closed expectation rather than deleting coverage.
- Successful close: redirect to the same round; exactly one session save before commit, no later save in close response handling, existing session identity and prior unread messages retained, no messages cookie. Next round GET shows success once; following GET does not.
- Missing session from concurrent sign-out: 503, close rolled back, deleted session remains absent. Existing authorization and method/CSRF denial partitions still pass without adding success.
- Close write or outer commit failure: 503, rollback both round/session data and leave no phantom success; assert transaction-level behavior with real database transactions where needed.
- Browser RND-6.1 journey: close shows Closed and one notification, reload removes notification. Browser RND-6.5 injected session-save failure: visible existing unavailable page; retry after restored storage succeeds and does not falsely report an already-closed conflict.
- Existing focused server cases cover Draft/Closed state denial, foreign workspace, tester/signed-out denial, CSRF, double close and round/result races. Reuse those checks rather than duplicate their assertions.

## State and handoff

- Trigger/context: coordinator task for human `/slice 144 on a separate worktree`; builder read the role, worktree AGENTS and only relevant specs/code. Candidate starts at `c1372cd7cd14c28435334cc06a99d310b43b3553`; no Git state changed by builder. Model: gpt-6.1-sol, medium (coordinator-observed execution metadata).
- Coordinator reproduced existing 400/Closed regression before implementation (1 passed); this is supplied evidence, not a builder-run check. Coordinator prepared an isolated PostgreSQL test environment; use its settings and unique external basetemp when resumed.
- Scope-hook probe: subprocess submission of a hypothetical builder edit to `AGENTS.md` was refused; the file was not mutated. This proves the hook decision, not native client dispatch/trust. Effective session approval reviewer is `auto_review`.
- Usage: coordinator captured baseline; direct builder session telemetry unavailable without a selected source. Final accounting belongs in coordinator log, not raw transcripts here.
- Checkpoint 1 committed by coordinator as `f1f2e3ed859839e06d5fc5ebe0bd607d0bc029b2`; checkpoint 2 used the fresh `relay-144-builder-2.json` scope snapshot.
- Checkpoint 2 red: changed `test_a_failed_session_save_rolls_back_close_with_503` against unchanged production code returned 400 instead of 503: 1 failed in 1.75s. This replaces the prior residual expectation; it does not remove failure coverage.
- Checkpoint 2 implementation: close-local `save_close_message` saves existing unread/new messages inside the close transaction and marks storage/session clean in `finally`. Existing backend and middleware unchanged. Added real commit rollback and independent-connection deleted-session coverage, retained prior unread notifications, and a browser failure/retry/once-only journey. Browser coverage was added after the server regression demonstrated red; it exercises the same failure through the UI plus recovery by ordinary retry.
- Focused green: `pytest src/rounds/tests/test_messages.py src/rounds/tests/test_close.py src/rounds/tests/test_close_services.py` → 47 passed (6.28s); `pytest src/rounds/tests/test_retest.py src/rounds/tests/test_result_services.py` → 97 passed (12.17s); `pytest src/e2e/test_round_lifecycle.py src/e2e/test_review.py` → 5 passed (45.14s); `pytest src/rounds/tests/test_framing.py` → 14 passed (2.56s). Each command used `--ds=relay_slice144_settings`, external settings on `PYTHONPATH`, and a unique external `--basetemp`, with existing root virtualenv activated. Local PostgreSQL/Chromium calls required authorized sandbox escalation.
- Test repair: initial close-write failure injection patched `Round.save`, but service uses `QuerySet.update`; corrected injection without weakening expected rollback. Framing's obsolete close-400 expectation now covers close-503 and retains publish-400 response-middleware coverage. Initial ruff findings were import order and a long signature; formatted/fixed. Final targeted ruff check and format check passed on all four changed Python files.
- Next: coordinator checks scope/diff and commits checkpoint 2, captures a fresh snapshot, then resumes guide/final integrated verification. No full suite attempted yet; run it once at the final checkpoint, retaining any Windows environment failures. No open product decision; independent review and delivery remain outstanding.
