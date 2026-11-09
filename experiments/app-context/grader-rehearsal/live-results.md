# Three-scenario live pilot results

**Nine calls completed; eight replies passed schema validation.** Two D1 answers
and one F2 answer met every frozen semantic check. All three F3 answers returned
questions despite the scenario's complete observation. These are provisional
coordinator-model judgments; human inspection is pending.

This was the [bounded live pilot](live-method.md), using the exact D1/F2/F3
[targets and rubric](fixtures.json), relevant-only inputs and one call per
scenario/model. No background passages or repetitions were included. The full
540-call comparison and full 24-example grader calibration remain unrun.

Calls ran approximately **2026-11-09, 21:30:47–21:32:13 +08:00**. Requested
temperature was 0 with streaming off. Model names below are requested IDs;
backend identities and effective sampling settings were not independently
verified. There were no retries, refusals or gateway failures. One gateway
success failed the strict feature parser; its semantic quality was not graded.

## Answers and assessments

All-checks judgments below require every applicable frozen check to be met.
Counts are supplied for inspection, not as a composite score across scenarios.

| Call | Requested model | Scenario | Schema | Items | Checks met | Main assessment |
| --- | --- | --- | --- | ---: | --- | --- |
| live-01 | `qwen3.6:35b` | F3 | accepted | 5 | 1/4 | Returns unnecessary questions, repeats known filter state and introduces unstated sorting behaviour. |
| live-02 | `x-test-2` | F2 | accepted | 2 | 5/5 | Checks actual filter state and distinguishes pre-export list contents from exported contents. |
| live-03 | `llama3.1:8b` | F3 | accepted | 2 | 2/4 | Requests confirmation of the already-supplied filter label and row status. |
| live-04 | `qwen3.6:35b` | D1 | accepted | 1 | 6/6 | One combined draft covers all four boundaries with fresh setup and the correct observable results. |
| live-05 | `qwen3.6:35b` | F2 | accepted | 2 | 3/5 | Asks about actual filter application, then adds an unsupported need for separate item identification. |
| live-06 | `x-test-2` | F3 | accepted | 5 | 1/4 | Adds questions to the complete report and assumes CSV column structure that the target does not specify. |
| live-07 | `llama3.1:8b` | F2 | accepted | 2 | 3/5 | Misses the active-filter gap; broadly requests file contents and reconfirms reported row information. |
| live-08 | `llama3.1:8b` | D1 | rejected: `json` | unavailable | not graded | The whole reply failed strict JSON parsing. No claim is made about the precise formatting defect. |
| live-09 | `x-test-2` | D1 | accepted | 4 | 6/6 | Four drafts cover the four boundaries with supported steps, data and outcomes. |

The eight accepted answers received **39 criterion judgments**, with none
unavailable. Three accepted answers met all checks; five did not. The rejected
answer is a separate schema failure, not a semantically assessed answer.

The exact criterion judgments, field references and paraphrased evidence are in
[live-judgments.json](live-judgments.json). Model labels were omitted from the
transient candidate view. The judgments were saved and hashed before the
coordinator read the measurement artifact's model mapping. The coordinator
could access that mapping and authored the rubric, so this was not independent
blinded grading. The earlier reference-visible constructed exercise did not
establish reliability on these live answers.

No raw or validated provider answer text was retained in the repository. The
answers were inspected transiently; the table and judgment artifact retain only
assessments and paraphrased evidence. Hashes support identity checks, not later
reconstruction or independent regrading of discarded answers.

## Points for human inspection

- **F3 completeness:** the empty-output requirement comes from the frozen
  scenario's information needs. Inspect whether that definition is suitable
  before treating extra questions as quality defects in a larger study.
- **live-02 conditional wording:** its second question was read as conditional
  on the first, rather than asserting that the tester applied the filter. The
  pre-export list state was judged a useful missing detail.
- **live-05 item identification:** the extra identifier request was judged an
  unjustified information requirement and an unsupported assumption. These two
  unmet checks concern the same underlying issue; they are not independent
  defects or a reason to compute a pooled quality percentage.
- **Draft grouping:** both the combined D1 answer and the four-draft answer
  passed. The rubric rewards coverage and usability without requiring a
  particular number of drafts.

These observations support inspecting the feedback rubric and actual question
selection. This single pass cannot rank models, establish repeatability or
measure the effect of irrelevant context. No further calls are scheduled.

## Resources

Provider token counts were available for all nine calls. Codex development and
grading usage is separate in the [session log](../../../logs/Whimsyturtle/048-brainstorm-context-comparison-design.md).

| Requested model | Calls | Prompt tokens | Completion tokens | Total tokens | Mean call ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `llama3.1:8b` | 3 | 1,444 | 487 | 1,931 | 12,150 |
| `qwen3.6:35b` | 3 | 1,470 | 517 | 1,987 | 2,353 |
| `x-test-2` | 3 | 1,500 | 2,205 | 3,705 | 11,408 |
| Total | 9 | 4,414 | 3,209 | 7,623 | — |

| Call | Scenario | Elapsed ms | Prompt tokens | Completion tokens | Total tokens |
| --- | --- | ---: | ---: | ---: | ---: |
| live-01 | F3 | 1,620 | 479 | 112 | 591 |
| live-02 | F2 | 9,591 | 478 | 560 | 1,038 |
| live-03 | F3 | 3,861 | 473 | 46 | 519 |
| live-04 | D1 | 4,165 | 521 | 313 | 834 |
| live-05 | F2 | 1,274 | 470 | 92 | 562 |
| live-06 | F3 | 12,816 | 487 | 820 | 1,307 |
| live-07 | F2 | 2,617 | 464 | 40 | 504 |
| live-08 | D1 | 29,972 | 507 | 401 | 908 |
| live-09 | D1 | 11,817 | 535 | 825 | 1,360 |

Call durations sum to 77,733 ms. They include transport cleanup, exclude the
one-second intervals and are not provider-only inference times. No explanation
for model timing differences is established by this sample.

## Execution and evidence

Evaluated application base: `6603cf5cf982cf34f428acbbc40a6993039e9fb2`.
Production instructions/parsers were unchanged: `drafting-2` and
`observation-feedback-3`. The new local runner reused existing configuration
loading and transport without application database accounting.

The default preflight printed nine planned calls before live execution. All
nine retained rows passed checks for unique IDs/ordinals, distinct model/scenario
cells, allowed measurement fields, numeric availability, unchanged frozen
inputs and exact semantic-check coverage for accepted answers.

| Artifact | SHA-256 |
| --- | --- |
| [Frozen targets/rubric](fixtures.json) | `2b07171b2b0a04808fd3127af8214d92f8258327c0c37393ac04ed8a7bf5e8d8` |
| [Frozen live method](live-method.md) | `0ec5bf4ba3928d02e5139db4ac79f72de43d7a603d24c31fbabd3aa7df577062` |
| [Runner](live_probe.py) | `0eb76065e2aa0d159ac3e5729b26c3616a7d061701be101c817e71393fa1b762` |
| [Measurements](live-measurements.ndjson) | `93761d00471ed2ae7d64557da936b51328a552195081ad1e7fe6b0492bd627e6` |
| [Judgments, saved before model mapping inspection](live-judgments.json) | `c37211d1f6812982466ab2694d9bdec2a932cb591930e4f50f3b7268e1fd0cfb` |

Repository-wide Ruff check/format passed (152 Python files), and the focused
drafting, feedback and context suites passed 152 tests in 1.10 s before live
execution. The earlier full pytest run subsequently finished with 247 failed,
704 passed, 4 skipped and 2,402 errors in 833.67 s; its full verification did not
pass. The retrieved output was heavily truncated and did not establish the
underlying causes. No independent role review was performed for this operator
diagnostic, and no application-wide success is claimed.
