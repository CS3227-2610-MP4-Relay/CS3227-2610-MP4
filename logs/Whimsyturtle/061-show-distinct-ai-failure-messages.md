# Show distinct AI failure messages

Slice: #180 · Tier: High · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5 (session-stated model ID); effort unavailable (not exposed in session metadata) · Date: 2026-11-13

Tokens: 48,199,127 input, 270,997 output, 48,470,124 total across the coordinator and seven delegated runs; cutoff 2026-11-13 11:10:11 SGT.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — claude-opus-5-5 / effort unavailable, `claude:40213ed7493aa256c8e77126` | 17,061,885 | 16,267,212 | 69,594 | unavailable | 17,131,479 | 12,998.284 s measurement interval |
| Builder — claude-opus-5-5 / medium (configured), `claude:dcaffb817e8093df55838e1f` | 25,462,468 | 23,829,608 | 116,535 | unavailable | 25,579,003 | 07:44:47–10:47:43 SGT, resumed session |
| Verifier, first review — claude-opus-5-5 / high (configured), `claude:f58ecbd4dabd4c156b528e06` | 2,595,315 | 2,489,567 | 20,280 | unavailable | 2,615,595 | 09:49:56–09:54:10 SGT |
| Security-reviewer, first review — claude-opus-5-5 / high (configured), `claude:e667660cc7173b419e72d200` | 1,310,082 | 1,231,842 | 16,557 | unavailable | 1,326,639 | 09:49:56–09:53:19 SGT |
| Verifier, repair 1 — claude-opus-5-5 / high (configured), `claude:b6eece8a9bd3a18567f5625b` | 635,705 | 574,262 | 15,504 | unavailable | 651,209 | 10:40:13–10:43:18 SGT |
| Security-reviewer, repair 1 — claude-opus-5-5 / high (configured), `claude:2ac47956a1fb34a820ebf079` | 559,606 | 497,115 | 15,170 | unavailable | 574,776 | 10:40:13–10:43:17 SGT |
| Verifier, repair 2 — claude-opus-5-5 / high (configured), `claude:ee82c0701b95d39cee992bca` | 301,515 | 258,225 | 8,917 | unavailable | 310,432 | 11:07:37–11:09:28 SGT |
| Security-reviewer, repair 2 — claude-opus-5-5 / high (configured), `claude:d11205603776c6392cbb48c1` | 272,551 | 242,260 | 8,440 | unavailable | 280,991 | 11:07:37–11:09:30 SGT |

Seven delegated runs: one builder session, resumed for each checkpoint, and three verifier and three security-reviewer passes. `resource_usage.py` measured all eight sources with no warnings. Cache-write input was 2,808,300 tokens. Claude transcripts expose no reasoning-output count. Role effort comes from the adapter frontmatter; the transcripts confirm the model but not the effective effort. The baseline was taken at 07:33:33 SGT, after the initial issue, spec and code reads, which are excluded. Two repair rounds and one builder retry, after an API usage-limit stop. Definitions are in [token reporting](../../workflow/README.md#token-reporting).

## Requests

- Run `/slice 180` in a separate worktree, using Whimsyturtle log number 061. Issue #180 was authored by a repository `MEMBER` and has no comments.
- Scope, chosen by the human: distinct user messages plus feedback failure logging, in both AI features. The human accepted criteria changes in two requirements (RND-8 and RES-4), above the one-requirement budget. The hosted production AI check is deferred. No retry time is shown and the limits are unchanged.
- Messages: the human chose separate own-allowance and shared-allowance messages over a single quota message.
- After security review: check both quotas before the free deployment slot, record the remaining "deployment is full" residual in SECURITY-SPEC, and reword the TECHNICAL-SPEC user slot as "created at their first reserved call".

## Agent runs

- **Coordinator:** read the slice, log and PR procedures, issue #180, RND-8, RES-4, the gateway, drafting and feedback contracts, release verification and the AI views. Created `tmp/worktrees/issue-180` on `feat/180-distinct-ai-failure-messages` from `origin/main` `a93430a`. Before each role run, captured a `check_scope.py --snapshot` outside the repository, and after each run checked it with `--since`; every check passed. Inspected each staged diff, stat and numstat, and committed every unit. Ran ruff at each candidate and the final full suite. Opened [draft PR #190](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/190).
- **Builder** (role blob `6a377ba`, adapter blob `88f2c9a`): one session working through planned checkpoints, given excerpts and the human's decisions rather than the conversation.
  - Hook check: an edit to `AGENTS.md` was refused by the pre-edit hook.
  - Spec and plan checkpoint: `e9ba5d8` and `2c79077`. Changed RND-8.4 and RES-4.4, added RND-8.10 and RES-4.10, and updated the three AI contracts.
  - Gateway code split: `16d2256`. The gateway tests failed first with 19–20 failures, then gave 306 passed after one retry for database teardown.
  - Drafting and feedback, one assigned batch with disjoint files and separate failing and passing runs: drafting failed with 10 (`views.py` at HEAD); one run then showed drafting passing and feedback failing with 11; feedback then gave 123 passed. Committed as `37ef0dc` and `ef1ce09`. The run was first blocked by the shared test database (see Problems).
  - Docs and full verification: the first full run failed one stale access-matrix expectation, repaired in `8c04035` (test only). Then `f0f1d81` (User Guide) and `548247f` (plan); full suite 3270 passed, 5 skipped.
  - Repair round 1: spec `ed2cfaf` and plan `8e8efb2` came before code. The new order and rollback tests failed first with 4, then gave 313 passed; full suite 3279 passed, 5 skipped. Committed `4a34b9e` (gateway), `ca45a19` (exception-path log tests and the `NOT_SET_UP_CODES` rename) and `8a1b734` (plan). The run stopped once on an API usage limit and was resumed.
  - Repair round 2: spec `ec4a246`, tests `7d88b27` and plan `7b9a1cd`, with no behaviour change. The three changed test files gave 469 passed.
- **Verifier** (role blob `92f1028`, adapter blob `80909bd`), no shell; the coordinator supplied check results:
  - `a93430a..548247f`: no blocking defects. Raised the missing security evidence (the security review was running in parallel), the double WARNING on the exception path, rollback wording, not-set-up priority, a split commit and a naming nit.
  - `548247f..8a1b734`: no blocking defects. Raised the TECHNICAL-SPEC/gateway disagreement, stale plan lines, "always" wording and a loose log filter.
  - `8a1b734..7b9a1cd`: no blocking defects. Raised plan line 11 and plan line 66 and the race-test comment overstating what the test proves. The coordinator corrected both plan lines in the final plan commit; the test comment is left unchanged.
- **Security-reviewer** (role blob `fca2cb7`, adapter blob `a5217a5`), no shell:
  - `a93430a..548247f`: one Low. A user at their own quota could poll free `busy` against `user-quota` refusals to watch deployment-wide in-flight state; the human chose to check quotas first. Otherwise informational notes only.
  - `548247f..8a1b734`: confirmed the Low is closed. Info: an under-quota user can still learn for free that the deployment is full, which the human chose to record. Also suggested a committed-transaction rollback test, which was added.
  - `8a1b734..7b9a1cd`: nothing above Info.
- **Coordinator checks:** ruff clean at `548247f`, `8a1b734` and `7b9a1cd`. `pytest src/ai/tests/test_gateway.py -k "check_order or rolls_back_everything or racing"` at `8a1b734` gave 13 passed. Final `ruff check . && ruff format --check . && pytest -q -p no:cacheprovider --basetemp=<scratchpad>` at `7d88b27` (code identical at `7b9a1cd`) gave "All checks passed!", "152 files already formatted" and "3279 passed, 5 skipped, 254 subtests passed". `check_scope.py --unchanged` confirmed each frozen candidate unchanged after its review. Hosted CI: `ef1ce09` failed only on the access-matrix expectation fixed by `8c04035`; `548247f`, `8e8efb2` and `8a1b734` succeeded. Final-head CI is reported in the PR.

## Decisions and corrections

- Criteria: RND-8.4 and RES-4.4 changed; RND-8.10 and RES-4.10 added. The non-test `src/` diff was 117 insertions and 55 deletions, against the 400-line budget.
- Gateway codes: `busy`, `slots-missing` (a misconfiguration, which shows the generic message), `user-quota` and `deployment-quota`; provider 429 stays `quota`. Final order: own slot, slot rows, user quota, deployment quota, then free deployment slot. Every refusal rolls back.
- Correction: the coordinator's option text said that after the reorder, probing busy state would cost a real call. That was imprecise, because an under-quota user still gets a free `busy` refusal. The coordinator told the human, who then chose to record it as a residual.
- Accepted without change:
  - A missing configuration is detected after reservation, so it counts toward quota; the criteria now state that priority.
  - Drafting commit `37ef0dc` left the access-matrix test failing until `8c04035`; history was not rewritten.
  - The race-test comment overstates what that test proves.
  - Small extra lock hold on `busy` refusals.
  - Two older log tests keep the `startswith("ai")` filter.
- Next: human review of PR #190 and this log, then the merge decision. #180 stays open for the deferred hosted check. Branch `feat/183-route-back-navigation` also edits `src/ai/feedback_views.py` and its tests, so whichever merges second must resolve conflicts.

## Problems

- The shared test database `test_relay_test` was held by a concurrent #183 session. The builder was blocked for one run and its first failing runs were contaminated. The coordinator saw the other session had moved to `test_relay_183` and resumed the builder. No settings were changed.
- The default pytest temp directory was access-denied on this machine, so every run used `--basetemp` in a scratchpad.
- The builder wrote two pytest-output files to `/tmp` instead of its scratchpad. The hook blocked one builder `Write` to its scratchpad.
- The builder stopped once on an API usage limit and was resumed from its recorded state.
- The coordinator sent the repair round 1 step 2 resume in the same tool batch as the spec commit. The snapshot taken after that commit shows HEAD `8e8efb2`, so the builder's edits were checked against it.
- During the slice, the parent checkout was switched to another branch by a concurrent session. All work stayed in the worktree.
- No hosted AI call was made, so production AI behaviour remains unconfirmed.
- On this branch, `python workflow/scripts/check_logs.py` reports one finding: no Whimsyturtle logs 059 and 060. The human assigned number 061 for this log; this log does not say where 059 and 060 are.
