# Investigate Codex token accounting (#83)

Goal: reproduce the four reported accounting cases with synthetic inputs and explain what the existing collector can and cannot establish.

Tier: High, conservatively, because this investigates development telemetry and control evidence. Base: `471a4f77c28d255574efbd2be0928d271fd111dc`; branch: `chore/83-token-accounting-investigation`. The human's `/slice 83` request authorizes normal slice delivery; merge and release remain human decisions.

Why: reported fork, continuation, discovery and unavailable-counter cases may affect interpretation of recorded task usage. Investigation evidence belongs in the experiment report; this plan tracks the work and its boundaries.

## Scope and decisions

- No product requirement, acceptance criterion, security-control or application behavior changes. Existing reporting semantics remain in [Token reporting](../README.md#token-reporting); relevant controls remain in [Development workflow](../specs/SECURITY-SPEC.md#development-workflow).
- Read `workflow/scripts/resource_usage.py`, its existing tests and relevant excerpts of historical logs `001`, `006`, `009` and `012` under `logs/Whimsyturtle/`. Historical text is contextual evidence, not a basis for recalculating session totals.
- Add only a deterministic synthetic reproduction helper and findings report. Do not change the collector, add runtime telemetry, export real transcripts, recalculate historical totals, add dependencies/services/credentials or broaden discovery.
- Budget: zero changed product requirements and zero changed `src/` lines; estimated total diff 400–600 lines across the plan, helper, experiment and session log. Stop affected work and seek a specific decision if the confirmed scope or estimate is exceeded.
- Builder owns this plan only. Coordinator owns `workflow/scripts/investigate_codex_usage.py`, `experiments/83-codex-token-accounting.md` and the summary log, because those paths are outside builder scope. Only the coordinator changes Git or GitHub state.
- Follow-up collector changes are options for separate confirmation. Do not add their acceptance criteria, implementation tasks or regression requirements here.

## Investigation questions and evidence boundaries

1. Can inherited cumulative events with rewritten timestamps cause fork overlap to be counted, and what warning or absence of warning does the current collector produce?
2. When a continuation changes session identity, does interval reporting retain a usable baseline, reject missing original identities or mark newly added history unavailable? Distinguish these input arrangements.
3. Which synthetic descendants does bounded discovery select, and which automatic-approval-shaped or other-directory sources are outside its ancestry/project/directory rules? Do not infer live client coverage from fixtures.
4. When an inactive selected source has no usage, what happens to a separately measurable session's counters and the aggregate? Distinguish an available session subtotal from an exact task total.

For each case, record fixture assumptions, expected arithmetic under those assumptions, observed collector output/warnings and the code path explaining the result. A synthetic reproduction proves the collector's response to those inputs; it does not establish undocumented Codex rollout semantics or occurrence frequency. The coordinator-supplied [official app-server documentation](https://learn.chatgpt.com/docs/app-server) is context only where it directly supports a statement, not a definition of private rollout accounting.

Keep fixtures entirely synthetic and temporary. Persist only the helper and summarized numeric/identity evidence; no real session paths, message text, prompts, secrets or raw transcript exports. Missing telemetry remains unavailable, never zero. Do not add overlapping reports or fixture totals to measured conversation usage.

## Commit checkpoints

1. `plan: Bound the token accounting investigation (#83)` — this plan only. Read it back, run `git diff --check` and builder scope validation; coordinator commits before reproduction work begins.
2. `test: Reproduce Codex token accounting limits (#83)` — coordinator-owned helper and experiment report together. Run the helper against unchanged collector code, compare explicit expected/observed numbers, and run existing collector tests plus focused Ruff checks. This characterizes current behavior rather than implementing a fix, so a missing-behavior red test is not required. Report failures or inconsistent findings without weakening assertions.
3. `plan: Record token accounting investigation evidence (#83)` — builder updates this plan against actual supplied evidence after the coordinator's new commit/scope snapshot. Link findings rather than duplicating their tables. Run full verification on the integrated High-tier candidate, freeze it, then obtain independent verifier and security-reviewer reports. Record actual results and review limits; repair only confirmed investigation defects, with at most two repair rounds.
4. Coordinator records the session log, pushes checkpoints, opens/updates the draft PR and waits for configured required CI on the latest head. Human review and merge remain pending until actually given.

## Verification and handoff

- Initial assignment: plan-only checkpoint for `/slice 83`; supplied context includes the four reported cases, evidence/privacy boundaries, ownership, base/branch, estimate and pre-run scope manifest `relay-83-builder-plan.json` outside the repository.
- Builder adapter requests `gpt-6.1-sol` with medium effort; observed execution metadata is pending. Coordinator collects baseline/final usage with `resource_usage.py`; unavailable measurements must be identified explicitly.
- Required full command, from repository root with `.venv` active in Git Bash: `ruff check . && ruff format --check . && pytest`. Also run `python -m unittest discover -s workflow/scripts -p test_resource_usage.py` and the synthetic helper. Record exact results and distinguish existing-suite checks from synthetic accounting assertions.
- No criterion mapping is added because no product requirement changes. Verification maps the four questions above to the experiment's concrete inputs, expected/observed arithmetic and coverage limits.
- At this checkpoint, reproduction, full verification, independent reviews, hosted checks and delivery have not run. Do not infer their success from approval of this plan.

## Open issues and next step

- Coordinator checks the plan-only scope and commits it, then produces the synthetic evidence checkpoint. Builder waits for that commit and a fresh scope snapshot before closeout edits.
- Any ambiguity in real fork/continuation semantics remains an explicit limitation unless supported by attributable metadata or official documentation. No historical correction or collector repair is authorized by this investigation plan.
