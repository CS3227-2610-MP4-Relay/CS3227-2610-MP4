# Slice 13: save and submit results

Goal: let a tester save a private draft or immutable submission for the current build of an Open case ([RES-2](../specs/product/results.md#res-2-save-and-submit-an-outcome-with-observations)).

## Confirmed scope and decisions

- Human requested slice 13 stacked on PR #86. Starting commit: `114bbce3053a9e19b98f463a482bc62365c08da9`; branch `feat/13-submit-results`; High tier for ownership and writes.
- Human confirmed the full proposed contract and then "Yes—put it beside each case", authorizing the narrow RES-1.5 navigation amendment in addition to one new requirement, RES-2. No other RES-1 criteria change.
- Why: availability is already built; saving and submitting now need explicit ownership, validation, build/state, concurrency and failure contracts before persistence is added.
- Product decisions live in RES-2; architecture and controls live in the technical/security specs. Routine defaults accepted by the coordinator: identical Save/Submit validation, serialized draft last-save wins, every POST after submission refused, stale-build writes refused, current Open submission readable on entry, Closed entry refused. No extra history/review screen, AI, dependency, service or recovery subsystem.
- Budget: estimated 250–350 changed non-test source lines, excluding migrations; hard limit 400. Stop affected work before exceeding 350 or adding capability outside this scope and return a specific decision. Existing case/build caps plus result tuple uniqueness bound rows.
- Criterion review: eight new RES-2 criteria plus the narrow RES-1.5 navigation amendment exceed the guideline by one. This remains one result-entry journey using existing access, rendering and transaction patterns; the human explicitly confirmed the two-requirement exception, and detailed server partitions plus one browser journey keep its verification reviewable.

## Incremental checkpoints

Only the coordinator changes Git state. Builder yields after each unit for scope review, commit and a fresh baseline before starting the next.

1. **Specs and plan** — `workflow/specs/product/results.md`, relevant tester/result sections of `workflow/specs/TECHNICAL-SPEC.md` and `workflow/specs/SECURITY-SPEC.md`, and this plan. Read changed sections back; `git diff --check`. Yield before code.
2. **Persistence and service with regression tests** — `src/rounds/models.py`, a new migration, a focused result service module and `src/rounds/tests/test_result_services.py`. Write focused failing tests before implementation; check tuple uniqueness/PROTECT, owner separation, frozen submission, draft replacement, rollback and actual PostgreSQL races with close/retest/duplicate submit using existing concurrency patterns. Run targeted tests, Ruff and migration drift check before yielding.
3. **Form, route and UI with server tests** — result form, `src/rounds/tester.py`, `src/accounts/urls.py`, tester detail/result templates and `src/rounds/tests/test_results.py`; update existing assertions only where RES-1.5 now permits entry links. Record focused missing-behaviour failures before implementation. Cover RES-2.1–2.8 and RES-1.5 navigation: validation partitions and 1999/2000/2001 lengths, each invalid field independently, ownership and foreign IDs, methods/CSRF, conflict precedence, rollback/storage failures, text rendering, retest and closure. Run focused result/availability tests and Ruff before yielding.
4. **Browser journey** — `src/e2e/test_results.py` and necessary RES-1.5 navigation assertions in `src/e2e/test_tester.py`, using the existing harness. Record red evidence before implementation unless assertions already pass because the server checkpoint supplies the behaviour; explain that exception. Criterion-mark the real-form journey through draft reload, Fail validation, submit/read-only and refusal after retest/closure. Verify separate tester visibility with synthetic accounts. Run affected browser tests before yielding.
5. **Documentation and integrated verification** — `docs/UserGuide.md`, `docs/DeveloperGuide.md` and this plan. Describe built labels and design, link to canonical contracts, and read changed sections back. Run full `ruff check . && ruff format --check . && pytest` in the existing venv against the loopback PostgreSQL test configuration; report exact results and migration drift. Yield fixed candidate for independent verification/security review and coordinator delivery.

## Current checkpoint and evidence

Checkpoint 1: specifications and plan prepared; no implementation or test files changed. Scope snapshot supplied by coordinator: `%TEMP%/relay-13-builder-plan.json`. Spec-before-code evidence is this checkpoint's reviewed diff and subsequent coordinator commit.

Discovery reused existing workspace helpers, serialized round writes, text filters and browser harness. PostgreSQL is available at `127.0.0.1:55432` under the existing test settings; no installation is authorized or needed. Agent trigger/context, actual checks, resource deltas and handoffs are recorded by the coordinator; unavailable telemetry must remain unavailable.

Next: coordinator reviews/commits checkpoint 1, captures a fresh scope snapshot, and assigns checkpoint 2. No open product decision remains for the confirmed scope.
