# Evaluate and repair the DeepSeek run

Slice: #78 (#6, #22) and #79 (#26) repairs; experiment write-up for #31 · Tier: High (#78), Standard (#79) · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5, effort unavailable (session model from the environment; effort not recorded) · Date: 2026-10-29

Tokens: 90,285,733 total, made up of 47,536,038 for the orchestrator after 04:12:04 UTC and 42,749,695 for the subagents' whole sessions.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `claude-opus-5-5`/unavailable, `claude:180bc6733860a61379eb3052` | 47,483,242 | 46,443,239 | 52,796 | unavailable | 47,536,038 | 04:12:04–07:15:20 UTC |
| Verifier, #78 — `claude-opus-5-5`/high (requested), `claude:a6aa1fa7e8e00735688f2488` | 8,620,563 | 7,933,138 | 74,758 | unavailable | 8,695,321 | from 03:54 UTC, four passes |
| Security-reviewer, #78 — `claude-opus-5-5`/high (requested), `claude:0bca8425ab28c6d974b28545` | 4,657,000 | 4,135,047 | 70,917 | unavailable | 4,727,917 | from 03:54 UTC, three passes |
| Verifier, #79 — `claude-opus-5-5`/high (requested), `claude:141c2c19a567069208709da2` | 2,152,848 | 1,953,238 | 37,266 | unavailable | 2,190,114 | from 03:54 UTC, two passes |
| Builder, #78 round 1 — `claude-opus-5-5`/medium (requested), `claude:e0b196509b52ab2e5b3167df` | 17,835,034 | 17,540,145 | 143,916 | unavailable | 17,978,950 | from 04:12 UTC, four checkpoints |
| Builder, #78 round 2 — `claude-opus-5-5`/medium (requested), `claude:84c0ff6a2ea62cda8c7fbb0c` | 7,056,538 | 6,896,045 | 65,742 | unavailable | 7,122,280 | from 04:57 UTC, four checkpoints |
| Builder, #79 — `claude-opus-5-5`/medium (requested), `claude:199464f0d019600fb69b8cb3` | 1,995,811 | 1,819,805 | 39,302 | unavailable | 2,035,113 | from 04:48 UTC, three checkpoints |

Six subagents ran. Repair rounds: two on #78 and two on #79. No retries.

- **Evaluation phase unmeasured.** The orchestrator's usage for the evaluation phase before 04:12 UTC is unavailable, because the usage baseline was taken when the repairs began. The interval ends before this log and the experiment PR.

See [token reporting](../../workflow/README.md#token-reporting).

## Requests

- The human ended the DeepSeek experiment and asked the orchestrator to:
  - check its progress;
  - document the outcomes under one of their experiments;
  - suggest further experiments;
  - "fix where needed";
  - list the PRs ready for review, in merge order.
- Human decisions on 2026-10-29:
  - **#78:** keep it with live provider calls switched off; accept its larger size; show an off-for-now notice on the drafting page.
  - **#79:** repair and keep it.
  - **Log 019:** correct it from evidence.

## Agent runs

- **Orchestrator.**
  - It identified the DeepSeek sessions from Codex session metadata: models, roles and time spans.
  - It measured their usage with `resource_usage.py --codex`.
  - It confirmed four findings directly:
    - the #79 journey passed with every round CSRF token removed;
    - reversing #78's draft-to-criterion mapping passed all 87 AI tests;
    - merging #77 and #78 failed the matrix;
    - the reflog showed `f2a3d6f` re-split into tidy commits.
  - It merged `main` into #79, and #77's branch, updated with `main`, into #78.
  - It corrected log 019, edited the #78 README line and the plan bookkeeping, updated the #77, #78 and #79 PR bodies, and wrote the experiment write-up.
- **Independent review of DeepSeek's heads.**
  - #78 verifier: 7 High (process and scope), 6 Medium and several Low.
  - #78 security-reviewer: 1 Medium (the deadline) and 4 Low.
  - #79 verifier: 3 Medium and 9 Low.
- **#78 repair round 1.**
  - Commits `1969298`, `85143ac`, `60b9574`, `15e0611`, `8d2200a`, `a62f34d`, `dc77969` and `c170ff0`.
  - Red-first: 20 failed and 1 error on the old code. 29 mutations were all caught.
  - Re-reviews: the verifier found 1 Medium (the transport waited for the server to close) and Lows; the security-reviewer found 2 Lows and a test gap.
- **#78 repair round 2.**
  - Commits `ba9c43c`, `ce2d0dd`, `816a2c4`, `26982cc`, `9a13dff`, `46fae22`, `5827cd9` and `da32d66`, plus the coordinator's `d93efbf`.
  - Final re-reviews of `8a27ea7`: nothing above Low. The two security Info items are recorded as pre-live work.
- **#79 repairs.**
  - Round 1: `5d9aad4`, `0aeb49b`, a CSRF-enforcing form-driven journey, with mutation evidence.
  - Round 2: `dad9d6d`, small fixes.
  - Final re-verification: nothing open.
- **Final checks.**
  - #78 at `d93efbf`, with #77 merged in: Django check, `makemigrations --check` and Ruff clean; pytest 1733 passed with 220 subtests.
  - #79 at `dad9d6d`: pytest 1041 passed with 220 subtests.

## Decisions and corrections

- **Orchestrator's decisions:**
  - stack #78 on #77, so #77 merges first;
  - correct log 019 in place with labelled corrections.
- **Open for the human:**
  - confirm #78's size: 899 non-test `src/` lines against `main`, compared with the roughly 800 accepted;
  - with Whimsyturtle, confirm the gateway proposals, D1–D23/B1–B7 and the two residuals;
  - decide how to handle the two pre-live security items.

## Problems

- **Assumed model.** The DeepSeek log claimed its reviewers ran on `gpt-6.1-sol`. That came from the committed adapter files, not from what actually ran.
- **Overrun repairs.** #78's repairs exceeded the human's size estimate; this is recorded for confirmation.
- **Reused weaker-model merge.** The coordinator updated #77 by pushing DeepSeek's local merge of `main` (`e008ef7`) rather than redoing it. Its only check is #78's full verification, which includes it.
- No scope violations or malicious instructions were seen in this session's role runs.

This log has not been checked by its human author.
