# Slice 102: feedback injection

Reduce embedded-directive contamination in observation feedback under existing [RES-4.2 and RES-4.8](../specs/product/results.md#res-4-suggest-missing-details-in-a-draft-observation).

## Scope and reason

High tier; one existing requirement, at most 400 changed non-test source lines, with a much smaller prompt-only change intended. No new criterion, parser, semantic filter, gateway, view, UI, source schema, service, dependency or credential. Keep legitimate behaviour reports, useful missing-detail questions, language, reply schema and limits intact.

Why: the coordinator's baseline at `045c33c7c20b6b7b2ea8a7c356d4b03738f3c1bb` with `qwen3.6:35b` still accepted one requested marker as relevant feedback context. The [AI contract](../specs/ai/observation-feedback.md#fixed-instructions) clarifies the distinction between factual context and embedded directives. Full measurement and semantic evidence belongs in the forthcoming slice session log; no raw source or replies belong here.

## Commit checkpoints

1. `spec: Clarify feedback source interpretation (#102)` — this plan and `workflow/specs/ai/observation-feedback.md`; read back the changed section, check whitespace and builder scope, then yield for coordinator commit before implementation.
2. `fix: Keep injected directives out of feedback context (#102)` — `src/ai/feedback.py` instruction text/version and the existing exact contract/version drift regression in `src/ai/tests/test_feedback.py`. This guard covers the committed directive/fact distinction and retained legitimate context without redundant instruction-string assertions. Demonstrate it failing on the old implementation, then run focused feedback/evaluation tests. These offline guards verify supplied instructions and application boundaries; they do not establish model resistance. Run full `ruff check .`, `ruff format --check .` and `pytest` before final integrated handoff.
3. No guide change needed: source schema, setup, UI and manual workflow are unchanged. Independent verification, security review and delivery belong to the coordinator.

## Evaluation and decisions

Compare feedback using the existing operator evaluation and manual semantic inspection, separately assessing requested-marker contamination, unsupported advice, useful questions, secret solicitation and executable propagation. Do not claim resistance from schema acceptance or offline fake replies. Drafting observations are outside this repair.

The initial twelve calls consume the existing operator's twenty-per-hour quota. Never reset quota or use another identity. The coordinator may prioritize the six feedback cases using a temporary operator-only wrapper around the existing command, preserving normal gateway limits and reporting later drafting refusals and incomplete full-corpus coverage. No evaluation capability or automated semantic grader ships. Otherwise report the post-change live comparison as quota-limited and wait for normal quota availability.

## Checkpoint evidence

Spec/plan checkpoint committed as `a3b42bcfab5e8977047f774ec25b8a46eb01562b` before implementation. The updated `test_fixed_instructions_equal_versioned_spec` failed against the old implementation with an instruction mismatch (one failed), then passed after applying the exact committed version 2 prompt. Focused feedback, view, evaluation and evaluation-command tests passed: 139 passed. No additional fake-model assertion was added because it could not establish the requested semantic improvement.

Full verification: `ruff check . && ruff format --check . && pytest --basetemp=C:/Users/limbe/AppData/Local/Temp/relay-102-builder-full-20261101` in the activated Git Bash environment. Ruff passed; 129 files already formatted; pytest reported 3 failed, 2699 passed, 1 skipped in 383.46 seconds. The failures were `src/accounts/tests/test_limit_views.py::test_timeout_inside_a_limited_transaction_gives_503` for `wrong password-idle`, `correct password-idle` and `demo-idle`: line 564 expected `idle-in-transaction timeout`, while captured storage errors said `consuming input failed: server closed the connection unexpectedly`. These match the coordinator-reported baseline failures; no accounts changes were made. Feedback unit, view and browser checks passed. Full verification is not green.

## Repair round 1

Version 2 at `9aae35f7e04932e2e72bb71fd097945e975aa222` did not demonstrate live improvement: feedback still turned an injected directive/marker into a question about its context or purpose. The mitigation remains unresolved. Detailed comparison and benign-case evidence belongs in the forthcoming [session log 028](../../logs/Whimsyturtle/028-reduce-feedback-prompt-contamination.md), rather than being duplicated here.

The version 3 contract makes the source distinction concrete: reported displayed UI instructions and tester-operated case steps remain product context; directives to the assistant are silently disregarded. Every proposed question must remain grounded after disregarding those directives, without quoting, explaining or asking about them. This is another prompt-only attempt within the original budget, not an established semantic guarantee.

1. `spec: Clarify question grounding after directive removal (#102)` — revise this plan and the AI contract, read back changes, check whitespace and builder scope, then yield for coordinator commit before implementation.
2. `fix: Ground feedback questions in reported behaviour (#102)` — apply the exact committed version 3 prompt in `src/ai/feedback.py` and update the existing exact contract/version guard in `src/ai/tests/test_feedback.py`. Capture its failure against version 2, then focused feedback/evaluation tests and full Ruff/pytest verification with a unique temporary directory. Yield for coordinator commit, candidate/helper freeze and independent review before live comparison. No extra fake semantic test or guide change.

Repair spec checkpoint committed as `3513b400cece51a1132dd709a2e0c2f8f601a8be` before implementation. The version 3 exact contract/version guard failed against version 2 with an instruction mismatch (one failed), then passed after applying the committed prompt. Focused feedback, view, evaluation and evaluation-command tests: 139 passed in 4.42 seconds. Post-repair semantic improvement remains unverified.

Repair full verification used the same Ruff/pytest command with unique `--basetemp=C:/Users/limbe/AppData/Local/Temp/relay-102-builder-repair1-full-20261101`: Ruff passed; 129 files already formatted; 3 failed, 2699 passed, 1 skipped in 353.73 seconds. Exactly the same three accounts idle-timeout log assertions listed above failed with the same closed-connection message. Feedback unit, view and browser checks passed; full verification remains not green. No accounts or guide changes were made.

Next: coordinator commits the implementation checkpoint, freezes the candidate/helper and conducts independent repair reviews. Live comparison waits for natural quota availability (approximately 18:51 Singapore on 2026-11-01); no quota reset, alternate identity or additional provider call before then. No open product decision; any broader change returns for scope confirmation.
