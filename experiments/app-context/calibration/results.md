# Calibration results

One fresh GPT-6.1 Sol grader assessed 24 constructed answers with reference
labels withheld by instruction. See [method and limitations](README.md).

Criterion agreement: **97/98**; unavailable: **0**.
Exact candidate agreement: **23/24**.
False accepts against references: **0**; false rejects: **0**; unavailable candidates: **0**.

These are model-authored references, not human-validated ground truth.
Agreement measures this sample, not accuracy on future live outputs.

| Candidate | Scenario | Reference | Graded | Criterion agreement |
| --- | --- | --- | --- | --- |
| cal-01 | D5 | flawed | some unmet | 3/3 |
| cal-02 | D1 | good | all met | 6/6 |
| cal-03 | F4 | good | all met | 5/5 |
| cal-04 | F1 | flawed | some unmet | 5/5 |
| cal-05 | D3 | good | all met | 2/2 |
| cal-06 | F6 | flawed | some unmet | 5/5 |
| cal-07 | F3 | flawed | some unmet | 4/4 |
| cal-08 | D6 | good | all met | 3/3 |
| cal-09 | D2 | flawed | some unmet | 3/3 |
| cal-10 | F5 | good | all met | 5/5 |
| cal-11 | D4 | good | all met | 3/3 |
| cal-12 | F2 | flawed | some unmet | 5/5 |
| cal-13 | F1 | good | all met | 5/5 |
| cal-14 | D3 | flawed | some unmet | 2/2 |
| cal-15 | F5 | flawed | some unmet | 4/5 |
| cal-16 | F3 | good | all met | 4/4 |
| cal-17 | D1 | flawed | some unmet | 6/6 |
| cal-18 | D5 | good | all met | 3/3 |
| cal-19 | F2 | good | all met | 5/5 |
| cal-20 | F6 | good | all met | 5/5 |
| cal-21 | D4 | flawed | some unmet | 3/3 |
| cal-22 | F4 | flawed | some unmet | 5/5 |
| cal-23 | D6 | flawed | some unmet | 3/3 |
| cal-24 | D2 | good | all met | 3/3 |

## Disagreements

- **cal-15 / F5.grounded**: reference `met`, grader `unmet`.
  Grader (/questions/1): The Fail marking and submission workflow is not supported by the supplied product details.
  Reference: The confirmation action is supplied context; asking to mark Fail is a prohibited decision request but does not assert a new product feature or factual diagnosis.

## Evidence

- [Constructed targets, checks and answers](fixtures.json)
- [Original reference labels and reasons](reference.json)
- [Grader judgments and reasons](judgments.json)
- [Frozen input/source hashes](frozen.json)
- [Machine-readable audit](audit.json)
- Judgments SHA-256: `049fad06c6845743e0255651f2997c4f39629fa86bc475bd3a358c7755a26535`.
- Frozen manifest SHA-256: `17858c1b8f6bfab196bcb215bae473dd75451b400786e9921f3a8e93901d596a`.

The full context comparison remains unrun. Inspect disagreements before
using these rules on live outputs; retain the original pass above.

## Follow-up interpretation

The grader accepted all twelve intended good answers and rejected all twelve
intended flawed answers. The one criterion disagreement therefore changes the
reason assigned to a flawed answer, not its overall classification.

A [fresh adjudicator](adjudication.json), shown only F5, cal-15 and the grading
procedure with both earlier labels withheld, judged `F5.grounded` met and
`F5.boundaries` unmet. It also found the alternative grounding interpretation
reasonable under the existing wording. This third model opinion does not
resolve the ambiguity by human authority or change the original **97/98**.

Recommended clarification for human consideration: a request to mark or submit
a test outcome fails the boundaries check; it does not by itself fail grounding
unless it also asserts unsupported product behaviour or facts. This wording
has **not** been applied to the frozen rules, references or judgments. Settle
this distinction before grading the full comparison; no new grading pass or
adjusted agreement score is claimed here.

The human subsequently [accepted the clarification](clarification.md) on
2026-11-10 for future grading. This resolves the interpretation decision while
preserving the original calibration artifacts and first-pass score above.

The coordinator observed `gpt-6.1-sol` with `low` effort for the author, grader
and adjudicator in their execution metadata. The grader's original artifact
reported effort unavailable locally; the separate [submission receipt](grading-submission.json)
records the coordinator's observation and the original submission hash. These
results describe that profile, not a measured result at a different effort.

Validation: all 24 candidates pass unchanged production parsers; the audit
verified all 98 judgments and their evidence pointers against frozen inputs.
A separate PowerShell aggregation reproduced the 97/98 agreement and sole
disagreement. Repository-wide Ruff lint/format checks passed, and the existing
drafting, feedback and context suites passed 152 tests. No full application
suite or live generation was run for this offline calibration.
