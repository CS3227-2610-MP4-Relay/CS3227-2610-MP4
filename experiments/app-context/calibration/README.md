# Constructed-answer grader calibration

The human approved the existing marking rules and requested this calibration
on 2026-11-10. It checks the proposed grader against 24 constructed answers
across six drafting and six feedback scenarios. This is an offline research
exercise using Codex agents; it makes no SoC calls. The
[540-call context comparison](../follow-up-proposal.md) remains separate.

## Method established before grading

1. A GPT-6.1 Sol author prepares synthetic targets, scenario-specific checks,
   candidates and separate reference labels. D1/F2/F3 retain the exact target
   data and checks from the approved [rehearsal](../grader-rehearsal/fixtures.json).
   Nonempty candidates are newly constructed for this exercise; the canonical
   empty answers necessarily repeat the same JSON shape. Each scenario has
   one intended good answer and one flawed answer, assigned opaque shuffled
   identifiers. These fictional app behaviours are evaluation inputs, not new
   Relay requirements or a frozen corpus for live generation.
2. The coordinator checks the corpus and references, applies the unchanged
   production parsers, and freezes artifact/source hashes in `frozen.json`
   before grading. Every candidate must pass its parser without changes to its
   content. Semantic faults therefore cannot be detected just by rejecting JSON.
3. A fresh GPT-6.1 Sol agent with no inherited conversation reads only
   [fixtures.json](fixtures.json) and [rubric.md](rubric.md), then records every
   judgment with a field reference and brief evidence in `judgments.json`.
   It does not read reference labels, prior results, author messages or this
   method's answer distribution. The author and grader are different sessions;
   shared filesystem access means separation is instructional, not an access
   control boundary. Both agents use the same model family.
4. Freeze the submitted judgments before comparing them with the original
   references. The audit reports complete criterion agreement, unavailable
   judgments, exact candidate agreement, and good/flawed classification errors.
   Counts concern agreement with constructed references; they are not quality
   scores for comparing scenarios with different check counts.
5. Preserve original grades and references. Inspect every disagreement, using
   a separate adjudicator only if needed. Any correction belongs in a separately
   identified artifact with a reason; do not overwrite the first-pass evidence
   or report adjusted agreement as the original result. No numeric success
   threshold is invented after seeing outcomes.

The approved general rules are in [rubric.md](rubric.md); each exact criterion
lives in its scenario in [fixtures.json](fixtures.json). The human approved the
marking approach, not the new reference labels or resulting grades. This small
constructed sample does not establish accuracy on natural model outputs,
background-contaminated outputs, or unseen scenarios. No human validation or
production-readiness claim follows from agreement alone.

## Reproduce the offline audit

From the repository root in the existing virtual environment:

```bash
python experiments/app-context/calibration/check.py
python experiments/app-context/calibration/check.py --freeze
python experiments/app-context/calibration/check.py --audit
```

Default mode validates artifacts without changing them. `--freeze` creates a
new manifest and refuses to replace an existing one. `--audit` checks frozen
inputs and judgment coverage, then creates `audit.json` and `results.md` without
overwriting existing outputs. The helper audits saved semantic judgments; it
does not produce them or call a model. Provider calls remain disabled under
test settings, and no `.env` file or application database is used.

Results and any disagreements are recorded in [results.md](results.md), with
machine-readable counts in [audit.json](audit.json). Development and grading
usage belongs in the session log rather than SoC generation accounting.
