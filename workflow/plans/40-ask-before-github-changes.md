# Ask before agent sessions change GitHub settings, content or reviews (#40)

Goal: agents change GitHub state only when the human asks for that specific action. This closes the agent admin-credential gap that the #8 security review raised.

Tier: High, because it changes development security controls (agent permissions). Base: `9fe329a`. The coordinator makes the edits, because they fall under `AGENTS.md` and `.claude/`, outside the builder's write scope. The verifier and security-reviewer review the candidate.

Decisions (coordinator, under the human's delegation of 2026-10-26, "make my decisions for me"):

- The rule and its categories live only in [`AGENTS.md`](../../AGENTS.md#approvals-and-claims). [SECURITY-SPEC Development workflow](../specs/SECURITY-SPEC.md#development-workflow) holds the threat, the enforcement and the residuals. There are no product criteria: this is a repository control.
- A slice request still covers pushing its own branch and creating and updating its own draft pull request. Anything else needs the human to ask for that specific action in the session, including requesting reviewers and marking a pull request ready. Role agents never change GitHub state.
- Enforcement in Claude Code: project `ask` rules for `git push` and the GitHub-changing `gh` command groups and subcommands, in both the Bash and PowerShell tools.
  - Every `gh api` call is gated, as are global flags placed before `pr` or `issue`, plus aliases and extensions.
  - `gh pr edit` stays ungated, so delivery can update its own pull request.
  - Codex has no rule or hook; it follows the instruction, as it does for role scopes.
- No server-side change: GitHub can't tell an agent from its human user, so branch protection remains the server-side control for `main`.
- Review round 1 (findings from the verifier and security-reviewer on `9fe329a..d361535`):
  - add PowerShell mirrors;
  - add the ungated commands they found (credential, branch-update, gist, project, alias and other forms);
  - keep a single home for the rule;
  - widen the categories to credentials, other pull requests, branches, tags and Actions runs;
  - state the root-launch, permission-mode, MCP, token and best-effort residuals;
  - require sessions to start at the repository or worktree root ([workflow README](../README.md#using-it));
  - assert the full rule list in the test.

  Not adopted: mid-pattern `gh pr edit` flag rules, because their wildcard support is unverified on our client. That case is a stated residual instead.

## Checkpoints

1. `spec:` SECURITY-SPEC control and this plan (`c89fe17`).
2. `chore:` the `AGENTS.md` rule, the ask rules and the adapter test (`d361535`).
3. Round-1 repairs: `spec:` SECURITY-SPEC; `fix:` `AGENTS.md`, settings, workflow README and test; `plan:` this record.

## Verification

- The adapter test asserts all 114 Bash and PowerShell rules (`git push` plus 56 `gh` forms in each tool). Run against round 0's settings, 84 of them are missing, so the test would have failed there.
- Observed, round 1: a headless Claude Code 2.1.89 session (`claude -p`) was started at the `relay-40` worktree root, with the round-1 settings and `--allowedTools "Bash(gh *)"`. In that session:
  - `gh pr view 48 --json number` ran;
  - `gh api repos/CS3227-2610-MP4-Relay/CS3227-2610-MP4 --jq .name` and `gh pr ready 999999` were refused.

  A control run without the allow flag refused `gh api` too, as expected in headless mode. The PowerShell tool and the interactive prompt were not observed.
- Manual check (reviewer), in an interactive session opened at the repository root: ask for `gh api repos/CS3227-2610-MP4-Relay/CS3227-2610-MP4` and `gh pr ready 999999`, with a PR number that doesn't exist. Each must prompt; deny both.
- Full verification runs on the final candidate, and the reviewers re-check the repaired range.

## Open issues

- PowerShell rules and interactive prompts were not observed. Codex and parent-folder sessions rely on the instruction alone (see the residuals).
- The overnight coordinator session that produced this change was itself started from the parent folder, so these rules did not apply to it.
