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
- Spec checkpoint candidate: only AI prompt wording/version and this plan; no implementation or tests changed yet. No live effectiveness claim is made from static prompt checks.
- Next: coordinator checks/commits the spec checkpoint, supplies a fresh scope snapshot, then assigns implementation. Independent verification/security review and coordinator-owned live evaluation follow the integrated candidate. Record live schema acceptance separately from semantic usefulness and injection following using the existing procedure; do not retain raw replies.
- Open issues: live success remains unmeasured for the new wording. If it cannot satisfy the existing contract within this scope, report `needs-decision` before adding any mechanism.
