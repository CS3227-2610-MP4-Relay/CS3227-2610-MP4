# Slice 26: Test the Test Coordinator's features end to end (#26)

Goal: one server-side HTTP journey proves a coordinator can create a demo workspace, sign in, prepare a round, publish it, retest a case twice and close it, submitting each action through the form its page renders, with the shipped state transitions and refusals ([ACC-1](../specs/product/accounts.md#acc-1-sign-in-and-out-by-role), [ACC-2.1](../specs/product/accounts.md#acc-2-create-an-isolated-demo-workspace), [RND-1](../specs/product/rounds.md#rnd-1-prepare-a-test-round), [RND-2](../specs/product/rounds.md#rnd-2-manage-acceptance-criteria-and-test-cases), [RND-3](../specs/product/rounds.md#rnd-3-publish-a-round-to-beta-testers), [RND-5](../specs/product/rounds.md#rnd-5-request-a-retest), [RND-6](../specs/product/rounds.md#rnd-6-close-a-round)).

Tier: Standard, test-only: no product code, criteria, security controls, dependencies or CI change. Base/branch: `a121d6e` / `26-test-coordinator-e2e`; main merged in at `922a8d4`. Owner: zheng-jj. The PR refers to #26 ("Refs #26") and does not close it: [RND-4](../specs/product/rounds.md#rnd-4-review-submitted-results) (results, unimplemented) is not covered, and RND-8 (AI test drafting, specified only on the #78 branch, not on this branch) is not covered.

Size: the estimate was 220-300 lines in one test file; the first candidate exceeded it at about 420 lines. The repair adds a form-reading helper and the assertions below, so the final size is recorded in the repair handoff. This is test code, so it does not count against the 400-line non-test slice budget.

## Scope and decisions

In scope: one journey test file driving only real HTTP routes in sequence with the Django test client. Out of scope: Playwright changes, new dependencies, service-layer setup, product or spec changes, and the exhaustive boundary, concurrency, security and rendering matrices already in `test_views.py`, `test_records.py`, `test_publish.py`, `test_retest.py`, `test_close.py`, `test_sample_round.py` and the accounts tests.

- **Division of work with `src/e2e/` (#81).** The Playwright suite covers browser rendering and interaction: `test_rounds.py` creates, adds a linked case and publishes through Chromium, and checks RND-2.6 and RND-3.3 refusals; `test_accounts.py` covers ACC-1 sign-in, sign-out and wrong-role navigation with fixture accounts. This HTTP journey keeps what those do not: demo-workspace creation and its credentials, sign-in with those credentials, round/criterion/case edits, two retests, closing, and the Open- and Closed-round 409 refusals, in one server-side sequence. It is not ported to Playwright.
- **File name.** Renamed from `test_coordinator_e2e.py` to `src/rounds/tests/test_coordinator_journey.py`, so it is not confused with the browser suite in `src/e2e/`; it stays with the rounds tests because most of what it asserts is RND behaviour.
- **Browser-faithful submissions.** The client is `Client(enforce_csrf_checks=True)`. Every POST is built from a form on the page just fetched: its `action`, its hidden `csrfmiddlewaretoken`, its default values, and fields chosen by their visible label or checkbox label; the helper fails readably if the form, button or label is missing. Refusal checks resubmit forms kept from earlier pages (a stale tab), so they also carry real tokens. A small local form reader is used because `src/ai/tests/html_forms.py` exists only on the #78 branch; unify them when both are on main. Sign-in submits the rendered form, whose action is `/sign-in/` without `next`; the earlier hand-built conflicting `next` field is dropped, as `next` handling belongs to the sign-in tests.
- **Shared helpers.** Reuse `conftest.page`, `ROW` from `src/accounts/tests/test_demo_views.py` and `HOME_ITEM` from `test_sample_round.py`; one helper slices a case or build section up to the next `<h3>`. Lookups that can miss fail with an assertion naming what was missing, not a `ValueError`. Build labels are read as text, so multi-line labels parse.
- **Marks and comments.** The test is marked ACC-2.1, ACC-1.1, RND-1.1, RND-1.2, RND-2.1, RND-2.2, RND-3.1, RND-5.1, RND-5.5, RND-6.1, RND-6.2 and RND-6.3. Comments and the docstring name only those, or say explicitly that a criterion is observed in part and not marked.
- **Exact text.** Use the spec/template strings, including state names, success messages, the close warning and conflict headings; assert message counts where the spec says "once".

## Journey and criterion mapping

1. **Demo workspace** (ACC-2.1): submit the start page's "Create a demo workspace" form; assert `200`, `no-store`, no session, the heading, workspace name, credential table with Test Coordinator then two Beta Testers, the save-passwords warning and the Sign in link.
2. **Sign in** (ACC-1.1): submit the sign-in form with the shown coordinator credentials; assert `302` to `/coordinator/`, the home title, workspace and username, and exactly one linked "Sample round" in Draft (RND-7 observed, not marked).
3. **Create a round** (RND-1.1): submit the New round form; follow its redirect; assert the heading, "State: Draft", "Edit round", both empty-list texts, and the round first on the Coordinator home.
4. **Add criteria** (RND-2.1): submit the criterion form twice; assert both texts in creation order under "Acceptance criteria" with their edit controls.
5. **Add cases** (RND-2.2): submit the case form twice, checking criteria by their labels (the first case links both, the second only the second); assert each case's fields and linked criteria.
6. **Edit** (RND-1.2; RND-2.3 editing observed, not marked): the edit-round form shows the current title and a "Save" button; submit a new title; edit one criterion and one case through their forms; assert the new title on the round page and Coordinator home, the changed texts, and that the first case still links both criteria (the revised text included) and the second still links only the second.
7. **Publish** (RND-3.1): assert the publish form ("Build label", "Publish round") comes after the Test cases section; submit it; assert "Round published." once under the heading, "State: Open", each case's current build, the build's coverage, and no Draft controls or publish form.
8. **Open-round refusals** (part of RND-1.7, RND-2.8 and RND-3.6, observed and not marked): resubmit the kept edit-round and publish forms; assert `409` with the Open conflict heading, the attempted title absent, the title heading unchanged and the round page otherwise unchanged.
9. **First retest** (RND-5.1, RND-5.5): the retest page lists both cases unchecked, by title, with "Build label" and "Request retest"; retest the first case; assert the singular message once under the heading, the first case's current build changed, the second's unchanged, both builds' coverage in order, and criteria and case content unchanged.
10. **Second retest** (RND-5.5): retest the first case again on a third label; assert all three builds listed oldest first with their coverage and content still unchanged.
11. **Close** (RND-6.1, RND-6.2): assert the warning paragraph immediately before the Close round form; submit it; assert "Round closed." once under the heading, "State: Closed", content and builds kept, and no forms or controls.
12. **Closed-round refusals** (RND-6.3; edit, publish, retest and record changes observed in part for RND-1.7, RND-2.8 and RND-3.6, not marked): resubmit kept edit, publish, close, retest, criterion/case edit and delete forms; assert each `409` with the Closed conflict heading, and afterwards the attempted title absent, the title heading unchanged, and the page, builds and coverage unchanged.

## Evidence

Coverage-only exception: the journey exercises implemented behaviour, so it passes on first run; its assertions are shown to detect defects by mutation. The first candidate's evidence (mutations A-E: publish and record Draft guards removed, retest covering every case, publish text changed, retest changing case steps; each failed the journey and was restored byte-for-byte; afterwards `59 passed` once stale `__pycache__` was removed) applies to that candidate only. The repair adds CSRF mutations: removing `{% csrf_token %}` from the close form in `round.html`, and separately from `round_form.html` (used by the retest form), must each fail the journey; each file is restored and checked with `cmp`, with stale bytecode removed first.

## Commit checkpoints

1. `0c9327f` plan: record the coordinator end-to-end coverage.
2. `fb402d1` test: the journey test.
3. `ccb0553` test: narrow the criterion marks.
4. `6e5bf9b` test: assert retests preserve case content.
5. `922a8d4` chore: merge main (#81 Playwright journeys and deployment work).
6. plan (this repair): record the review repairs, division with `src/e2e/`, overclaim fixes and history. Check: `git diff --check`; read back.
7. test (repair): rename to `test_coordinator_journey.py`; CSRF-enforcing form submissions; unchanged-title and unchanged-page checks after refusals; shared helpers; readable lookups; the step 6, 7, 9 and 11 assertions; comment and docstring fixes. Checks: the focused commands below and the CSRF mutations.

## Focused checks

With `.venv` active, from the repository root:

- `pytest -q src/rounds/tests/test_coordinator_journey.py`
- `pytest -q src/rounds/tests/test_sample_round.py src/accounts/tests/test_demo_views.py` (modules whose patterns are imported)
- `ruff check src/rounds/tests && ruff format --check src/rounds/tests`
- Full verification is run by the coordinator: `ruff check . && ruff format --check . && pytest`

## History

- The first candidate (checkpoints 1-4) was produced in a DeepSeek workflow experiment. Its builder ran as Codex role "default", not the builder adapter, although its handback says "Agent: builder".
- An independent review then found: CSRF disabled with hand-built POSTs (M1), undocumented overlap with #81 (M2), an overclaim to close #26 (M3), plan overclaims at steps 6-9 and 11 and a wrong step 8 tag (L4), no unchanged-title checks after refusals (L5), duplicated helpers (L6), `ValueError` lookups and a single-line `current_build` (L7), comments naming unmarked criteria (L8), an unrecorded size overrun (L9), stale checkpoints (L10) and the role record (L12). The human decided on 2026-10-29 to repair and keep the HTTP journey; checkpoints 6 and 7 carry that repair.

## Next step

Checkpoint 7: the test repair with its CSRF mutation evidence. Then the coordinator runs full verification, updates the PR body to "Refs #26", and returns the repaired range to an independent verifier.
