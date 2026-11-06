# 141: Warn about pending drafts before closing

Goal: show coordinators a private aggregate warning before closing under [RND-6](../specs/product/rounds.md#rnd-6-close-a-round).

## Scope and decisions

- Human trigger: `/slice 141`, stacked atop PR #151; High tier because an authorized coordinator query crosses the private-result boundary. Coordinator owns Git, verifier/security review and draft-PR delivery; builder does not delegate or change Git state.
- Why: coordinators cannot currently tell that closing will strand saved pending drafts. Extend RND-6 only with RND-6.6; keep immediate close semantics. Issue #141's MEMBER-authored title/context were supplied as data, not requirements.
- Confirmed scope: boolean existence warning beside the existing Open-round close control for saved unsubmitted drafts still eligible on each case's current build. No counts, identities, outcomes, observations, extra confirmation, blocking, autosave, live updates, recovery, credentials, dependencies or new service. Browser-only work is unknown; the request snapshot can become stale.
- Reuse `show_round`'s authorized case/current-build map and `results.covered_results`; add one existence read restricted to same-workspace Beta Testers and current case/build pairs. Pass only a boolean. Draft/Closed skip the read. Existing wrappers handle access, caching and storage failures. No changes to RND-4 review or tester writes.
- Estimate: 25–60 production source lines, 150–240 server/browser test lines, and 40–70 spec/plan/guide lines; approximately 215–370 inserted/deleted lines total, no new operating burden. Budget: one requirement's criteria changed, at most 400 production source lines. Stop and report any necessary expansion or estimate overrun.
- Starting HEAD: `4fedf0a019d8ee28c93d4d5561427dc76ac506c1`, branch `feat/141-pending-draft-warning`, base `origin/feat/140-unsaved-result-warning`; coordinator's pre-edit snapshot `%TEMP%/relay-141-builder-plan-before.json`. Preserve unrelated untracked files and others' edits.

## Commit checkpoints

1. **Specs/plan** (`spec:`): RND-6.6 in `workflow/specs/product/rounds.md`, architecture/control clarifications in `workflow/specs/TECHNICAL-SPEC.md` and `workflow/specs/SECURITY-SPEC.md`, and this plan. Read changed sections back; run whitespace and builder scope checks. Yield before tests or implementation.
2. **Behavior and regressions** (`feat:`): `src/rounds/results.py`, `src/rounds/views.py`, `src/rounds/templates/rounds/round.html`, focused `src/rounds/tests/test_close.py` and `src/e2e/test_round_lifecycle.py` (or a narrowly scoped companion using the existing harness). Add criterion-marked tests first and run focused missing-warning regressions against unchanged production code; record real red evidence. Implement only the boolean read and fixed copy, run focused new and existing close/review suites, then yield with red/green, diff size and scope evidence for coordinator commit/new snapshot.
3. **User Guide and final validation** (`docs:`): update `docs/UserGuide.md` using built warning text and its snapshot/browser-only limitation; read back. Run High-tier full checks with the existing venv and coordinator-confirmed PostgreSQL/browser environment: `ruff check . && ruff format --check . && pytest`. Report exact failures and environmental limits; no installs or tracked test-environment changes. Yield for coordinator's fixed-candidate verifier/security review and delivery.

## Verification map

- RND-6.6 positive/zero partitions: warning for one eligible draft and multiple testers/cases; no warning for no rows or submitted-only rows. Reload after submit/save reflects the new existence state. Read leaves all rows unchanged; close still succeeds despite pending drafts and preserves them.
- Current-build boundaries: selected-case retest removes its old draft from eligibility; unselected-case drafts remain eligible. Reject uncovered, cross-round and cross-workspace case/build combinations, foreign-workspace testers and coordinator-owned rows, including directly seeded malformed records. Same-workspace tester identity/outcome/observation and draft case/build associations never enter warning context or HTML; verify that the query selects no draft payload fields.
- Existing access/state boundaries: signed out redirects; tester gets 403; missing/foreign rounds get fixed 404; Draft/Closed show no warning and do not run the draft query. Forged query selectors change nothing. Exercise never-cached responses and a draft-query database failure yielding fixed 503 without partial content.
- Browser journey: coordinator sees fixed warning adjacent to irreversible-close text, closes with one button and no added confirmation, sees Closed without warning; draft remains saved. Cover no-warning state and reload/retest transition through the existing browser harness. Server tests carry detailed malformed-row partitions.
- Environment: reuse existing venv and installed Chromium; coordinator will confirm external temporary test settings and PostgreSQL loopback port (56440 may be available; normal 55432 is Windows-reserved). No provider calls. Existing full-suite environment failures must be reported, never hidden by test/config changes.

## Status and next step

- Specs/plan checkpoint prepared before source/test edits. Next: coordinator reviews and commits this checkpoint, supplies fresh scope snapshot and confirms test environment before authorizing checkpoint 2.
- Trigger/context: coordinator supplied confirmed issue scope, High tier, budgets, base/snapshot, relevant paths and checkpoint boundaries. Usage baseline is coordinator-owned across related sessions; builder session/model counters are unavailable to the builder unless supplied by the coordinator.
- Open product decisions: none.
