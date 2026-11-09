# Temperature-zero repeatability results

**Repeated calls added information in this SoC pilot.** With identical requests
within each model/input group and requested temperature 0, 10/12 groups returned
different reply text; 9/12 returned different schema-accepted answers. This shows
observed service variation, not its cause or whether the provider honoured the
requested sampling settings.

All **60 calls** completed with gateway-accepted provider envelopes; **53/60**
passed feature validation. No transport failures, provider refusals or retries
occurred. Run window: **2026-11-09, 18:58:41–19:06:22 +08:00**. The
[method](repeatability-method.md) was frozen before execution; this used two
existing scenarios and short pilot background, not the full follow-up corpus.

Each table row contains five calls with one identical request hash. Raw uniqueness
compares reply text. Validated uniqueness compares feature parser results,
including their cleaning; it still distinguishes ordering and wording and does
not measure semantic quality. Items are drafts or questions, depending on task.

| Requested model | Input | Schema accepted | Unique raw replies | Unique validated answers | Accepted item counts | Latency range, ms |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `llama3.1:8b` | Drafting, selected | 3/5 | 4 | 2 | 2 | 2,475–6,654 |
| `llama3.1:8b` | Drafting, broader | 0/5 | 4 | 0 | unavailable | 3,617–21,318 |
| `llama3.1:8b` | Feedback, selected | 5/5 | 1 | 1 | 2 | 1,382–2,887 |
| `llama3.1:8b` | Feedback, broader | 5/5 | 1 | 1 | 2 | 1,301–2,376 |
| `qwen3.6:35b` | Drafting, selected | 5/5 | 5 | 5 | 1 | 1,926–2,484 |
| `qwen3.6:35b` | Drafting, broader | 5/5 | 3 | 3 | 1 or 2 | 1,706–3,000 |
| `qwen3.6:35b` | Feedback, selected | 5/5 | 5 | 5 | 4 or 5 | 1,445–1,839 |
| `qwen3.6:35b` | Feedback, broader | 5/5 | 5 | 5 | 3 or 4 | 1,279–1,695 |
| `x-test-2` | Drafting, selected | 5/5 | 5 | 5 | 1 or 4 | 9,210–14,472 |
| `x-test-2` | Drafting, broader | 5/5 | 5 | 5 | 4 | 12,804–19,297 |
| `x-test-2` | Feedback, selected | 5/5 | 5 | 5 | 5 | 9,075–25,045 |
| `x-test-2` | Feedback, broader | 5/5 | 5 | 5 | 5 | 10,072–18,901 |

Qwen and `x-test-2` varied after validation on all four inputs. Llama's selected
drafting input varied in both validated content and schema acceptance; its two
feedback inputs repeated exactly. Its broader drafting replies varied but were
all invalid. These examples show why raw diversity, validity and quality must be
reported separately. Even identical Llama feedback answers had different latency.

Provider-reported resources, with all three token fields available for 60/60 calls:

| Requested model | Calls | Prompt tokens | Completion tokens | Total tokens | Mean call ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `llama3.1:8b` | 20 | 9,535 | 2,955 | 12,490 | 3,928.5 |
| `qwen3.6:35b` | 20 | 9,735 | 2,784 | 12,519 | 1,914.6 |
| `x-test-2` | 20 | 9,990 | 19,722 | 29,712 | 14,243.4 |
| Total | 60 | 29,260 | 25,461 | 54,721 | — |

Call milliseconds include transport and cleanup, exclude the one-second intervals,
and are not provider-only inference time. They sum to 401,730 ms. These descriptive
values do not establish comparative model speed under controlled infrastructure.
Codex development usage is separate in the [session log](../../logs/Whimsyturtle/047-test-temperature-zero-repeatability.md).

The [follow-up proposal](follow-up-proposal.md) now incorporates the recommended
handling of repeats, grading, scenario-level comparisons and longer contexts.

Backend versions, effective temperature/seed, routing, cache behaviour and the
mapping behind model aliases were not independently verified. This small run
cannot establish universal determinism, rank semantic quality or diagnose Llama's
invalid output. No provider replies were retained for later qualitative review.

Execution and evidence:

```bash
python experiments/app-context/repeatability_probe.py --live \
  --output experiments/app-context/repeatability-results.jsonl
```

After completion, the hash/numeric-only artifact was renamed to
[`repeatability-results.ndjson`](repeatability-results.ndjson), because the
repository ignores `*.jsonl`. No rows changed. To repeat the run, supply a new
output filename; running the [probe](repeatability_probe.py) without `--live`
only prints the schedule and loads no `.env`.

Source base: `46317632dcc0df8f2bb2b2ffc3391e93e497fb9c`; existing corpus and
production sources were unchanged. Frozen input versions: `context-1`,
`drafting-2`, `observation-feedback-3`.

| Artifact | SHA-256 |
| --- | --- |
| Runner before and after execution | `dfa5922b698479577e2a1d9114212cb2334b690afe5a5438f19029000bce4de6` |
| Frozen method | `96e337687a1ad37cc4801f2b4beb2c57409d68bfa0e2d455372c31c45f4d5ba9` |
| Final 60-row artifact | `b203b4dd44ddc401a408578e5384425ecbd3ad92111aebf84f152350c2cf58eb` |

Validation: all twelve groups had exactly repeats 1–5 and one request hash;
ordinals were exactly 1–60. Repository-wide Ruff check/format passed, Python
compilation passed, and the existing context/drafting/feedback suites passed
152 tests. No full application/database test run or independent role review was
performed for this standalone research diagnostic.
