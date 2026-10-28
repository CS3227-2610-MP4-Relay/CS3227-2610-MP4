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
- Spec/plan committed `3abd7b40ae74f8fc455152df72ec417cf1a1fc71`; implementation snapshot `%TEMP%/relay-django-build-implementation.json`. Red: `pytest src/relay/tests/test_release.py -q -k archive_keeps_runtime_requirements_without_tooling_manifest` failed because tooling pyproject was uploaded. After removing that required archive root and correcting the Git fixture's root selection, `pytest src/relay/tests/test_release.py src/relay/tests/test_ci.py -q` passed 67 tests. Ruff/format passed after formatting two new long test lines; whitespace/scope passed. Runtime pins and local Ruff configuration are unchanged.
- Implementation committed `38cedcce07d4c585beb554651628ddfd69856a3b`; its real 53-file archive selects `requirements.txt` and all six pins. Full local checks passed Django/Ruff/format; pytest: 1,034 passed, three documented Windows idle-timeout wording failures, one skipped. The temporary local database was stopped afterward.
- Verifier and security reviewer independently reviewed that fixed candidate against the base, each passing 67 release/CI tests with no actionable findings; scope and unchanged-candidate checks passed. [Linux CI](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40717377811): 1,035 passed, three skipped; Django/Ruff/format/site passed and publication jobs skipped.
- [Draft PR 84](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/84) carries final summary-head CI. Next: human review/merge, then prepare a fresh archive from the verified merged commit for the protected bootstrap. Hosted build success remains unverified. Usage and agent evidence: [session log](../../logs/Whimsyturtle/012-prepare-vercel-and-neon-production-delivery.md).
