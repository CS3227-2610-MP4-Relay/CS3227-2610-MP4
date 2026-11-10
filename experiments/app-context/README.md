# App-context experiments

These experiments examine how supplied context affects test drafting and
observation feedback in Relay. The 540-call comparison found that irrelevant
background usually hurt drafting, while feedback often asked unnecessary
questions even when the report was complete; effects varied by model and task.

Detailed results, methods and evidence are in [app-context.zip](app-context.zip),
following the [agent-setups archive layout](../agent-setups/README.md#the-archive).
The archive preserves all 114 original experiment files byte for byte, including
the earlier eight-call comparison, repeatability study, rehearsal, calibration
and full comparison. It also includes the five production source snapshots named
by the frozen manifest, preserving their original line endings for offline hash
checks. Original paths cited by historical logs are inside the ZIP.

## Read the results

Extract the ZIP outside the checkout, then open these paths:

| Report | Path inside the archive |
| --- | --- |
| Full comparison, examples and limits | `experiments/app-context/full-comparison/results.md` |
| Full comparison method | `experiments/app-context/full-comparison/method.md` |
| Temperature-zero repeatability | `experiments/app-context/repeatability-results.md` |
| Constructed-answer calibration | `experiments/app-context/calibration/results.md` |
| Nine-call live pilot | `experiments/app-context/grader-rehearsal/live-results.md` |
| Original eight-call comparison | `experiments/app-context/README.md` |

The full comparison used 12 synthetic scenarios with five repeats per
model/context combination. Its model-authored grades are not human-validated
ground truth; provider-effective settings and backend versions were unverified.
The detailed report records the remaining grading ambiguity and limitations.

## Reproduce the analysis offline

The helpers use production parsers and frozen source hashes, so run them in a
disposable copy of this repository. From the repository root in Git Bash, with
the existing virtual environment active, choose a new extraction directory:

```bash
mkdir -p /tmp/relay-app-context
git archive HEAD | tar -x -C /tmp/relay-app-context
unzip -o experiments/app-context/app-context.zip -d /tmp/relay-app-context
cd /tmp/relay-app-context
python experiments/app-context/full-comparison/analyze.py \
  --measurements experiments/app-context/full-comparison/measurements.jsonl \
  --judgments experiments/app-context/full-comparison/judgments \
  --output full-comparison-summary-check.json
```

Compare the output with `experiments/app-context/full-comparison/summary.json`;
the original SHA-256 is
`6cc52e39e8d765edccbf0dd1a8d9161d94d78cb76feedd795f5c5c31bc4e4694`.
The extracted READMEs document other offline checks and historical execution.

The two regression test modules remain in `src/ai/tests/` and extract the bundled
tooling into pytest's temporary directory. CI still runs all 34 runner/analyzer
checks without live provider calls. The [run log](../../logs/Whimsyturtle/050-run-full-context-comparison.md)
records the original execution and review.
