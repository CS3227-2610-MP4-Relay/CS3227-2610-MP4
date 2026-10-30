# Slice 26: Test the Test Coordinator's features end to end (#26)

Goal: one server-side HTTP journey proves a coordinator can create a demo workspace, sign in, prepare a round, publish it, retest a case twice and close it, submitting each action through the form its page renders, with the shipped state transitions and refusals ([ACC-1](../specs/product/accounts.md#acc-1-sign-in-and-out-by-role), [ACC-2.1](../specs/product/accounts.md#acc-2-create-an-isolated-demo-workspace), [RND-1](../specs/product/rounds.md#rnd-1-prepare-a-test-round), [RND-2](../specs/product/rounds.md#rnd-2-manage-acceptance-criteria-and-test-cases), [RND-3](../specs/product/rounds.md#rnd-3-publish-a-round-to-beta-testers), [RND-5](../specs/product/rounds.md#rnd-5-request-a-retest), [RND-6](../specs/product/rounds.md#rnd-6-close-a-round)).

Since the [2026-10-30 review repair](#review-repair-2026-10-30-whimsyturtle), Playwright browser journeys in `src/e2e/` carry this coverage and the HTTP journey is deleted; the sections up to History record the earlier candidates.

Tier: Standard, test-only: no product code, criteria, security controls, dependencies or CI change. Base/branch: `a121d6e` / `26-test-coordinator-e2e`; main merged in at `6a79f31`. Owner: zheng-jj. The PR refers to #26 ("Refs #26") and does not close it: [RND-4](../specs/product/rounds.md#rnd-4-review-submitted-results) (results, unimplemented) is not covered, and [RND-8](../specs/product/rounds.md#rnd-8-draft-test-cases-with-ai) (AI test drafting, on this branch since #78 merged at `6a79f31`) is covered by its own tests, including `src/e2e/test_drafting.py`, not by this journey.

Size: the estimate was 220-300 lines in one test file. The first candidate exceeded it at about 420 lines; the repaired journey, with its form-reading helper and the added assertions, is about 516 lines, roughly 1.7 times the estimate. This is test code, so it does not count against the 400-line non-test slice budget.

## Scope and decisions

In scope: one journey test file driving only real HTTP routes in sequence with the Django test client. Out of scope: Playwright changes, new dependencies, service-layer setup, product or spec changes, and the exhaustive boundary, concurrency, security and rendering matrices already in `test_views.py`, `test_records.py`, `test_publish.py`, `test_retest.py`, `test_close.py`, `test_sample_round.py` and the accounts tests.

- **Division of work with `src/e2e/` (#81).** The Playwright suite covers browser rendering and interaction: `test_rounds.py` creates, adds a linked case and publishes through Chromium, and checks RND-2.6 and RND-3.3 refusals; `test_accounts.py` covers ACC-1 sign-in, sign-out and wrong-role navigation with fixture accounts. This HTTP journey keeps what those do not: demo-workspace creation and its credentials, sign-in with those credentials, round/criterion/case edits, two retests, closing, and the Open- and Closed-round 409 refusals, in one server-side sequence. It is not ported to Playwright.
- **File name.** Renamed from `test_coordinator_e2e.py` to `src/rounds/tests/test_coordinator_journey.py`, so it is not confused with the browser suite in `src/e2e/`; it stays with the rounds tests because most of what it asserts is RND behaviour. This plan keeps its name, `26-test-coordinator-e2e.md`, which matches the branch.
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

Coverage-only exception: the journey exercises implemented behaviour, so it passes on first run; its assertions are shown to detect defects by mutation. The first candidate's evidence (mutations A-E: publish and record Draft guards removed, retest covering every case, publish text changed, retest changing case steps; each failed the journey and was restored byte-for-byte; afterwards `59 passed` once stale `__pycache__` was removed) applies to that candidate only. Repair CSRF mutations, each run after removing `src/**/__pycache__`, against the journey and against a throwaway copy without `submit`'s token precheck; each template was then restored and `cmp` reported it identical:

1. `round.html`, token removed from the close form only: the journey failed at the close submission with "form has no CSRF token" (`1 failed`); the copy got `403` instead of `302` (`1 failed`), showing the server rejects the tokenless close.
2. `round_form.html`, token made conditional on `button != "Request retest"`, so only the retest form lost it: the journey failed at the first retest submission with "form has no CSRF token" (`1 failed`); the copy got `403` instead of `302` (`1 failed`), showing the server rejects the tokenless retest.

The repaired journey then passed (`1 passed`), and with the modules it imports helpers from gave `29 passed`.

## Commit checkpoints

1. `0c9327f` plan: record the coordinator end-to-end coverage.
2. `fb402d1` test: the journey test.
3. `ccb0553` test: narrow the criterion marks.
4. `6e5bf9b` test: assert retests preserve case content.
5. `922a8d4` chore: merge main (#81 Playwright journeys and deployment work).
6. `5d9aad4` plan: record the review repairs, division with `src/e2e/`, overclaim fixes and history. Check: `git diff --check`; read back.
7. `0aeb49b` test: rename to `test_coordinator_journey.py`; CSRF-enforcing form submissions; unchanged-title and unchanged-page checks after refusals; shared helpers; readable lookups; the step 6, 7, 9 and 11 assertions; comment and docstring fixes. Checks: the focused commands below and the CSRF mutations.
8. `e3d6a12` test and `dad9d6d` plan, repair round 2: a readable workspace-name assertion, sign-in fetched without a misleading `next`, a tidier close-form string, and this plan's size, evidence and next step.
9. Merges: `f1dc15d` (#87's branch), then `origin/main` at `50f2a61` (#89), `2b9f1cb` (#77), `b80cf93` (#92) and `6a79f31` (#78).
10. `fb2294f` plan and `d982e56` test, the [review repair](#review-repair-2026-10-30-whimsyturtle). The coordinator committed the plan entry before the tests it records.
11. Review repair round 1 (`test:` and `plan:`), below.

## Focused checks

With `.venv` active, from the repository root:

- `pytest -q -p no:cacheprovider src/e2e/test_round_lifecycle.py src/e2e/test_accounts.py src/e2e/test_rounds.py`
- `ruff check src/e2e && ruff format --check src/e2e`
- Full verification is run by the coordinator: `ruff check . && ruff format --check . && pytest`

## History

- The first candidate (checkpoints 1-4) was produced in a DeepSeek workflow experiment. Its builder ran as Codex role "default", not the builder adapter, although its handback says "Agent: builder".
- An independent review then found: CSRF disabled with hand-built POSTs (M1), undocumented overlap with #81 (M2), an overclaim to close #26 (M3), plan overclaims at steps 6-9 and 11 and a wrong step 8 tag (L4), no unchanged-title checks after refusals (L5), duplicated helpers (L6), `ValueError` lookups and a single-line `current_build` (L7), comments naming unmarked criteria (L8), an unrecorded size overrun (L9), stale checkpoints (L10) and the role record (L12). The human decided on 2026-10-29 to repair and keep the HTTP journey; checkpoints 6 and 7 carry that repair.
- The independent re-verification of `922a8d4..0aeb49b` passed the repair and left only Low findings, which checkpoint 8 (repair round 2, the last allowed) fixes.

## Review repair (2026-10-30, Whimsyturtle)

On `6a79f31` (`origin/main` with #78 merged in). Inline comment on `src/rounds/tests/test_coordinator_journey.py` line 39, where its `HTMLParser` form reader starts: "Same issue as #78, I feel like this is reinventing the wheel, can't we use existing Playwright functionality?" Human decision (2026-10-30): the same fix as #78. Rewrite the journey as Playwright tests in `src/e2e/`, delete the parser and the Django-client file, keep the criteria it proves, don't duplicate the existing create, add and publish journey, and add no dependency.

- **Changed:** `src/rounds/tests/test_coordinator_journey.py` deleted.
  - `src/e2e/test_accounts.py` gains `test_demo_workspace_credentials_sign_in_to_coordinator_home` (ACC-2.1, ACC-1.1). Chromium creates a demo workspace from the start page and sees the heading, credential table (Test Coordinator, then two Beta Testers) and save warning. A second tab is sent to sign in, so the visitor stays signed out. It then signs in with the shown coordinator credentials and sees the Coordinator home with the workspace, username and the Sample round in Draft.
  - New `src/e2e/test_round_lifecycle.py`, `test_coordinator_edits_retests_twice_and_closes_round` (RND-1.2, 5.1, 5.5, 6.1 to 6.3). A `browser_accounts` override creates a Draft round with two criteria and two linked cases before Playwright starts. The browser retitles the round (checked on the round page and the Coordinator home) and edits a criterion and a case. It publishes, retests the first case twice, and checks each exact status message and which build is current for each case. It closes the round and checks that the content stays and no button remains. Stale tabs then get the exact 409 heading for publishing an Open round, and for closing, retesting and retitling a Closed one. After Playwright stops, the override checks the stored state, title, criteria, case fields and links, and each build's coverage.
- **Division of work with `src/e2e/`:** `test_rounds.py` keeps creating, adding and publishing (RND-1.1, 2.1, 2.2, 3.1, already marked there). `test_accounts.py` keeps ACC-1 sign-in with fixture accounts. `test_tester.py` (RES-1) and `test_results.py` (RES-1, RES-2) already retest and close through the coordinator's forms, including 409s for stale retest and close forms, but they assert what testers see and their results. The new tests cover what the HTTP journey added: demo credentials, edits, and the coordinator's RND-5 and RND-6 view, which no other browser test asserts. That view is the retest form's contents, the exact retest and close messages, each case's current build after two retests of one case, the close warning and removed controls, and the Closed-round refusals and stored state. Detailed markup, order and cache-header checks stay in the server-side tests (`test_views.py`, `test_publish.py`, `test_retest.py`, `test_close.py`, `test_demo_views.py`).
- **Evidence:** each file was copied to the scratchpad, broken, run, then restored, and `cmp` reported it identical.
  - `rounds/views.py` close flash changed to `"Round closed!"`: `pytest -q -p no:cacheprovider src/e2e/test_round_lifecycle.py` gave `1 failed`, "Locator expected to have text 'Round closed.'".
  - `rounds/services.py` `request_retest` covering every case: the same command gave `1 failed`; `get_by_text("Synthetic build 1.0")` expected count 2 and got 1, because the second case lost its current build.
  - `accounts/views.py` `create_demo` signing the coordinator in: `pytest -q -p no:cacheprovider src/e2e/test_accounts.py -k demo` gave `1 failed`; the second tab stayed on `/coordinator/` instead of `/sign-in/`.
- **Checks:** focused `pytest -q -p no:cacheprovider src/e2e/test_round_lifecycle.py src/e2e/test_accounts.py`: 7 passed. Full, without `TOX_PARALLEL_ENV`: `manage.py check` and `makemigrations --check --dry-run` (test settings) clean; `ruff check .` and `ruff format --check .` clean; `pytest -q -p no:cacheprovider`: 2099 passed and 231 subtests. `check_scope.py builder --base 6a79f31` clean.
- **Size:** non-test `src/` is 0. All files, `6a79f31` to the candidate: 271 insertions (250 test, 21 plan), plus the mandated 518-line deletion and 4 plan deletions, 793 in total. The coordinator's ~600-line stop guards against growth, so it is counted on insertions; the deletion is what the human decision requires (coordinator, 2026-10-30).
- **Open:** `TECHNICAL-SPEC.md`'s Browser verification still says "the four selected journeys … are in slice 80's plan", which was already stale before this repair (`test_tester.py`, `test_results.py` and `test_drafting.py` are additional). It is left unchanged here, by the coordinator's direction.

### Round 1 (2026-10-30)

On `d982e56`. The verifier found nothing High and no lost coverage; all its findings are fixed in `src/e2e/test_round_lifecycle.py` and this plan.

- **L1:** build labels were counted page-wide, so swapping the two cases' current builds passed. `expect_builds` now reads each case's own "Current build" paragraph. Red: with `show_round` swapping the two cases' current builds for display only, `d982e56`'s test passed and the new one failed ("expected to have text 'Synthetic build 1.1'", actual `Synthetic build 1.0`).
- **L2:** a local `sign_in_coordinator` replaces the import from `test_rounds`.
- **L3:** `stale_tab` waits for the tab's heading before the next state change.
- **L4:** the stale-form refusals assert status 409 through `expect_response`, as `test_results.py` does. Red: with `state_conflict` returning 200 for POSTs (409 for GETs), `d982e56`'s test passed and the new one failed (`assert 200 == 409`).
- **M1, L5, L6, I1, I2:** checkpoints completed with hashes and the commit-order note; `6a79f31` and RND-8 status in the header and next step; `test_tester.py` and `test_results.py` in the division of work; the focused command now matches the recorded run.
- Each broken variant ran with a temporary copy of `d982e56`'s test beside the new one; `views.py` was restored and `cmp` reported it identical, and the copy was deleted.
- **Checks:** focused `pytest -q -p no:cacheprovider src/e2e/test_round_lifecycle.py src/e2e/test_accounts.py src/e2e/test_rounds.py`: 11 passed. Full, without `TOX_PARALLEL_ENV`: `manage.py check` and `makemigrations --check --dry-run` (test settings) clean; `ruff check .` and `ruff format --check .` clean; `pytest -q -p no:cacheprovider`: 2099 passed and 231 subtests. `check_scope.py builder --base d982e56` clean.
- **Size:** `git diff --numstat 6a79f31` after this round: 301 insertions (262 test, 39 plan), plus the mandated 518-line deletion and 6 plan deletions, 825 in total; non-test `src/` is 0. This round alone (`git diff --numstat d982e56`): 88 lines, 62 test (37 insertions plus 25 deletions) and 26 plan (21 plus 5).

## Next step

After the review repair is committed and passes full verification, the slice is complete. The draft PR (#79) refers to #26 with "Refs #26"; the humans decide on review and merge. #26 stays open for RND-4 coverage, to be planned when RND-4 is on main. RND-8 is on main with its own browser test, so whether #26 needs more for it is for the humans.
