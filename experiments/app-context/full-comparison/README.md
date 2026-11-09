# Full app-context comparison

Local research artifacts for the human-authorized comparison. The frozen
[method](method.md) defines scope, scheduling, retention and analysis;
[rubric](rubric.md) defines semantic grading. The completed run and its
plain-English explanation, examples and next steps are in [results](results.md).
Original calibration and pilot artifacts remain separate and unchanged.

Retained evidence: [540 attempt measurements](measurements.jsonl),
[criterion judgments](judgments/), [machine-readable analysis](summary.json),
[coordinator grading audit](grading-audit.json) and the separate
[consistency review](consistency-review.json). Raw answers are not retained.

The completed run used these commands from the repository root in the existing
virtual environment; the existing freeze and output prevent accidental overwrite:

```bash
python experiments/app-context/full-comparison/runner.py
python experiments/app-context/full-comparison/runner.py --freeze
python experiments/app-context/full-comparison/runner.py --live --show-candidates \
  --output experiments/app-context/full-comparison/measurements.jsonl
```

Default preflight is offline. Freeze and output paths must be new; live execution
requires matching frozen source/request hashes. Candidate stdout is transient
grader input: do not redirect, tee or copy it into files or session logs. Retain
only safe metadata, hashes and paraphrased judgments. Result reporting follows
execution and must distinguish attempted calls, semantic assessments and failures.

Recompute the retained analysis offline, choosing a new output path:

```bash
python experiments/app-context/full-comparison/analyze.py \
  --measurements experiments/app-context/full-comparison/measurements.jsonl \
  --judgments experiments/app-context/full-comparison/judgments \
  --output tmp/full-comparison-summary-check.json
```

The [session log](../../../logs/Whimsyturtle/050-run-full-context-comparison.md)
records implementation, review, verification and separate Codex usage.
