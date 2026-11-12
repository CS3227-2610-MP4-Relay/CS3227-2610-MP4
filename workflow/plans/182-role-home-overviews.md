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

## Open issues

None.

## Next

Coordinator commits checkpoint 1, then the builder starts checkpoint 2.
