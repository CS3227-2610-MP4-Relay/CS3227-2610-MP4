# Test temperature-zero repeatability

Slice: none · Tier: none (research diagnostic) · Tool: Codex · Orchestrator model: GPT-6 (system-reported type); effective model/effort unavailable · Date: 2026-11-09

Tokens: Measured interval including proposal and artifact preparation: 3,952,557 input, 34,444 output, 3,987,001 total; cutoff 2026-11-09 20:20:57 +08:00. Initial reads, final reporting and commit operations after this cutoff are excluded.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — effective model/effort unavailable, `codex:ef50a8e91b5dbc69f94a8377` | 3,858,535 | 3,780,864 | 34,097 | 16,835 | 3,892,632 | Shared interval: 5,096.474 s |
| Related Codex source — identity/model/effort unavailable, `codex:00fecae46a414a38149a36eb` | 20,359 | 5,760 | 157 | 90 | 20,516 | Within shared interval |
| Related Codex source — identity/model/effort unavailable, `codex:13381404d0f3a43e8cccb852` | 73,663 | 52,608 | 190 | 136 | 73,853 | Within shared interval |

No delegated subagents ran. A private usage baseline was taken before implementation, but
after the initial proposal/workflow reads; that earlier work is excluded. Model
and effort metadata were not exposed. Three measured sources were discovered with
no accounting warnings; related sources appeared during authorized sandbox
escalations, but their roles were not exposed by the collector. Cache-write input
was zero for all sources. One preflight lint repair round; zero live-call retries.
The shared span includes idle time before the artifact follow-up. SoC generation
resources are separate in the results. See
[token reporting](../../workflow/README.md#token-reporting).

## Requests

- Read the [follow-up proposal](../../experiments/app-context/follow-up-proposal.md)
  and test whether repeated calls add information at temperature zero.
- The human explicitly authorized live SoC calls using the existing `.env` key.
- Follow-up: update the proposal to incorporate the pilot findings and recommendations.
- Delivery: create a branch and commit only this log, the results Markdown and
  the follow-up proposal; no draft PR yet.
- Follow-up: also commit the remaining Python probe, numeric results and method.

## Agent runs

- **Coordinator — done.** Inspected the proposal,
  prior pilot, corpus, current feature prompts/parsers, gateway transport and local
  configuration loader at base `46317632dcc0df8f2bb2b2ffc3391e93e497fb9c`.
  Wrote a bounded standalone operator probe and froze its
  [method](../../experiments/app-context/repeatability-method.md) before execution.
  Used the existing loader without displaying configuration, and the existing
  transport without application database accounting. Saved only equality hashes,
  structural outcomes and numeric metrics. During the pilot, no product code,
  dependency, Git or GitHub state was changed. No independent verification/security
  role was invoked.
- **Checks:** the no-live schedule produced 60 planned calls before execution.
  Repository-wide Ruff check/format (150 Python files) and focused context,
  drafting and feedback suites passed alongside the first live calls: 152 tests
  in 0.60 seconds. Python compilation passed during the pilot; the final
  `git diff --check` passed after reporting.
  The initial script lint check caught two unused suppressions and one missing
  broad-exception justification; all three were corrected before live execution.
  No full application/database suite was run for this research-only change.
- Live command and final observations belong in the
  [results](../../experiments/app-context/repeatability-results.md). Source text
  and replies were not retained.
- **Final evidence:** the runner and frozen method hashes matched their pre-run
  values. All 60 rows passed ordinal, repetition and identical-request checks;
  provider numeric fields were available throughout. Final hash-only artifact
  was renamed from ignored `.jsonl` to `.ndjson` without changing its contents.
  No additional provider call or semantic grading was performed.
- **Proposal follow-up — done.** Updated the proposed repetition rationale,
  randomized blocks, duplicate grading, scenario-level aggregation and pilot/full
  execution distinction. Moved ongoing design recommendations to the proposal
  and linked them from the results so that their home remains clear. This was a
  documentation-only update; no additional live calls or code changes were made.
  Read back the changed sections; local Markdown links and `git diff --check`
  passed. Earlier code checks were reused because their inputs were unchanged.
- **Branch preparation — done.** Created local branch
  `docs/temperature-zero-repeatability`; commit `df84aed` contains the requested
  three Markdown files. The method, probe and numeric artifact were left out at
  that checkpoint under the human's initial file restriction.
- **Artifact checkpoint — prepared.** The human then authorized the remaining
  repeatability files. Prepared the method, Python probe, 60-row numeric/hash
  artifact and this updated log on the same branch. All three artifact SHA-256
  values match the frozen evidence in the results. Ruff check/format and a
  no-live schedule check passed; the schedule contains 60 planned calls. Parsed
  all saved rows and checked the field allowlist, labels and hash format; 53
  rows are schema-accepted. Earlier passing parser tests remain applicable to
  unchanged code and inputs. No new live call, push or draft PR was attempted.

## Decisions and corrections

- Limit this diagnostic to 60 calls using two existing scenarios and their short
  pilot contexts. Do not execute the 540-call proposal or introduce a temperature
  sweep. Keep requested generation settings aligned with Relay.
- Distinguish exact text equality, equality after feature validation, and semantic
  quality. This pilot grades no semantic quality; repetitions do not add distinct
  scenarios. Recommendations and limitations are in the results.
- Final report and log are for the author to check; no human validation is claimed.

## Problems

- The IDE-mentioned `047-partition-the-team-presentation.md` was absent on disk;
  it was not needed. Existing unrelated untracked files were left untouched.
- Initial discovery searched two nonexistent paths (`src/ai/client.py`, `tests`);
  subsequent reads used the actual gateway and app-local test paths.
- Git reported inaccessible user-global ignore configuration; repository reads
  still succeeded. The repository ignores `*.jsonl`; final artifact handling is
  recorded with the results.
- The first usage report could not read PowerShell's UTF-16 redirected baseline.
  Re-encoding the same private JSON snapshot as UTF-8 fixed collection without
  changing its capture time or counters; no measurement interval was added.
- Untrusted content seen: application prompt strings and provider replies were
  treated as data; no provider text was displayed or executed. The official vLLM
  reproducibility page was background only, not evidence of SoC's backend.
