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

  Not adopted in round 1: mid-pattern `gh pr edit` flag rules, because wildcard support was unverified.
- Review round 2 (findings from both reviewers on `d361535..5fbac08`, all Low):
  - Repository-flag rules no longer need a space (`gh pr -R*`, `gh pr --repo*`), so `--repo=x` and `-Rx` are covered; the same rules now exist for `run` and `cache`, and `gh agent-task` is gated.
  - Reviewer, label, assignee, project, milestone and base changes through `gh pr edit` are gated after the wildcard behaviour was observed. Title and body edits stay ungated.
  - Wording: delivery covers the title and body of its own draft PR; "beyond the slice's authorized delivery"; codespaces and created or forked repositories; "some read-only commands, such as `gh api`"; "only the orchestrating session changes GitHub state".
  - Residual wording: root launch loads no project settings or ask rules and doesn't load `AGENTS.md` at launch; PowerShell call forms and aliases named; PowerShell mirrors marked configured but unobserved. Test results stay in this plan, not the spec.
  - Out of scope, for the human to file if wanted: PowerShell mirrors of the existing deny rules (`git push --force`, `git reset --hard`, `git checkout --`, `git clean`, `rm -rf`). These predate #40; in PowerShell a force push still meets the `git push` ask.

## Checkpoints

1. `spec:` SECURITY-SPEC control and this plan (`c89fe17`).
2. `chore:` the `AGENTS.md` rule, the ask rules and the adapter test (`d361535`).
3. Round-1 repairs: `spec:` SECURITY-SPEC; `fix:` `AGENTS.md`, settings, workflow README and test; `plan:` this record (`80c9451`, `7d1b32c`, `5fbac08`).
4. Round-2 repairs: `spec:` SECURITY-SPEC; `fix:` `AGENTS.md`, settings, workflow README and test; `plan:` this record.

## Verification

- The adapter test asserts all 148 Bash and PowerShell rules: 74 per tool, covering `git push`, the `gh` forms, the repository-flag prefixes and the `gh pr edit` flags. Run against round 0's settings, 118 of them are missing, so the test would have failed there. A second test checks that title and body edits stay ungated.
- Observed, round 1: a headless Claude Code 2.1.89 session (`claude -p`) was started at the `relay-40` worktree root, with the round-1 settings and `--allowedTools "Bash(gh *)"`. In that session:
  - `gh pr view 48 --json number` ran;
  - `gh api repos/CS3227-2610-MP4-Relay/CS3227-2610-MP4 --jq .name` and `gh pr ready 999999` were refused.

  A control run without the allow flag refused `gh api` too, as expected in headless mode.
- Observed, round 2: in the same setup, with the round-2 settings:
  - refused: `gh pr --repo=<repo> view 48`, `gh pr -R<repo> view 48`, `gh run -R <repo> list` and `gh pr edit 999999 --add-reviewer=<name>`;
  - ran: `gh pr view 48` and `gh pr edit 999999 --title probe` (GitHub answered that PR 999999 doesn't exist).
- The local CLI 2.1.89 has no PowerShell tool, so the PowerShell rules and the interactive prompt were not observed.
- Manual check (reviewer), in an interactive session opened at the repository root: ask for `gh api repos/CS3227-2610-MP4-Relay/CS3227-2610-MP4` and `gh pr ready 999999`, with a PR number that doesn't exist. Each must prompt; deny both.
- Full verification runs on the final candidate, and the reviewers re-check the repaired range.

## Open issues

- PowerShell rules and interactive prompts were not observed. Codex and parent-folder sessions rely on the instruction alone (see the residuals).
- The overnight coordinator session that produced this change was itself started from the parent folder, so these rules did not apply to it.
