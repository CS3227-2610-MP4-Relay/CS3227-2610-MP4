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

- The 30-case limit message is an inline f-string in `rounds/services.py` `add_case`, not a constant, so the view keeps its own copy. Sharing it needs a constant added to `src/rounds/services.py`, which another builder owns. This is left for the orchestrator.

## Progress

- Checkpoint 1: plan written.
