# Full context comparison: results

Irrelevant background usually made drafting less reliable in these cases, but
its effect depended on the requested model and task. Feedback was difficult even
with relevant information alone: every accepted answer to the two complete-report
scenarios still asked unnecessary questions. Adding context always increased
measured input tokens; it did not consistently increase latency or reduce quality.
These are descriptive results for synthetic examples, not a model ranking.

## What was tested

The completed run made **540 transport attempts**, with no retries, interruptions
or unattempted calls: 12 scenarios × 3 requested models × 3 context conditions ×
5 repeats. Six scenarios asked for test drafts; six asked for missing information
about a tester's observation. Each task was repeated with relevant information
only, unrelated app descriptions, and benign off-topic passages. Think of these
as asking the same question with either a clean desk or extra unrelated papers
beside it. The added passages were approximately 500 words each.

The [frozen method](method.md) and [request/source manifest](frozen.json) record
the schedule, production prompts/parsers and requested temperature 0. A fixed
execution-order seed shuffled each repetition block; it was not a provider seed.
The [summary](summary.json) and [attempt measurements](measurements.jsonl)
are the sources for the tables below. Original
[criterion judgments](judgments/) remain unchanged.

Of 540 attempts, 486 returned text, 465 passed the production JSON/schema parser,
21 failed that parser, and 54 timed out. All 54 timeouts were Llama requests.
There were no other recorded provider failures. The 465 accepted answers yielded
321 distinct parser results within their own scenario/model/condition cells;
all 321 were graded once, covering 1,388 distinct-answer criterion assessments.
Their judgments were then reused at each exact answer's observed frequency.
No criterion was unavailable and no accepted answer was left ungraded.

## Quality, including failures

An answer succeeds here only when it passes the parser **and every scenario
check**. The main percentage first averages the five calls in each scenario,
then averages the six scenarios equally. A timeout or schema failure remains
in its attempted-call denominator. The conditional percentage instead asks how
often all checks passed among fully assessed answers, again averaging scenarios
equally and excluding scenarios with no assessed answer. It can therefore differ
from simply dividing the displayed success count by the assessed count.

Each row has 30 attempts. `N` is the number of scenarios contributing to the
conditional percentage. Schema and provider columns are counts out of 30.

| Task | Requested model | Context | All checks met / attempts | Scenario mean | Conditional mean (N) | Assessed / 30 | Schema / 30 | Provider / 30 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| drafting | llama3.1:8b | relevant-only | 12/30 | 40.0% | 50.0% (6) | 22/30 | 0/30 | 8/30 |
| drafting | llama3.1:8b | app-clutter | 2/30 | 6.7% | 25.0% (4) | 5/30 | 10/30 | 15/30 |
| drafting | llama3.1:8b | off-topic | 0/30 | 0.0% | 0.0% (4) | 9/30 | 6/30 | 15/30 |
| drafting | qwen3.6:35b | relevant-only | 29/30 | 96.7% | 96.7% (6) | 30/30 | 0/30 | 0/30 |
| drafting | qwen3.6:35b | app-clutter | 20/30 | 66.7% | 80.0% (5) | 25/30 | 5/30 | 0/30 |
| drafting | qwen3.6:35b | off-topic | 25/30 | 83.3% | 83.3% (6) | 30/30 | 0/30 | 0/30 |
| drafting | x-test-2 | relevant-only | 30/30 | 100.0% | 100.0% (6) | 30/30 | 0/30 | 0/30 |
| drafting | x-test-2 | app-clutter | 30/30 | 100.0% | 100.0% (6) | 30/30 | 0/30 | 0/30 |
| drafting | x-test-2 | off-topic | 29/30 | 96.7% | 96.7% (6) | 30/30 | 0/30 | 0/30 |
| feedback | llama3.1:8b | relevant-only | 0/30 | 0.0% | 0.0% (6) | 25/30 | 0/30 | 5/30 |
| feedback | llama3.1:8b | app-clutter | 0/30 | 0.0% | 0.0% (6) | 22/30 | 0/30 | 8/30 |
| feedback | llama3.1:8b | off-topic | 0/30 | 0.0% | 0.0% (6) | 27/30 | 0/30 | 3/30 |
| feedback | qwen3.6:35b | relevant-only | 9/30 | 30.0% | 30.0% (6) | 30/30 | 0/30 | 0/30 |
| feedback | qwen3.6:35b | app-clutter | 2/30 | 6.7% | 6.7% (6) | 30/30 | 0/30 | 0/30 |
| feedback | qwen3.6:35b | off-topic | 5/30 | 16.7% | 16.7% (6) | 30/30 | 0/30 | 0/30 |
| feedback | x-test-2 | relevant-only | 5/30 | 16.7% | 16.7% (6) | 30/30 | 0/30 | 0/30 |
| feedback | x-test-2 | app-clutter | 9/30 | 30.0% | 30.0% (6) | 30/30 | 0/30 | 0/30 |
| feedback | x-test-2 | off-topic | 5/30 | 16.7% | 16.7% (6) | 30/30 | 0/30 | 0/30 |

Across tasks and conditions, 212/540 attempts met every check; 212/465 assessed
answers did so. These pooled counts describe this run only; the scenario means
above are the comparison measure. All 21 schema failures occurred in drafting:
7 invalid JSON, 5 invalid draft collections, 5 invalid draft keys, 2 invalid
expected-result texts and 2 unsupported criterion labels. Schema acceptance alone
was not evidence of semantic quality.

## What changed when background was added

Each delta below subtracts relevant-only from the other condition **on the same
scenario and model**, then averages those paired differences. Positive quality
values mean more success; positive latency means slower. `pp` means percentage
points: a change from 40% to 20% is −20 pp. Attempt-quality and latency comparisons
have six paired scenarios per row. Conditional quality uses the paired N shown;
its changing coverage matters especially for Llama drafting.
Input-token deltas use six paired scenarios except Llama drafting/app-clutter,
which has five because one scenario has no available token counter there.

| Task | Model | Added context | Attempt quality Δ pp (N=6) | Conditional quality Δ pp (paired N) | Input tokens Δ / call | Mean latency Δ seconds |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| drafting | llama3.1:8b | app-clutter | -33.3 | -50.0 (4) | +582 | +5.66 |
| drafting | llama3.1:8b | off-topic | -40.0 | -75.0 (4) | +594 | +4.33 |
| drafting | qwen3.6:35b | app-clutter | -30.0 | -16.0 (5) | +580 | -0.30 |
| drafting | qwen3.6:35b | off-topic | -13.3 | -13.3 (6) | +593 | +0.03 |
| drafting | x-test-2 | app-clutter | +0.0 | +0.0 (6) | +574 | +0.08 |
| drafting | x-test-2 | off-topic | -3.3 | -3.3 (6) | +587 | +1.74 |
| feedback | llama3.1:8b | app-clutter | +0.0 | +0.0 (6) | +582 | +2.08 |
| feedback | llama3.1:8b | off-topic | +0.0 | +0.0 (6) | +594 | -3.18 |
| feedback | qwen3.6:35b | app-clutter | -23.3 | -23.3 (6) | +580 | -0.22 |
| feedback | qwen3.6:35b | off-topic | -13.3 | -13.3 (6) | +593 | +0.35 |
| feedback | x-test-2 | app-clutter | +13.3 | +13.3 (6) | +574 | -1.11 |
| feedback | x-test-2 | off-topic | +0.0 | +0.0 (6) | +587 | -1.73 |

For Qwen drafting, app clutter reduced attempted success by 30.0 pp and off-topic
text by 13.3 pp. Llama drafting also lost success, alongside many timeouts and
schema failures. The requested x-test-2 model preserved drafting success with
app clutter and lost one successful call with off-topic text. Feedback did not
follow one direction: x-test-2 improved by 13.3 pp with app clutter, while Qwen
declined. This improvement concerns these six scenarios; it does not establish
that clutter helps feedback in general.

## Tokens and time

Token counters were available for 486/540 attempts and missing for all 54
timeouts. Available generation totals were **417,309 input + 141,785 output =
559,094 total tokens**. They are partial observed totals, not estimates of tokens
used by timed-out calls. Counters include schema-rejected replies when available.
Grading and development used Codex separately; their accounting belongs in the
[session usage log](../../../logs/Whimsyturtle/050-run-full-context-comparison.md),
not in these provider-generation totals.

Below, all token columns are sums over the available calls in that row; the
coverage column applies to each token counter. Latency covers all 30 attempts,
including failures, in seconds. Means also equal scenario-weighted latency means
here because every scenario has five attempted calls. Elapsed time excludes the
one-second inter-call spacing and includes transport cleanup.

| Task | Model | Context | Token coverage | Input sum | Output sum | Total sum | Latency mean / median | Latency min–max |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| drafting | llama3.1:8b | relevant-only | 22/30 | 10,091 | 2,634 | 12,725 | 19.27 / 25.97 | 2.52–31.00 |
| drafting | llama3.1:8b | app-clutter | 15/30 | 15,813 | 4,856 | 20,669 | 24.93 / 29.91 | 4.73–31.04 |
| drafting | llama3.1:8b | off-topic | 15/30 | 15,836 | 4,022 | 19,858 | 23.60 / 29.16 | 6.95–31.02 |
| drafting | qwen3.6:35b | relevant-only | 30/30 | 14,255 | 3,844 | 18,099 | 1.86 / 1.37 | 0.32–6.84 |
| drafting | qwen3.6:35b | app-clutter | 30/30 | 31,655 | 3,067 | 34,722 | 1.56 / 1.43 | 0.26–3.49 |
| drafting | qwen3.6:35b | off-topic | 30/30 | 32,045 | 3,836 | 35,881 | 1.89 / 1.59 | 0.28–4.32 |
| drafting | x-test-2 | relevant-only | 30/30 | 14,760 | 14,297 | 29,057 | 6.42 / 5.03 | 0.74–21.20 |
| drafting | x-test-2 | app-clutter | 30/30 | 31,980 | 14,436 | 46,416 | 6.50 / 5.97 | 2.36–14.60 |
| drafting | x-test-2 | off-topic | 30/30 | 32,370 | 17,110 | 49,480 | 8.15 / 5.36 | 1.99–27.92 |
| feedback | llama3.1:8b | relevant-only | 25/30 | 11,618 | 959 | 12,577 | 15.09 / 11.76 | 1.51–31.01 |
| feedback | llama3.1:8b | app-clutter | 22/30 | 22,997 | 1,142 | 24,139 | 17.17 / 19.41 | 1.63–30.99 |
| feedback | llama3.1:8b | off-topic | 27/30 | 28,564 | 1,580 | 30,144 | 11.92 / 9.78 | 1.75–30.88 |
| feedback | qwen3.6:35b | relevant-only | 30/30 | 14,085 | 2,966 | 17,051 | 1.47 / 1.46 | 0.70–2.46 |
| feedback | qwen3.6:35b | app-clutter | 30/30 | 31,485 | 2,353 | 33,838 | 1.25 / 1.25 | 0.71–2.15 |
| feedback | qwen3.6:35b | off-topic | 30/30 | 31,875 | 3,168 | 35,043 | 1.81 / 1.45 | 0.99–8.13 |
| feedback | x-test-2 | relevant-only | 30/30 | 14,350 | 21,255 | 35,605 | 12.28 / 10.50 | 5.05–24.30 |
| feedback | x-test-2 | app-clutter | 30/30 | 31,570 | 20,484 | 52,054 | 11.17 / 11.12 | 5.10–20.25 |
| feedback | x-test-2 | off-topic | 30/30 | 31,960 | 19,776 | 51,736 | 10.55 / 10.56 | 4.47–18.14 |

The longer conditions added roughly 574–594 measured input tokens per call in
paired scenario averages. Missing timeout counters mean Llama token totals cannot
be treated as complete consumption or directly compared as equal-work costs.
Its latency distributions include many roughly 30-second timeouts. Provider load,
caching and effective backend settings were not controlled or observed, so
latency differences cannot be attributed solely to the background text.

## Repetition: different wording versus different quality

Distinct raw-reply counts are sums of distinct hashes **within cells**, not
globally unique texts. Parser-result counts use the exact validated object,
preserving array order; exact duplicates were merged only within their cell.
A quality vector is the complete set of criterion met/unmet outcomes. Different
answers can have the same vector. The final three columns count scenarios out
of six with more than one observed raw reply, parser result or quality vector.
Failures and absent answers do not supply quality vectors.

| Task | Model | Context | Distinct raw | Distinct parsed | Raw-varied / 6 | Parsed-varied / 6 | Quality-varied / 6 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| drafting | llama3.1:8b | relevant-only | 10 | 10 | 4/6 | 4/6 | 0/6 |
| drafting | llama3.1:8b | app-clutter | 13 | 4 | 5/6 | 0/6 | 0/6 |
| drafting | llama3.1:8b | off-topic | 11 | 6 | 3/6 | 2/6 | 2/6 |
| drafting | qwen3.6:35b | relevant-only | 10 | 10 | 3/6 | 3/6 | 1/6 |
| drafting | qwen3.6:35b | app-clutter | 13 | 11 | 3/6 | 3/6 | 0/6 |
| drafting | qwen3.6:35b | off-topic | 12 | 12 | 5/6 | 5/6 | 0/6 |
| drafting | x-test-2 | relevant-only | 23 | 23 | 5/6 | 5/6 | 0/6 |
| drafting | x-test-2 | app-clutter | 23 | 23 | 5/6 | 5/6 | 0/6 |
| drafting | x-test-2 | off-topic | 23 | 23 | 6/6 | 6/6 | 1/6 |
| feedback | llama3.1:8b | relevant-only | 8 | 8 | 2/6 | 2/6 | 0/6 |
| feedback | llama3.1:8b | app-clutter | 13 | 13 | 4/6 | 4/6 | 2/6 |
| feedback | llama3.1:8b | off-topic | 17 | 17 | 5/6 | 5/6 | 2/6 |
| feedback | qwen3.6:35b | relevant-only | 22 | 22 | 6/6 | 6/6 | 2/6 |
| feedback | qwen3.6:35b | app-clutter | 22 | 22 | 5/6 | 5/6 | 3/6 |
| feedback | qwen3.6:35b | off-topic | 27 | 27 | 6/6 | 6/6 | 4/6 |
| feedback | x-test-2 | relevant-only | 30 | 30 | 6/6 | 6/6 | 5/6 |
| feedback | x-test-2 | app-clutter | 30 | 30 | 6/6 | 6/6 | 4/6 |
| feedback | x-test-2 | off-topic | 30 | 30 | 6/6 | 6/6 | 4/6 |

Across 108 cells, 85 had multiple raw replies, 79 had multiple parser results,
and 30 had multiple quality vectors. The within-cell distinct counts summed to
337 raw replies, 321 parser results and 149 quality vectors. For example,
x-test-2 produced 23 distinct drafting answers under both relevant-only and
app-clutter, yet each condition had zero scenarios with varying quality vectors:
all those answers passed every check. Answer diversity alone is not quality
variation, and five repeats with no variation do not establish determinism.

## What the individual checks revealed

These are frequency-weighted criterion counts from the `cells[].criteria`
entries in [summary.json](summary.json), using the original judgments. Each
scenario has 45 attempts across its models and conditions. Denominators below
include only accepted, assessed answers; failed calls are excluded here.

- D1 usually covered the supplied name-length boundaries: the four boundary
  checks passed on 30/31, 31/31, 31/31 and 30/31 accepted answers. Usability
  passed only 19/31, showing that mentioning the right values did not guarantee
  executable tests with the required setup and consistent results.
- D3 required an empty draft collection because its source did not establish
  testable behaviour. The empty-output check passed on 29/34 accepted answers,
  while grounding passed on 34/34. These separate checks should not be collapsed.
- F2 established the missing active export filter in 30/40 answers, but only
  20/40 avoided asking for already supplied or unrelated information.
- F3 and F4 were complete reports that required no questions. Their empty-output
  and only-missing checks each failed on **all 43/43 accepted answers per
  scenario**. No accepted answer to either scenario met every check.
- F5 asked which deletion-confirmation action was actually selected. Coverage
  passed on 21/43 and only-missing on 8/43; grounding passed on 25/43. Intended
  case steps were often treated as if the tester had reported performing them.
- F6 supplied no observation. Full missing-information coverage passed on just
  4/43 accepted answers, despite only-missing passing on 43/43. Questions could
  be relevant while still failing to establish the necessary actions and setup.
- Feedback boundaries were mostly respected: every assessed F1–F4 and F6
  answer passed that check; F5 passed on 42/43. This did not compensate for
  missing coverage or unnecessary questions.

### Four concrete examples, paraphrased

These are summaries of transient examples supplied by the coordinator, checked
against their saved mappings and judgments. They are not retained answer text.

1. **Useful drafting:** D1 asked for tests around a name-length limit.
   `g-0180` (x-test-2, relevant-only) used the supplied empty, minimum, maximum
   and over-limit values, with a fresh valid form each time and observable
   results. All six checks passed ([assessment](judgments/draft-21.json)).
2. **Useful clarification despite clutter:** F2 described an export mismatch
   but did not establish the active filter. `g-0049` (x-test-2, app-clutter)
   asked only about that missing filter state. All five checks passed
   ([assessment](judgments/feedback-05.json)).
3. **Background entered the answer:** D5 required a refresh test. `g-0203`
   (Llama, app-clutter) included that test plus four unrelated tests about
   astronomy, textiles, gardening and audio. Coverage passed, but usability
   and grounding failed ([assessment](judgments/draft-24.json)).
4. **An intended action became an assumption:** F5 did not say which
   confirmation choice the tester made. `g-0197` (Qwen, app-clutter) treated
   Confirm as already selected rather than asking which action occurred.
   Coverage, only-missing and grounding failed
   ([assessment](judgments/feedback-23.json)).

## Supplementary F6 consistency review

The tables above use the original grades only. A separate label-hidden
[consistency review](consistency-review.json) examined `g-0058` and `g-0216`
without the prior grades. Both map to Llama/F6/off-topic, and each occurred once.
The review disagreed with 2 of their 10 criterion labels: it changed `g-0058`
distinctness from unmet to met, and `g-0216` grounding from met to unmet.
It saw both questions as sharing an unsupported assumption about an unreported
save attempt, while treating a broad outcome question and a narrower visible
signal question as potentially distinct.

If those supplementary labels were substituted, the frequency-weighted F6
distinctness count would rise from 24/43 to 25/43 and grounding would fall from
22/43 to 21/43. In that one five-call cell, those criterion rates would change
by +20 and −20 pp respectively. Both answers still fail coverage, so **no
all-check success count or quality percentage in the main tables changes**.
The review itself records a reasonable alternative interpretation of question
presuppositions. This is unresolved grading ambiguity, not human adjudication;
original results and supplementary review remain separate.

## Limits and next steps

There are 12 synthetic cases here, not 540 independent real-world scenarios.
The repeats measure variation within a case. No p-values, model-winner claim,
size-based causal claim or determinism claim follows from this run. Models
differ in family and serving behaviour; the team-confirmed DeepSeek mapping for
`x-test-2` was not verified through provider backend identity or version data.
Requested temperature 0 does not establish effective provider settings.

Quality was assessed by GPT-6.1 Sol, not validated by a human. Graders received
opaque IDs without model/condition labels, but that hiding was procedural,
not an access-control boundary; the coordinator could inspect mappings.
Original calibration agreement and its accepted clarification are documented
separately in the [calibration report](../calibration/results.md) and
[clarification](../calibration/clarification.md). They do not establish that
every experiment grade is correct. The analyzer checks evidence-pointer
structure against saved collection sizes; the [grading audit](grading-audit.json)
records the coordinator's additional checks of all 1,388 primary pointers and
10 supplementary pointers against actual transient accepted candidates. It also
found no conflicting criterion vectors in 14 groups of identical answers
appearing across different cells; those remained separately graded. Raw replies
and candidates were not retained, limiting later independent regrading.

Next, a human should review the F6 ambiguity and a sample of complete-report,
grounding and usability judgments. Focused prompt improvements could make
empty-question answers explicit, distinguish intended steps from actual actions,
and reinforce that background supplies no new task requirements. Any change
should be evaluated with a newly frozen comparison that names the specific
change and keeps the original run available. No further provider run is
authorized or claimed by this report.
