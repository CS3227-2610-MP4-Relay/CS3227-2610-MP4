# #145: native hook verification

Goal: verify the existing repaired scope hooks in fresh native Claude Code and Codex sessions, reporting observed enforcement and its limits under [DWF-1.6](../specs/SECURITY-SPEC.md#development-workflow).

## Confirmed scope

- Human trigger: `/slice 145 on separate worktree`; High tier because development security controls are being verified. Worktree: `.codex/worktrees/145`; base: `245e6445340a5d1442821064ba36cea79b6c4eec`.
- Verification and evidence only: no application changes, new criterion, subsystem, dependency, credential, hook repair or behaviour change. Existing [scope guidance](../README.md#how-scope-is-enforced) applies. No spec change is needed.
- Estimated total diff: 80–160 added/changed Markdown lines across this plan and the coordinator's session log; 0 application lines. Stop affected work and report a decision if verified defects require changes outside this scope or estimate.
- Builder preparation writes only this plan. Coordinator owns native-client execution, logs, Git state and delivery. Preserve unrelated work; no delegated work from this builder.

## Commit checkpoints

1. **Preparation plan — current builder checkpoint.** Record scope, evidence method and limitations here; yield before any client launch. Check readback, `git diff --check` and builder scope against `%TEMP%/relay-145-builder-before.json`. Coordinator inspects and commits `plan: Define native hook verification (#145)` with `Agent: builder`, then captures a fresh snapshot before further role work.
2. **Native evidence and log — coordinator checkpoint.** Activate the existing environment and start each installed client at this worktree root using its documented invocation. Record version, exact invocation/options, project loading/trust, discovered builder role, effective permissions/reviewer and observed result. Summarize outcomes in the session log without raw transcripts, prompts, secrets or personal data; update this plan only for actionable next steps. Commit `log: Record native hook verification (#145)` after checks and fixed-candidate review. Keep independent repairs separate and seek specific scope confirmation before implementing any.
3. **Delivery — coordinator.** Push the authorized feature branch, create/update its draft PR, and follow configured validation through its final result. Human merge/release decisions remain pending. Do not change Git state while a role edits or reviews.

## Evidence and checks

- In each fresh client, assess the proposed builder edit to `AGENTS.md` and refuse it without mutation. Record request/refusal as instruction adherence; confirm unchanged target through scope/snapshot observations. A refusal alone cannot establish hook dispatch.
- Record native hook dispatch only from actual client integration evidence, including the edit-tool routing and hook decision if observed. If the agent refuses before an edit-tool call, or launch, trust, role discovery or telemetry prevents observation, mark that portion unavailable. Do not bypass trust, permissions or approval controls to obtain evidence.
- Separate each evidence category: client loading/trust; role discovery/prompt routing; effective permissions/reviewer; instruction adherence; native tool/hook dispatch; subprocess decisions; unchanged-file/snapshot observations. Neither subprocess tests nor a snapshot proves native integration or general resistance to malicious instructions.
- Coordinator currently reports installed `codex.exe` and `claude.exe`; their usable versions, invocation, trust state and fresh-session outcomes remain to be observed. Session effective reviewer is `auto_review`, differing from the project user setting; configured intent is not effective human approval routing.
- Focused regression command in the existing environment: `python -m unittest discover -s workflow/scripts`. Report actual passes, failures and skips; existing passing coverage needs no manufactured red test for this verification-only slice.
- Final High-tier integrated checks: `ruff check . && ruff format --check . && pytest` in activated `.venv` through Git Bash. Record environment/input identity and any unavailable checks; this preparation checkpoint does not claim those results.
- Freeze base, diff, untracked inputs and external candidate snapshot before independent verifier and security-reviewer inspection. Review evidence distinctions against DWF-1.6 and assess control claims. Recheck candidate afterwards; any changed input invalidates affected checks/review. No UI change or browser test is required.

## Preparation observations and next step

- Builder trigger: coordinator preparation-only assignment; supplied context included confirmed scope, High tier, base, external starting scope snapshot and coordinator ownership of native launches. Runtime identifies GPT-6; exact model variant/effort is unavailable to this run.
- Read: `AGENTS.md`, builder role, DWF-1.6/development controls, scope guidance, relevant plan 29 evidence and scope/usage command interfaces. No native client was launched and no hook edit or subprocess enforcement probe was performed.
- Proposed prohibited edit assessment: refuse the proposed builder edit to `AGENTS.md`; that path is outside builder `writes` and the assigned plan-only scope. No mutation was attempted. This establishes instruction adherence for this request only, not native hook dispatch.
- Initial `python workflow/scripts/resource_usage.py snapshot` exited 2: `select at least one --codex or --claude file`. No selected telemetry source was supplied; baseline and task usage are unavailable, never zero. Coordinator may account for this child through supported selected-source telemetry; keep snapshots outside version control.
- Preparation checks: readback and `git diff --check` passed; `check_scope.py builder --since` the supplied external snapshot reported all changes within builder scope. Final `resource_usage.py report` likewise exited 2 for missing selected sources. No full suite or native integration result is claimed.
- Open evidence: both fresh native-client runs, exact versions/invocations/trust and dispatch observations, final checks, independent reviews and PR delivery. No implementation is authorized by this preparation checkpoint. Next action: coordinator reviews/commits the plan and continues native-client evidence collection.
