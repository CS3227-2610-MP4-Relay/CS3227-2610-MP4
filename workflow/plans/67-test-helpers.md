# Slice 67: Share duplicated test helpers (#67)

Goal: each test helper copied across modules has one home, no test imports from a `test_*` module, and three weak drafting-view tests are removed or strengthened, with no change to behaviour, specs or criteria.

Tier: Standard (tests only). Base: `045c33c` (main), branch `67-test-helpers`. Owner: zheng-jj. Budget: 0 lines of `src/` outside tests; no spec or criterion changes; no test weakened. A removed assertion names where it is still covered; every criterion ID stays marked somewhere.

Scope comes from the human's request to run #67 starting with a read-only sweep; this slice is the sweep's test-helper part. Out of scope: lifting cross-app account/round fixtures into `src/conftest.py`; the per-round `snapshot(round_)` helpers in `test_*_services.py` and `test_sample_round.py` (they compare one round, a different purpose).

## Decisions

Helpers go where the repository already shares them: plain functions in `src/rounds/tests/conftest.py`, imported by name (`from .conftest import ...`, or `from rounds.tests.conftest import ...` in `ai/tests`), as `csrf_token` and `signed_in` already are.

1. **`no_store(response)`**: the 7 copies all assert `"private"` and `"no-store"` in `Cache-Control`; they differ only in layout, so none is stricter. One copy in the rounds conftest; `test_history.py` stops importing it from `test_results.py`.
2. **`snapshot()`**: one rows-unchanged snapshot in the rounds conftest: every model of the `rounds` app (Round, Criterion, Case, CaseCriterion, Build, BuildCase, Result, read from the app registry so a new model is included), each `order_by("pk").values()`. It replaces `everything()` in `test_retest.py`, `test_records.py`, `test_record_ids.py`, `test_publish.py`, `test_direction_controls.py`, `test_close.py` (unordered `.values()`, and some omit Build, BuildCase or Result) and `snapshot()` in `test_tester.py` (omits Result) and `test_result_services.py` (imported by 3 ai and 3 rounds modules). Name `snapshot`, the clearer and already most-imported name; the `everything()` call sites are renamed. Each call site is checked to compare only `before == after` around a refused or read-only action, so a superset can only find more changes.
3. **`locked(round_)`**: the 4 copies in `test_retest_services.py`, `test_close_services.py`, `test_publish_services.py` and `test_record_services.py` are identical (`select_for_update().get(pk=...)`); one copy in the rounds conftest.
4. **Browser sign-in**: a `sign_in` fixture in `src/e2e/conftest.py` returns `sign_in(page, role="coordinator")`, bound to `browser_accounts`, filling the real form; it replaces `sign_in`/`sign_in_coordinator` in `test_feedback.py`, `test_tester.py`, `test_results.py`, `test_review.py`, `test_rounds.py`, `test_round_lifecycle.py` and the inline copy in `test_drafting.py`. It takes `page` because some journeys sign in on separate contexts. `test_accounts.py`'s `submit_sign_in(page, username, password)` stays: sign-in with chosen credentials is what that module tests.
5. **`probe`**: moves from `relay/tests/test_configuration.py` to a new non-test module `src/relay/tests/probes.py` beside `settings_probe.py` (not into `settings_probe.py`, which is the script `probe` runs). `test_configuration.py`, `accounts/tests/test_models.py` and `rounds/tests/test_framing.py` import it from there. After items 1, 2 and 5, `grep -rn "from .*test_[a-z_]* import" src` finds nothing.
6. **Delete `test_foreign_origin_and_missing_token_are_refused`** (`ai/tests/test_views.py`): its client has no CSRF cookie, so it gets 403 without the foreign Origin being checked. Covered by `test_posts_need_a_token_and_this_sites_origin` (both routes, missing token and foreign Origin with a valid token, no gateway call; marked RND-8.7) and the access matrix's `NO_TOKEN`/`BAD_ORIGIN` kinds for `ai:draft` and `ai:use-draft`.
7. **Delete `test_use_draft_requires_coordinator`**: checks only a tester's 403 on `ai:use-draft`. Covered by `test_a_beta_tester_is_forbidden_on_both_routes` (GET and POST draft, POST use-draft, all 403, no gateway call; marked RND-8.7).
8. **Strengthen `test_storage_error_from_the_gateway_gives_503`**: also assert the page shows "Relay is temporarily unavailable. Try again later." (`relay/templates/503.html`) and that `snapshot()` is unchanged.
9. **Small duplicates**: `title_tag` (`test_rendering.py`, `test_review.py`) and `assert_no_raw_markup` (`test_rendering.py`, `test_record_rendering.py`) move to the rounds conftest beside `MARKUP`, `SCRIPT_TAG` and `IMG_TAG`. `csrf_client` (`accounts/tests/test_demo_views.py` loads `/`, `test_sign_in.py` loads `/sign-in/`) becomes one `csrf_client(path)` in a new `src/accounts/tests/conftest.py`, each caller passing its page, so neither test changes what it loads.

## Checkpoints

1. **Plan** (`plan:`): this file. Check: `git diff --check`.
2. **Shared rounds, ai, relay and accounts helpers** (`test:`), items 1, 2, 3, 5 and 9: `src/rounds/tests/conftest.py`, the rounds and ai modules named above, `src/relay/tests/probes.py`, `src/relay/tests/test_configuration.py`, `src/accounts/tests/{conftest,test_models,test_demo_views,test_sign_in}.py`. Mutation: a temporary service change that writes a `BuildCase` or `Result` row on a refused action fails a test that the old helper passed; restored and confirmed with `git diff --exit-code`.
3. **Browser sign-in fixture** (`test:`), item 4: `src/e2e/conftest.py` and the 7 e2e modules. Run every changed e2e module in Chromium.
4. **Drafting view tests** (`test:`), items 6 to 8: `src/ai/tests/test_views.py`. Item 8's new assertions fail when the 503 page text is changed in a temporary copy.

Checks at each code checkpoint: `pytest -q -p no:randomly` on every changed module and every module whose imports changed; `ruff check` and `ruff format --check` on changed files; `git diff --check`; test counts per changed module before and after (`pytest --collect-only -q <path> | tail -1`). Full verification on the final candidate.

Collected at base: rounds `test_retest` 74, `test_results` 69, `test_records` 125, `test_publish` 49, `test_close` 28, `test_review` 53, `test_history` 24, `test_record_ids` 18, `test_direction_controls` 83, `test_tester` 59, `test_result_services` 23, `test_retest_services` 34, `test_close_services` 5, `test_publish_services` 23, `test_record_services` 20, `test_rendering` 19, `test_record_rendering` 7, `test_framing` 13; ai `test_feedback_views` 58, `test_views` 56, `test_evaluation_command` 12; accounts `test_models` 15, `test_demo_views` 19, `test_sign_in` 61; relay `test_configuration` 59; e2e `test_accounts` 6, `test_drafting` 1, `test_feedback` 2, `test_results` 3, `test_review` 1, `test_round_lifecycle` 1, `test_rounds` 4, `test_tester` 1. Expected after: unchanged except ai `test_views` 54.

## Open issues

- None.

## Checklist

- [ ] Checkpoint 1: plan.
- [ ] Checkpoint 2: shared helpers.
- [ ] Checkpoint 3: browser sign-in fixture.
- [ ] Checkpoint 4: drafting view tests.
