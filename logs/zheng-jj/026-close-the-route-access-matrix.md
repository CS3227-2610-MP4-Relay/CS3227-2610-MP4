# Close the route access matrix

Slice: #25 (PR #107) · Tier: High · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5, effort unavailable (session model from the environment; effort not recorded) · Date: 2026-11-01

Tokens: 11,902,938 input, 113,983 output, 12,016,921 total, from 2026-11-01 10:18:47 UTC to about 11:04 UTC.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `claude-opus-5-5`/unavailable, `claude:180bc6733860a61379eb3052` | 5,635,850 | 5,554,909 | 24,682 | unavailable | 5,660,532 | 10:18:47 – 11:03:58 UTC |
| Builder — `claude-opus-5-5`/role default, `claude:51406ab74fe88f83e6253a9a` | 2,840,227 | 2,586,379 | 37,082 | unavailable | 2,877,309 | 10:19 – 10:53 UTC |
| Verifier — `claude-opus-5-5`/role default, `claude:7cbcc2473c7d5aaf918dfba6` | 1,817,583 | 1,643,923 | 27,906 | unavailable | 1,845,489 | 10:41 – 11:03 UTC |
| Security-reviewer — `claude-opus-5-5`/role default, `claude:2a13de61b14f437044fd6d3e` | 1,609,278 | 1,421,119 | 24,313 | unavailable | 1,633,591 | 10:41 – 11:03 UTC |

**How the figures were measured:**
- **Orchestrator:** `resource_usage.py report` against a snapshot taken before the slice began.
- **Subagents:** each row is `resource_usage.py snapshot` of that agent's transcript. Each agent ran only for this slice.

Scale: 3 subagents. The builder was reused for two checkpoints, a plan update and one repair round. Each reviewer ran once and was continued once for the re-review. Repair rounds: 1. The measurement cutoff is about 11:04 UTC, so this log, the final plan wording and the PR updates are not counted. See [token reporting](../../workflow/README.md#token-reporting).

## Requests

- **Next work.** "is it merged? if so continue working through other unblocked issues". #104 had merged at 09:45 UTC. The orchestrator surveyed the open issues and chose #25, the user's own unblocked High-tier issue, whose earlier plan had kept it open until the later routes had rows.

## Agent runs

- **Orchestrator.**
  - **Survey:** it found that every route already had a matrix row (the completeness test enforces it), so it scoped the slice to the [earlier plan's](../../workflow/plans/25-route-access-matrix.md#open-issues) open items.
  - **Setup:** it created branch `25-result-conflict-matrix` from `045c33c`, briefed the builder, and committed and pushed each checkpoint after its scope check.
  - **Delivery:** it opened draft PR #107 once the tests were committed.
  - **Reviews:** it ran both reviews on frozen candidates.
- **Builder** ([plan](../../workflow/plans/25-result-conflict-matrix.md)):
  1. Spec (`ea18693`): the accounts routes accept exactly the methods listed, so HEAD gets 405 on every route but `/`. This states built behaviour. Plan: `5dbab3e`.
  2. Matrix tests (`b6f757e`), 51 lines added and 24 removed:
     - **Result entry:** rows for a submitted result, a formerly current build, and both, in Open and Closed rounds.
     - **Feedback:** "stale submitted" and "stale missing" in every state.
     - **Results:** 781 passed, against 741 at base. Five mutations that reorder the conflict checks each fail the new matrix; the base matrix caught one of them. Evidence is in `70adac0`.
  3. Repair round 1 (`29c9964`, `ceb4299`): an autouse fixture wraps `ai.gateway.complete` and counts calls on every request. A feedback or `ai:draft` POST that passes every check expects 1 call, and everything else expects 0. Three mutations (g1, g2, d1) each fail the new matrix and pass the `70adac0` matrix. The repair also reworded the plan and a docstring.
- **Verifier**, on `045c33c..70adac0`: 0 High, 0 Medium, 3 Low (plan wording: the earlier open item not recorded as done, out-of-scope tracking, the goal overstating coverage), 3 Nit and 2 Info. Its re-verification of `70adac0..ceb4299` found its findings resolved or declined with reasons, nothing weakened, and 1 Info and 1 Nit on plan wording, both fixed in the final plan commit.
- **Security-reviewer**, on `045c33c..70adac0`: 0 High, 0 Medium, 1 Low and 1 Nit.
  - **Low:** with live calls off, the matrix could not see whether a feedback refusal reached the gateway.
  - **Re-review** of `70adac0..ceb4299`: the Low is resolved. It confirmed both AI call sites go through the patched module attribute, with no new findings beyond an optional Nit.
  - Within those ranges, `045c33c..ceb4299` is security-reviewed for the controls it covered.
- **Reviewer limits.** Neither reviewer could run commands. The orchestrator supplied the diffs, the commit bodies, #25's text and its own check results; mutation results are the builder's, which both reviewers checked against the code without rerunning them.
- **Checks run by the orchestrator:** full verification on `b6f757e` and on `ceb4299`, each with Ruff clean and 2,743 passed and 231 subtests. CI passed `verify` and `site` on `ceb4299`.

## Decisions and corrections

- **Orchestrator's choice within the request:** #25 next; this PR closes it.
- **Builder's routine choices, accepted:**
  - no matrix check for the Tester home's Draft titles, which two existing tests cover;
  - the "stale and submitted in Closed" row, which catches an implementation that handles that overlap before Closed.
- **Not adopted, with reasons in the plan:**
  - verifier Nit 1 (derive refusals from the situation flags);
  - verifier Nit 3 (one way of creating own rows);
  - security N1 (assert competing conflict texts are absent);
  - the security reviewer's optional note on documenting the gateway call convention for future AI routes.
- **Left for the human to track separately:**
  - SECURITY-SPEC's opening status sentence, which omits the RES, RND-4 and AI controls;
  - `delete_criterion`'s link check without a round filter, which can only over-refuse a delete through a directly stored cross-round link.
- **Still open from the earlier plan, with reasons:** PATCH, DELETE and OPTIONS; CSRF variants beyond a missing token and a foreign Origin; Session and limit counters outside the snapshot.

## Problems

- **Builder telemetry.** The builder and reviewers could not see their own usage; their rows come from the orchestrator's snapshots of their transcripts.
- **Mutation helpers.** The builder wrote its mutation helpers to the session scratchpad, outside the repository. Each mutation was restored from a copy and confirmed with `git diff --exit-code`.
- **Untrusted content.** None seen. Issue #25's text, code comments and test payloads were treated as data.

This log has not been checked by its human author.
