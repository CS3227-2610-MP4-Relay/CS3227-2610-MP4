# Codex approval controls for GitHub state changes (#66)

Goal: add the smallest project-level Codex approval controls and regression validation for the [development-workflow GitHub control](../specs/SECURITY-SPEC.md#development-workflow).

Tier: High, because approval routing and command rules affect development security. Base: `ec1a951a76018a82c10e4c39911a724071a15977`; branch: `chore/66-codex-github-approvals`. The human's `/slice 66` request authorizes normal slice delivery under `AGENTS.md`; merge and release remain human decisions.

Why: Codex previously relied on the instruction alone for this control. Add native project configuration and prefix rules while stating their actual enforcement boundary.

## Scope and decisions

- No product criteria change. The security spec owns the control and its limits; setup instructions belong in `workflow/README.md`.
- Use `.codex/config.toml` and `.codex/rules/github.rules`; no dependency, credential, service, general shell parser, hook subsystem or hosted GitHub setting change.
- Use the defaults and prefixes described in the security spec. Accept prompts for read-only `gh` calls and authorized PR title/body edits because native prefix matching cannot make the semantic delivery exemption. Human authorization and client execution approval remain distinct.
- Preserve existing Claude Code controls. Do not claim coverage for broader Git flag/alias forms, absolute paths, PowerShell wrappers or non-shell connectors without observed native evidence.
- Budget: at most 400 changed non-test/non-migration `src/` lines; expected zero. Estimated implementation/test/documentation diff: 180–280 lines. No runtime operating service is added; the operating tradeoff is additional client prompts.
- Builder owns only this plan and the Development workflow subsection of `SECURITY-SPEC.md`. Coordinator owns `.codex/`, workflow regression scripts and setup documentation because they are outside the builder's write scope. Only the coordinator changes Git state.

## Commit checkpoints

1. `spec: Define Codex GitHub approval controls (#66)` — security spec and this plan; read changed sections back, run `git diff --check`, check builder scope, then coordinator commits before implementation.
2. `chore: Gate Codex GitHub commands through user approval (#66)` — `.codex/config.toml`, `.codex/rules/github.rules` and regression validation under `workflow/scripts/`; capture focused failures for missing controls before implementation, then passing focused tests and native `execpolicy check` results. Keep controls and regression tests together.
3. `docs: Explain Codex approval setup and limits (#66)` — `workflow/README.md` and evidence updates here; document trusted project loading, new-session requirement and actual verification limits. Run full verification and workflow regression tests on the integrated candidate.
4. Freeze a fresh candidate for independent verifier and security-reviewer runs. Repair only reported defects within scope, with affected checks and a new fixed candidate; no more than two repair rounds under the slice workflow.
5. Coordinator records the session log, pushes checkpoints, opens/updates the draft PR and checks configured CI on its latest head. Required human merge review remains pending until given.

## Verification

- Pending: focused red/green regression results, native command-evaluator matrix, full verification, workflow-script regression suite and independent reviews.
- Native evaluator: installed Codex CLI `0.159.2` exposes `execpolicy check` (coordinator supplied). Test direct `gh`/`gh.exe` reads, state changes, API/global-flag/alias forms and PR title/body edits; direct `git`/`git.exe push`; unrelated commands; and representative unsupported forms. These are command decisions, not real GitHub mutations.
- Keep project trust/loading, sandbox restrictions and actual interactive approval routing separate from evaluator coverage. A live trust/loading or prompt check is unavailable until actually performed; do not infer it from TOML parsing or a `prompt` evaluator result.
- The current coordinator session uses `auto_review`; new project files cannot retroactively change it. Any fresh-session observation must record its effective reviewer, launch root, trust state and result without retaining prompts or secrets.
- Final required commands: activated `.venv`, `ruff check . && ruff format --check . && pytest`; `python -m unittest discover -s workflow/scripts`. Record exact failures or unavailable checks instead of claiming completion.
- Builder checkpoint trigger: coordinator's spec/plan-only assignment for `/slice 66`; model identified by runtime as GPT-6 Codex, exact effective model/effort unavailable. Supplied context: base/branch, clean starting tree, scoped control design, official-source summaries and pre-run scope snapshot `relay-66-builder-before.json`. Builder usage source unavailable; coordinator retains overall telemetry baseline. Checkpoint results appear in the handoff; implementation remains pending.

## Open issues and next step

- No implementation or enforcement observation is complete at this checkpoint. Coordinator checks the builder's scope and commits the spec/plan before building controls and tests.
- References supplied by the coordinator: [rules](https://learn.chatgpt.com/docs/agent-configuration/rules), [approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security), [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference). Documentation claims require local evaluation where possible; unsupported live checks remain explicit.
