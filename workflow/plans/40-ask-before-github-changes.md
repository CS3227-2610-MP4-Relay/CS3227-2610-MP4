# Ask before agent sessions change GitHub settings, content or reviews (#40)

Goal: agents change GitHub settings, shared content or reviews only when the human asks for that specific action. This closes the agent admin-credential gap that the #8 security review raised.

Tier: High, because it changes development security controls (agent permissions). Base: `9fe329a`. The coordinator makes the edits: they fall under `AGENTS.md` and `.claude/`, outside the builder's write scope. The verifier and security-reviewer then review the candidate.

Decisions (coordinator, under the human's delegation of 2026-10-26, "make my decisions for me"):

- The control's home is [SECURITY-SPEC Development workflow](../specs/SECURITY-SPEC.md#development-workflow); the agent rule lives in [`AGENTS.md`](../../AGENTS.md#approvals-and-claims). There are no product criteria: this is a repository control.
- A slice request still covers its own delivery: pushing its branch and creating and updating its own draft PR. Anything else needs the human to ask for that specific action in the session. That includes requesting reviewers and marking a PR ready.
- Enforcement in Claude Code is project `ask` rules for the GitHub-changing `gh` subcommands and every `gh api` call. `gh pr edit` stays ungated so delivery can update its own PR. There is no Codex hook or rule: Codex follows the instruction, as with its role scopes ([workflow README](../README.md#how-scope-is-enforced)).
- No server-side change: GitHub can't tell an agent from its human user. Branch protection stays the server-side control for `main`.

## Checkpoints

1. `spec:` SECURITY-SPEC control and residuals, plus this plan.
2. `chore:` the `AGENTS.md` rule, the `.claude/settings.json` ask rules, and a `test_adapters.py` test that the rules exist. Focused check: `python -m unittest discover -s workflow/scripts`.

## Verification

- Full verification on the final candidate. The verifier and security-reviewer review that candidate.
- Manual check, after merge, in a Claude Code session opened at the repository root: ask for `gh api repos/{owner}/{repo}` and `gh pr review --approve`; each must prompt for approval. This can't be automated, because the prompts come from the client.

## Open issues

- PowerShell-tool and Codex sessions have no command gate; they rely on the instruction.
