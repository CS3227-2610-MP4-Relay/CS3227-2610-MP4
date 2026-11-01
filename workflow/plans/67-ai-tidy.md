# AI tidy (#67)

Remove duplicated checks, constants and parsing helpers in `src/ai/` without changing any message, log code, status code, gateway call or sensitive-variable coverage.

## Scope and decisions

- High tier: AI input/output paths, the gateway's configuration and exception mapping, and sensitive-variable marking. Base `045c33c` (main), branch `67-ai-tidy`. Behaviour-preserving refactor under existing criteria; no spec, criterion or template change. Budget: under 400 changed lines (the sweep's estimate of about 115 non-test source lines was the coordinator's brief, not a human-confirmed figure). Actual non-test source size: +117/−148 at `2025e81`; +126/−149 after review round 1, under the budget. `src/rounds/` gains only one constant (`services.py`); the rounds-tidy slice owns the rest of that app.
- **F1 adopt.** `coordinator_view` already applies `never_cache` outermost, so the two inner `@never_cache` decorators in `ai/views.py` and their import go.
- **F2 adopt.** `DraftSelectForm` subclasses `rounds.forms.RecordForm` (import only) and declares `invalid_choice`/`invalid_pk_value` as `services.FOREIGN` on the field, as `CaseForm` does; `views._form` and `drafting.FOREIGN` go; the docstring names only the selection page. The field stays optional, so the form's messages are unchanged: "Choose criteria from this round." for a foreign or malformed ID, Django's list message otherwise; RND-8.3's count message stays in the view.
- **F3 adopt.** `services.CASE_LIMIT_MESSAGE`, built from `CASE_LIMIT`, used by `add_case` and the drafting view; `drafting.MAX_CRITERIA = 5`, used by the view and by `SELECT`'s text, which stays "Select 1 to 5 acceptance criteria.".
- **F4 adopt.** `_suggest(user, selected)` returns `(drafts, error)` with early returns, under `@sensitive_variables()` (every local hidden, a superset of the names `draft_page` lists today); covered criteria are sorted once per draft. `draft_page` keeps `sensitive_post_parameters` and lists its remaining locals. Test change: `test_error_reports_hide_covered_criterion_text` pins the `ai/views.py` frames to `["draft_page", "_suggest"]` instead of `["draft_page"]`; it still proves the exception passes through exactly those frames and that neither frame's variables show the criterion text.
- **F5 adopt.** One `drafting.load_reply(reply)` (under `@sensitive_variables()`) decodes strictly, raising `InvalidReply("repeated-key")` for a repeated key and `InvalidReply("json")` for a constant, a parse error or `RecursionError`; both parsers use it. The dead `except InvalidReply: raise` goes (confirmed: `InvalidReply` subclasses `Exception`, not `ValueError`). The gateway keeps its own `ValueError` hooks (importing drafting would be circular). New guard cases pin the `repeated-key` and `json` codes for both parsers.
- **F6 adopt.** `clean` drops the explicit U+D800-DFFF test, because category `Cs` is exactly those 2048 code points; `_invalid_numeric` becomes `_nonfinite_or_surrogate`, still raising code `surrogate`.
- **F7 adopt.** `gateway._configured()` (sensitive; private because it returns the raw key, renamed from `configured()` in review round 1) returns `(url, model, api_key)` or `None`, using `_endpoint()` and the existing key checks; `_transport` (marking `config`) and the operator command use it, so the command reads no setting itself. Refusal codes and the fixed preflight message are unchanged; the command tests set the same environment variables.
- **F8 adopt.** The `(aiohttp.ClientError, OSError, ValueError)` clause goes; a comment on the catch-all names what it covers. `TimeoutError` and `_ResponseTooLarge` stay first.
- **F13 adopt.** `ai/__init__.py` and `apps.py` docstrings name the gateway, drafting (RND-8), observation feedback (RES-4) and injection evaluation (SEC-INJ-1).

## Commit checkpoints

1. [x] **Plan:** this file (`85d5c4c`). Checks: readback, `git diff --check`, builder scope.
2. [x] **Views and forms (F1-F4, F13)** (`32a5359`) — `refactor:`; `src/ai/{views,forms,drafting,__init__,apps}.py`, `src/rounds/services.py` (one constant), the one `test_views.py` frame assertion. Guards: `src/ai/tests/test_views.py`, `src/rounds/tests/{test_routes,test_records,test_record_services}.py`, `src/relay/tests/test_access_matrix.py`, e2e `test_drafting.py`.
3. [x] **Parsers, gateway, command (F5-F8)** (`f7fda6f`) — `refactor:`; `src/ai/{drafting,feedback,gateway}.py`, `src/ai/management/commands/evaluate_injection.py`, new code cases in `test_drafting.py`/`test_feedback.py`. Guards: `src/ai/tests/{test_drafting,test_feedback,test_feedback_views,test_gateway,test_transport,test_evaluation,test_evaluation_command}.py`, e2e `test_feedback.py`.
4. [ ] **Review and PR:** independent review of the final candidate, then the coordinator marks the draft PR ready.

Each implementation checkpoint: ruff check/format, focused tests, collection compared with the 2703-test baseline, then the mutations below, restored from a copy and confirmed with `cmp`.

## Mutations (each must fail a guard, then be restored)

- F1: drop `never_cache` from `coordinator_view` (`test_every_ai_route_is_never_cached`).
- F2: drop the field's `error_messages` (RND-8.8 view tests); return all criteria from `RecordForm`'s queryset (foreign-criterion tests).
- F3: change `CASE_LIMIT_MESSAGE` text; set `MAX_CRITERIA = 4` (RND-8.3 tests).
- F4: remove `_suggest`'s `@sensitive_variables()` (frame test); sort covered criteria in reverse (RND-8.1 order test).
- F5: let the key hook accept repeats, then make the constant hook return the value (code cases).
- F6: drop `Cs` from `clean` (`test_clean_removes_null_and_surrogates`).
- F7: drop the key's printable check in `_configured()` (gateway and command not-configured tests); let the command pass a missing configuration (preflight test).
- F8: map the catch-all to another code (transport exception tests).

## Status

- Existing passing tests are the regression evidence; a refactor has no missing behaviour to show red, so mutations stand in for red evidence.
- Checkpoint 2: guards 946 passed (e2e included); all 8 mutations failed a guard and were restored.
- Checkpoint 3: guards 588 passed (e2e included); 7 new code cases (2 drafting, 5 feedback; collection 2710). Mutations F5 (repeat accepted, constant accepted, `repeated-key` reported as `json`), F6 (both), F7 (both) and F8 failed a guard and were restored. Removing `load_reply`'s `@sensitive_variables()` fails no test. For feedback the marking keeps the old level, because the decode used to run inside the marked `feedback.parse` frame; for drafting it is added, because `drafting.parse` is unmarked. It is defence in depth, not a pinned control.
- Full verification on the integrated candidate: `ruff check .` and `ruff format --check .` clean; `pytest` 2710 passed, 231 subtests passed.

## Review round 1 (`045c33c..2025e81`)

- Verifier: 0 High, 0 Medium, 3 Low, 5 Nit, 3 Info. Security reviewer: 0 High, 0 Medium, 0 Low, 1 Nit, 4 Info.
- Fixed: `configured()` renamed `_configured()` (security Nit); `load_reply`'s marking described accurately above (security Info, verifier Info 9); `MAX_CRITERIA` comment names RND-8.3 and the copies of "1 to 5" in `ai/draft.html` and `src/e2e/test_rounds.py` (Nit 5); `_suggest` docstring (Nit 6); `drafting` module docstring names the shared loader (Nit 7); the feedback recursion test patches `drafting.json.loads` (Nit 8); plan commits, size, lessons and this record (Low 1-3, Nit 4).
- Not adopted: verifier Info 10, non-finite numbers in a drafting reply report code `surrogate`; unchanged in a behaviour-preserving slice.
- Open: security Info, `_endpoint()` can raise `ValueError` (from `urlsplit`) where `_transport` calls it, outside its `try`; pre-existing and unchanged here.
- Evidence: focused `test_gateway`, `test_transport`, `test_evaluation_command`, `test_feedback`, `test_drafting`, `test_views` 570 passed. Full verification after the repair: ruff clean; `pytest` 2710 passed, 231 subtests passed. Mutation: `load_reply` no longer maps `RecursionError` makes `test_parser_recursion_failure_is_fixed_invalid_reply` fail; restored. Base check: with `drafting.py` and `feedback.py` temporarily replaced by their `045c33c` text (restored, hashes matched), the 7 new cases and both recursion tests pass, so the new cases describe the old behaviour.

## Lessons

- Checkpoint 3 (`f7fda6f`) bundled the parser change (F5, F6) with the gateway and command change (F7, F8), and `32a5359` bundled the F13 docstrings with the view refactor; separate commits per purpose would have been easier to review.
- Agent runs, models and usage are recorded in the coordinator's session log, not in this plan.

## Next

- Item 4: the coordinator's review of this repair, then the PR.
