# Temperature-zero repeatability pilot

Method frozen before live execution on 2026-11-09. This is a small diagnostic for
the [follow-up proposal](follow-up-proposal.md), not its full context experiment.

- Budget: 60 attempted calls, no automatic retries. Three proposed model IDs ×
  two existing synthetic scenarios (`drafting-boundary`, `feedback-complete`) ×
  their `selected`/`broader` pilot variants × five repetitions. The broader input
  is the short existing pilot background, not the proposal's 1,000-word passage.
- Use the existing [corpus](../../src/ai/context_comparison.py), current feature
  instructions and validators, and existing gateway transport. Request temperature
  0 and `stream: false`; send no seed, token cap or other sampling overrides,
  matching Relay. Effective provider settings/backend revisions are unavailable.
- Shuffle all twelve cells within each repetition block using a fixed **execution
  order** seed, 20261109. This is not a provider seed. Calls are serial with a
  one-second interval after completion and the gateway's 30-second deadline.
- Invoke the transport directly for this local operator experiment. No application
  database, quota configuration or product behaviour is changed; these calls do
  not create application accounting records.
- Retain request/reply SHA-256 hashes, validated-content SHA-256 hashes, schema
  acceptance, accepted item counts, provider token counts and elapsed milliseconds.
  Retain no key, source text, reply text or provider error body. Missing counts
  remain unavailable. Each request hash must be identical within its cell.
- Report raw and validated unique-reply counts per cell separately. Validated
  hashes compare parser results (including its existing text cleaning), not
  semantic equivalence or quality. Variation in invalid replies is reported as
  such; failures are not distinct successful answers.

Interpretation decided before running:

1. Any within-cell reply difference demonstrates that the tested SoC service did
   not return identical text for every identical temperature-zero request. It
   does not establish why: sampling support, routing, numerics and caching are
   unobserved. Identical replies cannot distinguish determinism from caching.
2. If validated answers differ, repeats can measure answer variation, but the
   full experiment still needs criterion-level grading to tell whether quality
   changes. Text diversity alone is not quality diversity.
3. If all five are identical, report **no variation observed in this small
   sample**, not guaranteed determinism. Prioritize distinct scenarios over more
   quality repetitions; keep a smaller repeated subset for latency/failures.
4. Treat scenarios as the distinct cases for quality comparisons. Repetitions
   of the same scenario are nested observations, not additional independent
   scenarios. Do not increase temperature just to manufacture diversity in an
   evaluation intended to represent Relay's temperature-zero operation.

General rationale: [vLLM's reproducibility documentation](https://docs.vllm.ai/en/v0.10.2/usage/reproducibility.html)
describes serving/scheduling limitations on reproducibility. This is background,
not evidence that SoC uses vLLM or that a particular cause applies here.

Run from the repository root in the existing virtual environment:

```bash
python experiments/app-context/repeatability_probe.py
python experiments/app-context/repeatability_probe.py --live \
  --output experiments/app-context/repeatability-results.jsonl
```

The first command does not load `.env` or call SoC. Live mode uses the existing
local configuration loader under the human's explicit authorization. Output must
be a new file. [Results and interpretation](repeatability-results.md) follow.
