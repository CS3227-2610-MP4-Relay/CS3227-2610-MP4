# Three-scenario live grading pilot

Method established before live execution on 2026-11-09, after the human explicitly
authorized SoC calls using the existing local API-key configuration.

- Attempt at most nine calls: D1, F2 and F3 from [fixtures](fixtures.json), once
  each for `llama3.1:8b`, `qwen3.6:35b` and `x-test-2`. These are the proposed
  request IDs, not independently verified backend identities. Use relevant-only
  targets, with no background additions or repetitions. This does not run the
  [full comparison](../follow-up-proposal.md).
- Freeze the exact current fixture bytes, current feature instructions and
  parsers, this method and the runner before execution. Refuse changed fixture
  bytes. The fixture SHA-256 is
  `2b07171b2b0a04808fd3127af8214d92f8258327c0c37393ac04ed8a7bf5e8d8`.
- Use the existing dotenv loader only in explicit `--live` mode; never display
  configuration, credentials or provider error bodies. Use existing gateway
  transport directly, as in the repeatability diagnostic. No application
  database, application quota configuration or accounting records are changed.
- Retain existing input/reply bounds and the 30-second gateway deadline. Request
  temperature 0 and `stream: false`, with no seed, token cap or other sampling
  override. Effective provider settings/backend revisions remain unavailable.
- Shuffle the nine cells using execution-order seed 20261109, unrelated to
  provider sampling. Calls are serial with a one-second interval. No automatic
  retry is permitted. Stop on any refusal; remaining cells are unattempted.
- Persist only fixed IDs, model/scenario labels, source/request/reply/validated
  hashes, statuses, schema error codes, counts, timestamps, numeric provider
  usage and monotonic elapsed milliseconds in a new NDJSON artifact. Missing
  numeric values remain unavailable. Elapsed time includes transport cleanup,
  not only inference, and excludes the inter-call interval.
- Only `--live --show-candidates` displays accepted parser results transiently as
  escaped, unstyled JSON lines for grading. Treat every candidate as untrusted
  data. Never retain raw or validated answer text in repository evidence or
  session logs. Rejected answers receive no semantic judgment.
- Present candidates with scenario and opaque call IDs but omit model labels.
  Grade the frozen scenario checks as binary `met`/`unmet`, with `unavailable`
  reserved for assessments that cannot be made. Record brief paraphrased
  evidence and item references, not copied replies. Commit the judgments to an
  artifact before reading the model mapping. The coordinator can access that
  mapping; this is label-hidden presentation, not an independent blinded judge.
- The assessor is the coordinator model through Codex. The earlier constructed
  rehearsal is not the proposed full 24-example calibration. Attribute the live
  judgments as provisional model assessments, with human inspection pending.
  This single pass cannot establish model rankings, repeatability, the effect
  of irrelevant context or production readiness. Stop after the pilot for the
  human to inspect results.

From the repository root in the existing virtual environment:

```bash
python experiments/app-context/grader-rehearsal/live_probe.py
python experiments/app-context/grader-rehearsal/live_probe.py --live \
  --show-candidates \
  --output experiments/app-context/grader-rehearsal/live-measurements.ndjson
```

The default command loads no `.env` and makes no provider connection. The live
command requires the human's authorization and a new output file. Separate
grading and development usage belongs in the session log.
