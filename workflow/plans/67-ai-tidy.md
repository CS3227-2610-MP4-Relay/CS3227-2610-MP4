# AI tidy (#67)

Remove duplicated checks, constants and parsing helpers in `src/ai/` without changing any message, log code, status code, gateway call or sensitive-variable coverage.

## Scope and decisions

- High tier: AI input/output paths, the gateway's configuration and exception mapping, and sensitive-variable marking. Base `045c33c` (main), branch `67-ai-tidy`. Behaviour-preserving refactor under existing criteria; no spec, criterion or template change. Budget: about 115 changed non-test source lines, well under 400. `src/rounds/` gains only one constant (`services.py`); the rounds-tidy slice owns the rest of that app.
- **F1 adopt.** `coordinator_view` already applies `never_cache` outermost, so the two inner `@never_cache` decorators in `ai/views.py` and their import go.
- **F2 adopt.** `DraftSelectForm` subclasses `rounds.forms.RecordForm` (import only) and declares `invalid_choice`/`invalid_pk_value` as `services.FOREIGN` on the field, as `CaseForm` does; `views._form` and `drafting.FOREIGN` go; the docstring names only the selection page. The field stays optional, so the form's messages are unchanged: "Choose criteria from this round." for a foreign or malformed ID, Django's list message otherwise; RND-8.3's count message stays in the view.
- **F3 adopt.** `services.CASE_LIMIT_MESSAGE`, built from `CASE_LIMIT`, used by `add_case` and the drafting view; `drafting.MAX_CRITERIA = 5`, used by the view and by `SELECT`'s text, which stays "Select 1 to 5 acceptance criteria.".
- **F4 adopt.** `_suggest(user, selected)` returns `(drafts, error)` with early returns, under `@sensitive_variables()` (every local hidden, a superset of the names `draft_page` lists today); covered criteria are sorted once per draft. `draft_page` keeps `sensitive_post_parameters` and lists its remaining locals. Test change: `test_error_reports_hide_covered_criterion_text` pins the `ai/views.py` frames to `["draft_page", "_suggest"]` instead of `["draft_page"]`; it still proves the exception passes through exactly those frames and that neither frame's variables show the criterion text.
- **F5 adopt.** One `drafting.load_reply(reply)` (under `@sensitive_variables()`, as `feedback.parse` is) decodes strictly, raising `InvalidReply("repeated-key")` for a repeated key and `InvalidReply("json")` for a constant, a parse error or `RecursionError`; both parsers use it. The dead `except InvalidReply: raise` goes (confirmed: `InvalidReply` subclasses `Exception`, not `ValueError`). The gateway keeps its own `ValueError` hooks (importing drafting would be circular). New guard cases pin the `repeated-key` and `json` codes for both parsers.
- **F6 adopt.** `clean` drops the explicit U+D800-DFFF test, because category `Cs` is exactly those 2048 code points; `_invalid_numeric` becomes `_nonfinite_or_surrogate`, still raising code `surrogate`.
- **F7 adopt.** `gateway.configured()` (sensitive) returns `(url, model, api_key)` or `None`, using `_endpoint()` and the existing key checks; `_transport` (marking `config`) and the operator command use it, so the command reads no setting itself. Refusal codes and the fixed preflight message are unchanged; the command tests set the same environment variables.
- **F8 adopt.** The `(aiohttp.ClientError, OSError, ValueError)` clause goes; a comment on the catch-all names what it covers. `TimeoutError` and `_ResponseTooLarge` stay first.
- **F13 adopt.** `ai/__init__.py` and `apps.py` docstrings name the gateway, drafting (RND-8), observation feedback (RES-4) and injection evaluation (SEC-INJ-1).

## Commit checkpoints

1. **Plan:** this file. Checks: readback, `git diff --check`, builder scope.
2. **Views and forms (F1-F4, F13)** — `refactor:`; `src/ai/{views,forms,drafting,__init__,apps}.py`, `src/rounds/services.py` (one constant), the one `test_views.py` frame assertion. Guards: `src/ai/tests/test_views.py`, `src/rounds/tests/{test_routes,test_records,test_record_services}.py`, `src/relay/tests/test_access_matrix.py`, e2e `test_drafting.py`.
3. **Parsers, gateway, command (F5-F8)** — `refactor:`; `src/ai/{drafting,feedback,gateway}.py`, `src/ai/management/commands/evaluate_injection.py`, new code cases in `test_drafting.py`/`test_feedback.py`. Guards: `src/ai/tests/{test_drafting,test_feedback,test_feedback_views,test_gateway,test_transport,test_evaluation,test_evaluation_command}.py`, e2e `test_feedback.py`.

Each implementation checkpoint: ruff check/format, focused tests, collection compared with the 2703-test baseline, then the mutations below, restored from a copy and confirmed with `cmp`.

## Mutations (each must fail a guard, then be restored)

- F1: drop `never_cache` from `coordinator_view` (`test_every_ai_route_is_never_cached`).
- F2: drop the field's `error_messages` (RND-8.8 view tests); return all criteria from `RecordForm`'s queryset (foreign-criterion tests).
- F3: change `CASE_LIMIT_MESSAGE` text; set `MAX_CRITERIA = 4` (RND-8.3 tests).
- F4: remove `_suggest`'s `@sensitive_variables()` (frame test); sort covered criteria in reverse (RND-8.1 order test).
- F5: let the key hook accept repeats, then make the constant hook return the value (code cases).
- F6: drop `Cs` from `clean` (`test_clean_removes_null_and_surrogates`).
- F7: drop the key's printable check in `configured()` (gateway and command not-configured tests).

## Status and next steps

- Existing passing tests are the regression evidence; a refactor has no missing behaviour to show red, so mutations stand in for red evidence.
- Database tests wait for the coordinator's go-ahead (shared test database). Full verification runs on the final candidate.
