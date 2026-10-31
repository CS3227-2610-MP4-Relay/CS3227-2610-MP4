# Slice 23: observation feedback

Goal: give a tester transient clarifying questions for their own saved draft under [RES-4](../specs/product/results.md#res-4-suggest-missing-details-in-a-draft-observation).

Why: settle the existing planned observation-feedback contract before adding its explicit saved-draft request and manual-review journey.

## Scope and decisions

- High tier: AI calls and tester-owned source selection. One new requirement, RES-4, with eight criteria; existing RES criteria remain unchanged.
- Starting HEAD: `a8d6da759163da7d6307ae0b491cfb104ea911e0`; branch `feat/23-observation-feedback`. Human `/slice 23` authorizes normal branch/draft-PR delivery; only the coordinator changes Git or GitHub state.
- Saved-draft-only separate page, explicit POST, questions-only schema, original source retained and manual editing through existing entry. Product/AI/architecture/security facts live in their linked specs, not this plan.
- Estimate: 250–350 inserted/deleted non-test/non-migration source lines, below the 400-line slice budget. Tests and specification/documentation changes are additional. No migration, dependency, service, credential, cache or automatic editing. Stop and report before exceeding the confirmed scope or budget.
- Builder owns role-allowed spec/plan/source/guide paths and does not delegate. Coordinator owns checkpoints, usage collection, fixed-candidate independent review and authorized delivery. Preserve others' edits.

## Incremental checkpoints

1. **Specs and plan** (`spec: Define saved observation feedback (#23)`, `Agent: builder`; body begins with Why). Paths: `workflow/specs/product/results.md`, `workflow/specs/ai/observation-feedback.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`, this plan. Read changed sections, inspect diff/whitespace and run builder scope check against the supplied private snapshot. Yield before runtime implementation; coordinator reviews/commits and supplies a fresh snapshot.
2. **Source helper and parser with regression tests** (`feat: Validate observation feedback sources and questions (#23)`). Paths: `src/ai/feedback.py`, `src/ai/tests/test_feedback.py`; reuse existing cleaner without refactoring unrelated drafting. Tests first: exact data/instruction contract, cleaned strings, strict schema/JSON failure partitions, input/reply/question boundaries and source equality. Run focused tests before code, record actual missing-behaviour failures, then pass focused pytest and Ruff. Yield with size/evidence before coordinator commit.
3. **Authorized route and feedback UI with regression tests** (`feat: Suggest details for a tester saved draft (#23)`). Paths: `src/ai/feedback_views.py`, `src/ai/templates/ai/feedback.html`, `src/accounts/urls.py`, `src/rounds/templates/rounds/tester_result.html`, `src/ai/tests/test_feedback_views.py`, `src/relay/tests/test_access_matrix.py`; adjust helper only as required. Add tests first and capture meaningful red evidence for missing route/behaviour. Cover RES-4.1–4.8: source selection/ownership, unchanged domain rows, precedence of denials, no calls before eligibility, CSRF/method guards, shared gateway outcomes, error/log hygiene, escaped output and post-call state/source changes without a lock/transaction during fake calls. Run focused feedback/access-matrix tests, existing result-entry regressions and Ruff; yield before commit.
4. **Browser journey and guides** (`test: Exercise observation feedback and manual editing (#23)`, then `docs: Explain saved observation feedback (#23)` as separately reviewable units). Paths: `src/e2e/test_feedback.py`, `docs/UserGuide.md`, `docs/DeveloperGuide.md`, this plan. Use the existing browser harness with fake gateway, synthetic tester accounts and fixed test settings; add criterion-marked journeys for feedback → manual edit/save and unavailable → manual entry. Run new journey before implementation where feasible; if behaviour already exists by this checkpoint, explicitly record that exception and how assertions detect regressions. Run focused browser tests, then complete `ruff check . && ruff format --check . && pytest` with activated `.venv` in Git Bash. Update guides only to behaviour actually built; use maintain-docs instructions when that checkpoint is assigned. Yield code/browser evidence separately from guide edits for coordinator commits.

## Verification and next steps

Detailed partitions/evaluation are in the [AI contract](../specs/ai/observation-feedback.md#evaluation); tests carry RES-4 IDs. Parser/source tests cover RES-4.3/4.8; route tests cover RES-4.1–4.8; browser tests cover RES-4.1/4.2/4.4. No provider is called during automated verification; pending live model evaluation is separate from local correctness.

Current checkpoint: spec/plan only. Runtime tests and implementation have not started. Coordinator next reviews this checkpoint, checks role scope and commits, then supplies the next checkpoint and fresh snapshot. Final integrated candidate requires full verification, independent verifier and security-reviewer, authorized draft PR delivery and configured CI results. No merge/release approval is inferred.

Open decisions: none within the coordinator-confirmed narrow workflow. Live feedback evaluation remains an explicit operator follow-up; fake-provider checks cannot establish model usefulness.

Usage: builder source `codex:eb10a2893b0c05143aa57aa0`. Coordinator retains the private baseline/reports and records final observed totals; no raw transcripts are stored here.
