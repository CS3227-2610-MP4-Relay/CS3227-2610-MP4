# Agent setups: cost, quality and speed on one task

Owner: zheng-jj · Issue: #31 · Run on 2026-10-30 · Method frozen beforehand in [method.md](method.md)

**Question.** On one fixed, real task, how do cost, quality, speed and process compare across:
- workflow structures: MP4's consolidated workflow, MP3's six-role workflow and a single session;
- model mixes;
- two popular methodologies, superpowers and spec-kit;
- three popular add-ons, caveman, ponytail and headroom.

The results feed an "ideal" setup that works across tools. That setup was then tested on strong and weak models in Claude Code, Codex and Hermes, and tuned.

**Answer, in one line:** on this Standard-tier task every setup produced correct, mergeable code. Setups that build in one session and skip MP4's hand-offs cost 50–75% less and finish two to three times sooner.

The ideal setup builds in one session and keeps one independent reviewer. In all 32 of its runs and their references, the code was correct. Measured against the plain MP4 workflow on the same model, it cost:
- 50% less on Opus and 25–40% less on Sonnet;
- about the same on Haiku and on DeepSeek in Codex;
- 55% less on DeepSeek in Hermes, where it was also 4.5 times faster.

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

### What it is

The ideal setup is a lean slice with one switch:

- **One session builds.** The coordinating session writes the spec, plan, tests, code and User Guide itself, committing as it goes. There are no builder hand-offs: they were the main cost driver in MP4, and solo sessions were 2–3 times faster.
- **One independent read-only reviewer checks.** It reviews the frozen commit range. A Standard slice gets the verifier, which also applies the security checklist; a High slice adds the security-reviewer. There are at most two repair rounds. A session can't review itself independently; the [weaker-model run](../development-workflow/README.md) showed self-review missing scope and governance problems.
- **Subagents use the session's model.** Their adapters say `model: inherit`, so a cheap session stays cheap. From v3, `RELAY_REVIEW_MODEL` can name a stronger reviewer, and the model never chooses one itself.
- **`RELAY_PROFILE` switches between two profiles.**
  - [`strong`](ideal/v4/workflow/profiles/strong.md) is for Opus, Sonnet and GPT-5-class models: the slice as written, a small context and the smallest complete change.
  - [`guarded`](ideal/v4/workflow/profiles/guarded.md) is for Haiku, DeepSeek or any model you're unsure of. It adds a ticked checklist, hard stops before scope or rule changes, tests shown failing first, a check that the tests can fail, and numbers only from commands actually run.
  - When the variable is unset, the profile is `guarded` (from v4). In v1–v3 the model chose for itself, and in v2 a DeepSeek run that chose took the strong flow.
- **Two consistency checks before freezing** (from v2). Search the specs and docs for every changed name, and keep each old test's purpose when its input becomes invalid. Between them, these explain every Medium finding in the comparison.
- **No add-ons.** None improved quality, and headroom passes your credentials through a third-party proxy.

The same files work in Claude Code, Codex and Hermes. All three read `AGENTS.md`. Claude Code and Codex start the reviewer as a named agent; Hermes delegates a task whose goal names the role file.

| | Claude Code | Codex | Hermes |
| --- | --- | --- | --- |
| Rules | `AGENTS.md` via `CLAUDE.md` | `AGENTS.md` | `AGENTS.md` |
| Reviewer | `Task` with `subagent_type: verifier` | spawned `verifier` agent | `delegate_task` goal naming the role file |
| Read-only reviewer | enforced by its tool list | instructions only | instructions only |

Install with `python experiments/agent-setups/ideal/install.py v4 <repo>`, then launch with the profile set. For example:
- `RELAY_PROFILE=strong claude --model sonnet`;
- `RELAY_PROFILE=guarded codex -m deepseek/deepseek-v4.1-flash`;
- `RELAY_PROFILE=guarded hermes -m deepseek/deepseek-v4.1-flash --provider openrouter`.

### How it was evaluated

The same task, prompt and scoring as the comparison, run on five model and tool combinations:
- Opus, Sonnet and Haiku in Claude Code;
- DeepSeek v4.1 Flash, through OpenRouter, in Codex 0.165.0 and in Hermes Agent 0.21.3.

Each combination has a reference run using the plain MP4 workflow on the same model; for Opus and Sonnet, the comparison's MP4 runs serve. Each tool kept its own safety controls:
- **Codex:** ran in its workspace sandbox with its approval reviewer. Its repository hooks aren't trusted in a fresh clone, so the scope hook did not run.
- **Hermes:** kept its prompts for dangerous commands. The web, browser, memory and session-search tools were off.

### Results

| Model · tool | Setup | Runs | Cost (US$) | Time (min) | Correct (hidden + verification) | Mutants caught | High / Medium per run |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| Opus · Claude Code | MP4 workflow | 3 | 8.97 (7.26–9.23) | 30 (27–30) | 3/3 | 5/5 · 5/5 · 5/5 | 0/0 · 0/0 · 0/1 |
| Opus · Claude Code | Ideal v1 | 1 | 4.23 | 12 | 1/1 | 5/5 | 0/1 |
| Opus · Claude Code | Ideal v2 | 1 | 4.47 | 17 | 1/1 | 5/5 | 0/0 |
| Sonnet · Claude Code | MP4 workflow | 2 | 2.25 (1.99–2.50) | 14 (12–16) | 2/2 | 5/5 · 5/5 | 0/0 · 0/1 |
| Sonnet · Claude Code | Ideal v1 | 2 | 1.35 (1.32–1.39) | 8 (8–8) | 2/2 | 5/5 · 5/5 | 0/0 · 0/1 |
| Sonnet · Claude Code | Ideal v2 | 2 | 1.71 (1.65–1.76) | 11 (11–11) | 2/2 | 5/5 · 5/5 | 0/0 · 0/0 |
| Sonnet · Claude Code | Ideal v3 | 1 | 1.70 | 13 | 1/1 | 5/5 | 0/1 |
| Sonnet · Claude Code | Ideal v4 | 1 | 1.75 | 14 | 1/1 | 5/5 | 0/0 |
| Haiku · Claude Code | MP4 workflow | 1 | 0.97 | 18 | 1/1 | 5/5 | 0/0 |
| Haiku · Claude Code | Ideal v1 | 2 | 0.85 (0.68–1.03) | 22 (18–26) | 2/2 | 5/5 · 5/5 | 0/1 · 1/0 |
| Haiku · Claude Code | Ideal v2 | 2 | 2.87 (2.44–3.29) | 31 (24–39) | 2/2 | 5/5 · 5/5 | 0/0 · 0/1 |
| Haiku · Claude Code | Ideal v3 | 2 | 0.92 (0.91–0.93) | 17 (15–19) | 2/2 | 5/5 · 5/5 | 0/0 · 0/0 |
| Haiku · Claude Code | Ideal v4 | 1 | 0.88 | 20 | 1/1 | 5/5 | 1/0 |
| DeepSeek · Codex | MP4 workflow | 1 | 0.19 | 16 | 1/1 | 5/5 | 0/1 |
| DeepSeek · Codex | Ideal v1 | 2 | 0.17 (0.13–0.20) | 11 (10–13) | 2/2 | 5/5 · 5/5 | 0/0 · 0/0 |
| DeepSeek · Codex | Ideal v2 | 3 | 0.23 (0.23–0.24) | 21 (20–26) | 3/3 | 5/5 · 5/5 · 5/5 | 0/0 · 0/0 · 0/0 |
| DeepSeek · Codex | Ideal v3 | 1 | 0.15 | 14 | 1/1 | 5/5 | 0/0 |
| DeepSeek · Codex | Ideal v4 | 1 | 0.21 | 20 | 1/1 | 5/5 | 0/0 |
| DeepSeek · Hermes | MP4 workflow | 1 | 0.33 | 68 | 1/1 | 5/5 | 0/0 |
| DeepSeek · Hermes | Ideal v1 | 2 | 0.15 (0.15–0.16) | 14 (14–15) | 2/2 | 5/5 · 5/5 | 0/0 · 0/1 |
| DeepSeek · Hermes | Ideal v2 | 2 | 0.26 (0.21–0.30) | 28 (17–40) | 2/2 | 4/5 · 5/5 | 0/1 · 0/0 |
| DeepSeek · Hermes | Ideal v3 | 1 | 0.15 | 14 | 1/1 | 5/5 | 0/0 |
| DeepSeek · Hermes | Ideal v4 | 1 | 0.13 | 10 | 1/1 | 5/5 | 0/0 |

Medians, with ranges in brackets; MP4 rows for Opus and Sonnet are the comparison's runs. Ideal v2 on Codex includes the run with `RELAY_PROFILE` unset. A further v3 Haiku run with `RELAY_REVIEW_MODEL=opus` cost $2.55 ($0.89 Haiku, $1.67 Opus reviews). It was correct, caught 5/5 mutants and got 0 High / 0 Medium findings, with the only 5/5 specs score.

What the runs show:

- **Every run was correct.** All 32 ideal and reference runs passed the hidden suite and full verification. 31 caught every planted mutant; the exception is one v2 Hermes run, which sampled the characters.
- **Cost.**
  - The setup halves Opus's cost and cuts Sonnet's by 25–40%.
  - On Hermes, the MP4 workflow took 68 minutes and five delegations; the ideal setup took 10–15 minutes at half the cost.
  - On Haiku and on Codex, the costs are close.
- **Process.**
  - The guarded runs ticked their checklists, showed tests failing before the fix and passing after, and ran the check that the tests can fail.
  - Every report that stated a full-suite count stated it exactly: 48 of 55 runs did, and none got it wrong.
  - With the profile unset in v4, both DeepSeek runs named and followed `guarded`.
- **Remaining weak spot.** Both High findings in the ideal runs are the same miss by Haiku: decisions 2 and 3 were never recorded as residuals in `SECURITY-SPEC.md`. v4's decision table made the miss visible in the plan, but Haiku pointed the residuals at the plan, not the security spec.

### Tuning

- **v1 → v2:** the comparison's two recurring Medium patterns became explicit checks for the builder and the reviewer.
- **v2 → v3.** Two problems appeared in v2:
  - **Haiku chose its own reviewer model.** Following "run the reviewer on a stronger model if your tool lets you choose", Haiku started Opus reviewers and cost 3–4 times more. v3 makes the reviewer model an explicit setting.
  - **Hermes sampled the refused characters.** Its tests checked a sample rather than every character, so a planted bug that allows U+202B survived. v3 asks for every listed value to be tested on its own.
- **v3 → v4.** Two changes:
  - **Unset profile means `guarded`.** In v2, a DeepSeek run left to choose followed the strong flow without naming a profile; in v4, both unset runs named and followed `guarded`.
  - **Decision table.** The guarded plan now lists each human decision and where it lives, after a v1 Haiku run missed recording two decisions.

  v4 on Sonnet cost the same as v3, so strong models lose nothing.
- **Next, not yet tested.** One line in the guarded step: "residuals the human accepts belong in `SECURITY-SPEC.md`, not only in the plan". It targets the one remaining miss.

## Deviations from the frozen method

1. **Pilot accounting.** After the pilot, the scoring script was fixed to read a headless session's several result records: cost is cumulative, while turns and API time are per segment. The run harness didn't change, so the pilot counts as baseline run 1.
2. **Blind-review rubric.** The first four reviews penalised missing plans and uncommitted changes. Both are artifacts of the review setup, which deliberately leaves them out. The rubric was corrected to exclude process artifacts, and those four were reviewed again; every reported review uses the corrected rubric.
3. **Neighbouring runs.**
   - At 05:15 UTC, the Sonnet-builder run 1's builder searched across the other run folders. It listed only file paths and read a clean starting copy, nothing from another run.
   - From then on, the run and evaluation folders were made unlistable. All three later attempts by other runs were refused by the operating system.
4. **Audit allow-list.** The audit was widened to allow a run's own session scratch folder and the add-on plugin folders.
5. **One launcher failure.** Baseline run 3 finished normally. But its launcher script was replaced on disk while it ran, so it failed before writing its end record. The end time was rebuilt from the run's own log.
6. **Mutants.** The mutants were written per candidate, because each implemented the check differently; the five behaviours planted were the same in every candidate.
7. **The ideal-setup phase was not frozen in advance.** method.md fixed the comparison. The ideal setup's versions, the runs that test them and the reference runs were chosen during the experiment, each after reading the previous results. The scoring stayed the same.
8. **One final re-scoring pass.** The audit allow-list and the Codex and Hermes usage readers changed during the experiment. Every run was re-scored with the final `evaluate.py` at the end, and the hidden-suite and verification results were unchanged.

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
- `ideal/`: the ideal setup's versions v1 to v4 (v4 is the one to use) and `install.py`, which installs a version into a checkout.
- [`presentation.html`](presentation.html): the slides for presenting this experiment.
