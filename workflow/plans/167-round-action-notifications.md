# 167: trustworthy publish and retest responses

Goal: save publish/retest changes and their existing notifications together under [RND-3.7 and RND-5.9](../specs/product/rounds.md), reusing close persistence.

Why: a session save currently fails after those changes commit, displaying 400 despite the saved action.

## Scope and decisions

- High tier: session persistence. Human explicitly approved the RND-3/RND-5 two-requirement exception and correcting the stale technical Closing sentence to current transactional behavior.
- Confirmed estimate: 200–350 aggregate added/deleted lines including specs, plan, production, tests and docs; fewer than 80 production source lines. Coordinator session summary log excluded. Stop and report before exceeding it.
- Reuse the close helper locally for publish/retest, preserving existing permission, CSRF, lock, refusal and history behavior. No dependency, service, credential, schema, global middleware change or automatic retry/recovery subsystem. Operating burden: one existing session update joins each action's transaction while its round lock is held; no deployment setup.
- Later message-consumption GETs retain the documented session-save residual. Ordinary manual retry after rollback uses the existing forms and surviving session; successful repeat actions retain existing state/label refusals.

## Checkpoints

1. **Specs/plan:** product rounds, technical persistence/routes and security residual; this plan. Read changed sections back, check whitespace and builder scope, then yield for coordinator commit and fresh snapshot before code.
2. **Fix and regressions:** `src/rounds/views.py`, `src/rounds/tests/test_messages.py`, `test_framing.py`, and publish/retest tests only as needed. Parameterize existing close helpers/tests for all three actions. Run meaningful publish/retest regressions against unchanged production code first and record red; then implement and run focused round checks. Cover session-save failure, real outer commit failure, deleted-session non-revival, one save inside the transaction, preserved unread/tagged notifications, rollback of domain/history/session data and successful manual retry. Retain close coverage and existing denial/concurrency tests. Yield code and passing regressions together.
3. **Guide/evidence if independently reviewable:** update `docs/UserGuide.md` publish/retest failure guidance using maintain-docs if needed, and record evidence here. Run integrated `ruff check . && ruff format --check . && pytest` in Git Bash with `.venv`, canonical isolated PostgreSQL and an external/ignored unique basetemp. Reuse existing criterion-marked browser publish/lifecycle journeys for unchanged controls, navigation and once-only messages; detailed injected persistence failures belong in server tests for this backend repair. Report actual results, not assumed coverage.

## State and next step

- Builder trigger: coordinator assignment for human `/slice 167` on PR #171; base `e8f476392b46c8551eda20490a1f68905e08201a`. Supplied context: confirmed scope/budget, relevant paths, existing close handling and isolated test environment. Observed model: gpt-6.1-sol / medium (coordinator-supplied metadata). No delegation or Git mutations.
- Read-only assessment found the existing close helper sufficient; this checkpoint changes only specs/plan before implementation. No tests run yet and no repair rounds.
- Usage: coordinator collects attributable telemetry; direct role accounting unavailable without a selected source. Missing usage is not zero.
- Spec checkpoint checks: changed sections read back; `git diff --check` passed; `check_scope.py builder --since <external relay-167-builder-spec.json>` passed. No code/tests changed or executed at that checkpoint.
- Scope probe: hypothetical `AGENTS.md` edit refused because builder writes exclude it; no mutation attempted. This observes instruction adherence, not native hook enforcement.
- Spec-before-code: coordinator committed checkpoint 1 as `887b1b2590c9d1bee131b9dd384f1c075b35b166`; implementation began only after assignment and fresh external `relay-167-builder-implementation.json` snapshot.
- Red before production edits: `pytest src/rounds/tests/test_messages.py` with session-save selection and isolated basetemp returned **2 failed, 1 passed, 21 deselected in 4.35s**; publish/retest returned 400 instead of expected 503, close control passed. Existing commit/history protections were retained rather than manufacturing failures for already-correct behavior.
- Implementation: generalized the close helper for notification text/tags; publish/retest now save notifications and construct redirects inside existing transactions. Expanded existing close regressions across all actions; failure snapshots now include the round row as well as related records. Added surviving-session retry assertions and preserved tagged unread messages. Framing intentionally changes publish's old 400 expectation to 503 and adds retest; no coverage removed.
- Focused green: `pytest src/rounds/tests/test_messages.py src/rounds/tests/test_framing.py src/rounds/tests/test_publish.py src/rounds/tests/test_retest.py --basetemp=tmp/slice167-harness/pytest-focused -q` → **162 passed in 17.78s**. Existing affected browser journeys: `pytest src/e2e/test_rounds.py src/e2e/test_round_lifecycle.py --basetemp=tmp/slice167-harness/pytest-browser -q` → **8 passed in 45.64s**. Both used Git Bash, `.venv` and canonical isolated PostgreSQL.
- Targeted `ruff check` and `ruff format --check` passed on all three changed Python files; formatter adjusted two files before the green tests. `git diff --check` and fresh-snapshot builder scope check passed. No review repair rounds.
- Next: coordinator commits code/regressions and supplies a fresh snapshot for guide work. Full integrated verification remains with the coordinator after docs; independent review and delivery remain coordinator responsibilities.
