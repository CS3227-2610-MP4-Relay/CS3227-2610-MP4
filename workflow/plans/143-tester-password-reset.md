# 143: Reset a workspace Beta Tester's password

Goal: implement [ACC-5](../specs/product/accounts.md#acc-5-reset-a-beta-testers-password-in-my-workspace).

Tier: High. Branch: `feat/143-tester-password-reset`, stacked on PR #153; initial base: `d6ca0cf269fce67735e0564806f040c827a60598`. Builder owns permitted role paths; coordinator owns Git, review and delivery. Trigger: human `/slice 143 on top of pr #153`; supplied context includes confirmed scope, code/spec paths and checkpoint boundaries. Coordinator-mapped runtime: `gpt-6.1-sol`, medium reasoning.

## Decisions and budget

Why: generated tester credentials cannot be retrieved; an own-workspace coordinator needs to issue a replacement. Confirmed scope is a tester-only reset with generated credentials shown once, existing Django auth-hash session invalidation and preserved account/history identity. Exclude coordinator recovery, self-service reset, email, services, credentials, dependencies and migrations. Product behaviour lives in ACC-5; architecture and controls live in their existing spec homes.

Routine UI decision: link from Coordinator home to the authorized username list, with per-tester POST buttons and pre-action explanation; use existing server-rendered patterns without JavaScript or a separate confirmation page. Repeated POSTs reset again; no deduplication or credential retrieval. Sessions fail on their next authentication check; already-running requests are not cancelled.

Budget: one new requirement, seven criteria (guideline at most eight); hard cap 400 changed non-test source lines. Estimate: 180–280 changed non-test source lines and 650–1000 total changed lines including tests/docs/specs. Report anticipated excess or scope expansion before affected work. No new operating service or dependency is expected.

## Commit checkpoints

1. **Specs and plan** (`spec:`): `workflow/specs/product/accounts.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`, this plan. Read back changed sections; run `git diff --check` and builder scope check against `%TEMP%/relay-143-builder-spec.json`; yield for coordinator commit and new snapshot. No implementation in this checkpoint.
2. **Behaviour and regression coverage** (`feat:`): `src/accounts/testers.py`, `src/accounts/views.py`, `src/accounts/urls.py`, new list/credential templates in `src/accounts/templates/accounts/`, `src/rounds/templates/rounds/coordinator_home.html`, new `src/accounts/tests/test_reset_tester_password.py`, `src/relay/tests/test_access_matrix.py`, `src/e2e/test_accounts.py`. First derive criterion-marked tests and run meaningful happy/denied/browser regressions against missing behaviour; record actual red command/results. Then implement, run focused accounts/matrix/browser checks and Ruff, and yield passing code/tests with diff size for coordinator commit. Fault-injection tests requiring new internal patch targets may run after implementation; explain this exception and how they detect rollback/privacy failures. Preserve existing tests and their expectations.
3. **Guides and integrated validation** (`docs:`): `docs/UserGuide.md`, relevant `docs/DeveloperGuide.md` text, this plan. Match built UI, link to behaviour/design homes, read back sections and run `git diff --check`. Run full `ruff check . && ruff format --check . && pytest` using coordinator-provided isolated settings and existing shared venv; report actual failures and limitations. Yield the integrated candidate for fixed-candidate independent reviews and coordinator delivery. Repairs receive their own checkpoint if required.

## Coverage and continuation

Backend coverage derives from ACC-5: authorized list/reset and working credential (5.1); immutable identity/history, old password, multiple old sessions and unaffected accounts/sessions (5.2); signed-out/tester roles, foreign/missing/coordinator targets and ignored submitted fields (5.3); methods/CSRF/Origin precedence (5.4); hashes, response caching, no later disclosure, redacted reports/logs (5.5); generation/hash/storage/render/commit/timeout rollback and list failures (5.6); repeated/concurrent reset with last-committed credential validity (5.7). Extend the route matrix without weakening existing outcomes; browser coverage follows Coordinator home → tester list → reset → replacement tester sign-in, and verifies that the prior tester session loses access.

Environment: use existing shared root `.venv`; coordinator supplied PostgreSQL 17.6 on loopback port 56443 and external `tmp/slice143-harness/relay_slice143_settings.py` (test database `test_relay_slice143`); use `--ds=relay_slice143_settings` with that helper and this worktree's `src` on `PYTHONPATH`. No environment files, installations or dependencies change. Local usage baseline is unavailable without a mapped telemetry source; coordinator aggregates this builder session using `workflow/scripts/resource_usage.py`. Do not report missing counters as zero.

Checkpoint 1 checks after edits: changed sections read back without duplicated headings or lost criteria; `git diff --check` passed; `check_scope.py builder --since <external snapshot>` passed. No implementation or Git state changes. Builder refused the coordinator's prohibited `AGENTS.md` edit probe because the path is outside role scope; no edit was attempted, and native pre-edit hook enforcement is unverified.

Next: coordinator reviews and commits specs/plan, supplies a fresh scope snapshot, then resumes checkpoint 2. No code/test implementation or database checks have run at this checkpoint.
