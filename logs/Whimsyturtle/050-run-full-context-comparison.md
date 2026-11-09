# Run full context comparison

Slice: none · Tier: none (operator research) · Tool: Codex · Orchestrator model: gpt-6-astra / xhigh (observed turn metadata) · Date: 2026-11-10

Tokens: 58,743,504 input, 272,909 output, 59,016,413 total; baseline 2026-11-09 17:28:56 UTC to cutoff 20:05:31 UTC.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Coordinator — gpt-6-astra / xhigh, `codex:0d515a21fa0caa9c104481f7` | 36,975,855 | 36,545,024 | 147,392 | 46,765 | 37,123,247 | shared 2h 36m 35s interval |
| Supplementary reviewer (reused adjudicator) — gpt-6.1-sol / low, `codex:d98d4645305fabe93b1a4fcc` | 146,947 | 143,872 | 2,425 | 115 | 149,372 | shared 2h 36m 35s interval |
| Automatic approval review 1 — codex-auto-review / low, `codex:601382ec782038bfb52fec40` | 236,821 | 207,616 | 670 | 181 | 237,491 | shared 2h 36m 35s interval |
| Input author — gpt-6.1-sol / low, `codex:3c9472ffc9f3fb3de79d2df2` | 379,173 | 343,808 | 4,933 | 42 | 384,106 | shared 2h 36m 35s interval |
| Runner author — gpt-6.1-sol / low, `codex:d26419d53bcdcbbb8dae608c` | 2,530,537 | 2,452,096 | 15,514 | 423 | 2,546,051 | shared 2h 36m 35s interval |
| Analysis and results author — gpt-6.1-sol / low, `codex:73f01df57f3b94bc0772da26` | 2,691,089 | 2,632,064 | 21,514 | 1,106 | 2,712,603 | shared 2h 36m 35s interval |
| Automatic approval review 2 — codex-auto-review / low, `codex:4925cdfcb52bf8be0f81c7ac` | 1,388,116 | 1,290,112 | 2,004 | 713 | 1,390,120 | shared 2h 36m 35s interval |
| Verifier — gpt-6.1-sol / high, `codex:c9a83acded2f85748d05ffbb` | 2,719,407 | 2,613,120 | 11,883 | 2,876 | 2,731,290 | shared 2h 36m 35s interval |
| Security reviewer — gpt-6.1-sol / high, `codex:700d69871d573abdde01cb42` | 1,438,766 | 1,317,760 | 4,441 | 1,108 | 1,443,207 | shared 2h 36m 35s interval |
| Drafting grader — gpt-6.1-sol / low, `codex:ceaf5866876c7d93b5ea20de` | 4,002,616 | 3,950,720 | 31,544 | 544 | 4,034,160 | shared 2h 36m 35s interval |
| Feedback grader — gpt-6.1-sol / low, `codex:c9e91416d84a48adad6e5813` | 5,808,063 | 5,702,016 | 29,525 | 156 | 5,837,588 | shared 2h 36m 35s interval |
| Automatic approval review 3 — codex-auto-review / low, `codex:6a0d59456b63c63daa7efeb7` | 426,114 | 388,992 | 1,064 | 300 | 427,178 | shared 2h 36m 35s interval |

Eight delegated sessions ran (seven new and one reused), alongside three automatic
approval-review sources. The recorded wall interval was 9,395.352 seconds; table
spans identify that shared measurement window, not individual active durations.
Observed model/effort metadata supplies the labels above. All selected counters
were available, with no telemetry warnings and zero measured cache-write tokens.
Two discovered prior-calibration sessions had no interval activity and are omitted
from the table. Initial repository reads and work after the cutoff, including
this final log update/commit and final response, are excluded.

Primary grading alone used 9,810,679 input and 61,069 output tokens
(9,871,748 total, including 9,652,736 cached input); supplementary review used
149,372 total. These Codex measurements are separate from the provider-generation
usage in the [results report](../../experiments/app-context/full-comparison/results.md).
Cached input is included in input, and reasoning output in output; see
[token accounting](../../workflow/README.md#token-reporting). Generation made
540 attempts with zero retries. Runner/analysis repairs and review rounds are
recorded below; no system-wide retry total is inferred from unavailable telemetry.

## Requests

- The human accepted the calibration clarification: requests to mark or submit
  outcomes fail boundaries, and fail grounding only when they also assert
  unsupported product facts. Original references, judgments and 97/98 agreement
  remain unchanged.
- Requested small cohesive commits, full comparison implementation and the
  experiment run. Existing permission to use GPT-6.1 Sol subagents continued.
- This authorized the proposed 540 calls and local commits, without a push,
  pull request, production change, dependency or new credential.

## Agent runs

- **Coordinator.** Committed the preceding calibration in four units:
  `3469fc7` corpus/references, `7e73dd2` offline audit/freeze, `70273dd` results
  and accepted clarification, and `23ba3b8` calibration log. Preserved unrelated
  untracked notes. Read the slice workflow for review discipline; this operator
  research changes no product behaviour and used scoped research workers rather
  than a feature builder. Took the usage baseline after initial repository reads.
- **Input author.** Trigger: prepare the authorized comparison's inputs and
  protocol before implementation. Supplied proposal, calibration scenarios and
  clarification, production prompts and limits. Owned method, rubric, backgrounds,
  README and directory attributes. Composed 486-word app clutter and 491-word
  off-topic text without length tuning. JSON parsing, word counts, readback and
  diff whitespace checks passed. No live calls.
- **Runner author.** Trigger: implement frozen, bounded serial execution.
  Supplied the method, production gateway/parsers and synthetic scenario source.
  Owned runner and its offline tests. Coordinator inspection repaired escaping
  interruption accounting; security review repaired offline settings initialization;
  final repair made artifact newlines explicit. Final focused suite: 12 passed.
- **Analysis author.** Trigger: audit safe metadata and aggregate repeated calls
  according to the method. Owned analyzer and its offline tests. Review found the
  schema-error allowlist differed from the production parser; repaired with an
  actual-parser regression. Explicit LF output was the final repair. Final
  focused suite: 22 passed. No live calls.
- **Verifier and security reviewer.** Trigger: independent review of the fixed
  research candidate, before live execution. Supplied method, changed files,
  relevant production contracts and scope snapshot. Role files were the unchanged
  `workflow/agents/verifier.md` and `security-reviewer.md` at `ecb647f`.
  Initial candidate HEAD
  `23ba3b8`, snapshot SHA-256
  `8a8e51fd66096a9fa44c72c1d0b723955ba40639081204167b9d64aae61e5119`.
  Both found the parser/analyzer error-code mismatch; security additionally found
  that inherited local settings could load dotenv during offline preflight.
  Repaired candidate snapshot
  `fc5fc89697cb00406f4b8d75c5a1cdc8386bf82e4033be0fc5c05d3bedda6215`
  passed their 34 focused checks with no remaining findings.
- **Narrow newline review.** Coordinator identified Windows newline conversion
  as a freeze reproducibility risk. Both reviewers inspected the three-file
  repair at HEAD `d4ebdc7`, snapshot
  `f132d4f04950235d02abb7ef80b9600c0b67bf889a89032d68a8e0fddf0eeb8d`.
  Security independently passed two LF/overwrite/budget/privacy checks. The
  verifier found no new issue but did not capture its independent repeat's final
  exit; no completed verifier rerun is claimed. Scope and snapshot checks passed.
  Security review is limited to these candidates and recorded repair ranges.
- **Drafting and feedback graders.** Trigger: assess parser-accepted live answers
  using the frozen scenario-specific rubric. Fresh GPT-6.1 Sol contexts received
  only their feature's scenarios/checks, rubric and opaque candidate IDs with
  transient candidate JSON. Model/condition labels, calibration examples and
  reference labels were withheld. Workers own separate judgment files; only
  paraphrased reasons and evidence pointers are saved. Coordinator audits every
  pointer against transient candidate content. All 321 distinct candidates were
  assessed: 122 drafting candidates with 429 checks, and 199 feedback candidates
  with 959 checks, across 70 files. No judgment was unavailable. Exact duplicates
  within a cell reused the first assessment at their observed frequency.
- **Runner's limited grading handoff.** Root briefly delegated stream monitoring,
  but unified exec session IDs were inaccessible from that worker. The first
  read failed without consuming output; no access retry or provider invocation
  occurred. Root retained sole stream polling. The worker coordinated and
  independently audited the twelve already-transferred batch-08 candidates
  (50 criteria), then returned control. Transient stores were also confirmed
  agent-local, so subsequent handoffs continued through escaped tool messages.
- **Supplementary reviewer.** The feedback grader flagged a different grounding
  interpretation for two similar F6 answers. Reused the prior calibration
  adjudicator's session, supplying only F6, the current rubric and those two
  opaque candidates; full-comparison labels and mappings were withheld. Its
  ten judgments differed from first-pass labels on two checks (one grounding,
  one redundancy), while both answers still failed coverage. It recommended
  consistent grounding treatment but acknowledged ambiguity in retrospective
  question presuppositions and overlapping questions. The separate review
  preserves every first-pass judgment and changes no frozen rule. Coordinator
  evidence-pointer audit passed. One metadata-only repair replaced an inaccurate
  fresh-session description with the actual reused-session identity.
- Implementation checkpoints: `8507149` protocol/inputs, `33702b2` runner and
  tests, `d4ebdc7` analyzer and tests, `0302c76` newline repair, `ecb647f` frozen
  requests. Explicit paths, staged diff, stat and numstat were inspected before
  each commit. Git was not mutated while agents edited or reviewed candidates.
- Frozen manifest SHA-256:
  `8e15a0112868c6a237860d29262f0e9c71e900332f92a5bb5e8221baa0024934`.
  Offline CLI smoke accepted the actual manifest and an empty partial dataset;
  staged manifest bytes matched the working artifact. Live execution launched
  once with explicit `--live --show-candidates --output`, without redirected
  candidate output. It exited successfully after exactly 540 attempts, without
  retries: 465 schema-accepted, 54 provider/gateway failures and 21 schema
  failures. The strict full-run analysis passed. All 1,388 primary evidence
  pointers and ten supplementary pointers resolved against transient candidates.
  The [audit receipt](../../experiments/app-context/full-comparison/grading-audit.json)
  preserves artifact hashes and audit coverage. Across 300 distinct exact-text
  groups, including 14 shared across cells, no identical-answer criterion vector
  conflicted. A limited twelve-word overlap scan found no copied answer passage
  in saved grading reasons.
- **Results author.** Reused the analysis worker after all primary grading
  finished and model/context mappings were released for analysis. Supplied the
  retained measurements, summary, judgments, audits and coordinator's safe
  example paraphrases. Wrote the [results report](../../experiments/app-context/full-comparison/results.md),
  recalculated tables and supplementary frequencies, checked example mappings
  and read the report back. Coordinator corrected the source attribution to
  include attempt measurements alongside the summary. No frozen input changed.
- **Results verifier.** Reviewed HEAD `ecb647f` plus results snapshot
  `1328f3c152ffd7f0bf6b93a0eda26257e38bcc455821cdde1868894451a9312c`.
  Independently reproduced the summary byte for byte, checked all audit hashes,
  and reconciled 66 table rows and 354 numeric fields with zero mismatches.
  Criterion prose, example mappings and supplementary changes matched retained
  evidence. No substantive report finding remained. The verifier could not
  independently establish raw-specific paraphrases or transient pointer checks
  from retained hashes; the report states this limit. Its initial whole-tree
  checks flagged a concurrent browser artifact; after coordinator cleanup,
  verifier scope and unchanged-candidate checks both passed. Full-suite evidence
  remains coordinator-owned.
- Results were committed after execution and review in separate units:
  `27620f2` measurements, `fa3736b` drafting judgments, `a6f54dd` feedback
  judgments, `92e228c` supplementary review, `6377c3b` analysis/audit and
  `7c812ef` report/navigation. These are post-run artifact commits, not evidence
  of incremental implementation. Staged diffs, stat and numstat were inspected;
  the large measurement diff was inspected through parsed added rows and matching
  staged/working blob identities after an initial output capture was truncated.
  The 540-line measurement file was force-staged by its exact path. No push or
  pull request was made. The automatic approval sources reviewed authorized
  local Git/test-environment operations; the requested escalations were approved.

## Decisions and corrections

- The [method](../../experiments/app-context/full-comparison/method.md) is the
  run's home for schedule, settings, retention, grading and aggregation. It was
  frozen before execution and remained unchanged throughout the run.
- Kept all existing production gateway quotas, parsers and prompts unchanged.
  The separate operator runner uses direct existing transport. Model IDs are
  requested identifiers; the team-provided `x-test-2` mapping is not an observed
  backend identity. Provider-effective settings are unavailable.
- Preserve original calibration history and pilot results. Live judgments are
  model assessments, and repeated calls measure within-cell variation; neither
  is human validation or evidence of deterministic output.
- Next: human review of the reported grading ambiguity and selected examples,
  then a focused prompt change and newly frozen evaluation if authorized. The
  current experiment is complete; its results remain the comparison baseline.
- Raw replies pass only through escaped JSON stdout and transient coordinator/
  grader context. No candidate files, raw replies or transcript excerpts are
  retained in repository artifacts.

## Problems

- Docker was unavailable. Used the already installed PostgreSQL 17 binaries to
  create an isolated temporary cluster on loopback port 55432 with synthetic test
  data. Initial sandboxed initdb failed with restricted-token error 87; approved
  escalation succeeded. No dependency was installed or existing server changed.
- Initial full-suite attempt encountered TLS fixture setup failures because
  pytest could not access its shared Windows temporary directory (WinError 5).
  Interrupted that attempt without claiming a final count. Native certificate
  helper checks passed; moving pytest's base/cache directories into ignored
  workspace paths resolved the environment failure. TLS suite: 69 passed.
- Full Ruff lint/format and pytest then passed: 3,228 passed, 5 skipped in
  930.62 seconds. That suite started before the final LF-only patch; the final
  candidate separately passed all 34 focused tests. Final post-run verification
  on the completed implementation passed Ruff lint/format (157 files) and pytest:
  **3,228 passed, 5 skipped, 1 warning in 950.60 seconds**, exit 0. It used a
  fresh workspace base directory and recreated the isolated test database.
  The warning was inability to write pytest's cache nodeids; no test failed.
  The temporary PostgreSQL cluster was then stopped successfully.
- A security-review test invocation created synthetic files in an unignored
  directory despite the read-only role. Coordinator verified its resolved path,
  removed that exact directory and rechecked the fixed snapshot/scope. Source
  files were unchanged; later reviewer artifacts used ignored temporary paths.
- Git warned that global ignore configuration was inaccessible. Measurement
  JSONL is covered by a pre-existing ignore pattern and was staged by exact
  forced path. Unrelated personal notes remain untouched.
- `python workflow/scripts/check_logs.py` exited 1 with seven pre-existing
  findings outside this task: duplicate 039, 040, 041, 042, 044 and 046, and
  missing 043. No unrelated numbering repair was made.
- During browser verification, a new untracked root `debug.log` appeared at
  19:52:58 UTC. Metadata timing and the extracted module marker
  `shared_image_manager.cc:401` identify a browser diagnostic artifact; its
  message text was not printed or retained. This caused the results review's
  initial whole-tree/scope checks to fail even though all 83 reviewed experiment
  files and the measurement hash matched. Coordinator verified the exact path,
  removed that generated file and reran both checks successfully.
- Untrusted content: production prompt strings and live candidate answers were
  evaluated as data. Generated instructions were not executed. Raw transcripts,
  prompts, secrets and provider replies are excluded from this log.
