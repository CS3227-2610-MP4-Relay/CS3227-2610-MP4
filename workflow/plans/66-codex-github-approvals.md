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

- Spec-first checkpoint `f7a9ecc`; controls and regression tests `98b0052`. Builder scope check and `git diff --check` passed before the spec commit. Coordinator made the implementation because its paths are outside builder scope.
- Focused red: `python -m unittest discover -s workflow/scripts -p test_codex_approvals.py` failed with 138 errors from the absent config/rules. Green after implementation: 5 tests passed in 12.778 seconds. Ruff lint/format and `git diff --check` passed. No real GitHub operation was executed by these tests.
- Native CLI `0.159.2` returned `prompt` for the tested direct commands, including `.exe` variants, reads, API calls, flags, aliases, new command names and PR title/body edits; a broad `allow` lost to `prompt`. Literal wrappers, uppercase `GH`, absolute paths and Git flags before `push` returned no match. Wrapper results do not establish live shell handling.
- Workflow regression command `python -m unittest discover -s workflow/scripts`: 77 tests run, 76 passed and 1 existing skip, in 33.336 seconds. The native Codex tests ran. These include the existing synthetic scope/hook fixtures; the builder also refused the prohibited `AGENTS.md` edit request without attempting mutation, which establishes instruction adherence only, not hook execution.
- Local full command `ruff check . && ruff format --check . && pytest`: lint and formatting passed (67 files), pytest collected 737 tests but stalled on database connection and was stopped. Diagnostic `PGCONNECT_TIMEOUT=2 pytest -x -q` returned `django.db.utils.OperationalError: connection timeout expired` at `src/accounts/tests/test_demo.py::test_workspace_has_one_coordinator_and_two_testers` (1 error). Windows reserves ports 55428–55527, including fixed test port 55432; a throwaway PostgreSQL 17.6 cluster failed to bind with `Permission denied`. No OS port policy or application settings were changed. Hosted full verification remains required.
- Keep project trust/loading, sandbox restrictions and actual interactive approval routing separate from evaluator coverage. A live trust/loading or prompt check is unavailable until actually performed; do not infer it from TOML parsing or a `prompt` evaluator result.
- The current coordinator session uses `auto_review`; new project files cannot retroactively change it. Any fresh-session observation must record its effective reviewer, launch root, trust state and result without retaining prompts or secrets.
- Final required commands: activated `.venv`, `ruff check . && ruff format --check . && pytest`; `python -m unittest discover -s workflow/scripts`. Record exact failures or unavailable checks instead of claiming completion.
- Builder checkpoint trigger: coordinator's spec/plan-only assignment for `/slice 66`; adapter requests `gpt-6.1-sol`/medium, effective execution metadata unavailable to the builder. Supplied context: base/branch, clean starting tree, scoped control design, official-source summaries and pre-run scope snapshot `relay-66-builder-before.json`. Coordinator retains telemetry coverage and records final usage in the session log.

## Open issues and next step

- Independent verifier and security-reviewer found no actionable defects in `ec1a951a..cab12352f6a68c964f950b6d674942225abb36bd`. Both independently passed all 5 focused tests (13.359s and 14.242s). Their scope checks and final candidate check passed against manifest SHA256 `f44ddf5e69e751a677756c4447aed08b174478e72dfe68c169357df41d27b782`. No repair round was needed; review limits are in the [session log](../../logs/Whimsyturtle/008-add-codex-github-approval-controls.md).
- [Draft PR #69](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/69) is open. [Hosted CI on cab1235](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40458304827) passed Django checks, Ruff and full pytest: 734 passed, 3 skipped in 23.17s. The skips are native Codex tests because CI lacks the CLI; those passed locally. Only summary records change after the reviewed candidate; the final summary head must pass the PR's required `verify` check too.
- Fresh trusted-session loading and interactive prompt observations remain unavailable in this already-running `auto_review` session; the workflow README gives the harmless read-only client check. Those live claims remain unverified, including PowerShell and connector routing. Human log review and merge remain pending.
- References supplied by the coordinator: [rules](https://learn.chatgpt.com/docs/agent-configuration/rules), [approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security), [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference). Documentation claims require local evaluation where possible; unsupported live checks remain explicit.
