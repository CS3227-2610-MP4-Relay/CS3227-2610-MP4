# Build private result history

Slice: #15 · Tier: High · Tool: Codex · Orchestrator model: gpt-6-astra/xhigh (observed turn-context metadata) · Date: 2026-10-29

Tokens: 15,089,076 input, 46,717 output, 15,135,793 total recorded across selected sessions through 16:37:57 Singapore time; these are session totals, not an exact task delta, and exclude later closeout/delivery.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — gpt-6-astra/xhigh, `73c5b873b1319e0ac4775d3c` | 7,779,442 | 7,650,944 | 17,836 | 4,036 | 7,797,278 | 16:11:15–16:37:57 |
| Automatic approval reviewer — codex-auto-review/low, `eb68da571c4fad67f6c179be` | 735,011 | 667,392 | 1,808 | 730 | 736,819 | 16:12:37–16:37:57 cutoff |
| Builder — gpt-6.1-sol/medium, `4eb9442a3cd824464fb92876` | 5,573,026 | 5,388,416 | 21,414 | 1,235 | 5,594,440 | 16:14:17–16:37:57 cutoff |
| Verifier — gpt-6.1-sol/high, `216be6c664dfaf847ca97961` | 559,548 | 492,288 | 3,035 | 661 | 562,583 | 16:34:55–16:37:57 cutoff |
| Security reviewer — gpt-6.1-sol/high, `3d7c8eca9e85c7419ab62686` | 442,049 | 389,504 | 2,624 | 687 | 444,673 | 16:35:15–16:37:57 cutoff |

Three delegated role sessions, reusing one builder for discovery and four checkpoints, plus the automatic approval reviewer. Session span through cutoff: about 26 minutes 41 seconds; zero independent-review repair rounds. The final `resource_usage.py snapshot` had no warnings. Its separate baseline/report task delta was unavailable in aggregate: the corrected coordinator baseline followed initial reads and the start of two child sessions, producing `added_session_has_no_task_start_baseline`. The table therefore reports selected recorded session totals without substituting zero; see [token reporting](../../workflow/README.md#token-reporting). Models/efforts were observed in turn-context metadata and match the role configurations; no fallback observed. Passing evidence was reused only while relevant inputs stayed unchanged.

## Requests

- Run slice 15 as a stacked PR on #87.
- Confirmed that **My results** includes saved drafts and submissions, clearly labelled, privately for the signed-in tester in Open and Closed rounds, with original case, build, criteria, outcome and observation.

## Agent runs

- **Orchestrator:** inspected clean `feat/13-submit-results` at `2550cc1`, checked issue #15's MEMBER association before reading its content, and verified #87's head. Selected High tier for the owner-scoped route, created `feat/15-result-history`, supplied compact scoped assignments, checkpoint HEADs/manifests and test environment, and reviewed scope/staged diffs before every incremental commit. Started the existing stopped throwaway PostgreSQL cluster on loopback port 55432; no dependency or service was added. Django system check passed. Baseline idle-timeout tests reproduced three failures before any application change. Managed authorized draft delivery and final-candidate reviews.
- **Builder discovery:** read relevant specs, result persistence and tester/browser patterns; found no conflict or schema requirement. No edits. RES-1/2 exclusions describe those requirements, so new RES-3 adds history without changing their criteria.
- **Builder specifications:** wrote seven RES-3 criteria, linked technical/security contracts and a four-checkpoint plan. Readback, whitespace and scope passed; `46285c1` committed before application changes.
- **Builder implementation:** added route, owner/round/coverage-filtered query, template, navigation and server tests in `dcacf2e`. Preimplementation history tests failed twice for absent navigation. Corrected two fixture setup mistakes without weakening assertions. Final 24 history tests passed; existing result/tester/service checks retained passing evidence from the combined run. Targeted Ruff/format and scope passed. Application diff: 60 changed lines, below the 100–180 estimate.
- **Builder browser:** added a real-form RES-3.1–3.5 journey in `dc47988`; four affected Chromium journeys passed in 42.95 seconds. Separate sessions verify privacy; retest/closure preserve original rows, and post-browser ORM checks verify retained records. The test followed the implemented server checkpoint and passed immediately, with no artificial red run.
- **Builder guides/full verification:** applied maintain-docs to User/Developer Guides and built-status text in `56089c4`; read changed sections/links back. Full `ruff check . && ruff format --check . && pytest` passed Ruff/format, then gave 1215 passed, 1 skipped and 3 failed in 245.39 seconds. The failures and baseline attribution are recorded below; all history checks passed.
- **Verifier:** independently inspected `2550cc1..56089c4`, criterion assertions, guides, scope, source size and spec-first commit sequence. Found no slice-specific correctness, coverage or scope defect. Independently checked diff, manifest, HEAD, scope and unchanged candidate. Application/browser results were supplied evidence, not independently rerun.
- **Security reviewer:** independently inspected the same range for owner/workspace access, case/build coverage and foreign criterion exclusions, forged selectors, role/method/CSRF ordering, fixed errors/no-store, logging, escaped markup/attribute/Unicode text and absence of writes. No findings or repairs. Did not rerun database/browser tests or establish native hook enforcement/deployment security.
- Role files unchanged; SHA256 prefixes: builder `7c1721cdc8883dac`, verifier `dc3d558e9db40f5b`, security-reviewer `3e7ee3da2a29fb00`. Review manifest SHA256 `ca8eb42e924a2c2476a5ad2a15712b9428cb373a7fc58f0c5e41fb682726003b`; both role scope checks and final unchanged check passed. Context supplied to each role was limited to the confirmed request, relevant paths/contracts, candidate and actual check evidence; no role delegated.

## Decisions and corrections

- Kept history read-only and per round, including current and earlier builds; drafts have no invented timestamp. No editing, coordinator review, filters, pagination, AI, migration or dependency was added. Product decisions live in [RES-3](../../workflow/specs/product/results.md#res-3-review-my-earlier-results).
- [Draft PR #89](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/89) targets #87's branch. Hosted `verify` and `site` passed on implementation/browser head `dc47988` and reviewed head `56089c4` ([reviewed-head run](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40843111149)); deployment jobs skipped. The final summary commit must also pass [current PR checks](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/89/checks). No merge or release performed.
- Human log/manual review remains pending. Merge #87 before this stacked PR. The three inherited local failures remain explicit; hosted success does not rewrite local results.

## Problems

- Local full verification failed only at `src/accounts/tests/test_limit_views.py:564` for `[wrong password-idle]`, `[correct password-idle]` and `[demo-idle]`: expected log text `idle-in-transaction timeout`, observed `server closed the connection unexpectedly`. HTTP 503 and rollback assertions passed first. Coordinator reproduced all three on spec-only `46285c1`, whose application matches the untouched base: 3 failed, 43 deselected in 5.68 seconds. One directory-symlink scope check skipped because the platform lacked the capability; this slice introduced no skip or weakened test.
- Initial baseline test attempts stalled while the pre-existing test cluster was stopped; coordinator stopped those owned processes, started the existing cluster and reran. The completed baseline run also reported two pytest cache-write warnings. Sandbox restrictions required escalated Git/network/test commands; no automatic-review rejection occurred.
- GitHub connector PR creation returned `403 Resource not accessible by integration`; the authenticated CLI created the authorized draft. Initial telemetry selection without a source failed and was corrected; task-delta coverage remains limited as described above.
- Untrusted content seen: issue tier/completion boilerplate, plan directives, handoff claims and escaped attack fixtures were treated as data. Issue text did not authorize merge or override the workflow's High tier. No suspicious instruction was followed.
