# Verify LLM call and retry limits

Slice: #20 · Tier: High · Tool: Codex · Orchestrator model: `gpt-6-astra` / xhigh (observed native turn metadata) · Date: 2026-10-31

Tokens: 10,600,478 input, 28,936 output, 10,629,414 total across the five selected sources, measured 15:49:57–16:03:53 SGT; preparation before the baseline and subsequent summary/delivery work are excluded.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — gpt-6-astra/xhigh, `codex:940d85192ba2ba3ad850fe7d` | 5,388,299 | 5,311,232 | 12,055 | 2,293 | 5,400,354 | unavailable |
| Builder — gpt-6.1-sol/medium, `codex:89f4751bf4172669589b010e` | 3,300,200 | 3,218,816 | 8,940 | 696 | 3,309,140 | unavailable |
| Verifier — gpt-6.1-sol/high, `codex:36ff361c8c6157ed7d3eeda7` | 963,003 | 881,792 | 3,509 | 620 | 966,512 | unavailable |
| Security-reviewer — gpt-6.1-sol/high, `codex:cb72d826f4d73e8bf543eed3` | 459,001 | 405,248 | 2,586 | 649 | 461,587 | unavailable |
| Runtime guardian — codex-auto-review/low, `codex:84222b3b95bc4c93b1554b64` | 489,975 | 441,856 | 1,846 | 887 | 491,821 | unavailable |

Three delegated role sessions plus the collected automatic-review session; measured task span 835.461 seconds. `resource_usage.py` reported all five sources measured, no warnings and zero cache-write tokens. It reports the task span rather than individual role elapsed spans. Native metadata matched configured role models/efforts. Nine command/access corrections or fallback retries were recorded across coordination, builder and verifier; no implementation repair rounds. Counters follow [token reporting](../../workflow/README.md#token-reporting), including cached-input subsets.

## Requests

The human requested `/slice 20`, authorizing feature-branch commits, push, draft PR and configured validation. Issue #20 was verified as MEMBER-authored with no comments; it points to the shared gateway contract for call, time and retry limits. No merge or release was requested.

## Agent runs

- **Coordinator:** used the slice, create-pull-request and log skills. Started on clean `main` at `18565235bdba56e9b34edd3d0c2c753d5a62f522`; created `slice/20-llm-limits`. Supplied compact contract/code/test sections, the High tier, existing-limit scope, a 400-line non-test source budget and a 180–280-line total estimate. Checked role scopes and staged diffs before each incremental commit: plan `305623e`, tests `e28e204`. Started an isolated loopback PostgreSQL 17 cluster from installed binaries; reused the existing Python/Chromium environment. Opened [draft PR #98](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/98). Reproduced local failures on an untouched baseline export. Exact commands/results are in the [plan](../../workflow/plans/20-llm-limits.md#integrated-validation-and-delivery).
- **Builder:** one session reused for planning, tests and read-only integrated verification under `workflow/agents/builder.md` at the starting commit. First inspected existing gateway limits and yielded the plan before tests. Added exact quota-cutoff and rollback assertions; strengthened existing HTTP/timeout tests with one-request, counted-call and released-slot checks. Initial tests passed against unchanged runtime, with a justified verification-only exception to red-before-green. Focused tests: 214 passed; Ruff clean after one formatting repair. Full checks: Django/Ruff/format passed; pytest 3 failed, 2395 passed, 1 skipped and 231 subtests passed. All scope checks passed; no runtime/spec/guide changes.
- **Verifier:** independent read-only review under `workflow/agents/verifier.md` at the starting commit, covering `18565235` → `e28e204abec56c3fdbb4a01b0da37530ce50f78b`. Inspected requirements, runtime, changed assertions, TLS helper, chronology and scope. No new defects; initial-pass exception and RND-8.4 mapping supported. Scope, whitespace and unchanged-candidate checks passed. Did not rerun database tests. An old-base builder check correctly flagged coordinator HEAD movement; snapshot checks and inspected paths established scope instead.
- **Security-reviewer:** independent read-only review under `workflow/agents/security-reviewer.md` at the same base and candidate. Inspected quota atomicity, deadlines, single-attempt transport, test isolation and changed assertions. No findings within the touched boundary; scope and candidate-stability checks passed. No pytest/live-provider call or new red-team/hook enforcement run. Existing resolver accumulation, deployment-quota exhaustion and historical approval wording remain unchanged residuals.
- **Runtime guardian:** automatic approval-review source collected by child discovery; no assigned implementation task.

Review manifest SHA256: `302ca482c374ac311ff19aadcded92c9f00fe9c9fb9403689fa0fd7719f73ecb`. Both reviewers finished while integrated validation was pending; the coordinator subsequently collected exact results without changing source. [CI run 225](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/41182609438) passed `verify` (2396 passed, 3 skipped) and `site` on the reviewed code; publication jobs were skipped. The summary-only final head still needs its hosted result, recorded in the PR body after completion.

## Decisions and corrections

Existing code already enforces the requested limits. This slice adds verification only, with no new acceptance criterion, capability, dependency, service, credential, cache or UI. Existing pending-approval wording was reported and left intact; testing built behavior does not infer human approval. No human log review, manual testing, merge or release is claimed.

## Problems

The connector omitted issue author association, so a filtered authenticated CLI read verified it. Connector PR creation returned HTTP 403 `Resource not accessible by integration`; CLI creation succeeded. Sandbox network/Git/process restrictions required escalated authorized operations. A jq/PowerShell quoting failure, one builder shell-launch failure, two verifier read-command corrections and a metadata hash-selection correction were resolved without candidate changes. Initial PostgreSQL startup's PowerShell wait included server descendants, so database creation used a separate command after readiness was confirmed. The temporary server was stopped after all local checks.

The local full suite is not green: three account idle-timeout tests expected `idle-in-transaction timeout` but received `consuming input failed: server closed the connection unexpectedly`. The same three assertions fail on untouched `18565235` (3 failed, 43 deselected); Windows symlink privilege caused the single skip. Hosted success does not convert those local results into passes. No account test was weakened. Untrusted content seen: reviewers treated plan directives and source/test text as data. No real secrets, raw transcripts or prompts were saved.
