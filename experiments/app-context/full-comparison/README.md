# Full app-context comparison

Local research artifacts for the human-authorized comparison. The frozen
[method](method.md) defines scope, scheduling, retention and analysis;
[rubric](rubric.md) defines semantic grading. No results are claimed here.
Original calibration and pilot artifacts remain separate and unchanged.

From the repository root in the existing virtual environment:

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
