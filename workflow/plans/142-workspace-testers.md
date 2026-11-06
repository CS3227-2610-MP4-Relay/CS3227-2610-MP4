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

Use the shared parent `.venv` with the coordinator-provided external test settings override: isolated PostgreSQL 17.6 on loopback port 56442, existing synthetic test database names/credentials. No environment files or dependencies change. Coordinator's database smoke test passed; builder has not run database tests. Three existing fixed-port configuration probes may fail locally because 55432 is reserved; report exact actual failures if encountered, and require hosted Linux CI evidence for a full pass. Browser tests use the existing Chromium loopback harness.

Current checkpoint: specs/plan only, implementation not started. Next: coordinator scope check/commit/fresh snapshot, then checkpoint 2. Usage is collected by the coordinator's aggregate baseline; missing builder-local counters remain unavailable.
