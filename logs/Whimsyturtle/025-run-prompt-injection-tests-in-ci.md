# Run prompt-injection tests in CI

Slice: #24 · Tier: High · Tool: Codex · Orchestrator model: gpt-6-astra / xhigh (native turn metadata) · Date: 2026-10-31

Tokens: 18,927,825 input, 48,729 output and 18,976,554 total across selected sources; cutoff 2026-10-31 17:52:53 +08:00, before final summary and delivery work.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — gpt-6-astra / xhigh, `codex:288a4c088329823acdcbc1c2` | 9,167,832 | 9,083,520 | 17,515 | 5,524 | 9,185,347 | 23m 14s task window |
| Automatic approval reviewer — codex-auto-review / low, `codex:a98992df5342b538f1af6aa5` | 795,858 | 733,312 | 1,880 | 613 | 797,738 | 20m 32s |
| Builder — gpt-6.1-sol / medium, `codex:31e26132423f2daa2241c44a` | 6,995,690 | 6,887,296 | 22,393 | 3,264 | 7,018,083 | 19m 18s |
| Builder automatic approval reviewer — codex-auto-review / low, `codex:51b80c5c51450714c06c0069` | 437,122 | 386,304 | 1,038 | 351 | 438,160 | 8m 3s |
| Verifier — gpt-6.1-sol / high, `codex:8f53db27ab5e941ca37b3a91` | 744,980 | 659,456 | 3,020 | 430 | 748,000 | 2m 2s |
| Security reviewer — gpt-6.1-sol / high, `codex:d394c198f069acd2fe11fba8` | 786,343 | 724,992 | 2,883 | 709 | 789,226 | 1m 50s |

Three delegated role sessions plus two client-owned automatic approval-review sources were measured with `resource_usage.py`; native metadata supplied effective models/effort. The baseline-to-cutoff span was 1,394.395 seconds, including waits; concurrent spans are not additive. Cache-write tokens were zero, with no collector warnings. The builder reported two execution retries and two pre-handoff lint/format corrections; independent review required no repair rounds. Initial orientation before the 17:29:39 baseline and work after the cutoff are excluded. See [token reporting](../../workflow/README.md#token-reporting).

## Requests

The human requested `/slice 24`: run prompt-injection tests in CI. Normal slice authorization covered a feature branch, incremental commits, push, draft PR and configured validation. Merge and release remain human decisions.

## Agent runs

- **Coordinator:** used slice, create-pull-request, maintain-docs and log workflows. Started from clean `main` at `446f470`; created `slice/24-prompt-injection-ci`. Filtered GitHub reads confirmed issue author MEMBER and no collaborator comments; branch protection requires `verify`. Supplied compact scope/spec/code context, High tier, existing acceptance criteria, zero runtime changes and a 250–380-line whole-slice estimate. Started an isolated temporary PostgreSQL 17 cluster from installed binaries and verified loopback-only listening and its data directory. Checked role scope and staged diff/stat/numstat before each checkpoint. Opened [draft PR #100](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/100); final-head CI follows the summary commit and is reported there.
- **Builder**, role-file SHA256 prefix `7c1721cdc8883d`: one session reused for four checkpoints: specs/plan `d5293f6`, injection regressions/marker `b3fb1b5`, CI/configuration assertions `9f322bf`, guide/evidence `07e228e`. Context and criterion mapping are in the [plan](../../workflow/plans/24-prompt-injection-ci.md). Baseline affected tests passed 206; selected tests passed 95; affected files passed 234. Collection proved 95 and 2,438 disjoint selections equal all 2,533 tests. Two stale CI command assertions failed before adaptation; all three CI tests then passed. Full Django/Ruff checks passed; full pytest results and failures are below. No runtime changes, delegation or Git mutations; all scope checks passed.
- **Verifier**, role-file SHA256 prefix `dc3d558e9db40f`: High-tier independent review of `446f470..07e228e1b0020619d79c551e67eb68a3ad535ea2`, its spec/plan, changed tests/CI/guide and relevant runtime source. Found no defect, weakened assertion or scope expansion. Independently checked exact source/instruction boundaries, reply rejection, rendering, unchanged domain snapshots, commit order and scope. Reused supplied execution results because executable inputs remained unchanged; no suites rerun. Scope, diff and frozen-candidate checks passed; no edits or delegation.
- **Security reviewer**, role-file SHA256 prefix `3e7ee3da2a29fb`: same fixed range, triggered by AI and CI controls. Independently inspected direct and coordinator-to-tester injection, delimiter/Unicode attacks, authorization/context, strict replies, rendering and non-mutation assertions. Found no security finding within examined controls; CI retains pinned actions, read-only validation and production-secret isolation. Reused supplied test results and performed no live calls, suite reruns or edits. Scope and frozen-candidate checks passed after correcting a relative manifest lookup to its absolute temporary path.
- **Automatic approval reviewers:** client-owned execution-review sources, included in the table; they are not application verification or human approval evidence. Effective runtime reviewer is automatic, so this session does not establish human approval routing or development-hook enforcement.

## Decisions and corrections

- The existing full CI suite already included some injection checks. Added a selectable marker, strengthened independent attacker-field and fake-reply cases, and split CI into injection selection plus its complement. No new product criteria, runtime code, dependency, service, credential or live evaluation was added. The reviewed diff was 206 insertions/35 deletions; summary-only evidence follows it.
- Existing behavior passed the stronger regression assertions immediately; no artificial red failure was manufactured. Existing combined feedback attacks remain alongside isolated fields. CI assertions changed to verify the new complete-suite command layout, retaining diagnostics and validation controls. Detailed rationale is in the plan.
- Full local verification: Django, Ruff lint and format passed; pytest returned **2,529 passed, 3 failed, 1 skipped** in 352.69 seconds. Existing browser journeys passed. [Hosted CI at `9f322bf`](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/41189784142) passed: 95 injection tests, then 2,435 other tests with three skips; site passed and deployments skipped. This is not final-head hosted evidence.
- Both reviews found no defect within the fixed candidate and requested no repair. Human log review, manual review, merge/release and live-model evaluation remain pending. Fake-provider success establishes application boundaries, not resistance by a live model or advice quality.

## Problems

The three local failures are `src/accounts/tests/test_limit_views.py::test_timeout_inside_a_limited_transaction_gives_503[wrong password-idle]`, `[correct password-idle]` and `[demo-idle]`, line 564: captured Windows connection errors lack the expected `idle-in-transaction timeout` text. They match the [previous baseline evidence](024-record-llm-usage-and-latency.md); no account code or tests changed. Full local verification is not green. The sole local skip aligns with the directory-symlink privilege check, but this run did not emit its reason. An early coordinator update mistook initial account-test progress for completion of the transactional variants; it was corrected when those variants ran.

The connector omitted issue author association, so filtered CLI reads enforced the collaborator rule. Connector PR creation returned HTTP 403 `Resource not accessible by integration`; authorized CLI creation succeeded. Network, Git and PostgreSQL sandbox restrictions required escalation; no approval rejection remained. The initial usage command omitted an explicit source selector and was corrected before the baseline. An early sandbox test launch was interrupted after stalling; its late output showed 206 passed but exit 1, so the successful elevated baseline was used instead. Default pytest cache warnings did not fail the focused runs; dedicated temporary cache/basetemp paths were used for full verification. The builder corrected one selector quoting attempt and lint/format issues before handing off.

Untrusted content seen: the issue's merge-completion wording and synthetic fixtures requesting instruction overrides, disclosure, state changes or concealed failures were treated as data, not authorization. No secret files were read or payloads copied into this log. This log awaits its author's check.
