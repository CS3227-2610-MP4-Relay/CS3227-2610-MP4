# Implement AI test drafting

Slice: #6, #22 (`22-test-drafting-spec`) · Tier: High · Tool: Codex CLI · Orchestrator model: unavailable (the session did not expose its model ID) · Date: 2026-10-29

Tokens: unavailable — no Codex session transcript path or baseline was available to `workflow/scripts/resource_usage.py`.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — model/effort unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| Verifier — `gpt-6.1-sol`/high (configured), source unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| Security-reviewer — `gpt-6.1-sol`/high (configured), source unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |

Three agent runs: the orchestrator and two review agents. The reviews ran three rounds; the final security-reviewer pass found no blocking issue.

## Requests

- Pull the latest remote state, find open issues that are now unblocked, and continue the two PRs where it made sense. The human wanted real implementation before asking a teammate for review.
- The human corrected repeated permission prompts and then approved the push.

## Agent runs

- **Orchestrator.**
  - Synced `main` and inspected open PRs #77–#79 and the issue set.
  - Chose #6 and #22 for the implementation; #77 already had a substantive access-matrix test and #79 had an E2E test.
  - Added `ai/llm-gateway.md` contract, plan `6-llm-gateway.md`, gateway, RND-8 pages and a browser fallback journey.
  - Split the work into spec, gateway, drafting and repair commits; pushed to PR #78.
- **Verifier.**
  - Candidate `89bebf9`: High finding for missing instruction wording/version; Mediums for deadline, fixed-window quota, byte cap, invisible-only fields, sensitive locals, missing tests/browser coverage, stale plans, missing route coverage.
  - Candidate `3caf1e8`: confirmed most closure; found oversize-response `ValueError`, blocking-read deadline, combined criterion mark, missing adversarial cases, stale plan and unused `Usage` records.
  - Candidate `78ab9b7`: confirmed the functional repairs; remaining blocking-read deadline and documentation issues.
  - Candidate `d234c9c`: confirmed deadline closure and no functional regression.
- **Security-reviewer.**
  - Candidate `89bebf9`: Medium deep-nesting 500; Lows for instructions, deadline, missing tests and stale docs.
  - Candidate `3caf1e8`: deep nesting closed; found oversize `ValueError`, cap issue, deadline residual, instruction-test tautology, dead `Usage` and doc mismatches.
  - Candidate `d234c9c`: deadline closed against a real stalled local server; no blocking security issue; two informational hardening notes.

## Decisions and corrections

- The provider endpoint, model, credential and retention terms remain deployment settings; no provider was invented.
- The gateway uses rolling quota records (`CallRecord`) and two seeded deployment in-flight slots.
- The live provider evaluation remains an operator step.
- Residuals pending human confirmation: reload spends another call; free demo workspaces can consume the deployment allowance.

## Problems

- The first full suite failed because Playwright was missing from the shared virtualenv; installing the already-pinned `requirements-dev.txt` fixed it.
- A `git push` was rejected under the session's approval policy; after the human restarted with prompting enabled, the pushes succeeded.
- The first implementation branch exceeded the slice budget when gateway and drafting were combined; it was split into separate commits.
- Independent reviews found real defects that the focused tests missed, including the deep-nesting crash and over-cap response escape; both were repaired and re-reviewed.
- This log has not been checked by its human author.
