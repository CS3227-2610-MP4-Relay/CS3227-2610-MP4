# Shared LLM guards (#19)

Goal: close the existing shared result-boundary gaps under the [gateway contract](../specs/ai/llm-gateway.md), preserving the built transport and feature validators.

## Scope and decisions

- High tier; starting HEAD `48f7d5610e4e2e9d1c8d3207b1b7532da35eaa2a`, branch `slice/19-llm-guards`.
- Inspection: `_transport` already separates system instructions from unchanged source data, bounds request characters and response bytes, rejects unencodable requests before networking, and validates strict JSON/chat envelopes. Existing tests cover these controls. Feature authorization and structured-output validation remain in the features.
- Existing coverage: `test_input_over_limit_is_refused_before_a_call`, `test_an_unencodable_request_fails_before_the_network`, `test_chat_content_character_bound`, and `test_unsafe_chat_json_is_rejected_even_in_metadata` in `src/ai/tests/test_gateway.py`; `test_one_post_carries_separate_parts_and_bearer_key` and response-byte-cap cases in `src/ai/tests/test_transport.py`. These are inspected assertions, not test execution evidence for this checkpoint.
- Concrete repair: `complete()` currently accepts any `Success.text` and any `Refused.code`/`Failed.code` from an injected provider. This bypasses reply validation and permits provider text in outcome logs. Validate the result before logging/returning, reusing the existing text rule and fixed outcomes; retain quota/release and storage-error behaviour.
- Spec clarification only: the existing result and fixed-code rules apply at the test seam, with the existing malformed-result fallback. No new criterion, capability, dependency, service, credential, cache or input-normalization policy. Unencodable input keeps its existing transport-failure behaviour.
- Estimated total diff: 200–350 inserted/deleted lines including tests; 60–120 outside tests/migrations, within the 400-line source budget. At most one contract clarification. Stop and report before exceeding confirmed scope/budget.

## Commit checkpoints

1. **Plan/contract clarification** — `workflow/plans/19-llm-guards.md`, `workflow/specs/ai/llm-gateway.md`. Read changed sections back, check whitespace and builder scope; yield for coordinator commit before implementation. Why: document that injected results obey the shared boundary already promised by the contract.
2. **Result guards and regressions** — `src/ai/gateway.py`, `src/ai/tests/test_gateway.py` (transport tests only if necessary). First run focused new tests against unchanged code and record actual defect failures; then repair and rerun focused gateway/transport checks. Cover malformed success types, empty and ordinary text, reply limit minus one/at/plus one for BMP/non-BMP characters, surrogate text, valid fixed outcomes, unknown/non-string codes, fixed-only logs, and slot release/counting after invalid results. Reuse existing input/envelope/separation coverage; add combined input-length boundary coverage if inspection finds it missing. Mark relevant acceptance tests with existing RND-8 IDs. Keep tests and repair in one commit.
3. **Integrated validation/review** — run `.venv` Git Bash `ruff check . && ruff format --check . && pytest`; report actual results and criterion links. Update this plan with evidence and next steps before yielding the candidate. Docs only if setup or built user behaviour changes; none identified. Coordinator owns scope snapshots, independent High-tier reviews, commits and delivery.

## Checkpoint evidence and next step

- Trigger/context: coordinator's #19 first-checkpoint assignment; supplied gateway, fake-provider, gateway/transport tests and AI/resource security sections. Builder model configured as `gpt-6.1-sol`, medium; native run metadata unavailable.
- Reviewed candidate: starting HEAD above, with clean tree reported by coordinator and no source edits in this checkpoint. Read-only `git status --short` showed no changes before this plan/spec edit (Git emitted inaccessible global-ignore warnings).
- First checkpoint changes only this plan and the test-seam clarification. No code tests run yet; red-before-green belongs to checkpoint 2.
- Usage baseline/report are coordinator-owned outside the repository at `%TEMP%/relay-19-usage-before.json`; own usage is unavailable until the coordinator collects the final selected-source report. No retries or repair rounds in this checkpoint.
- Open decisions: none. Next: coordinator checks scope and commits checkpoint 1, then supplies a fresh snapshot and assigns checkpoint 2. This checkpoint does not complete the slice.
