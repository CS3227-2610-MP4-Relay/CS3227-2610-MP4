# Relay AI: context relevance and model comparison

**Status:** Full comparison implementation and execution authorized on 2026-11-10. The [execution method](full-comparison/method.md) defines the frozen run; results will be reported separately. Follow-up to the [eight-call pilot](README.md) and [temperature-zero repeatability pilot](repeatability-results.md).

**Question:** How does irrelevant context affect answer quality, token use and latency across three models?

## Setup

| Factor | Proposal |
| --- | --- |
| Tasks | 12 synthetic scenarios: six test-case drafting, six observation-feedback |
| Models | Llama 3.1 8B (`llama3.1:8b`), Qwen 3.6 35B (`qwen3.6:35b`), DeepSeek Flash 4.1 (`x-test-2`, team-confirmed mapping) |
| Repetitions | Five identical requests per scenario, model and context condition at requested temperature 0, measuring answer stability, schema acceptance and latency |
| Generation budget | **12 × 3 × 3 × 5 = 540 SoC calls** for this full comparison, with no automatic retries; pilot usage is separate |
| Grader | GPT-6.1 Sol through Codex; grading usage recorded separately |

Llama/Qwen IDs come from [recorded live runs](../../logs/Whimsyturtle/027-fix-live-drafting-reply-schema.md) in commit `7b4c83d`.

The [repeatability pilot](repeatability-results.md) observed variation in validated answers at requested temperature 0, supporting five repeats as stability measurements while leaving semantic quality and behaviour with longer backgrounds unmeasured. Keep Relay's requested temperature and sampling settings; do not raise temperature merely to produce diversity. Five is a practical starting count, not a measured optimum; prioritize broader scenario coverage before adding more repetitions.

Each scenario has three input variants:

| Condition | Supplied context |
| --- | --- |
| Relevant only | Target task and necessary information |
| App clutter | Same target input plus unrelated app-feature descriptions |
| Off-topic text | Same target input plus benign encyclopedia passages, e.g. geology/history |

Match the two background additions at approximately 500 words each to reduce length differences when comparing background types, with no length-tuning step. Record actual token counts because equal word counts need not mean equal tokens. Freeze passages and exact requests before running. Keep task instructions, input structure, context placement and generation settings fixed. Within each repetition block, interleave all scenarios, models and conditions in randomized order; record the execution-order seed separately from provider settings. Use the existing [drafting](../../src/ai/drafting.py) and [feedback](../../src/ai/feedback.py) prompts and output validators.

## Automatic grading

Code checks JSON structure, required fields and output limits. Sol assesses scenario-specific requirements: drafting coverage and usable steps/results; feedback questions that address missing information without redundancy; unsupported claims in either feature.

Give Sol the target scenario, expected behaviours and validated candidate answer, with model/condition labels hidden. Require criterion-level binary `met`/`unmet` judgments with brief evidence; reserve `unavailable` for assessments that cannot be completed and report them separately. Check the grader against **24 constructed good/flawed examples**, then freeze its rubric before grading experiment outputs. This adds Codex usage, not SoC generation calls.

A [24-answer calibration](calibration/results.md) now uses a fresh GPT-6.1 Sol grader with reference labels withheld; its [boundary/grounding clarification](calibration/clarification.md) was accepted for subsequent grading. The earlier [D1/F2/F3 rehearsal](grader-rehearsal/README.md) remains separate.

A separately authorized [nine-call relevant-only pilot](grader-rehearsal/live-results.md) now provides model-generated D1/F2/F3 assessments for inspection; it does not run this proposal's context comparison.

Within each scenario/model/condition group, grade each distinct validated answer once and reuse that judgment for exact duplicates, retaining their observed frequencies. Compare exact parser results for this deduplication, preserving array order; do not merge answers merely because they seem similar. Keep every call's schema outcome, token counts and latency. Different answers can receive the same quality judgment.

## Results to report

- Quality: criterion pass rates, schema failures and provider failures.
- Resources: prompt/output/total tokens, latency and separate grading usage.
- Repeatability: unique raw replies and unique validated answers, criterion-level quality variation, latency spread and failures across five calls.

Summarize drafting and feedback separately. First summarize the five calls within each scenario/model/condition group, then compare context conditions on the same scenario and model and aggregate across scenarios. Treat the 12 scenarios as the distinct cases, not all 540 calls. Identical answers still contribute latency and failure measurements; observing no variation in five calls does not establish determinism. Record requested generation settings and mark effective provider settings or backend versions unavailable when unobserved.

Results are model-assessed, not human-validated; answer diversity alone does not establish quality variation, and model-family differences prevent attributing outcomes solely to size. Unchanged quality with higher token use is still a useful finding. Reassess repeatability on the full frozen inputs, including both longer background conditions.

**Execution:** The existing [repeatability probe](repeatability_probe.py) covers only its pilot corpus. The authorized full comparison uses a [separate local runner and frozen method](full-comparison/README.md), leaving Relay's production quotas unchanged.
