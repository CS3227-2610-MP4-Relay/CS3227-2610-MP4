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
- Open issues: none. `docs/Runbook.md` is outside builder scope; coordinator assesses whether its smoke description needs a linked update.
- Next step: coordinator reviews/commits this spec-and-plan checkpoint and supplies a fresh scope snapshot before the implementation unit.
