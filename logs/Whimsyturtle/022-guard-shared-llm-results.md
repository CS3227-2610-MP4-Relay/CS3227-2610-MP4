# Guard shared LLM results

Slice: #19 · Tier: High · Tool: Codex · Orchestrator model: gpt-6-astra/xhigh (observed turn metadata) · Date: 2026-10-31

Tokens: 9,302,793 input, 29,029 output, 9,331,822 total across selected sources; cutoff 2026-10-31 14:20:21 +08:00.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Coordinator — gpt-6-astra/xhigh; `codex:2ecbb4da408f1f6f2775c81a` | 5,328,051 | 5,261,696 | 12,476 | 2,624 | 5,340,527 | 857.097 s task window |
| Runtime guardian — codex-auto-review/low; `codex:67533a3599e2828d19008729` | 415,818 | 328,448 | 1,296 | 515 | 417,114 | per-source span unavailable |
| Builder — gpt-6.1-sol/medium; `codex:f90e37b94db0cc011c79cc36` | 2,682,512 | 2,608,128 | 10,252 | 1,706 | 2,692,764 | per-source span unavailable |
| Verifier — gpt-6.1-sol/high; `codex:388b959af1f816018bdb98d1` | 384,456 | 319,616 | 2,619 | 574 | 387,075 | per-source span unavailable |
| Security-reviewer — gpt-6.1-sol/high; `codex:abfcb0b327dd14f5b5d289be` | 491,956 | 436,096 | 2,386 | 409 | 494,342 | per-source span unavailable |

Three delegated role sessions plus one runtime guardian were collected with the coordinator using `resource_usage.py`. Models/efforts above were observed in native turn metadata; role settings matched their adapters. The measured interval is 14:06:04–14:20:21 +08:00, excluding initial preparation and later summary/delivery work. All five sources were measured without collector warnings; cache-write tokens were zero. No independent-review repair rounds occurred. See [accounting definitions](../../workflow/README.md#token-reporting).

## Requests

The human requested `/slice 19`, authorizing a feature branch, incremental commits, push, draft PR and configured validation. Issue #19's MEMBER association was verified; it points to the shared gateway contract. No merge or release was authorized.

## Agent runs

- **Coordinator:** applied slice, create-pull-request and log skills; started from clean `main` at `48f7d5610e4e2e9d1c8d3207b1b7532da35eaa2a`; created `slice/19-llm-guards`. Chose High tier for AI controls, supplied compact relevant paths and budgets, and checked role scopes and staged diffs before each commit. Started a temporary PostgreSQL 17 cluster on loopback 55432 using installed binaries and fixed test settings, reusing Python 3.14.2 and Chromium without installation. Created [draft PR #96](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/96). Independently reproduced the three local full-suite failures on an untouched baseline export; exact checks and results are in the [plan](../../workflow/plans/19-llm-guards.md#integrated-validation-and-independent-review).
- **Builder:** one session reused for three checkpoints under `workflow/agents/builder.md` at the starting commit. Inputs: scoped request, gateway/fake/provider tests, relevant AI/security contracts, budget and fresh scope snapshots. Clarified existing obligations before code (`519faf7`), then repaired result validation with regressions (`a14fc61`), then ran integrated checks read-only. Red gateway run: 26 failed/116 passed; focused gateway/transport: 206 passed. All scope checks passed. Source delta is 34 additions/7 deletions; no existing assertion was weakened. One initial test selection was superseded by the full gateway-file red run; one Ruff duplicate-case warning was resolved with explicit surrogate IDs; one full-run launch quoting failure was corrected before checks started.
- **Verifier:** independently inspected fixed `a14fc613b9b1a7a3445268cbe40aa1c52b210686` against the starting commit under `workflow/agents/verifier.md` at that base. Reviewed contract, changed source/assertions, scope, chronology, criterion mapping and relevant guides. No defects found; no pytest rerun. Scope and candidate-stability checks passed. RND-8.4/8.5 tests support existing input/failure/schema obligations; no new criterion or UI journey was introduced.
- **Security-reviewer:** independently inspected the same range under `workflow/agents/security-reviewer.md` at the base, including fixed-code logging, reply bounds, quota/release and relevant feature authorization/adversarial assertions. No findings within that boundary; no pytest or live-provider calls. Scope and stability passed. Schema-valid misleading advice, provider operation and development-hook enforcement remain outside this review's assurance.
- **Runtime guardian:** collected automatic-approval-review session, with no assigned implementation responsibility.

The review manifest SHA256 is `a889be57a27b14407f47460194d9e3e88a064f169623088227aa91bae1c13e97`. Reviewers inspected the fixed candidate while the builder's full suite finished; their reports marked full/hosted checks pending. The coordinator subsequently collected exact results without changing code. Local Ruff, formatting and Django checks passed; pytest had **3 failed, 2387 passed, 1 skipped, 231 subtests passed**. [Hosted run 220](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/41175706330) on the same code passed `verify` and `site`, with **2388 passed, 3 skipped**. The summary-only head still needs its own hosted result; the PR body will carry final delivery evidence.

## Decisions and corrections

Earlier slices already built input separation, transport/envelope bounds and feature validators. This slice repairs only the unchecked injected-provider result boundary; its contract lives in [llm-gateway.md](../../workflow/specs/ai/llm-gateway.md). No dependency, service, credential, input policy, cache or UI was added. The local account failures were reproduced and left outside this slice. No human review, log approval, merge or release is claimed.

## Problems

The connector omitted issue author association, so an authenticated read-only `gh` query verified it. Connector PR creation returned 403 `Resource not accessible by integration`; authenticated `gh pr create` completed it. Sandbox Git/network restrictions required escalated commands; `pg_isready` was absent from PATH and Docker was stopped, so installed PostgreSQL binaries supplied the isolated test cluster, which was stopped after local checks. A temporary PR-body PowerShell pipeline syntax error was corrected before creation.

Full local verification failed only at the three baseline-reproduced idle-timeout log-text assertions: expected `idle-in-transaction timeout`, actual `consuming input failed: server closed the connection unexpectedly`. Windows directory-symlink privilege caused the one skip. Passing hosted CI does not make local execution green. No live provider calls, real secrets or raw transcripts were used or saved. Untrusted content seen: synthetic instruction overrides, delimiter spoofing and state-change requests in existing tests were treated only as data.
