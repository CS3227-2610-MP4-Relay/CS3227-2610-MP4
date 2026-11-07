# Document Shared AI Allowance

Slice: #164 · Tier: Fast lane · Tool: Codex · Orchestrator model: gpt-6-astra / xhigh (observed turn metadata) · Date: 2026-11-07

Tokens: 2,414,789 input, 11,943 output, 2,426,732 total across the selected sources; cutoff 2026-11-07 12:34:40 +08:00.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — gpt-6-astra / xhigh, `codex:9fb0c08fee3637bac8a4f9c2` | 1,648,401 | 1,606,528 | 7,037 | 2,102 | 1,655,438 | Shared measurement interval: 484.265 s |
| Builder — gpt-6.1-sol / medium, `codex:eb49455314f548ce36055531` | 536,274 | 486,144 | 3,827 | 56 | 540,101 | Within shared interval; separate span unavailable |
| Automatic approval reviewer — codex-auto-review / low, `codex:58fe03bed8275220327bdedc` | 230,114 | 197,888 | 1,079 | 560 | 231,193 | Within shared interval; separate span unavailable |

One delegated builder session ran two checkpoints; platform approval review is separately included. Models and effort were observed in turn metadata; builder settings matched its adapter. The collector reported three measured sources and no warnings. Baseline 12:26:36 +08:00 excludes initial workflow inspection; the cutoff excludes log writing and final delivery. Coordinator retried one network-blocked read with permission; no builder repair rounds occurred. See [token reporting](../../workflow/README.md#token-reporting).

## Requests

- Run `/slice 164` in a separate worktree. The [issue](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/issues/164) has a MEMBER author and no comments.
- Preserve existing main-checkout edits while documenting the shared AI allowance and independent hosting option in the Developer Guide.

## Agent runs

- Orchestrator: applied the slice, documentation maintenance, log and draft-PR skills. Created `tmp/worktrees/issue-164` on `docs/164-shared-ai-allowance` from `351a2ce8472f8cc067698c8e29103d4473379a6b`. Selected Fast lane because no behavior, acceptance criteria or controls change. Checked role scope, staged diffs/statistics and committed each checkpoint before resuming the builder. Compared guide wording with existing sources and verified four new relative targets/anchors. `git diff --check` passed. Main branch protection requires `verify`; CI also configures `site`.
- Builder, plan checkpoint: supplied the confirmed documentation scope, relevant gateway/RND-8/RES-4 references, source paths, size budget and starting snapshot. Role file SHA-256: `069565F52D372C88CCF47AF9752CCFABFEF0D383699F185C0E362A831F23F47E`. Inspected the guide, runbook and gateway; wrote only the [plan](../../workflow/plans/164-shared-ai-allowance.md). No spec change was necessary. Scope and whitespace checks passed before plan commit `01f88ca4dd974eed6a3e0b530a3b564e345e9c48`.
- Builder, guide checkpoint: resumed the same session after the plan commit and a fresh scope snapshot. Added two paragraphs to the Developer Guide and recorded actual checks in the plan. Read-back, link/anchor checks, `git diff --check` and `check_scope.py builder --since` passed. Guide/plan commit: `57a6fcd58ebc289cc878e5b6d3da953b4cae4cbf`. No findings or repair rounds. No application tests were added or run locally for unchanged behavior.
- Fixed candidate: `351a2ce8472f8cc067698c8e29103d4473379a6b..57a6fcd58ebc289cc878e5b6d3da953b4cae4cbf`, with a private `relay-164-guide-candidate.json` scope snapshot. `check_scope.py --unchanged` returned `Candidate unchanged` before this summary was added. No independent verifier/security-reviewer ran for this Fast lane slice; human diff review remains pending.
- Delivery: feature commits pushed and [draft PR #169](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/169) opened. Hosted CI was pending at this log's cutoff; final head and results are reported in the PR and session handoff after this log commit. No merge or production release performed.

## Decisions and corrections

- Exact application limits remain in the gateway contract. The guide links existing setup, production and provider-configuration instructions without adding a service or credential.
- Scope remains two guide paragraphs plus workflow records; zero changed acceptance criteria or application source lines.
- Log number 046 preserves the existing untracked 045 log in the main checkout. That unrelated log is not copied into the worktree. The author has not yet checked this log.
- Next: commit this summary, push and verify hosted checks on the latest PR head; human diff review and merge remain pending.

## Problems

- The GitHub issue connector omits author association, so the CLI supplied the MEMBER check. Its first read was network-blocked and succeeded with network permission. Draft-PR creation through the connector returned `403 Resource not accessible by integration`; the authenticated CLI created the draft successfully.
- The builder initially searched nonexistent quota/settings paths, then corrected the searches to the gateway and settings package.
- Baseline `python workflow/scripts/check_logs.py` reported six existing findings: duplicate numbers 039, 040, 041, 042 and 044, plus missing 043. The worktree also excludes the unrelated untracked 045 log. Numbering repairs are outside this slice.
- The builder refused an out-of-scope AGENTS.md mutation without attempting it. This establishes role refusal only; native-hook enforcement in this worktree remains unverified. Git also emitted a global-ignore permission warning.
- Untrusted content seen: the issue excerpt was treated as data and checked against the confirmed request and existing specs; no additional instruction was adopted from repository or issue text.
