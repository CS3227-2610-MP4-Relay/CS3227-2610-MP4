# Slice 159: Runtime database readiness

Make deployment smoke checks prove runtime database connectivity under [PLT-1](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification).

## Scope and decisions

- High tier: deployment boundary and new public route; one requirement, PLT-1.
- Human confirmed the public read-only endpoint and required deployment probe; estimated total diff 250–350 insertions/deletions, with at most 400 changed non-test source lines. Stop and report before exceeding the tighter total estimate.
- Why: existing anonymous HTML checks do not query the runtime database, while migrations use a separate direct connection; no production outage was observed.
- Use constant `SELECT 1` through Django's default runtime connection, existing connection timeout and generic database-failure handling. No new dependency, credential, service or recovery subsystem.
- Correct Neon branch identity is deferred. No UI journey changes; existing browser coverage remains applicable.

## Commit checkpoints

1. `spec: Define runtime database readiness (#159)` — product platform criteria, technical release verification, security delivery controls and this plan. Read back changed sections and run builder scope check; yield before tests or implementation.
2. `feat: Require runtime database readiness for delivery (#159)` — `src/relay/pages.py`, `src/relay/urls.py`, `src/release.py`, relevant `src/relay/tests/` and `docs/DeveloperGuide.md`. Keep endpoint, smoke integration and regression tests together. First run focused new tests against missing behaviour and record actual red evidence; implement, rerun focused checks, then full Ruff lint/format and pytest verification with the shared virtual environment. Coordinator commits only after the builder yields and scope passes.
3. Final summary only after coordinator freezes the candidate and independent verification/security review complete; repairs require fresh coordinator assignment/snapshot.

## Verification and handoff

- PLT-1.15: actual synthetic database success; connection/query failures with sensitive synthetic error text; GET/HEAD parity; rejected methods issue no query; fixed bodies, content type and cache prevention; constant query reads no application records.
- PLT-1.13/PLT-1.12: successful bounded probe; unavailable, malformed, redirected, timed-out or cacheable readiness responses fail delivery while existing page/header/cookie checks remain enforced. Reuse existing request bounds and no-redirect transport coverage.
- No live production requests. CI assertions change only if existing fixtures enumerate smoke requests.
- Open issues: none. Coordinator checked that the Runbook already links the authoritative contract; no Runbook edit is needed.
- Spec checkpoint committed by coordinator at `a7c82039d92e218d6aff3007cbea42aae883ad72` before implementation.
- Regression red: focused readiness selection on the unchanged application produced 32 failures (26 missing-route/query/method cases, six unchecked deployment failures); database setup succeeded. After implementation, both readiness/release modules passed: 100 tests in 3.35 seconds.
- Integrated lint/format passed. Local full pytest received one coordinator-directed Ctrl+C; the parent continued to exit 1 with interruption-contaminated subprocess/browser results: 251 failed, 2913 passed, 4 skipped, 27 errors, 94 subtests passed in 1048.94 seconds. This is incomplete verification, not success.
- Before interruption, failures identified missing readiness matrix coverage (builder self-correction) and the unchanged database-name assertion expecting `test_relay_test` rather than isolated `test_relay_159` (environment mismatch; untouched). Independent-review repair rounds remain zero.
- Final focused checks: 36 readiness/failure/public-matrix cases passed in 6.44 seconds; both complete readiness/release modules plus the route-completeness regression passed, 101 tests in 4.29 seconds. Final lint and format passed (148 files). Scope and whitespace checks passed.
- Coordinator pre-commit correction: normalize comma-separated cache directives with whitespace/case trimming while matching exact `no-store`. New regressions first produced two valid-format failures and three invalid-token passes; corrected readiness/release modules passed 105 tests in 3.38 seconds, with lint/format passing. Independent-review repair rounds remain zero; full CI remains pending.
- Next step: coordinator scope review/commit and Linux CI full verification before independent fixed-candidate review. Do not repeat the full local run.
