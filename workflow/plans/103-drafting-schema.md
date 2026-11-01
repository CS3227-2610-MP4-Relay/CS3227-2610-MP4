# Slice 103: drafting reply schema

Goal: make live test drafting replies conform to the existing [drafting contract](../specs/ai/test-drafting.md#fixed-instructions) by supplying its schema in the fixed prompt.

Why: the current prompt refers to an unspecified reply schema and field limits; the reported live replies fail the existing strict validator, including the benign control.

## Scope and decisions

- High tier (AI prompt), starting at `7c777d287ea2910da450da26099efcedd4411219` on `slice/103-drafting-schema`. Existing RND-8.1/.4/.5/.6 cover this bug; no new product criterion.
- Small prompt-only fix, within the confirmed ceiling of 400 changed non-test source lines and one requirement. No new dependency, service, credential, capability or gateway transport extension; the strict validator stays unchanged.
- Builder owns this plan, `workflow/specs/ai/test-drafting.md`, `src/ai/drafting.py` and drafting regression tests. Only the coordinator changes Git/GitHub state and runs the existing live evaluation. No new UI journey or setup change is intended.
- Fixed wording and version live in the AI spec; tests check implementation parity and contract examples. Preserve all existing input/output limits and data/instruction separation.

## Commit checkpoints

1. **Spec and plan** — `spec: Supply the exact drafting reply contract (#103)` (`Agent: builder`; body begins `Why:`). Paths: AI spec and this plan. Define `drafting-2` before code, read back edited sections, run whitespace and builder scope checks, then yield for the coordinator's commit and fresh snapshot.
2. **Prompt and regressions** — `fix: Include the reply schema in drafting instructions (#103)` (`Agent: builder`). Paths: `src/ai/drafting.py`, `src/ai/tests/test_drafting.py`, directly relevant existing drafting tests if needed. First update exact spec/version parity and add prompt-example/empty-reply parser checks; capture meaningful failures before changing the constant. Cover observed wrong top keys, array steps, missing criteria labels and surrounding Markdown/prose with strict rejection tests, reusing existing partitions where sufficient. Check supplied numeric limits against model limits, prompt length against 2500 and existing serialized request boundaries. Rejection tests may already pass because the validator is deliberately unchanged. Then implement the fixed prompt, run focused tests/Ruff and full `ruff check . && ruff format --check . && pytest` in Git Bash with `.venv` active, and yield.

## Evidence and next step

- Trigger: coordinator's `/slice 103` builder assignment; supplied context includes collaborator issue findings, existing criteria, confirmed prompt-only option, budget and spec-first checkpoint. Effective model/effort and session telemetry are unavailable to the builder; coordinator collects related-session usage.
- Spec-before-code checkpoint: `d72c13353058edd70124b86309aa0c2960057934`. Implementation changes only the fixed prompt/version; the validator and gateway stay unchanged.
- Red evidence: `pytest src/ai/tests/test_drafting.py -q` with unique temporary/cache paths produced 4 failures and 65 passes before code changed: exact spec parity, missing JSON example, missing empty JSON and missing numeric limits. The explicit array-steps rejection already passed because the validator is unchanged.
- Focused green: drafting parser/prompt, drafting views and evaluation tests passed (144 tests, 4.75s); focused Ruff lint/format passed. Added prompt-size and maximum encoded selection checks are compatibility guards, not proof of model compliance; they preserve existing passing request-boundary coverage. Prompt length is 1755 characters.
- Criterion mapping: RND-8.1 → parser-accepted prompt example and existing drafting view/evaluation tests; RND-8.4 → parser-accepted empty reply and existing unavailable/empty view tests; RND-8.5 → exact version/spec parity, numeric limits, malformed reply rejection (including array steps) and request size checks; RND-8.6 → existing cleaning/injection partitions plus encoded selection checks. Existing tests retain their acceptance markers and expectations.
- Integrated command, in Git Bash: `source .venv/Scripts/activate && ruff check . && ruff format --check . && pytest --basetemp="$TEMP/relay-103-builder-full" -o cache_dir="$TEMP/relay-103-pytest-cache"`. Ruff passed; format passed (127 files); pytest: **3 failed, 2564 passed, 1 skipped in 371.49s**, exit 1. All browser tests, including drafting, passed.
- Exact failures: `src/accounts/tests/test_limit_views.py::test_timeout_inside_a_limited_transaction_gives_503` for `[wrong password-idle]`, `[correct password-idle]`, `[demo-idle]`, each at line 564: `assert 'idle-in-transaction timeout' in caplog.text`. Actual log reports `consuming input failed: server closed the connection unexpectedly`; earlier unavailable/state assertions passed. These match the coordinator's warning about existing Windows idle-timeout assertions; no unrelated repair was made. Full verification is not claimed passing.
- Next: coordinator commits/freezes the candidate for independent verification/security review, hosted validation and the existing live evaluation. Record live schema acceptance separately from semantic usefulness and injection following; do not retain raw replies. No live effectiveness claim is made from static prompt checks.
- Open issues: live success remains unmeasured for the new wording. If it cannot satisfy the existing contract within this scope, report `needs-decision` before adding any mechanism.
