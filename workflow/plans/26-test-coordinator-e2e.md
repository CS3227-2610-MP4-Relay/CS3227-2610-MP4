# Slice 26: Test the Test Coordinator's features end to end (#26)

Goal: one HTTP-only journey proves a coordinator can create a demo workspace, sign in, prepare a round, publish it, retest a case and close it, with the shipped UI, state transitions and refusals ([RND-1](../specs/product/rounds.md#rnd-1-prepare-a-test-round), [RND-2](../specs/product/rounds.md#rnd-2-manage-acceptance-criteria-and-test-cases), [RND-3](../specs/product/rounds.md#rnd-3-publish-a-round-to-beta-testers), [RND-5](../specs/product/rounds.md#rnd-5-request-a-retest), [RND-6](../specs/product/rounds.md#rnd-6-close-a-round), [RND-7](../specs/product/rounds.md#rnd-7-sample-draft-round-in-a-new-demo-workspace), [ACC-2](../specs/product/accounts.md#acc-2-create-an-isolated-demo-workspace)).

Tier: Standard. This is test-only coverage of existing Standard/High behaviour; it changes no product code, criteria, security controls, dependencies or CI. Base/branch: `a121d6e` / `26-test-coordinator-e2e`. Owner: zheng-jj. Slice budget: no `src/` production change; expected about 220-300 lines in one test file (well inside the 400-line non-test budget, which this slice does not consume).

## Scope and decisions

In scope: one coherent journey test file using the existing pytest/Django test client conventions, driving only the real HTTP routes in sequence. Coverage is RND-1, RND-2, RND-3, RND-5, RND-6 and RND-7; RND-4 is excluded because RES results are unimplemented. Reuse `src/rounds/tests/conftest.py` helpers (`detail`, `page`, `signed_in`, `csrf_token`) and the account test patterns for `/demo/`, `/sign-in/` and credential rows.

Out of scope: Playwright, Selenium, browser harnesses, new dependencies, service-layer setup for the journey, duplicate exhaustive boundary/concurrency/security matrices already in `test_views.py`, `test_records.py`, `test_publish.py`, `test_retest.py`, `test_close.py` and `test_sample_round.py`, and any product or spec change. ACC-2/RND-7 coverage is limited to what the new demo workspace provides: credential display, coordinator sign-in, and observing the sample round.

Decisions:

- **One journey, staged reads:** POST actions assert exact `302` and `Location`; subsequent GETs assert the resulting observable UI. This follows the existing route tests and verifies persistence through pages rather than response-only state.
- **One small second journey for denial:** after publishing, attempt an edit and a publish to assert both are refused with `409` and the exact conflict heading. This keeps the happy journey readable while covering the required denied action. Closing is followed by a denied edit/publish/retest check on the Closed page/routes.
- **Stable assertions:** extract the new round's link from the Coordinator home, assert criterion/case text around their labels, and assert build coverage blocks per build. No internal service calls and no reliance on database IDs except route construction from the extracted link.
- **Exact text:** use the spec/template strings, including `Draft`, `Open`, `Closed`, success messages and conflict text exactly as rendered. Assert message counts where the spec says "once".
- **Sample round:** assert exactly one "Sample round (Draft)" is linked from the Coordinator home of the newly created workspace; do not duplicate RND-7's exhaustive 3-criteria/4-case tests.

## Test file

`src/rounds/tests/test_coordinator_e2e.py`

Suggested helpers (local to the file): credential-row parser, coordinator sign-in, coordinator-home round-link parser, round URL builder derived from the parsed link, and `assert_state(page, state)`. Mark the journey test and denial test with `pytest.mark.ac` for the criteria they directly exercise. Use `pytestmark = pytest.mark.django_db`, matching the rounds suite.

## Journey and criterion mapping

1. **Create a demo workspace and show credentials** (ACC-2.1, ACC-2.2; RND-7.1 minimal): GET `/`, assert the "Create a demo workspace" button is a POST to `/demo/`; POST `/demo/`; assert `200`, `Cache-Control: no-store`, title/heading "Your demo workspace", `Workspace: <name>`, the Role/Username/Password table, exactly Test Coordinator then two Beta Testers, the save-passwords warning and the `/sign-in/` link. Keep the coordinator credentials from the table.
2. **Sign in as its coordinator** (ACC-2.2): POST `/sign-in/` with the displayed coordinator username/password; assert `302` to `/coordinator/`; GET `/coordinator/`; assert title/heading "Coordinator home", the workspace name, and exactly the sample round link labelled "Sample round" with state "(Draft)" (RND-7.1 minimal, RND-7.2 context).
3. **Create a round** (RND-1.1): GET `/coordinator/rounds/new/`; assert "New round", Title field, "Create round". POST a synthetic title; assert `302` to the round URL derived from the Coordinator home or from the response `Location`; GET that URL and assert `<h1>` title, "State: Draft", "Edit round", "No acceptance criteria yet." and "No test cases yet."; GET `/coordinator/` and assert the title with "(Draft)" appears newest first.
4. **Add criteria** (RND-2.1): POST two criteria in sequence, asserting each `302` to the round page; GET the round page and assert both texts under "Acceptance criteria" in creation order, the Draft controls, and no "No acceptance criteria yet." Capture criterion IDs from the edit links.
5. **Add a case linked to criteria** (RND-2.2, RND-3.4 setup): GET the new-case page and assert Title/Steps/Expected result fields and both criterion checkboxes in creation order. POST a case with one or both criteria; assert `302` to the round page. GET and assert the case title heading, Steps, Expected result, and "Linked acceptance criteria" listing the linked criterion text(s), plus Draft edit/delete controls.
6. **Edit the round and a record** (RND-1.2, RND-2.3): GET the edit-round page and assert the current title prefilled and "Save"; POST a new title; assert `302`; GET the round page and Coordinator home to assert the new title. GET the criterion/case edit page and assert current values; POST an edited criterion text and an edited case expected result; assert each `302`, then GET the round page and assert the changed text with the original links preserved.
7. **Publish on a build** (RND-3.1): on the Draft round page assert the "Build label" field and "Publish round" button after the Test cases section. POST a synthetic label; assert `302` to the round page. GET and assert "Round published." once directly under the heading, "State: Open", each case's "Current build" and the same label, a "Builds" section with the build heading and "Covered test cases" naming the published cases, and absence of all Draft controls, publish form and "Edit round" link (RND-3.4: criteria/cases/links unchanged).
8. **Denied action after publication** (RND-3.6, RND-6.3 shared rule; also RND-1.7/RND-2.8 state refusal): POST the edit-round route and the publish route; assert both `409`, exact heading "This action is not available while the round is Open.", and no state/content change on a subsequent GET. Optionally GET the edit-round form and assert the same 409, demonstrating a form that state does not allow.
9. **Request a retest for a case** (RND-5.1, RND-5.5): GET the retest page from the Open round; assert title/heading "Request a retest", all cases listed unselected, "Build label" and "Request retest". POST one case and a new label; assert `302` to the round page. GET and assert the exact singular message "Retest requested for 1 test case on build <label>." once under the heading, the selected case's "Current build" changed to the new label while the other case keeps the published label, the original build remains listed covering its original case(s), and the new build lists only the selected case. Assert criteria/cases/links are unchanged.
10. **Verify current/earlier build coverage** (RND-5.1, RND-5.5): within the same GET, assert both builds in oldest-first order, the new build's coverage block, and the old build's coverage block. Optionally retest the same case again on a third label to assert earlier builds remain, but keep this to one extra action only if it does not obscure the primary journey.
11. **Close the round** (RND-6.1, RND-6.2): on the Open round page assert the warning "Closing makes this round read-only. It cannot be reopened." immediately before the "Close round" button. POST close; assert `302` to the round page. GET and assert "Round closed." once directly under the heading, "State: Closed", criteria/cases/builds still visible, and no Edit round, RND-2 controls, publish form, warning or Close button.
12. **Verify the Closed round is read-only** (RND-6.3, RND-6.5 shared rule; RND-2.8/RND-3.6/RND-5.8 state refusals): POST edit, publish, retest and a criterion/case edit/delete; assert `409` with the exact Closed conflict heading for each, and assert a subsequent GET still shows the same Closed content. This is the denied-action coverage for the terminal state.

If the journey becomes too long in one test, split only at the publish boundary into `test_coordinator_journey_draft_to_closed` and `test_coordinator_published_round_is_read_only`; both must use the same demo-workspace-to-published fixture built through HTTP. Prefer one journey plus denial checks.

## Red-first evidence plan

The journey exercises already-implemented behaviour, so a correct test is expected to pass immediately. Do not manufacture a product failure. Record the exception and prove detection with temporary mutations that are restored byte-for-byte (`cmp`), using an empty `PYTHONPYCACHEPREFIX`:

1. Add the test; expect it to pass against current code. Record that this is a coverage-only exception justified by the already-green criteria; do not present a missing-file error as meaningful red evidence.
2. Mutation A: make `publish_round` accept an Open round (or remove its state check); expect the post-publication denial assertion to fail (status not 409), then restore and confirm `cmp` clean.
3. Mutation B: make `close_round`/`record_form` skip the Closed state check; expect the Closed read-only assertion to fail, then restore and confirm `cmp` clean.
4. Mutation C: alter the retest coverage selection (e.g., cover every case instead of the selected case); expect the current-build/coverage assertion to fail, then restore and confirm `cmp` clean.
5. Mutation D: remove the success message or change its text; expect the exact-message assertion to fail, then restore and confirm `cmp` clean.

If any mutation also causes unrelated tests to fail, report that; do not weaken the journey. Reuse only passing evidence while the candidate and environment are unchanged.

## Commit checkpoints

1. **Plan** (`plan:`): this file. Check: `git diff --check`; read back headings/links.
2. **Journey test** (`test:`): `src/rounds/tests/test_coordinator_e2e.py`. Check: focused new file; focused affected rounds modules; Ruff check/format; `git diff --check`.
3. **Small repair** (only if the journey exposes a genuine existing defect or test-only helper issue): isolate the repair in its own commit with its regression assertion and evidence. No product behaviour change is expected; if a product defect or spec contradiction appears, stop and report it rather than changing product/spec.

## Focused checks

From the repository root with `.venv` active:

- `pytest -q src/rounds/tests/test_coordinator_e2e.py`
- `pytest -q src/rounds/tests/test_views.py src/rounds/tests/test_records.py src/rounds/tests/test_publish.py src/rounds/tests/test_retest.py src/rounds/tests/test_close.py src/rounds/tests/test_sample_round.py src/accounts/tests/test_demo_views.py src/accounts/tests/test_sign_in.py`
- `ruff check src/rounds/tests/test_coordinator_e2e.py && ruff format --check src/rounds/tests/test_coordinator_e2e.py`
- Final Standard verification (coordinator/integrated candidate): `ruff check . && ruff format --check . && pytest`

The focused command may use the configured test settings/database. Report exact results, including unavailable database checks.

## Ownership and handoff

Builder writes only `workflow/plans/26-test-coordinator-e2e.md` for this checkpoint, then the test file at checkpoint 2. No Git state changes. Coordinator commits and provides a fresh snapshot before the test checkpoint. Verifier is required by the Standard tier; security review is not triggered because this slice adds no login, permission, dependency, CI or product boundary.

## Open decisions

- Exact helper extraction points for round links, criteria IDs and build coverage: choose the most stable HTML labels during implementation; no spec decision needed.
- Whether to perform a second retest to show two earlier builds: optional; include only if it stays within the intended small test size.
- No spec conflict found. If implementation reveals one, stop with `needs-decision` and the exact criterion/observable mismatch.

## Next step

Coordinator reviews and commits this plan, then assigns checkpoint 2 with a fresh snapshot and the current base commit.
