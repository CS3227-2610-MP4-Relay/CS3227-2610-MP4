# Role home overviews (#182)

Goal: show counts and next actions on Coordinator home, Tester home and the tester round page, without new routes, models or capabilities.

Tier: Standard plus security-reviewer (new workspace- and tester-scoped queries). Base: `a93430a`. Branch `feat/182-role-home-overviews`.

## Human decisions (this session)

- One slice for the whole issue. The one-requirement budget is raised for this slice only to cover RND-1 and RES-1. Estimate 6–8 added/changed criteria and about 150–250 lines under `src/` outside tests and migrations; hard limit 400. Exceeding either returns as needs-decision.
- Coordinator home follows the approved preview: summary line of round counts by state and Beta Tester count, always shown; Draft rounds show their case count; Open rounds show current-build submitted coverage plus "Review results"; Closed entries unchanged. Eligible results are exactly RND-4's "Results for this build". No "reviewed" state.
- Tester home keeps "Available tests" and "No tests available.", grouping rounds under "Open tests" and "Closed tests", each only when non-empty, same order within each. Open rounds show the tester's own "to record · draft(s) · submitted" counts using one shared helper with the RES-1.5 links. The Open tester round page shows "Your result: …" in each case summary; the link stays in the body.
- No new routes, models, migrations, dependencies, JS or permissions.

Coordinator decisions (checkpoint 1 revision):

- Storage failure on Coordinator home keeps its existing accounts-route rule (generic 500, no partial content), as RND-1.11 states; accounts behaviour and the two `test_coordinator_home_*_keeps_the_accounts_storage_rule` tests stay unchanged.
- `platform.md` stays unchanged: PLT-4.9's "retains" is a minimum, not an exhaustive list, and editing it would touch a third requirement beyond the raised budget. RES-1 owns the "Your result" status.
- Eligibility is exactly RND-4's "Results for this build" selection (submitted, covered, current build, tester in the round's workspace; no role filter). The implementation extracts or reuses one helper shared by `results_page` and the overview, so the two cannot drift; RND-4's behaviour stays unchanged. The summary's Beta Tester count still counts users with the tester role in the workspace.
- RES-1.1's ordering is amended: Open rounds under "Open tests" before Closed rounds under "Closed tests", each newest first.

## Criteria

[RND-1.8 to RND-1.11](../specs/product/rounds.md#rnd-1-prepare-a-test-round) and [RES-1.9 to RES-1.12](../specs/product/results.md#res-1-see-the-tests-available-to-me) added, and [RES-1.1](../specs/product/results.md#res-1-see-the-tests-available-to-me) changed (9 total). The slice stays reviewable: the changed criterion is a one-clause ordering amendment, there are no new routes or models, and `src/` stays within the estimate. Supporting sentences are in the [technical spec](../specs/TECHNICAL-SPEC.md) (workspace helper, storage failure, tester routes) and the [security spec](../specs/SECURITY-SPEC.md#rounds-observations-and-history).

## Checkpoints

1. `spec:`/`plan:` — `workflow/specs/product/rounds.md`, `workflow/specs/product/results.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`, this plan. Check: read-back only.
2. `feat:` RND-1 overview — `src/accounts/views.py` (`coordinator_home`), `src/rounds/templates/rounds/coordinator_home.html`, one eligible-results helper in `src/rounds/results.py` used by both `results_page` (`src/rounds/views.py`, behaviour unchanged) and the overview; tests in `src/rounds/tests/test_views.py` (existing RND-4 tests must keep passing) and `src/e2e/test_rounds.py`. Focused: `pytest src/rounds/tests/test_views.py -k "coordinator_home"` red before, green after; then the e2e file.
3. `feat:` RES-1 progress — `src/rounds/tester.py` (one classification helper used by `detail` and `home`), `tester_home.html`, `tester_round.html`; tests in `src/rounds/tests/test_tester.py` and `src/e2e/test_tester.py`. Focused: `pytest src/rounds/tests/test_tester.py` red before, green after; then the e2e file.
4. `docs:` `docs/UserGuide.md` in the product's exact words. Then full verification (`ruff check . && ruff format --check . && pytest`).

Run pytest with `-p no:cacheprovider --basetemp=tmp/slice182-harness/<name>`.

## Checkpoint evidence

Every pytest run below used `--ds=slice182_settings` (harness-only module in ignored `tmp/slice182-harness/settings182/`, `PYTHONPATH` set to it): it imports `relay.settings.test` and changes only the test database to `test_relay_test_slice182`, because a concurrent runner held `test_relay_test` (coordinator-accepted). All runs used `-p no:cacheprovider --basetemp=tmp/slice182-harness/<name>`. Times are local, 2026-11-13.

Checkpoint 2 (RND-1, committed 8c1923f):

- Red 08:03:42–08:04:13, `src/rounds/tests/test_coordinator_overview.py`: 14 failed (no summary or overview paragraph; `listed_results` and `current_build_coverage` missing), 7 passed. The 7 are already-true guards: draft-changes-nothing, query parameters, four 405/no-store cases and the query count.
- Green 08:05:16–08:05:27, same file: 21 passed. First focused run 08:05:36–08:10:17: 1 failed, 1118 passed. The failure was `Count` dropping `Meta.ordering`, fixed by restating the ordering. Focused 08:12:39–08:15:29 (`test_views`, `test_review`, `test_results`, `test_coordinator_overview`, `test_rendering`, `test_sample_round`, `relay/tests/test_access_matrix`, `test_pending_drafts`): 1119 passed.
- e2e 08:15:37–08:16:50 (`test_rounds`, `test_accounts`, `test_round_lifecycle`): 17 passed. Ruff check and format clean; `check_scope.py builder --base 6385960`: within scope.
- Changed expectations, which asserted `(State)</li>` and now see RND-1.8's overview line: `test_rendering.py` (4, via `ZERO_CASES`), `test_views.py` (2), `test_sample_round.py` (`HOME_ITEM`), `e2e/test_accounts.py` and `e2e/test_round_lifecycle.py` (item text plus case count).

Checkpoint 3 (RES-1):

- Red 08:21:56–08:22:04, `src/rounds/tests/test_tester_progress.py`: 15 failed (no headings or count line, flat order, no status, home 200 instead of 503 when results reads fail), 13 passed. The 13 are already-true guards: Closed rounds without counts or status, empty and Draft-only headings, eight GET-only/no-store cases, detail 503 and the home query count.
- Green 08:22:49–08:23:05 (`test_tester_progress`, `test_tester`): 88 passed. Focused 08:24:18–08:28:51 (`test_tester`, `test_history`, `test_results`, `test_rendering`, `test_sample_round`, `relay/tests/test_access_matrix`, `test_tester_progress`): 1058 passed.
- e2e: first `test_tester.py` run at 08:29 had 1 failure, a test bug (the collapsed second case hid "Continue draft"); the test now expands it. Final 08:29:31–08:32:17 (`test_tester`, `test_results`, `test_navigation`): 15 passed.
- Ruff check and format clean (153 files); `check_scope.py builder --base 8c1923f`: within scope.
- Changed expectation: `test_tester.py::test_publish_and_close_change_next_request` also strips the Open-only "Your result: Not recorded" span before comparing the Open and Closed pages, and asserts the span is present on Open and absent on Closed. RES-1.9/1.10 add it to Open pages only.
- `src/` shortstat, excluding tests, migrations, e2e and conftest: against 8c1923f, 4 files changed, 63 insertions(+), 17 deletions(-); cumulative against a93430a, 9 files changed, 135 insertions(+), 23 deletions(-), about 158 of the 150–250 budget. New file: `src/rounds/tests/test_tester_progress.py`.
- Assumptions:
  - The home's `rounds` context is the Open group followed by the Closed group.
  - An Open case without a current build would count as "to record" with no status or link; RES-1.3 says none exists.
- Open: the stray idle REPL (PID 1054) from checkpoint 2 is with the human.

Checkpoint 4 (User Guide):

- `docs/UserGuide.md` (Coordinator home overview; "View available tests" groups, counts and "Your result" statuses; three alt texts) was read back. `pytest --ds=slice182_settings --basetemp=tmp/slice182-harness/cp4-shots src/e2e/screenshots.py` (08:39:24–08:40:00, 2 passed) is the only selection that produces `tester-home`/`tester-round`. It rewrote all 16 PNGs; `coordinator-home`, `tester-home` and `tester-round` were inspected and are correct. The other 13 differ only in system-font rendering (the committed set used a different font; `start-page` compared by eye) and random demo identities. Originals are in `tmp/slice182-harness/images-before/`; keeping only the three targets mixes fonts in the guide. Ruff clean; `check_scope.py builder --base 0b1b389` within scope; DeveloperGuide unchanged.
- Coordinator decision: commit only the three content-changed PNGs, as #143 did. The other 13 were restored byte-identical to HEAD (hash-checked) to avoid unreviewable churn; the font mix is cosmetic.

## Open issues

None.

## Next

Freeze the candidate, run full verification, then the verifier and security-reviewer.
