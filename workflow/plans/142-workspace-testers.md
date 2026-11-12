# 142: Add workspace Beta Testers

Goal: implement [ACC-4](../specs/product/accounts.md#acc-4-add-a-beta-tester-to-my-workspace).

Tier: High. Branch: `feat/142-workspace-testers`; initial base: `4cc6166b2495b85b474496d7eed6fd1235c3d13a`. Builder owns only its role's permitted paths; coordinator owns Git and delivery.

## Decisions and budget

Human confirmed the coordinator action with generated credentials shown once and 10 testers total per workspace, including the initial two. Why: coordinators need additional testing participants without creating another workspace. Exclude member roster/editing, invitations, deletion, password reset, new dependencies, schema and external services. Product behaviour lives only in ACC-4; architecture and controls live in the linked technical/security specs.

Estimate: 200–300 changed non-test source lines, 600–900 total changed lines; hard slice cap: 400 non-test source lines. Stop affected work and report any anticipated excess or capability expansion before implementing it.

## Commit checkpoints

1. **Specs and plan** (`spec:`): `workflow/specs/product/accounts.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`, this plan. Read back changed sections and run `git diff --check`; yield for coordinator scope check, commit and fresh snapshot before code.
2. **Behaviour and regression coverage** (`feat:`): `src/accounts/demo.py` for shared credential generation only, new `src/accounts/testers.py`, `src/accounts/views.py`, `src/accounts/urls.py`, new accounts credential/refusal templates, `src/rounds/templates/rounds/coordinator_home.html`; account tests, `src/relay/tests/test_access_matrix.py`, `src/e2e/test_accounts.py`. Derive focused server, concurrency, credential-report redaction and browser tests from ACC-4, run them before implementation and record actual red outcomes. Extend matrix outcome/account-change handling for the new route without weakening existing checks. Implement and run focused tests, existing affected account/browser/matrix regressions, and Ruff; yield passing implementation plus red evidence for coordinator scope check and commit. Tests that already pass require a stated justification. No database tests until this checkpoint starts.
3. **Guides and integrated validation** (`docs:`): `docs/UserGuide.md`, relevant `docs/DeveloperGuide.md` text, this plan's checkpoint evidence. Match the built UI and link to requirements/design instead of duplicating them. Read back and run `git diff --check`; run full Ruff lint/format and pytest before claiming code completion. Yield candidate for independent verification/security review and coordinator delivery. Repairs are separate checkpoints only if needed.

## Verification environment and next step

Use the shared parent `.venv` with the coordinator-provided external test settings override: isolated PostgreSQL 17.6 on loopback port 56442, existing synthetic test database names/credentials. No environment files or dependencies change. Coordinator's database smoke test passed; builder results follow below. Three existing fixed-port configuration probes may fail locally because 55432 is reserved; report exact actual failures if encountered, and require hosted Linux CI evidence for a full pass. Browser tests use the existing Chromium loopback harness.

## Checkpoint evidence

- Specs/plan committed by coordinator at `6866eaf8b26e399ec03b96ef2ff7849ac87f9fc9`; implementation snapshot: `%TEMP%/relay-142-builder-implementation.json`.
- Before implementation: focused happy test failed on the missing home button; four capacity partitions failed on the missing route (404); the new browser journey failed waiting for the missing button (5000 ms). Fault-injection tests requiring new internal targets ran after implementation; their checks require rollback, fixed logging and redaction, not merely a successful response.
- Initial backend run: 17 passed, 2 failed. Repaired a collision-test snapshot taken before sign-in updated `last_login`, and changed the single-password generator's sensitive-variable decoration to protect nested hasher arguments exposed by the error-report assertion. Existing test expectations were not weakened. Failure logging emits no traceback because exception text itself can contain credentials; the technical spec reflects this implementation choice.
- Focused serial run with the external settings override: `pytest --ds=relay_slice142_settings src/accounts/tests/test_add_tester.py src/relay/tests/test_access_matrix.py src/e2e/test_accounts.py -q -p no:cacheprovider` passed, 812 tests. Pytest reported 3290.45 seconds amid host scheduling delays; this is not active-work measurement. Tightened the statement-timeout assertion afterwards to require an actual database timeout; then `pytest --ds=relay_slice142_settings src/accounts/tests -q -p no:cacheprovider` passed, 204 tests in 17.71 seconds, including the tightened test. Matrix/browser inputs and implementation were unchanged.
- Ruff lint and format checks passed for accounts and changed matrix/browser files. Guides and full-suite validation remain checkpoint 3; no whole-slice completion claim yet.

Implementation committed by coordinator at `35b2e13e553dcd01e1d36c6deed3512fcbe69ba4`; docs snapshot: `%TEMP%/relay-142-builder-docs.json`. Guides describe the built action and were read back with changed links checked. Usage is collected by the coordinator's aggregate baseline; missing builder-local counters remain unavailable. Observed builder runtime: `gpt-6.1-sol`, medium reasoning, as mapped by coordinator telemetry.

Full local verification ran once in Git Bash with the shared venv and external settings/PYTHONPATH override: `ruff check . && ruff format --check . && pytest --ds=relay_slice142_settings`. Ruff passed; all 145 Python files passed formatting. Pytest: **3 failed, 2920 passed, 5 skipped**, 2 cache-write warnings, 600.94 seconds. All failures are `src/relay/tests/test_configuration.py::test_driver_ignores_inherited_hostaddr` at line 145, parameters `relay.settings.test-127.0.0.1`, `relay.settings.local-localhost`, `relay.settings.local-127.0.0.1`: their subprocesses force port 55432 and return 1 with `psycopg.errors.ConnectionTimeout: connection timeout expired`. Coordinator separately verified that Windows reserves 55419–55518; the isolated application test database uses 56442. Cache warnings report WinError 183 while creating `.pytest_cache/v/cache`; no tests were changed or skipped to hide these outcomes. Full local verification did not pass; hosted Linux CI must establish a full pass. Next: coordinator docs commit and fixed-candidate independent reviews/delivery.

## Criterion evidence

Backend names below refer to `src/accounts/tests/test_add_tester.py`. Browser journey: `src/e2e/test_accounts.py::test_coordinator_adds_tester_then_hits_capacity_and_new_tester_signs_in`. Matrix entry: `accounts:add-tester` in `src/relay/tests/test_access_matrix.py`. All listed automated checks passed in checkpoint 2.

| Criterion | Checks |
| --- | --- |
| ACC-4.1 | `test_create_ignores_identity_fields_and_shows_working_credentials_once`, matrix, browser journey |
| ACC-4.2 | `test_capacity_counts_only_own_testers_and_refuses_before_generation`, browser journey |
| ACC-4.3 | `test_concurrent_posts_fill_only_the_last_place` |
| ACC-4.4 | Creation/identity test, `test_roles_methods_and_csrf_deny_without_writes`, matrix |
| ACC-4.5 | Role/method/CSRF test, matrix |
| ACC-4.6 | Creation test, `test_failures_roll_back_and_redact_error_reports`, `test_hashing_precedes_transaction_and_commit_failure_rolls_back`, browser journey |
| ACC-4.7 | Failure/redaction, collision, commit-failure, workspace-lock timeout, statement-timeout and session-loading-failure tests |
| ACC-4.8 | Creation test's repeated POST and return-home checks, browser journey |

## Review and delivery

Independent verifier and security-reviewer inspected fixed range `4cc6166b..f9a7fad` and returned no actionable findings; their scope checks and the candidate snapshot comparison passed. Review limits and measured resources are in the [session log](../../logs/Whimsyturtle/052-add-workspace-beta-testers.md). [Draft PR #153](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/153) contains the coherent checkpoints; subsequent work is summary-only. At the log cutoff, site CI passed and required verify CI was pending. Next: verify successful configured checks on the final summary head; human log/manual review, merge and release remain pending.
