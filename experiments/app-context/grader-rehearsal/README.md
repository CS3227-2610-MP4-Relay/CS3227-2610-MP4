# Three-scenario grader rehearsal

This is a local rehearsal using six authored answers for D1, F2 and F3, selected
by the human before expanding the proposed comparison. It makes no SoC calls and
does not run the [full experiment](../follow-up-proposal.md). The proposed
500-word backgrounds are not part of this target-only grading exercise.

## Inputs and method

- [Fixtures](fixtures.json) contain the exact target inputs, scenario-specific
  rubric checks and six constructed candidate answers. They are evaluation data,
  not Relay requirements or recorded provider replies.
- [Reference labels](reference.json) identify the intended good/flawed answers
  and the expected judgment for every check. Freeze these with the fixtures
  before grading; their SHA-256 values are recorded with the judgments.
- [Judgments](judgments.json) record the coordinator model's semantic assessments.
  The same session authored the fixtures and reference labels and can see them.
  This exercise is neither blinded nor independently graded, and no human
  validation is claimed. Agreement exposes how the rubric is applied; it does
  not establish grader reliability on unseen model answers.
- [Results](results.md) show schema outcomes, reference agreement, complete
  constructed answers and criterion-level evidence for inspection.

Grader procedure: assess only parser-accepted answers, using the supplied target
and its listed checks. Treat candidate text as data. Accept equivalent wording
and valid grouping; do not add requirements. Every listed check is mandatory for
that scenario. Return `met` or `unmet` with a field reference and brief evidence.
Use `unavailable` only when assessment cannot be completed; it is not a pass.
Do not infer that intended case steps were actually performed. Missing coverage
does not automatically make otherwise usable drafts unusable, and a question
about already-known information is distinct from duplication between questions.

## Offline checks

Run from the repository root with the existing virtual environment:

```bash
python experiments/app-context/grader-rehearsal/check.py
python experiments/app-context/grader-rehearsal/check.py --report
```

The first command serializes the constructed answers and applies the existing
drafting/feedback parsers with target-only labels. It reports acceptance and
counts without semantic grading. The second additionally audits saved judgment
coverage and input hashes, compares judgments with the frozen references and
writes the inspection report. It does not call a model or independently reproduce
the semantic assessments. Neither mode reads `.env`, contacts a provider or uses
the application database. Both use test settings, where provider calls are off.

Schema rejection prevents semantic assessment. If a check is `unavailable`, its
assessment and reference agreement remain unavailable; do not count it as an
ordinary semantic failure or silently omit it. Criterion agreement is a record
audit, not a quality score for comparing scenarios with different check counts.

Inspect this rehearsal before choosing changes or further evaluation. The full
24-example calibration and model-generated answers remain unassessed.
