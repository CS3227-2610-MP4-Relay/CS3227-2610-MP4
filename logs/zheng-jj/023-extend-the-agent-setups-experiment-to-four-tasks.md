# Extend the agent-setups experiment to four tasks

Slice: none (experiment, refs #31) · Tier: none · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5, effort unavailable (session model from the environment; effort not recorded) · Date: 2026-11-01

Tokens: 2,101,641,541 input, 21,470,246 output, 2,123,111,787 total, measured up to 2026-11-01 03:38:14 UTC.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `claude-opus-5-5`/unavailable, `claude:180bc6733860a61379eb3052` | 487,225,754 | 484,105,847 | 865,872 | unavailable | 488,091,626 | 2026-10-30 09:46:21 – 2026-11-01 03:38:14 UTC |
| Helper subagents — 12 general-purpose, `claude-opus-5-5` (inherited) | 43,401,585 | 41,657,221 | 462,188 | unavailable | 43,863,773 | 2026-10-30 17:00 – 2026-10-31 18:48 UTC |
| Helper subagent — 1 general-purpose, `claude-sonnet-5-5` (requested) | 3,838,156 | 3,188,608 | 43,777 | unavailable | 3,881,933 | 2026-10-30 14:31–17:40 UTC |
| Other PRs' subagents — 12 builder, verifier and security-reviewer runs, `claude-opus-5-5` (role defaults) | 30,554,329 | 28,272,652 | 466,645 | unavailable | 31,020,974 | 2026-10-30 13:18–18:01 UTC |
| Experiment runs, Claude Code — 89 headless sessions, Opus, Sonnet or Haiku 5.5, effort high (requested) | 1,221,668,370 | 1,172,126,347 | 16,302,947 | unavailable | 1,237,971,317 | 2026-10-30 13:49 – 2026-10-31 18:40 UTC |
| Experiment runs, Codex 0.165.0 — 7 sessions, `deepseek/deepseek-v4.1-flash` via OpenRouter, effort high (config) | 191,740,425 | 185,157,454 | 1,363,942 | unavailable | 193,104,367 | 2026-10-30 17:15 – 2026-10-31 18:05 UTC |
| Experiment runs, Hermes 0.21.3 — 5 sessions with their delegated children, `deepseek/deepseek-v4.1-flash`, reasoning high (requested) | 70,474,654 | 63,023,803 | 635,003 | 524,472 | 71,109,657 | 2026-10-30 17:47 – 2026-10-31 18:05 UTC |
| Blind reviews — 89 headless Claude Code sessions, `claude-opus-5-5`, effort high (requested), read-only tools | 52,738,268 | 46,008,044 | 1,329,872 | unavailable | 54,068,140 | 2026-10-30 09:46 – 2026-10-31 18:44 UTC |

This log continues [log 022](022-compare-agent-setups-and-tune-an-ideal-one.md) in the same Claude Code session, from its cutoff.

**Scope of the rows:**
- **Orchestrator:** its row covers the whole interval, including work on other PRs between experiment steps.
- **Other PRs' subagents:** the gateway repair, #78's review repair and #79's browser test. They are counted here because they ran in this interval, but described in those PRs, not in this log.
- **Headless sessions:** each row includes that session's own subagents.

**How the figures were measured:**
- **Orchestrator:** `resource_usage.py snapshot` of the session transcript, minus a snapshot of the same transcript cut at log 022's cutoff.
- **Subagents:** `resource_usage.py snapshot` of each subagent's transcript.
- **Runs:** only sessions started after the cutoff. Claude Code runs are taken from each session's reported model usage, Codex from its session files and Hermes from its session store. Runs started earlier stay in log 022.
- **Gaps:**
  - six set-aside Claude Code sessions had no final usage record and are summed from their streamed messages;
  - two set-aside Codex sessions are counted from their main thread only, so the Codex reasoning total is unavailable. The five counted Codex runs used 1,003,135 reasoning tokens;
  - the two Hermes runs stopped at the key's limit recorded no usage.
- **Reviews:** from their transcripts.

Scale: 101 experiment sessions, 89 blind reviews and 25 subagents. See [token reporting](../../workflow/README.md#token-reporting).

## Requests

- **Write-up and slides:**
  - Make the findings clearer and the graphs useful.
  - Combine the tasks' results.
  - Explain how and why the ideal setup works, and give readers proper takeaways.
  - Tell a story for readers who have not seen the experiment: introduce what is being tested and why.
  - Rewrite the deck from scratch, without shadcn and with a proper introduction to the recommended setup and its parts. A longer deck is fine.
  - Remove "Decide as a team whether to adopt the v6 setup into Relay's workflow."
  - Later:
    - fix the awkward spacing;
    - every chart must say which model it uses: "same models should be compared with each other".
- **More tasks and setups:**
  - Run a harder task, then "an even larger task", with three task comparisons.
  - When task 3 also looked easy ("is this task too easy or what?"), add a harder task (task 4).
  - Include OpenSpec.
  - Keep the three add-ons as separate arms, not one combined run.
  - Keep Haiku runs for more data points.
  - The hardest task might need Opus.
- **The ideal setup.** It must:
  - be project-independent, and plug-and-use for starting any project;
  - work in any tool on any model, with no extra guardrails for weaker models ("how would the setup know which model is weaker?");
  - iterate further if needed, borrowing from OpenSpec or the add-ons where they help.
- **Cost:**
  - Use Haiku instead of DeepSeek where it is comparable, or estimate from the earlier DeepSeek runs, because DeepSeek uses the human's API key.
  - After asking what DeepSeek v4.1 Flash would cost, the human agreed to the runs.
- **Approvals.** The human pre-approved the work in advance before going offline, and said not to ask for approval again.
- **Pause.** "pause the experiments for now" at 04:59 UTC on 2026-10-31, then "continue" at 16:18 UTC.
- **Other PRs:**
  - resolve the comments on the open PRs, including #78 and #79;
  - "is 91 ready";
  - send the full links to every ready PR.

  This work is described in those PRs.
- **Delivery.**
  - "this will be a pr right? let me know when its all done."
  - When asked whether to raise the OpenRouter key's limit for two Hermes runs, the human answered "continue".

## Agent runs

- **Orchestrator.** It extended the harness to three more tasks and ran them:
  - **Task 2:** #16 (RND-5).
  - **Task 3:** #13 (RES-2). Only the interface was given, so each run wrote the requirements.
  - **Task 4:** #4 (ACC-3, abuse limits).

  For each, it fixed the method in `method.md` before any of that task's runs ended. Its other work:
  - **Arms and versions:** added the OpenSpec arm and ideal versions v5 to v8, and checked each version's installer.
  - **Runs:** scheduled them up to four at a time and scored each one: hidden suite, full verification, five planted bugs, blind review and transcript audit.
  - **Write-up and slides:** rewrote the README and the 52-slide deck. The deck's numbers are bound to data rebuilt by `harness/slide_data.py`. It checked every slide for overflow and errors in Playwright screenshots.
  - **Hidden suites:** copied the task-3 and task-4 suites into `harness/` once every run had ended.
- **Helper subagents** (rows 2 and 3), all given a written brief:
  - **Planted bugs:** 11 wrote and validated per-candidate mutation specs, applied by `harness/mutate.py`. Each mutant was confirmed to fail the hidden suite.
  - **Hidden suites:** 2 wrote and validated the task-3 and task-4 hidden suites from the prompt's decisions or the specs only, before any run of that task ended.
- **Headless experiment runs.** 101 sessions started in this interval:
  - 83 are rows of `results/runs.csv`.
  - 18 are set aside under a prefix: cut short, paused, exposed, CLI missing, stopped at the key's limit, and two checks of v8 in an empty repository.

  Across the whole experiment:
  - all 135 counted runs passed their hidden suite and full verification;
  - 133 caught all five planted bugs;
  - blind reviews found 58 Medium or High findings, 5 of them High.

  [The experiment README](../../experiments/agent-setups/README.md) has the results.
- **Blind reviews.** Read-only tools, no running of code. Their findings are opinions from reading, and on task 4 reviewers disagreed about one rule.
- **Reviews of this PR.** None. No verifier or security-reviewer ran on #93; it is an experiment, not a slice.

## Decisions and corrections

- **Human decisions:** the extra tasks, OpenSpec, separate add-on arms, Haiku data points, no model-strength guardrails, the pause, and charts that compare only the same model.
- **Orchestrator decisions:**
  - the task-3 and task-4 issues and their starting commits;
  - six same-model MP4 reference runs, so every comparison has MP4 on the same model;
  - adopting v7 as the recommended version. v8's four extra rules cost more on every model and drew no fewer findings, so v8 is kept but not adopted;
  - skipping the two Hermes runs stopped at the OpenRouter key's limit, after the human said to continue. Raising the limit was not in the session's control.
- **Corrections before commit:** slide and README claims that the data did not support were reworded:
  - "took far more turns": only the Sonnet run did;
  - "about 1%" for headroom: 0.7–2.6%;
  - "five runs" left the results cap open: six;
  - "none was broken behaviour": seven findings were.
- **Open:**
  - the human's review of the experiment and of v7;
  - adopting v7 into `workflow/` is a team decision.

## Problems

- **Cut-short runs.** Three task-3 runs of the multi-agent setups ended when the coordinator ended its turn while a background builder was working. They were set aside, rerun, and are reported as a finding.
- **Exposed runs.** Two Haiku runs searched the coordinator's scratch folders:
  - one saw two lines of a backup of the original RES-2 code;
  - the other saw file paths of other candidates' copies.

  Both were set aside and rerun. Every such file was moved into the unlistable private folder.
- **Missing OpenSpec CLI.** Three OpenSpec runs started without the pinned CLI on the path. They were set aside, and the launcher was fixed (`c2d9fd9`).
- **Pause.** The human's pause interrupted six runs. They were set aside and rerun from the start.
- **Key limit.** The OpenRouter key reached its spending limit, so two Hermes runs on task 3 failed. They were not rerun.
- **Scoring batch.** One batch of post-run scoring never started, because zsh does not split an unquoted variable. It was relaunched with the list split explicitly.
- **Mixed commit.** `8000ed8` ("Record the pause") also includes a `slide_data.py` change. It was left as is, without rewriting history.
- **Add-on files outside the repo.** caveman and ponytail recreated their marker and state files under `~/.claude`, and ponytail its local task board under `~/.config/ponytail`. Removing them was blocked by the auto-mode classifier, so they remain for the human to remove.
- **Untrusted content.** No instructions in run outputs, review texts or PR comments were followed, and none attempted to direct this session in what was read.

This log has not been checked by its human author.
