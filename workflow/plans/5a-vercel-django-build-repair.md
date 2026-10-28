# 5a: Repair Vercel Django dependency discovery

Goal: deploy the existing pinned runtime requirements without the local Ruff configuration shadowing them.

## Scope and reason

- Continuing the human-authorized slice-5 deployment; High tier, branch `fix/5-vercel-django-build`, base `2c4ebe62307acaff57a76f4f86095d0bec37ef4c`, scope snapshot `%TEMP%/relay-django-build-plan.json`. The merged slice-5 plan stays frozen. Builder model: `gpt-6.1-sol`, medium; no delegation or Git/hosted changes.
- Why: the protected bootstrap completed Neon migrations but the hosted settings probe failed with `ModuleNotFoundError: No module named django`. The uploaded archive included a Ruff-only `pyproject.toml`, which shadows `requirements.txt` in the observed provider dependency discovery.
- Existing PLT-1.10 covers correct committed build inputs; no new criterion, dependency, service, credential or security exception. Omit only the tooling manifest from the release archive; keep it locally for Ruff and keep runtime pins in `requirements.txt`. Preserve exact-commit preparation, exclusion rules and all delivery/release gates. Do not mutate a previously prepared archive or deploy during this repair.
- Target: fewer than 100 total changed lines, with production source shrinking. Coordinator owns commits, independent reviews, log, draft PR and CI; human owns merge and release.

## Checkpoints

1. **Spec and plan**: correct the technical allowlist before code; read back, check whitespace/scope and yield for commit.
2. **Archive repair and regression**: change `src/release.py` with its tests in `src/relay/tests/test_release.py`. Reproduce failure before implementation using a committed tooling manifest alongside runtime requirements; assert it is absent from prepared output while pinned requirements and required application inputs remain unchanged. Run focused release/CI tests, Ruff/format and scope/diff checks, then yield for commit.
3. **Integrated verification and delivery**: coordinator runs full verification, freezes the candidate for verifier/security review, records evidence/usage, and delivers a draft PR with exact-head CI. Hosted retry remains separately controlled; a passing local check is not a successful Vercel build.

## Evidence and next step

- Read-only offline reproduction with installed `@vercel/python-analysis` 0.15.0: actual prepared source selects dependency-empty `pyproject.toml`; a fixture containing current requirements/version files selects all six pinned requirement strings; adding the unchanged tooling manifest switches selection back. Provider source prioritizes any pyproject over requirements.
- Coordinator inspected `@vercel/python` 25.1.2 ordering: toolchain setup, managed dependency installation, Django framework hook, then Django settings probe. This corroborates the manifest diagnosis; the remote CLI 65.1.0 build and repaired hosted outcome remain unverified. No production credentials were read or provider action performed in the investigation.
- Next: commit this spec/plan checkpoint, capture a fresh builder snapshot, then implement the regression and minimal archive change. Usage baseline `%TEMP%/relay-django-repair-plan-builder-before.json`; metadata only.
