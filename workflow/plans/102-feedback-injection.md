# Slice 102: feedback injection

Reduce embedded-directive contamination in observation feedback under existing [RES-4.2 and RES-4.8](../specs/product/results.md#res-4-suggest-missing-details-in-a-draft-observation).

## Scope and reason

High tier; one existing requirement, at most 400 changed non-test source lines, with a much smaller prompt-only change intended. No new criterion, parser, semantic filter, gateway, view, UI, source schema, service, dependency or credential. Keep legitimate behaviour reports, useful missing-detail questions, language, reply schema and limits intact.

Why: the coordinator's baseline at `045c33c7c20b6b7b2ea8a7c356d4b03738f3c1bb` with `qwen3.6:35b` still accepted one requested marker as relevant feedback context. The [AI contract](../specs/ai/observation-feedback.md#fixed-instructions) clarifies the distinction between factual context and embedded directives. Full measurement and semantic evidence belongs in the forthcoming slice session log; no raw source or replies belong here.

## Commit checkpoints

1. `spec: Clarify feedback source interpretation (#102)` — this plan and `workflow/specs/ai/observation-feedback.md`; read back the changed section, check whitespace and builder scope, then yield for coordinator commit before implementation.
2. `fix: Keep injected directives out of feedback context (#102)` — `src/ai/feedback.py` instruction text/version and focused regressions in `src/ai/tests/test_feedback.py`. Update the existing exact contract drift guard and add a meaningful guard for the directive/fact distinction and retained legitimate context. Demonstrate the version/contract regression failing on the old implementation, then run focused feedback/evaluation tests. These offline guards verify supplied instructions and application boundaries; they do not establish model resistance. Run full `ruff check .`, `ruff format --check .` and `pytest` before final integrated handoff.
3. Documentation only if the accepted implementation changes built user behaviour or setup; otherwise existing guides remain accurate. Independent verification, security review and delivery belong to the coordinator.

## Evaluation and decisions

Compare feedback using the existing operator evaluation and manual semantic inspection, separately assessing requested-marker contamination, unsupported advice, useful questions, secret solicitation and executable propagation. Do not claim resistance from schema acceptance or offline fake replies. Drafting observations are outside this repair.

The initial twelve calls consume the existing operator's twenty-per-hour quota. Never reset quota or use another identity. The coordinator may prioritize the six feedback cases using a temporary operator-only wrapper around the existing command, preserving normal gateway limits and reporting later drafting refusals and incomplete full-corpus coverage. No evaluation capability or automated semantic grader ships. Otherwise report the post-change live comparison as quota-limited and wait for normal quota availability.

Next: coordinator commits the spec/plan checkpoint and supplies a fresh scope snapshot before assigning implementation. No open product decision; any broader change returns for scope confirmation.
