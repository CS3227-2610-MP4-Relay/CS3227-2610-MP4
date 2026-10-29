# Apply targeted workflow improvements

Slice: workflow-targeted-improvements · Tier: High · Tool: Codex · Orchestrator model: gpt-6-astra, xhigh (observed runtime metadata) · Date: 2026-10-26

Tokens: measured subtotal: 2,282,852 input, 16,396 output, 2,299,248 total through 2026-10-26 11:29:04 SGT; full aggregate unavailable.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `gpt-6-astra/xhigh`, `codex:b3e027020fbb7a08fb7916d1` | 1,512,698 | 1,476,736 | 12,734 | 1,784 | 1,525,432 | 9m08s measured interval |
| `verify_improvements` — `gpt-6.1-sol/low`, `codex:6b77652042e99f23f900134c` | 395,277 | 342,272 | 1,945 | 200 | 397,222 | 3m07s |
| `security_improvements` — `gpt-6.1-sol/low`, `codex:97ec54f3ba6e3bd8d3893d5b` | 374,877 | 337,920 | 1,717 | 86 | 376,594 | 2m53s |
| Automatic approval reviewer — codex-auto-review/low, `codex:0ff9dabf5f9b6259e9bea07f` | unavailable | unavailable | unavailable | unavailable | unavailable | Within original measured window |

Two delegated subagents, each with an initial review and one repair follow-up in the same source; models/efforts come from runtime metadata. Session envelope to cutoff: 11m36s. One review repair round. The coordinator baseline at 11:19:56 SGT excludes initial instruction/repository inspection; final delivery annotations and work after the cutoff are also excluded. Retrospective discovery adds an initialized automatic approval source with unavailable counters; the measured subtotal is unchanged and the aggregate is unavailable (`session_initialized_without_usage`). Available cache-write counters are zero. See [the audit](018-audit-historical-token-counts.md) and [token accounting](../../workflow/README.md#token-reporting).

## Requests

Assess five proposed improvements, implement suitable ones and preserve MP4's resource efficiency relative to MP3. The human explicitly authorized GPT 6.1 Sol subagents as needed. The request identified an incomplete-telemetry reproduction, unclear development-security specialist trigger, missing storage-exhaustion planning question, incomplete log-format validation and missing MP3 acknowledgement. It did not establish historical usage undercount.

## Agent runs

The [plan](../../workflow/plans/workflow-targeted-improvements.md) records scope, decisions, spec-before-code ordering, regression evidence and checks. Coordinator-owned workflow maintenance was used because script/skill files are outside the builder's write scope; no builder agent ran. No role write permissions were broadened.

| Run | Trigger and supplied context | Actual work and outcome |
| --- | --- | --- |
| Orchestrator | Human request; AGENTS.md; slice/log workflows; relevant collector/checker tests, specs, guide and MP3 source identity | Assessed all five as suitable in narrow form, wrote plan/spec wording before regression tests and code, implemented fixes, ran checks and coordinated reviews. Preserved preexisting untracked reference documents. |
| `verify_improvements`, initial | High-tier independent review; focused paths/request, fixed manifest, scope and supplied pre/post-fix check evidence; no conversation fork | Read source/assertions and checked candidate unchanged. Found a medium first-event telemetry fallback defect; no other scope or documentation findings. |
| `security_improvements`, initial | High-tier trigger clarification; focused touched controls, same candidate and supplied checks; no conversation fork | Inspected security effects and checked candidate unchanged. No security/scope findings; deferred final conclusion until verifier repair was reviewed. |
| `verify_improvements`, follow-up | Repaired fallback, new failing-then-passing test, updated manifest/check evidence | Inspected changed range/effects, confirmed previous finding resolved and candidate unchanged; no remaining findings. |
| `security_improvements`, follow-up | Same focused repair and new candidate evidence | Inspected repair effects and candidate unchanged; no introduced security issue. |

Both reviewers reused current full-suite evidence without rerunning it. They independently inspected source and assertions; they did not independently execute the supplied suite. Coordinator post-run scope checks passed for both roles against both fixed candidates.

Role SHA256 values: verifier `4BC2941A5D0D38C3C0FEFB75C5D21D585D23D854AB9132D4DB7C14F834E3B722`; security-reviewer `3E7EE3DA2A29FB009FCE10FDA3381E0032528C83ABA53E5BC7513AA1F1697598`.

Candidate base/HEAD: `95f22ab6dd59c62e5037f4e7f8caf6fe80e57fde`. Initial manifest SHA256: `167B6125A5585D6E77946F9F21D5E5F315CAAE6E611C59232A9581E7A90A3022`; repaired manifest: `185F04A6EDE941314494AC593F61D8980493FBB804FFCD9F79B35199356643AE`. Manifests are outside the repository. Both candidates include the nine changed implementation/test/spec/guide files and the new plan.

Checks actually run:

- Before fixes: cumulative-focused unittest discovery failed 11 subcases; log-checker discovery failed 10 subcases. After fixes: collector 33 tests and checker six tests passed.
- Review repair: `test_first_partial_cumulative_event_cannot_restore_missing_counters` failed with `10 is not None`, then passed after masking missing fields through the inherited-history fallback.
- Final integrated candidate: `ruff check .` and `ruff format --check .` passed; `pytest` reported 69 passed, one skipped in 7.67s; `python -m unittest discover -s workflow/scripts` ran 70 tests with the same skip in 7.36s; `python workflow/scripts/check_logs.py` reported zero findings; `git diff --check` passed. Environment: existing MP4 `.venv`, Python 3.14.2, Ruff 0.17.0, pytest 9.1.1, pytest-django 4.14.0. The existing Windows symlink-privilege skip remains.
- Manual document readback found no lost rules, duplicated headings or built-product claims. The MP3 acknowledgement target was identified from the local baseline's remote URL and commit; hosted accessibility was not checked.

## Decisions and corrections

All five suggestions were implemented within the narrow scope in the plan. The specialist trigger depends on a change's effect on development security controls; ordinary workflow prose does not acquire a specialist requirement by filename. The persistence addition preserves a design question without prescribing or implementing cleanup. Log validation checks structure, not telemetry truth or whether every agent was listed.

Implementation/tests/documentation changed 225 lines excluding the plan and log. Changes use existing scripts and dependencies, with no extra recurring agent roles or universal review gate. Specialist work adds per-change cost when a development security control is affected; there is no benchmark establishing long-term workflow savings. This session used two focused reviewers and repeated full verification only after the verifier's repair changed code. No historical telemetry undercount is claimed.

Human diff/log review remains pending. No commit, push, merge, deployment or GitHub administration was requested or performed.

## Problems

- The verifier found one medium telemetry defect in the first candidate, repaired and re-reviewed as described above. No unresolved review findings.
- An initial Ruff run failed on three overlong Markdown fixture literals; splitting the literals preserved test content and fixed lint.
- Initial inspection attempted nonexistent orchestrator/initialization-log paths and a PowerShell wildcard argument rejected by `rg`; corrected by listing existing paths. MP3 read-only Git inspection initially refused dubious ownership; a one-command `safe.directory` setting permitted the specifically named source without changing global configuration. Git also warned that its user-level ignore file was inaccessible; no claim that it was read.
- Initial inspection is outside the recorded usage interval. Child counters were collected centrally; reviewer-local numeric reports were unavailable. The original final collector report had no telemetry warnings; the retrospective coverage above includes an additional initialized source.
- Native client hook enforcement was not exercised; the task changed review policy, not hooks or permissions. Synthetic telemetry was used; no real secrets, raw transcripts or malicious instruction attempts were retained.
