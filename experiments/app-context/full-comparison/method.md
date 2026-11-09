# Full app-context comparison method

Method recorded before freezing or provider execution. This local research
experiment uses the human-authorized 540-call budget; pilot calls are separate.
No product behaviour, dependency, quota or accounting configuration changes.

## Inputs and schedule

Use only the `scenarios` array of [calibration fixtures](../calibration/fixtures.json):
D1-D6 for drafting and F1-F6 for feedback. Constructed candidates and reference
labels are neither provider nor grader inputs. Preserve all original calibration
artifacts and its first-pass 97/98 agreement; the accepted
[clarification](../calibration/clarification.md) is incorporated in this run's
[rubric](rubric.md).

Cross each scenario with `llama3.1:8b`, `qwen3.6:35b`, `x-test-2`, and
`relevant-only`, `app-clutter`, `off-topic`. These are requested model IDs;
effective backend identities and revisions are unavailable unless observed.
For each feature, preserve the scenario data's field order and append the
`background` string last. Every condition has this identical field structure;
relevant-only uses `""`, while the others use [backgrounds.json](backgrounds.json).
The two benign passages were composed at approximately 500 words each, without
a length-tuning step. They contain no assistant instructions or target-feature
requirements. Record observed token counts rather than treating words as tokens.

Use current production feature instructions and parsers from `src/ai/drafting.py`
and `src/ai/feedback.py`, and direct existing gateway transport. Preserve input
and reply limits. Request temperature 0 and `stream: false`; add no provider
seed, token cap or other sampling overrides. Provider-effective settings remain
unavailable when unobserved. The execution-order seed is not a sampling seed.

Construct the 108 cells in scenario order D1-D6,F1-F6, model order as listed
above and condition order as listed above. Use a single `random.Random(20261110)`
instance to shuffle a fresh copy of that ordered list for each of five consecutive
repetition blocks. Execute serially, with a one-second interval after completion
before the next call and the existing 30-second gateway deadline. No retries;
at most 540 transport invocations. On refusal or an escaping transport exception,
record the attempt and stop. An escaping exception has `interrupted: true` and
fixed failure metadata, without exception text. Remaining cells are unattempted,
not semantic failures. An invocation does not prove the provider received it.

## Freeze and execution

`runner.py` defaults to an offline preflight: no dotenv loading or provider
connection. `--freeze` creates a new `frozen.json` containing source-file SHA-256
hashes and exact request hashes. Freeze the runner, these method/rubric/background
files, scenario source, and production prompt/parser/transport sources before
live execution. Refuse changed sources or requests and refuse to overwrite
existing freeze/output artifacts. `--live --show-candidates --output` uses the
existing dotenv loader and gateway without displaying configuration, credentials
or provider error bodies. The output must be a new measurements JSONL file.
Freezing and live execution are coordinator actions, separate from drafting this
method. [README](README.md) gives the command sequence.

Persist only safe fixed IDs, source/request/raw-reply/parser-result hashes,
statuses, interruption flags, schema error codes, timestamps, numeric token usage,
elapsed milliseconds and judgments. Raw provider replies remain transient in runner memory;
parser-accepted candidates travel only through escaped JSON stdout into
coordinator memory. Do not create candidate files or copy replies into logs.
Elapsed time includes transport cleanup and excludes inter-call delay.
Missing usage and unavailable resource counters remain unavailable, never zero.

## Grading and reuse

Grade only parser-accepted results using GPT-6.1 Sol through Codex with the frozen
scenario, its checks, candidate and rubric. Use opaque grader IDs; do not pass
model or condition labels to the grader. The coordinator can access mappings,
so this is label-hidden presentation, not an independent blinded assessment.
Record judgments before inspecting mappings. Grading/development usage is separate
from generation usage.

Deduplicate exact parser results only within the same scenario/model/condition
cell across its five repeats. Compare canonical JSON encodings of parser-result
objects with sorted object keys and preserved array order; do not merge merely
similar answers. Grade each distinct result once and reuse that judgment at its
observed frequency. Never reuse judgments across conditions, models or scenarios.
Keep every call's schema outcome, hashes, tokens and latency. Valid empty arrays
remain eligible for semantic grading. Each listed check receives `met`, `unmet`
or `unavailable`, a JSON pointer relative to the candidate and a brief paraphrase;
no copied reply text is retained.

## Analysis and limits

Report drafting and feedback separately. Summarize the five repeats within each
scenario/model/condition cell, including schema/provider failures, distinct raw
and parser-result counts, criterion rates and variation, token counts and latency
spread. Show unavailable assessments separately; exclude them from assessed
semantic denominators and report the denominator. Schema/provider failures have
their own attempted-call denominators and receive no semantic judgments.

Compare conditions paired on the same scenario and model. Aggregate cell averages
across scenarios, giving each scenario equal weight rather than pooling checks
or treating 540 calls as independent observations. State both attempted-call and
assessed-answer counts, preserve frequencies when reusing exact-duplicate
judgments, and report unattempted cells separately. The 12 scenarios are distinct
cases; five repeats measure within-cell variation. No observed variation does not
establish determinism. Model-assessed quality is not human validation; diversity
does not imply quality variation, and model-family differences prevent attributing
differences solely to model size. Report missing resource measurements as
unavailable. Result reporting follows execution; this file claims no outcomes.
