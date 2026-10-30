# Agent setups: cost, quality and speed on one task

Owner: zheng-jj · Issue: #31 · Run on 2026-10-30 · Method frozen beforehand in [method.md](method.md)

**Question.** On one fixed, real task, how do cost, quality, speed and process compare across:
- workflow structures: MP4's consolidated workflow, MP3's six-role workflow and a single session;
- model mixes;
- two popular methodologies, superpowers and spec-kit;
- three popular add-ons, caveman, ponytail and headroom.

The results feed an "ideal" setup that works across tools. That setup was then tested on strong and weak models in Claude Code, Codex and Hermes, and tuned.

**Status:** the comparison is complete. The ideal setup's evaluation is still running, and its section is filled in when it finishes.

**Answer, in one line:** on this Standard-tier task every setup produced correct, mergeable code. Setups that build in one session and skip MP4's hand-offs cost 50–75% less and finish two to three times sooner. The ideal setup keeps the one thing a single session can't give itself: an independent reviewer.

## The comparison (23 runs, Claude Code)

Every run redid issue #68 from `01f9a24` with the same prompt, decisions, tool version (Claude Code 2.1.312), permissions and test environment ([method](method.md)). Each setup ran twice and the MP4 baseline three times. The merged PR #71 was the hidden reference.

### Quality: all at the ceiling

| Check | Result across all 23 runs |
| --- | --- |
| Hidden acceptance suite, 132 tests written from the issue before any run | 132/132 in every run |
| Full verification (Django check, migrations check, Ruff, pytest) | Passed in every run |
| Five planted mutants in each candidate's own code | 5/5 caught by its own tests in every run; each mutant confirmed live by the hidden suite |
| Spec committed before code | Every run |
| Blind review by a fresh Opus session (random labels, product diff only) | 0 High findings; 0–2 Medium per setup, 10 in total |

On correctness, the task did not separate the setups. The Medium findings were consistency gaps, not wrong behaviour:
- **Out-of-date spec text.** Six of the 10 left a second spec saying something no longer true, such as `TECHNICAL-SPEC.md`'s list of field checks or a rendering-rule sentence.
- **Weakened tests.** Two changed an existing rendering test's input from a now-refused control character to an allowed mark. That quietly dropped coverage of text stored by other means.
- **Coverage gap.** One allowed-character test missed the joiners and right-to-left letters.
- **False positive.** One claimed a Ruff rule would fail, but the run's own Ruff check and ours both passed.

### Cost and speed

Cost is Claude Code's reported cost at API list prices; the account's subscription billing differs. Medians, with ranges in brackets.

| Setup | Runs | Cost (US$) | vs MP4 | Time (min) | Subagent runs | Output tokens | Cache reads | Medium / Low findings |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | --- |
| MP4, all Sonnet | 2 | 2.25 (1.99–2.50) | −75% | 14 (12–16) | 5 | 82k | 4.5M | 1 / 9 |
| Solo: one Opus session, no subagents | 2 | 3.35 (3.27–3.44) | −63% | 13 (12–14) | 0 | 46k | 6.2M | 0 / 8 |
| superpowers | 2 | 4.14 (3.99–4.30) | −54% | 12 (11–14) | 1 | 55k | 7.6M | 2 / 5 |
| spec-kit | 2 | 4.40 (3.96–4.84) | −51% | 12 (11–13) | 0 | 62k | 8.0M | 1 / 7 |
| MP4 + ponytail | 2 | 4.54 (3.93–5.14) | −49% | 17 (13–20) | 6 | 80k | 5.1M | 1 / 8 |
| MP4 + caveman + ponytail + headroom | 2 | 5.52 (5.16–5.88) | −38% | 20 (19–21) | 6 | 97k | 6.3M | 1 / 6 |
| MP4, Sonnet builder | 2 | 5.72 (4.17–7.28) | −36% | 22 (17–27) | 8 | 125k | 7.3M | 2 / 6 |
| MP3 six roles | 2 | 5.77 (5.50–6.04) | −36% | 22 (21–23) | 10 | 103k | 6.4M | 0 / 10 |
| MP4 + headroom | 2 | 5.85 (5.21–6.48) | −35% | 24 (23–26) | 6 | 104k | 7.5M | 1 / 8 |
| MP4 + caveman | 2 | 6.13 (5.45–6.82) | −32% | 24 (23–25) | 6 | 107k | 7.2M | 0 / 7 |
| **MP4 baseline** | 3 | **8.97 (7.26–9.23)** | — | **30 (27–30)** | 9 | 160k | 11.0M | 1 / 13 |

The 23 runs cost US$120.81 at list prices and took 7.5 hours of run time, three at a time. Per-run data is in [`results/runs.csv`](results/runs.csv).

### What the numbers say

1. **Hand-offs, not code, drive MP4's cost.**
   - In MP4 runs, 50–70% of cached reads happen in subagents. Each subagent re-reads the repository context and writes a fresh cache.
   - Fitting all 19 single-model Opus runs gives the cost split by token type: cache reads about 41%, cache writes about 40%, output about 20%.
   - MP4 wrote 0.50–0.63M cache tokens per run; solo wrote 0.14–0.15M.
   - The coordinator's choices widen the spread. One Sonnet-builder run added a security review and two repair rounds, so 11 subagent runs, and cost 75% more than its twin.
2. **One session is fastest.**
   - Solo, superpowers and spec-kit each built in a single session (superpowers used one subagent, for review) and finished in 11–14 minutes.
   - MP4's sequence of builder checkpoints, verifier and repair rounds took 27–30.
3. **Sonnet was enough here.** All-Sonnet MP4 was the cheapest setup and fully correct; one of its two runs had a Medium spec finding. A Sonnet builder under an Opus coordinator saved less, because the Opus coordinator and reviewers stayed.
4. **MP3's extra roles didn't add quality.** It used the most subagent runs (10) and wrote the most test code (410 lines, against 240 for MP4). It came out cheaper than MP4 only because each MP3 role reads less.
5. **The methodologies matched solo, at a little more cost.**
   - superpowers and spec-kit brought their own planning and test-first discipline, and both were correct.
   - Each cost about 25–30% more than solo and left the same kind of spec-consistency gaps.
   - Neither did an independent review unless asked. superpowers ran one review subagent.
6. **The add-ons:**
   - **ponytail** gave the smallest change: 126 lines of tests against 240, and the same quality. It was the cheapest add-on.
   - **caveman** cut output tokens by about a third (107k against 160k). But output is only about a fifth of cost, and its final reports were in normal prose anyway.
   - **headroom** compressed 0.9–1.1% of request traffic in all four runs that used it. Its cost difference from the baseline can't come from compression.
   - **All four add-on setups ran cheaper than every baseline run,** with fewer subagent runs: 6 against 9. With two runs each, I can't say whether that's an effect of the instructions they inject or just variation in the coordinator's choices.

## The ideal setup

Built from the comparison and the [weaker-model run](../development-workflow/README.md), then evaluated as below. The files are in [`ideal/`](ideal/), with an [installer](ideal/install.py).

<!-- ideal-results -->

## Deviations from the frozen method

1. **Pilot accounting.** After the pilot, the scoring script was fixed to read a headless session's several result records: cost is cumulative, while turns and API time are per segment. The run harness didn't change, so the pilot counts as baseline run 1.
2. **Blind-review rubric.** The first four reviews penalised missing plans and uncommitted changes. Both are artifacts of the review setup, which deliberately leaves them out. The rubric was corrected to exclude process artifacts, and those four were reviewed again; every reported review uses the corrected rubric.
3. **Neighbouring runs.**
   - At 05:15 UTC, the Sonnet-builder run 1's builder searched across the other run folders. It listed only file paths and read a clean starting copy, nothing from another run.
   - From then on, the run and evaluation folders were made unlistable. All three later attempts by other runs were refused by the operating system.
4. **Audit allow-list.** The audit was widened to allow a run's own session scratch folder and the add-on plugin folders.
5. **One launcher failure.** Baseline run 3 finished normally. But its launcher script was replaced on disk while it ran, so it failed before writing its end record. The end time was rebuilt from the run's own log.
6. **Mutants.** The mutants were written per candidate, because each implemented the check differently; the five behaviours planted were the same in every candidate.

## Limitations

- One Standard-tier task, small and clearly specified, with the decisions given up front. The ranking may not hold for large, ambiguous or High-tier work, where independent review has more to find.
- Two or three runs per setup. Only differences whose ranges don't overlap are worth reading. Quality was at the ceiling, so the comparison mostly measures cost and speed.
- Opus wrote the hidden suite, the mutants and the blind reviews, and also did most of the building. The hidden suite and the mutants are the objective checks.
- Cost is at API list prices from Claude Code's own report. Cache behaviour depends on the account's 1-hour cache.
- Runs overlapped three at a time, so times include some contention.

## Files

- [`method.md`](method.md): the frozen method.
- `inputs/`: the task prompt, the smoke-test prompt and the run queues.
- `harness/`:
  - `setup_arm.py` builds each setup;
  - `run_arm.sh` and `run_other.sh` launch runs in Claude Code, or in Codex and Hermes;
  - `schedule.py` runs a queue;
  - `evaluate.py`, `mutate.py` and `review.py` score each run;
  - `aggregate.py` builds the tables;
  - `test_hidden_direction_controls.py` is the hidden suite.
- `results/`: `runs.csv`, `summary.json` and the per-candidate mutant definitions in `mutations/`.
- `ideal/`: the ideal setup, its versions and its installer.
- [`presentation.html`](presentation.html): the slides for presenting this experiment.
