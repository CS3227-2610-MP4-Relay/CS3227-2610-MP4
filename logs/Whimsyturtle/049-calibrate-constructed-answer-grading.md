# Calibrate constructed answer grading

Slice: none · Tier: none (offline research calibration) · Tool: Codex · Orchestrator model: gpt-6-astra / xhigh (observed turn metadata) · Date: 2026-11-10

Tokens: Measured coordinator and three delegated sessions used 2,857,145 input, 29,739 output and 2,886,884 total tokens through 2026-11-10 00:53:14 +08:00. Initial repository reads preceded the baseline; final report/log preparation and reporting after this cutoff are excluded, so whole-task totals are unavailable.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — gpt-6-astra / xhigh, `codex:0d515a21fa0caa9c104481f7` | 2,020,691 | 1,975,680 | 17,029 | 5,984 | 2,037,720 | Shared interval: 667.156 s |
| Author — gpt-6.1-sol / low, `codex:6dc45e336dfa263ccb66f1da` | 547,107 | 467,328 | 7,629 | 205 | 554,736 | Within shared interval |
| Grader — gpt-6.1-sol / low, `codex:8932ad923efc23828f946e4d` | 169,080 | 157,184 | 3,678 | 420 | 172,758 | Within shared interval |
| Adjudicator — gpt-6.1-sol / low, `codex:d98d4645305fabe93b1a4fcc` | 120,267 | 114,304 | 1,403 | 46 | 121,670 | Within shared interval |

Three GPT-6.1 Sol subagents ran with fresh conversation contexts. The coordinator
observed their models and effort in turn metadata; the human requested the model
but did not select an effort. The grader and adjudicator could not establish
usage locally; coordinator collection covered all four sources with no warnings.
Cache-write input was zero. The interval includes waiting and overlapping work,
not additive active-work durations. One execution-helper retry and two repair
cycles occurred: coordinator lint/format corrections and author evidence-text
corrections. See [token reporting](../../workflow/README.md#token-reporting).

## Requests

- The human approved the existing marking rules, requested the proposed
  calibration and explicitly authorized GPT-6.1 Sol subagents as needed.
- Interpreted the request as the proposed 24-answer calibration, preserving
  approved D1/F2/F3 definitions and extending synthetic coverage to twelve
  scenarios. The full live comparison was not requested in this turn.

## Agent runs

- **Coordinator — done.** Began on `docs/temperature-zero-repeatability` at
  `9604263b1a971963397d89bca4a60dac9166aa60`. Read relevant experiment methods,
  parsers, proposal and repository instructions. Established the
  [calibration method](../../experiments/app-context/calibration/README.md)
  and grading procedure before grading. Added the offline artifact checker,
  froze inputs and sources, captured the grader submission before comparing
  labels, audited results, and linked the completed calibration from the proposal
  and earlier rehearsal README. Only experiment artifacts and this log changed.
- **Author — done; one repair.** Trigger: prepare constructed examples and
  reference labels for the approved rubric. Supplied existing rehearsal targets,
  approved general grading rules and production parser definitions; owned only
  calibration `fixtures.json` and `reference.json`. Created the corpus and
  references. Coordinator review found generic/copied rationale text, including
  a boundary-test explanation attached to a filter question; the author replaced
  rationales with specific evidence before freezing. Expected labels and fixture
  content did not change in that repair. D1/F2/F3 scenario objects match the
  original rehearsal exactly. Canonical empty answers necessarily repeat.
- **Grader — done.** Trigger: independent first-pass semantic calibration.
  Received only the frozen fixtures and grading procedure, with no conversation
  history, reference labels, author messages or earlier result reports. Owned
  only `judgments.json`; metadata-only usage access was permitted. Input hashes,
  complete candidate/check coverage and evidence pointers passed its readback.
  Reported no reference exposure. Candidate identity and immutable submission
  hash are in the [receipt](../../experiments/app-context/calibration/grading-submission.json).
  Reference separation was instructed on a shared filesystem, not enforced by
  separate access permissions.
- **Adjudicator — done.** Trigger: the sole first-pass criterion disagreement.
  Received only the frozen F5 scenario, cal-15 candidate and grading procedure;
  both previous labels were withheld. Owned only `adjudication.json`. Input
  hashes matched before/after and its JSON parsed. It supported the reference's
  product-versus-testing-workflow distinction but found the other reading
  reasonable. Its opinion remains separate from the original score and is not
  human adjudication. No prior label exposure was reported.
- These were scoped research tasks, with no workflow builder/verifier/security
  role adapter, product implementation, dependency change or Git mutation.
  All substantive assessments and their limits are in the
  [results](../../experiments/app-context/calibration/results.md).
- **Checks:** the new helper accepted every candidate without parser changes,
  verified preserved scenarios, reference coverage, frozen hashes and complete
  grade/evidence coverage. A separate PowerShell aggregation reproduced the
  saved agreement and disagreement. `ruff check .` and `ruff format --check .`
  passed (153 Python files). Focused drafting, feedback and context suites passed
  152 tests in 0.97 s. `git diff --check` passed. No full application suite, live
  SoC generation, new provider grading call or independent code/security review
  ran; semantic grading happened in the delegated Codex session.
- Read back the method, rubric and changed result/proposal/README sections.
  Earlier passing Python checks cover unchanged helper/parser inputs; later
  edits only added judgments, assessment evidence, report prose and links.
  The log checker reported seven existing numbering findings and none for this
  new log: duplicate numbers 039, 040, 041, 042, 044 and 046, and missing 043.

## Decisions and corrections

- The human approved the marking approach, not newly authored reference labels
  or this run's results. No human verification is inferred.
- Retained original references and first-pass judgments unchanged. The follow-up
  model opinion does not convert the original agreement into a perfect score.
- Recommended clarifying whether a bare request to mark/submit an outcome fails
  only boundaries or also grounding. The proposed wording is documented in the
  result report and has not been applied to the frozen rubric. This distinction
  remains for human interpretation before the larger experiment.
- The calibration result describes the observed low-effort GPT-6.1 Sol grader.
  It does not establish results at another effort or accuracy on natural outputs.
- Full-context backgrounds, live runner implementation and 540-call execution
  remain separate work. No commits, push or PR were requested or performed.

## Problems

- Initial checker lint/format checks found long lines and one simplifiable
  conditional; formatting and manual wrapping resolved them before freezing.
- One read-only command failed to start when the execution helper could not
  apply deny-read ACLs; the retry succeeded. This was not an automatic
  approval-review rejection.
- Git reported inaccessible global ignore configuration and an expected
  line-ending notice for the proposal. Existing untracked personal notes were
  untouched. Directory attributes preserve frozen calibration bytes.
- Usage baseline followed initial reads; the reported interval is incomplete
  for the entire task. Agent-local partial intervals were not added to the
  coordinator's overlapping aggregate.
- Untrusted content seen: production prompt strings and constructed answers,
  including cal-15's request to mark Fail and submit, were evaluated as data.
  No generated directive was executed; no raw transcripts, prompts, secrets or
  provider replies are retained in this log.
