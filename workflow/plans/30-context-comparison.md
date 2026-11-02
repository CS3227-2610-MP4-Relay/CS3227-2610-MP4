# Slice 30: compare app context

Goal: run the bounded operator comparison in [CTX-1](../specs/ai/context-comparison.md#ctx-1-compare-selected-and-broader-synthetic-context) and report paired quality/resource observations.

Why: the planned app-context comparison has no measured evidence for whether selected relevant context preserves quality while reducing observable resource use.

## Scope and decisions

- Human approved four fixed synthetic scenarios across both roles, eight gateway invocations maximum, opt-in escaped response inspection, and the existing configuration loader. No repeated confirmation is needed for that bounded execution. Coordinator owns Git/GitHub state and the actual live run; builder never delegates or changes Git state.
- High tier; feature branch `slice/30-context-comparison`, starting HEAD `4507e8f5415217988d971070bbfd750049901ee7`. Initial coordinator log is preserved. Builder uses a fresh coordinator scope snapshot at every checkpoint.
- One internal evaluation requirement, no product capability. Reuse current prompts, encoders, validators, gateway, quota and configured model/defaults. Only experiment JSON gains background data; no dependency, UI, credential, configuration subsystem, malicious payload or expansion of #28's decoding exception.
- Estimate 450–650 total changed lines including coordinator evidence, with 200–280 application source lines; hard ceiling 400 non-test source lines. Target at most 550 builder lines, reserving about 100 for coordinator evidence. Stop affected work and report if scope or these estimates need expansion before adding criteria, tasks or implementation.
- Operating burden: existing operator environment/database/user and up to eight sequential shared-quota invocations, at most roughly four minutes of provider deadline waiting plus local overhead. Failures reduce coverage and never justify retries, quota bypasses or replacement scenarios.
- Proposed implementation homes: `src/ai/context_comparison.py`, `src/ai/management/commands/compare_context.py`, and corresponding offline tests under `src/ai/tests/`. Coordinator owns `experiments/app-context/README.md` and session log. No raw reply retention; no changes to `docs/Reflections.md`.

## Commit checkpoints

1. **Specs and plan** — `spec: Define bounded app-context comparison (#30)`; paths: the CTX-1 contract, security-spec cross-reference and this plan. Read changed documents back; run whitespace and builder scope checks against supplied snapshot; yield before implementation. Commit body starts `Why:` and carries `Agent: builder`.
2. **Corpus and structural observations** — `feat: Compare paired synthetic AI context (#30)`; paths: new comparison module and its offline tests. Add criterion-marked tests first and capture missing-behaviour failures; freeze exact synthetic core/background strings and rubric correspondence before live results. Implement pairing, order, unchanged instructions/label allowlist, input bounds and strict parsed observations. Focused pytest/Ruff; yield for coordinator commit and fresh snapshot.
3. **Operator command** — `feat: Add bounded context comparison command (#30)`; paths: command and command tests, comparison helpers only as needed. Capture meaningful red tests before implementation. Verify fixed preflight/no calls, eight sequential invocations/no retries, interruptions, validated counts and deterministic command timing, default summary safety, escaped unstyled opt-in replies, and unchanged domain records using fake gateway execution only. Focused pytest/Ruff; yield for coordinator commit and fresh snapshot.
4. **Guide and integrated evidence** — `docs: Explain app-context comparison evidence (#30)`; builder paths: `docs/DeveloperGuide.md` and this plan; coordinator paths: experiment report/session log. Apply maintain-docs when assigned; link to CTX-1 and document actual command. Read back edited sections and run full `ruff check . && ruff format --check . && pytest` from Git Bash with `.venv` active and existing test environment. Report actual failures. Coordinator freezes/reviews candidate, runs authorized live pass, manually assesses rubric and publishes sanitized evidence/limitations, then completes hosted validation and draft PR delivery. Human owns merge/release.

## Current checkpoint and next step

Specs/plan only; no implementation, tests or live invocations yet. Next: coordinator reviews and commits this checkpoint, supplies the new baseline/snapshot, then assigns corpus/test work. Record focused red/green evidence and repairs here as work proceeds; actual measurements and semantic assessments belong only in the experiment report, with session resources in the coordinator log.
