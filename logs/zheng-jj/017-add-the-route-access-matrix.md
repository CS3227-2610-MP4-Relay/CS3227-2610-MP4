# Add the route access matrix

Slice: #25 part 1 (`25-route-access-matrix`) · Tier: High · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5, effort unavailable (session model from the environment; effort not recorded) · Date: 2026-10-27

Tokens: 23,462,099 total for the three subagents' whole sessions, plus the orchestrator's shared row below.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `claude-opus-5-5`/unavailable, `claude:180bc6733860a61379eb3052` | 10,061,971 | 10,015,591 | 13,584 | unavailable | 10,075,555 | 07:47:49–08:02:18 UTC only; shared with #22 |
| Builder — `claude-opus-5-5`/medium (requested), `claude:10fc4f8f10e62e730e8828dd` | 7,926,613 | 7,486,664 | 93,621 | unavailable | 8,020,234 | whole session from 07:02 UTC: two checkpoints, two repair rounds |
| Verifier — `claude-opus-5-5`/high (requested), `claude:0365ce7facd241d85f9b060f` | 3,276,021 | 2,883,520 | 49,234 | unavailable | 3,325,255 | whole session from 07:22 UTC: three runs |
| Security-reviewer — `claude-opus-5-5`/high (requested), `claude:6a4b625f82987af2967ab728` | 2,002,405 | 1,676,332 | 38,650 | unavailable | 2,041,055 | whole session from 07:22 UTC: three runs |

Three subagents ran. No retries; two repair rounds.

- **Orchestrator coverage.** The orchestrator's usage for #25 before 07:47 UTC is unavailable, because no baseline was taken between log 016's cutoff and the #22 baseline. Its row covers only the later interval, which it shares with #22. The total above leaves the orchestrator out.

See [token reporting](../../workflow/README.md#token-reporting).

## Requests

- The human said "just do everything that can be done". The orchestrator chose #25's first part: an authorization matrix for every route that exists now. It refers to #25 without closing it.

## Agent runs

- **Orchestrator.**
  - It branched from main `01f9a24`.
  - It confirmed the builder's HEAD/405 assumption against Django's `require_GET`.
  - After #75 (#70) merged, it merged main into the branch (`33ea8e6`). Git moved the matrix to `src/relay/tests/` with identical content; the orchestrator checked that with git diff. The SECURITY-SPEC path was updated inside that merge commit, not in a `spec:` commit.
- **Builder.**
  - Spec `0490f73` and plan `d53542d`.
  - Matrix `0d4a0b0`: 314 tests. It is a guard over existing behaviour, so it passed first time. Four mutations failed it: role check, workspace filter, round membership and an unlisted route.
  - Repair round 1: spec `25c8c8d`, plus test and plan commits up to `d0ad39a`.
    - Leaks checked both ways.
    - Writes confined to the caller.
    - Forged IDs in form bodies.
    - 404s compared on headers.
    - `Allow` headers, byte-for-byte 403s and zero IDs checked.
    - 419 tests.
  - Repair round 2 (`b2d6733`):
    - marks that tokens can't contain;
    - cookie names compared;
    - tester bystanders;
    - account rows protected.

    That gives 425 tests in about 21 s. With every CSRF token planted with the old marks, the old matrix false-failed 54 tests and the new one passed all 425.
- **Verifier.**
  - Round 0: 2 Medium (the case-sensitive marker missed usernames; `rounds:new` creation was unchecked) and 6 Low.
  - Round 1: 1 Low (the flaky marks) and 3 Info.
  - Round 2: nothing open.
- **Security-reviewer.**
  - Round 0: 1 Medium (no check for leaks into allowed pages) and 4 Low.
  - Round 1: 2 Low (flaky marks; cookies).
  - Round 2: nothing open.
  - No product defect was found in any round.
- **Final checks.** On `b2d6733`: Django check, `makemigrations --check` and Ruff clean; pytest 1354 passed, 220 subtests.

## Decisions and corrections

- **Orchestrator's decisions:**
  - keep the accounts HEAD/405 behaviour as a recorded assumption rather than a spec change;
  - leave Session and limit-counter rows out of the snapshot.
- **Open issues, in the plan:**
  - PATCH, DELETE and OPTIONS are not sent;
  - CSRF variants are left to Django;
  - the Tester home is not checked for Draft titles;
  - later slices add rows for RND-4, RES and AI routes.

## Problems

- **Old leak marker.** The first marker was matched case-insensitively against random tokens, which risked about a 1% false-failure rate per run. Both reviewers caught it.
- **Spec edit in a merge commit.** The SECURITY-SPEC path change rode inside a merge commit.
- No scope violations or malicious instructions were seen. This log has not been checked by its human author.
