# #67 AI app cleanup

Goal: remove duplication, dead code and stale text in `src/ai` without changing product behaviour, messages, rejection codes or security controls.

Tier: High (AI input/output, gateway credential reading, sensitive-variable handling). Base: `ebd890c`. Branch: `67-ai-cleanup`. Budget: about 280 non-test `src/` lines, stop at 400. No spec, criterion, dependency or User Guide change: every item preserves behaviour.

Owned paths: `src/ai/**` except `src/ai/feedback_views.py` and `src/ai/templates/ai/feedback.html`. `src/rounds` is read-only (import only). Test-helper definitions (`no_store` etc.) belong to another builder; only add cases or change the patch targets/frames listed below.

## Confirmed items

- **R4 (shared strict reply loader).** `drafting.load(reply)` does the length check (`too-long`), the repeated-key hook (`repeated-key`) and the constant hook plus decode/recursion errors (`json`), under `@sensitive_variables()`; `drafting.parse` and `feedback.parse` call it. Delete feedback's `_object`/`_constant`, drafting's dead `except InvalidReply: raise` and the surrogate range test in `clean()` that repeats category `Cs`. Codes `too-long` and `repeated-key` are unpinned in both parsers, and `json` for a constant is unpinned in feedback: add those cases.
- **R3 (drafting view).** `drafting.labels(count)` and `drafting.encode(texts)` (the cleaned, labelled `{"criteria": [...]}` JSON, or `None` when nothing is left after cleaning) are used by `draft_page`, `evaluation.corpus` and `context_comparison.corpus`. A `_suggest(user, selected)` helper with its own `@sensitive_variables()` runs the gateway and parse with early returns and builds `covered` once (ordered by label, `ids` derived from it). `DraftSelectForm` declares its `FOREIGN` messages from `rounds.services`; `drafting.FOREIGN` goes. Drop the outer `@never_cache` on both views (`coordinator_view` applies it). Rename `drafting.UNKNOWN` to `UNAVAILABLE`. `ai.views` keeps `gateway` and `drafting` as module attributes.
  - Test change: `test_error_reports_hide_covered_criterion_text` can no longer trigger its `TypeError` by sorting an unknown label. It will make the patched `drafting.parse` raise, expect frames `["draft_page", "_suggest"]`, and still check that the secret text is absent; it must fail when `_suggest`'s `@sensitive_variables` is removed.
- **R5 (operator commands).** `gateway._configuration()` returns the endpoint, model and key, or `None` unless all are usable. `_transport` uses it, and public `gateway.configured_model()` returns only the model. A new `ai/experiments.py` holds `preflight(options, corpus, count, refusal)`, `show_response(stderr, case, result)` and `status(result)`, used by both commands and both `score` functions. Fixed texts unchanged. The commands still call `gateway.complete`, `evaluation.corpus` and `comparison.corpus` as module attributes, and `compare_context` keeps `import time`.
- **R6 (ai part).** Fix the docstrings in `ai/forms.py`, `ai/__init__.py` and `ai/apps.py`; delete the unused `gateway.USER_IN_FLIGHT` (a grep of src, docs and workflow/specs finds only its definition).

## Commit checkpoints

1. `plan:` this file.
2. R4: `src/ai/drafting.py`, `src/ai/feedback.py`, `src/ai/tests/test_drafting.py`, `src/ai/tests/test_feedback.py`. Checks: `src/ai/tests/` (dblock), plus a mutation of `load`.
3. R3: `src/ai/views.py`, `src/ai/forms.py`, `src/ai/drafting.py`, `src/ai/evaluation.py`, `src/ai/context_comparison.py`, `src/ai/tests/test_views.py`. Checks: `src/ai/tests/`, `src/e2e/test_drafting.py`, `src/e2e/test_feedback.py`, the frame-test mutation, plus one encoder mutation.
4. R5: `src/ai/gateway.py`, `src/ai/experiments.py` (new), both commands, `src/ai/evaluation.py`, `src/ai/context_comparison.py`. Checks: `src/ai/tests/`, plus mutations of the preflight and of `_configuration`.
5. R6: `src/ai/forms.py`, `src/ai/__init__.py`, `src/ai/apps.py`, `src/ai/gateway.py`. Checks: `ruff`, `src/ai/tests/`.
6. Final: full verification (base: 2857 passed, 254 subtests).

## Decisions and open items

- The 30-case limit message is an inline f-string in `rounds/services.py` `add_case`, not a constant. Decision (orchestrator, option a): the view keeps its own copy in this slice. Follow-up: add a constant in `rounds.services` and import it in `ai/views.py`, outside this PR.
- Follow-up (orchestrator agreed), not changed here: `gateway._envelope` keeps its own repeated-key and constant hooks. They raise `ValueError`, which maps to `Failed("invalid-response")`. Sharing them with `drafting.load` would make the gateway depend on a feature module.

## Progress

- Checkpoint 1: plan written (`ffd7ce2`).
- Checkpoint 2 (R4, `6e42f10`): `drafting.load` is shared, and feedback's hooks, the dead `except` and the redundant surrogate test are gone. Added code cases: drafting `repeated-key`/`too-long`; feedback `json` (NaN)/`repeated-key`/`too-long`/`surrogate`. `ruff check .` and `ruff format --check .` passed; dblock `pytest src/ai/tests/` gave 673 passed. Each mutation failed the expected test in both parsers: constant code `json`→`constant`, `object_pairs_hook=dict`, length check removed. Dropping `"Cs"` from `clean()` failed `test_clean_removes_null_and_surrogates`.
  - Rerun after the 2026-11-05 session restart: `dblock.py` was gone from the scratchpad, so I ran without it only the two DB-free modules `test_drafting.py` and `test_feedback.py` (135 passed), and all four mutations failed as before. With the wrapper restored and the test database restarted, dblock `pytest src/ai/tests/` gave 673 passed.
- Checkpoint 3 (R3): new `drafting.labels`/`drafting.encode`, used by `draft_page`, `evaluation.corpus` and `context_comparison.corpus` (same JSON). `_suggest` (`@sensitive_variables()`) uses early returns and builds `covered` once from the label order, with `ids` derived from it. `DraftSelectForm` declares the `rounds.services.FOREIGN` messages; `drafting.FOREIGN` and both outer `@never_cache` are gone; `UNKNOWN` is now `UNAVAILABLE`.
  - Test changes: `test_error_reports_hide_covered_criterion_text` now forces the exception with `drafting.parse(side_effect=TypeError)` and expects frames `["draft_page", "_suggest"]`, because the unknown-label sort it relied on is gone. New `test_data_part_labels_cleaned_text_in_order_without_ascii_escapes` (RND-8.6) covers a gap: `ensure_ascii=True` had survived all view and corpus tests.
  - Checks (dblock): `src/ai/tests/` 674 passed; `src/e2e/test_drafting.py` and `src/e2e/test_feedback.py` 17 passed; ruff clean.
  - Mutations, each failing the named test: no `@sensitive_variables` on `_suggest` → the frame test; no `.strip()` in `encode` → `test_all_empty_criteria_make_no_call`; `covered` ignoring reply labels → `test_each_draft_covers_exactly_its_labelled_criteria`; no form `error_messages` → four foreign-selection tests; `ensure_ascii=True` → the new encoder test.
  - Rerun after the 2026-11-05 reboot, through `/Users/zheng/Desktop/mp4/.r67/dblock.py`. The candidate hashes were unchanged and no mutation was left applied. Ruff was clean, `src/ai/tests/` gave 674 passed and the two e2e modules 17 passed. The frame-test mutation and the `ensure_ascii` mutation each failed their named test again.
