# Specify AI test drafting

Slice: #22 spec (`22-test-drafting-spec`) · Tier: High · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5, effort unavailable (session model from the environment; effort not recorded) · Date: 2026-10-27

Tokens: 7,428,449 total for the three subagents' whole sessions, plus the orchestrator's shared row below.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `claude-opus-5-5`/unavailable, `claude:180bc6733860a61379eb3052` | 20,733,740 | 20,651,063 | 25,004 | unavailable | 20,758,744 | 07:47:49–08:13:48 UTC; overlaps log 017's row |
| Builder — `claude-opus-5-5`/medium (requested), `claude:be956b2191101465010c541e` | 4,381,881 | 4,157,774 | 70,335 | unavailable | 4,452,216 | whole session from 07:48 UTC: one checkpoint, two repair rounds |
| Verifier — `claude-opus-5-5`/high (requested), `claude:8e039d15455a87ef25d9bcb8` | 1,726,680 | 1,468,279 | 42,955 | unavailable | 1,769,635 | whole session from 07:56 UTC: three runs |
| Security-reviewer — `claude-opus-5-5`/high (requested), `claude:e46ab7eedbcc05135ff2fdcc` | 1,172,552 | 987,638 | 34,046 | unavailable | 1,206,598 | whole session from 07:56 UTC: three runs |

Three subagents ran. No retries; two repair rounds.

- **Shared orchestrator interval.** The orchestrator's row covers the same baseline as [log 017](017-add-the-route-access-matrix.md) and includes the #25 work in that interval, so it is not added to the total.
- **Interval cutoff.** The interval ends before this log and the PR.

See [token reporting](../../workflow/README.md#token-reporting).

## Requests

- The human said "just do everything that can be done".
- Asked how to handle #22, whose code needs Whimsyturtle's LLM gateway (#6, #19–#21), they chose "Draft it with defaults". The contract is written now, and each choice is listed for them and Whimsyturtle to confirm in the PR.

## Agent runs

- **Orchestrator.**
  - It branched from main `20f4ea7`.
  - It briefed the defaults: 1–5 selected criteria, up to 5 drafts, adoption only through the normal case form, a fixed failure message, and gateway decisions left to #6.
  - It accepted the reviewers' recommended fixes as defaults pending confirmation.
- **Builder.**
  - Checkpoint 1:
    - spec `d65f7df`, the full contract in `ai/test-drafting.md`;
    - RND-8 with 7 criteria;
    - planned routes;
    - plan `13e8e75`.
  - Repair round 1 (spec `83dbc7a`, plan `440de48`):
    - instruction wording due in the spec before code;
    - deployment-wide quota and in-flight needs for #6;
    - parser safety;
    - a Unicode 16.0.0 cleaning table;
    - JSON encoding with a measured size;
    - pre-fill re-cleaning;
    - RND-8.1–8.9.
  - Repair round 2 (spec `123e56f` and plan `2d8c793`):
    - in-flight caps and expiry;
    - connection release;
    - the allowance residual;
    - extra format characters;
    - a trim after cleaning;
    - wording fixes.
- **Verifier.**
  - Round 0: 4 Medium and 10 Low:
    - instruction wording deferred to code;
    - no shared-allowance bound;
    - the 30 s bound against the release gate;
    - hidden-field isolation;
    - wording, one home per fact, and granularity.
  - Round 1: 6 Low. Round 2: 2 Low, left open (see below).
- **Security-reviewer.**
  - Round 0: 2 Medium (no deployment-wide AI cap; parser crash paths) and 6 Low.
  - Round 1: 2 Low and 1 Info.
  - Round 2: nothing open; 2 Info for the implementation and #6.
- **Checks.**
  - `git diff --check` and the builder scope check passed at each checkpoint.
  - No file under `workflow/` contains literal invisible direction characters or U+FEFF.
  - There are no tests, because this is spec only.

## Decisions and corrections

- **Pending confirmation by the human and Whimsyturtle:** coordinator defaults D1, D2, D4–D6 and D8–D23, and builder proposals B1–B4, all listed in the plan.
- **Pending the human's confirmation:**
  - reload resubmission;
  - the demo workspaces' ability to exhaust the deployment-wide AI allowance.
- **Open after the last repair round** (the slice skill's limit of two rounds was reached):
  - the Cleaning intro could be read as cleaning `criteria` labels, which conflicts with exact label matching;
  - releasing the database connection depends on #6 holding no connection during the provider call. Closing a connection inside an atomic block breaks transaction-wrapped tests.
- **For later slices:**
  - the implementation slice's first checkpoint adds the exact instruction wording and needs its own security review before code;
  - #6 decides the gateway needs.

## Problems

- **Wrong commit hash.** The orchestrator gave a reviewer the wrong spec commit hash for repair round 1, then corrected it to `83dbc7a`.
- No scope violations or malicious instructions were seen. This log has not been checked by its human author.
