# Agent setups: what a coding-agent workflow costs, and what it buys

Owner: zheng-jj · Issue: #31 · Run on 2026-10-30 · Method fixed in advance in [method.md](method.md) · Slides: [presentation.html](presentation.html)

**Question.** Coding agents can be set up in many ways: one session or a team of subagents, a strong or a cheap model, a methodology plugin, a token-saving add-on. On real tasks, with everything else held fixed, how do these setups compare on cost, quality and speed? And what setup gives the best balance, in any tool?

**Answer.**
1. **Quality did not separate the setups.** On both tasks, every comparison run passed its hidden acceptance suite and full verification, and its own tests caught every planted bug. No blind review found a High issue.
2. **Hand-offs are the cost.** In MP4's workflow, about half of each run's money went on subagents re-reading the repository. Setups that build in one session cost 45–63% less than MP4 and took 40–66% of its time, on both tasks.
3. **The add-ons do not pay.** caveman, ponytail and headroom each cost 32–49% less than MP4 on task 1, but between 19% less and 10% more on task 2. Cost followed how many subagents the coordinator started, not the add-on.
4. **The methodologies are one session with ceremony.** superpowers and spec-kit cost what a single session costs, with the same quality. Neither adds an independent review unless asked.
5. **The ideal setup builds in one session and keeps one independent reviewer.** Its portable version cost about half of MP4 on Opus (45–48% less), and far less on Sonnet, with the same quality. A guarded profile keeps weaker models on track. On Haiku it is not reliably cheaper than MP4, but it is up to twice as fast.

## Takeaways

If you run coding agents on a real repository:

1. **Build in one session.** Builder subagents doubled the cost and the time here, with no quality gain. Each one starts cold and reads the repository again.
2. **Keep exactly one independent reviewer.** A session cannot review its own work independently. In an earlier weaker-model run, self-review missed scope and ownership problems. One reviewer costs a fraction of MP4's repeated reviews.
3. **Try the cheaper model first.** Sonnet passed every check on both tasks at 25–40% of Opus's cost. On task 1, Haiku and DeepSeek v4.1 Flash were correct too, with the guarded profile.
4. **Give weaker models a checklist, not freedom.** Without one, they chose expensive reviewer models, sampled values instead of testing each one, and took the loose profile.
5. **Check consistency before review.** Every Medium or High review finding was a consistency gap: spec text claiming more than the code or tests do, a decision left out of its home, or an old test weakened.
6. **Write the project's facts down once.** One file of commands, folders, homes and budgets let the same workflow move between repositories and tools.

Skip, or measure on your own work first:
- **Output-compression and proxy add-ons.** The savings were small or absent, and a proxy sees your credentials.
- **More roles.** MP3's six roles found nothing extra.
- **Letting the model pick its reviewer or profile.** It chose the expensive or the loose option.
- **Conclusions from one task.** Task 1 made the add-ons look useful; task 2 did not.

## What was compared

Twelve setups, each run headless in Claude Code 2.1.312 with the same prompt, permissions and test environment:

| Group | Setup | What it is |
| --- | --- | --- |
| Workflow | **MP4 baseline** | MP4's slice: a coordinator with builder, verifier and security-reviewer subagents |
| Workflow | MP3 six roles | spec-writer, spec-critic, test-writer, implementer, reviewer, security-reviewer |
| Workflow | Solo session | MP4's slice, with one session playing every role |
| Model mix | MP4, Sonnet builder | Sonnet builder; Opus coordinator and reviewers |
| Model mix | MP4, all Sonnet | every role on Sonnet |
| Methodology | superpowers | obra/superpowers skills, at a pinned commit |
| Methodology | spec-kit | GitHub's Spec-Driven Development toolkit |
| Add-on | MP4 + caveman | terse-output plugin |
| Add-on | MP4 + ponytail | smallest-change plugin |
| Add-on | MP4 + headroom | context-compressing local proxy |
| Ideal | Ideal v1 | the first lean slice built from the task-1 results |
| Ideal | Ideal v5 | the portable, project-independent version |

Opus 5.5 is the session model unless the setup says otherwise. Each add-on is compared on its own. A run with all three add-ons together was made on task 1 only; its data is in `results/runs.csv`, and it is left out of every comparison here.

## The two tasks

| | Task 1 · #68 | Task 2 · #16 |
| --- | --- | --- |
| Change | Refuse hidden text-direction characters in 12 round-text inputs | Request a retest (RND-5): a new page, form and service, with checks under a row lock, a build cap, label rules and escaping |
| Typical diff | 12–20 lines of code, about 200 of tests | 100–140 lines of code, about 1,000 of tests |
| Hidden suite | 132 tests | 27 HTTP tests |
| Planted bugs | no check; two controls allowed; a mark refused; build labels unchecked | foreign cases accepted; cap off by one; labels compared as typed; any round state accepted; label unescaped |
| Runs | 2 per setup, 3 for MP4 | 1 per setup, 2 for MP4 and v5; then v6 on Sonnet and Haiku |

Both prompts gave the human's decisions up front, so no run needed a human. Each run worked in its own clone with no later history, its own test database and no web or GitHub access.

**Scoring** ([method](method.md#measures)):
- **Hidden suite:** written from the issue and decisions only, before any run.
- **Full verification:** Django check, `makemigrations --check`, Ruff and the full pytest suite.
- **Planted bugs:** five per candidate, planted in its own code; its own tests must fail.
- **Blind review:** a fresh Opus session with a random label, reading only the product diff.
- **Transcript audit:** spec before code, commits, and any access outside the run's clone.

Cost is each tool's own report at API list prices; the subscription bills differently. Time is wall-clock, with three or four runs overlapping.

## Results

### Quality

| Setup | Task 1 | Task 2 |
| --- | --- | --- |
| MP4 baseline | 3/3 correct · bugs 15/15 · High/Med 0 / 1 | 2/2 correct · bugs 10/10 · High/Med 0 / 0 |
| MP3 six roles | 2/2 correct · bugs 10/10 · High/Med 0 / 0 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| Solo session | 2/2 correct · bugs 10/10 · High/Med 0 / 0 | not run |
| MP4, Sonnet builder | 2/2 correct · bugs 10/10 · High/Med 0 / 2 | not run |
| MP4, all Sonnet | 2/2 correct · bugs 10/10 · High/Med 0 / 1 | not run |
| superpowers | 2/2 correct · bugs 10/10 · High/Med 0 / 2 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| spec-kit | 2/2 correct · bugs 10/10 · High/Med 0 / 1 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| MP4 + caveman | 2/2 correct · bugs 10/10 · High/Med 0 / 0 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| MP4 + ponytail | 2/2 correct · bugs 10/10 · High/Med 0 / 1 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| MP4 + headroom | 2/2 correct · bugs 10/10 · High/Med 0 / 1 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| Ideal v1 | 1/1 correct · bugs 5/5 · High/Med 0 / 1 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| Ideal v5 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 | 2/2 correct · bugs 10/10 · High/Med 0 / 0 |

"Correct" means the whole hidden suite and full verification passed. Each planted bug was also confirmed to fail the hidden suite.

**What the blind reviews found.** Across every run, including the ideal-setup runs on other models, there were 24 findings of Medium or above. Two were High, both in the ideal setup's Haiku runs on task 1. None was wrong behaviour. Sorted by hand into kinds:
- **Spec text claiming more than the code or tests do (10).** The most common was a rendering rule rewritten to say each criterion's tests cover direction marks, when only one did.
- **A decision or accepted risk missing or misrecorded (7).** This includes both Highs, where Haiku did not record two of the human's decisions as residuals. Twice, a run recorded a residual as accepted that the human never accepted.
- **An old test weakened, or a coverage gap (6).** Examples are a rendering test switched from a now-refused character to an allowed one, an allowed-character test that skipped the joiners, and a storage-failure test that mocked the whole service.
- **A reviewer false positive (1).**

Task 2 produced 3 Medium findings in 16 runs, against 21 in 58 runs on task 1. One possible reason, not tested: its eight decisions were more explicit, which left less room for stale text.

**Reports were accurate.** Every final report that stated a full-suite test count stated the one we measured: 63 of 74 runs did, and none got it wrong.

### Cost and time

Medians, with ranges in brackets; "vs MP4" compares with MP4 on the same task.

| Setup | Task 1 runs | Task 1 cost (US$) | vs MP4 | Task 1 min | Task 2 runs | Task 2 cost (US$) | vs MP4 | Task 2 min | Subagent runs (T1 / T2) |
| --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- |
| MP4, all Sonnet | 2 | 2.25 (1.99–2.50) | −75% | 14 (12–16) | — | — | — | — | 5 / — |
| Solo session | 2 | 3.35 (3.27–3.44) | −63% | 13 (12–14) | — | — | — | — | 0 / — |
| superpowers | 2 | 4.14 (3.99–4.30) | −54% | 12 (11–14) | 1 | 5.60 | −51% | 17 | 1 / 1 |
| Ideal v1 | 1 | 4.23 | −53% | 12 | 1 | 6.35 | −45% | 25 | 2 / 3 |
| spec-kit | 2 | 4.40 (3.96–4.84) | −51% | 12 (11–13) | 1 | 5.48 | −52% | 23 | 0 / 0 |
| MP4 + ponytail | 2 | 4.54 (3.93–5.14) | −49% | 17 (13–20) | 1 | 9.32 | −19% | 31 | 6 / 10 |
| Ideal v5 | 1 | 4.96 | −45% | 19 | 2 | 5.97 (5.94–6.00) | −48% | 19 (18–20) | 3 / 3 |
| MP4, Sonnet builder | 2 | 5.72 (4.17–7.28) | −36% | 22 (17–27) | — | — | — | — | 8 / — |
| MP3 six roles | 2 | 5.77 (5.50–6.04) | −36% | 22 (21–23) | 1 | 11.88 | +4% | 37 | 10 / 14 |
| MP4 + headroom | 2 | 5.85 (5.21–6.48) | −35% | 24 (23–26) | 1 | 12.55 | +10% | 44 | 6 / 12 |
| MP4 + caveman | 2 | 6.13 (5.45–6.82) | −32% | 24 (23–25) | 1 | 10.85 | −5% | 41 | 6 / 9 |
| MP4 baseline | 3 | 8.97 (7.26–9.23) | — | 30 (27–30) | 2 | 11.46 (10.92–12.00) | — | 38 (36–40) | 9 / 10 |

Per-run data is in [`results/runs.csv`](results/runs.csv).

### Why: the money goes on hand-offs

Claude Code caches the context it sends. A cache write costs about 20 times a cache read, and a subagent always starts with an empty context. Every MP4 subagent therefore reads `AGENTS.md`, its role, the specs and the code again, and caches all of it afresh, and the coordinator then reads its report back. MP4 runs started 8–10 subagents on task 1 and 9–12 on task 2.

Splitting each run's tokens with rates fitted to 19 single-model Opus runs gives where the money went:
- **MP4:** about 54% (task 1) and 55% (task 2) of an average run's money went on subagent context, 21–24% on its main session and 22–24% on output.
- **One-session setups** spend most of theirs in the main session, which reads the repository once and keeps its cache for the whole build: 51–83% for solo, superpowers, spec-kit and the ideal. The ideal's one reviewer is 23–29%.
- **Cache writes:** MP4 cached 4.2 times as much context per run as a solo session on task 1.

The coordinator's choices widen the spread. One Sonnet-builder run on task 1 added a security review and two repair rounds, 11 subagent runs, and cost 75% more than its twin.

### The add-ons, one at a time

| Add-on | Promise | Measured | Verdict |
| --- | --- | --- | --- |
| caveman | Fewer output tokens | Output: 107k vs 160k (task 1), 200k vs 223k (task 2). Cost: −32% then −5%. | Real but small. Output is about a fifth of cost, and final reports came out in normal prose anyway. |
| ponytail | Smaller changes | Test lines: 126 vs 240 (task 1), 934 vs 1,129 (task 2). Cost: −49% then −19%. | Leaner tests, same quality. The saving shrank as soon as the coordinator started more subagents. |
| headroom | Compressed context | 0.9–1.1% of request traffic compressed, in all five runs that used it. Cost: −35% then +10%. | Too little compression to matter. It also routes your credentials through a third-party proxy. |

On task 1, every add-on run started fewer subagents than every MP4 run, 6 against 8–10, which explains its lower cost. On task 2 they started 9–12, as MP4 did, and the saving mostly went. None of the three changed quality.

### Workflows, models and methodologies

- **MP3's six roles** wrote the most test code and found nothing extra. MP3 was cheaper than MP4 on task 1 only because each role reads less. On task 2 it started 14 subagents and cost 4% more than MP4.
- **A solo session** playing every MP4 role was the cheapest Opus setup on task 1. Its weakness is that it reviews its own work.
- **Sonnet was enough** for both tasks. All-Sonnet MP4 cost 75% less than Opus MP4 on task 1, and the ideal setup on Sonnet cost $1.47 (task 1) and $2.29 (task 2). A Sonnet builder under an Opus coordinator saved less, because the Opus coordinator and reviewers stayed.
- **superpowers and spec-kit** each built in one session and cost what a solo session costs. They bring planning and test-first habits. superpowers started one review subagent; spec-kit started none.

## The ideal setup

The package to use is [`ideal/v6/`](ideal/v6/); its [README](ideal/v6/README.md) covers installing and running it. v6 is the portable v5 plus three rules taken from v5's own review findings. Versions v1 to v4 were Relay-specific steps towards it.

### How it works

One session builds the change; one independent, read-only reviewer checks it. The workflow, in [`agent-workflow/slice.md`](ideal/v6/agent-workflow/slice.md):
1. **Specify:** update the requirements first, and write a short plan.
2. **Build:**
   - write the tests first and see them fail, mocking only what lies outside the change;
   - make the smallest complete change;
   - test every listed value on its own;
   - commit as you go.
3. **Check consistency:**
   - every mention of what changed is updated, and every claim that tests cover something points to a test that does;
   - every old test still tests what it did;
   - every human decision has a home, and nothing is recorded as accepted that the human did not decide.
4. **Freeze:** run the project's full verification once, on the final candidate.
5. **Review:** start one independent read-only reviewer on the frozen commit range, and a security reviewer for high-risk areas.
6. **Repair:** at most two repair rounds, then report to the human.

Two switches tune it to the model:
- **`AGENT_PROFILE`:**
  - `strong` (Opus, Sonnet, GPT-5-class) follows the slice as written.
  - Anything else, or unset, gets `guarded`. That adds a ticked checklist, hard stops before scope or rule changes, tests shown failing first, a check that the tests can fail, and numbers only from commands actually run.
- **`AGENT_REVIEW_MODEL`:** optionally names a stronger reviewer. Otherwise the reviewer uses the session's model; the model never chooses one itself.

Everything particular to a repository is in one file, `agent-workflow/project.md`:
- the verification command and the folders;
- where requirements, docs, plans and accepted risks live;
- the high-risk areas and the size budget.

The installer adds a marked block to `AGENTS.md`, plus the adapters:
- Claude Code subagents and a skill;
- Codex agents;
- a skill that Codex and Hermes both read.

So the same workflow runs in any tool that reads `AGENTS.md`. Hermes delegates the review as a task.

### Why each rule is there

| Rule | Evidence |
| --- | --- |
| Build in one session | Subagent context was about half of MP4's money; one-session setups cost 45–63% less with the same quality. |
| Keep one independent reviewer | A session reviewing itself missed scope and ownership problems in the earlier weaker-model run. One reviewer is a fraction of MP4's repeated reviews. |
| Reviewer on the session's model unless set | Left to choose, Haiku started Opus reviewers on its own and tripled its cost (v2). |
| The three consistency checks | Every Medium or High finding was one of the three gaps. |
| Test each listed value | A DeepSeek run sampled the refused characters, and a planted bug that allowed one survived (v2). |
| Unset profile means guarded | A DeepSeek run left to choose took the strong flow (v2). From v4, every unset run chose guarded. |
| Project facts in one file | Haiku kept recording accepted risks in its plan until `project.md` named their home; the v5 Haiku run on task 1 got it right. |
| Only the human's decisions are accepted (v6) | Two runs recorded a residual as accepted that the human never accepted: one MP4 Sonnet-builder run and one v5 Sonnet run. |
| Claims about tests point to a test (v6) | The commonest finding was spec text saying tests covered something they did not. |
| Mock only outside the change (v6) | A v5 Haiku run mocked the whole retest service, so its storage-failure test checked nothing. |
| No add-ons | None improved quality, and their task-1 savings did not survive task 2. |

### How it was evaluated

The same scoring as the comparison, on five model and tool combinations. Each combination has a reference run of the plain MP4 workflow on the same model:
- **Claude Code:** Opus, Sonnet and Haiku.
- **Codex 0.165.0:** DeepSeek v4.1 Flash, through OpenRouter, in its workspace sandbox with its approval reviewer.
- **Hermes Agent 0.21.3:** DeepSeek v4.1 Flash, with its prompts for dangerous commands on and its web, browser and memory tools off.

DeepSeek ran on task 1 only. To keep API spending down, Haiku stood in for weaker models on task 2.

| Platform · task | Setup | Runs | Cost (US$) | Time (min) | Quality |
| --- | --- | ---: | --- | --- | --- |
| Opus · 1 | MP4 workflow | 3 | 8.97 (7.26–9.23) | 30 (27–30) | 3/3 correct · bugs 15/15 · High/Med 0 / 1 |
| Opus · 1 | Ideal v1 | 1 | 4.23 | 12 | 1/1 correct · bugs 5/5 · High/Med 0 / 1 |
| Opus · 1 | Ideal v2 | 1 | 4.47 | 17 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| Opus · 1 | Ideal v5 | 1 | 4.96 | 19 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| Opus · 2 | MP4 workflow | 2 | 11.46 (10.92–12.00) | 38 (36–40) | 2/2 correct · bugs 10/10 · High/Med 0 / 0 |
| Opus · 2 | Ideal v1 | 1 | 6.35 | 25 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| Opus · 2 | Ideal v5 | 2 | 5.97 (5.94–6.00) | 19 (18–20) | 2/2 correct · bugs 10/10 · High/Med 0 / 0 |
| Sonnet · 1 | MP4 workflow | 2 | 2.25 (1.99–2.50) | 14 (12–16) | 2/2 correct · bugs 10/10 · High/Med 0 / 1 |
| Sonnet · 1 | Ideal v1 | 2 | 1.35 (1.32–1.39) | 8 (8–8) | 2/2 correct · bugs 10/10 · High/Med 0 / 1 |
| Sonnet · 1 | Ideal v2 | 2 | 1.71 (1.65–1.76) | 11 (11–11) | 2/2 correct · bugs 10/10 · High/Med 0 / 0 |
| Sonnet · 1 | Ideal v3 | 1 | 1.70 | 13 | 1/1 correct · bugs 5/5 · High/Med 0 / 1 |
| Sonnet · 1 | Ideal v4 | 1 | 1.75 | 14 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| Sonnet · 1 | Ideal v5 | 1 | 1.47 | 10 | 1/1 correct · bugs 5/5 · High/Med 0 / 1 |
| Sonnet · 2 | Ideal v5 | 1 | 2.29 | 14 | 1/1 correct · bugs 5/5 · High/Med 0 / 1 |
| Sonnet · 2 | Ideal v6 | 1 | 2.20 | 12 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| Haiku · 1 | MP4 workflow | 1 | 0.97 | 18 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| Haiku · 1 | Ideal v1 | 2 | 0.85 (0.68–1.03) | 22 (18–26) | 2/2 correct · bugs 10/10 · High/Med 1 / 1 |
| Haiku · 1 | Ideal v2 | 2 | 2.87 (2.44–3.29) | 31 (24–39) | 2/2 correct · bugs 10/10 · High/Med 0 / 1 |
| Haiku · 1 | Ideal v3 | 2 | 0.92 (0.91–0.93) | 17 (15–19) | 2/2 correct · bugs 10/10 · High/Med 0 / 0 |
| Haiku · 1 | Ideal v4 | 1 | 0.88 | 20 | 1/1 correct · bugs 5/5 · High/Med 1 / 0 |
| Haiku · 1 | Ideal v5 | 1 | 1.46 | 27 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| Haiku · 2 | MP4 workflow | 1 | 1.95 | 56 | 1/1 correct · bugs 5/5 · High/Med 0 / 1 |
| Haiku · 2 | Ideal v5 | 1 | 2.18 | 29 | 1/1 correct · bugs 5/5 · High/Med 0 / 1 |
| Haiku · 2 | Ideal v6 | 1 | 1.85 | 36 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| DeepSeek · Codex · 1 | MP4 workflow | 1 | 0.19 | 16 | 1/1 correct · bugs 5/5 · High/Med 0 / 1 |
| DeepSeek · Codex · 1 | Ideal v1 | 2 | 0.17 (0.13–0.20) | 11 (10–13) | 2/2 correct · bugs 10/10 · High/Med 0 / 0 |
| DeepSeek · Codex · 1 | Ideal v2 | 3 | 0.23 (0.23–0.24) | 21 (20–26) | 3/3 correct · bugs 15/15 · High/Med 0 / 0 |
| DeepSeek · Codex · 1 | Ideal v3 | 1 | 0.15 | 14 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| DeepSeek · Codex · 1 | Ideal v4 | 1 | 0.21 | 20 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| DeepSeek · Hermes · 1 | MP4 workflow | 1 | 0.33 | 68 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| DeepSeek · Hermes · 1 | Ideal v1 | 2 | 0.15 (0.15–0.16) | 14 (14–15) | 2/2 correct · bugs 10/10 · High/Med 0 / 1 |
| DeepSeek · Hermes · 1 | Ideal v2 | 2 | 0.26 (0.21–0.30) | 28 (17–40) | 2/2 correct · bugs 9/10 · High/Med 0 / 1 |
| DeepSeek · Hermes · 1 | Ideal v3 | 1 | 0.15 | 14 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |
| DeepSeek · Hermes · 1 | Ideal v4 | 1 | 0.13 | 10 | 1/1 correct · bugs 5/5 · High/Med 0 / 0 |

A further v3 Haiku run with `RELAY_REVIEW_MODEL=opus` cost $2.55: $0.89 for Haiku and $1.67 for the Opus reviews. It was correct, caught 5/5 planted bugs, and had no High or Medium findings.

What the runs show:
- **Quality.** Every ideal-setup run was correct. All but one caught every planted bug: one v2 Hermes run tested a sample of the refused characters, and v3 fixed that.
- **Strong models.** The setup halves Opus's cost on both tasks and takes 40–70% of MP4's time. On Sonnet it cost $1.35–1.75 on task 1, against $2.25 for all-Sonnet MP4.
- **Weak models.**
  - On Hermes, MP4 took 68 minutes and five delegations; the ideal setup took 10–15 minutes at half the cost.
  - On Codex the costs were close.
  - **On Haiku, the ideal is not reliably cheaper than MP4.** MP4's subagents run on cheap Haiku too, while the guarded checklist adds turns.
    - Task 1: v3 and v4 matched MP4's cost, and v5 cost $1.46 against MP4's $0.97, over 128 turns. v5 was the first Haiku run on task 1 with no High or Medium finding.
    - Task 2: v5 cost $2.18 and v6 $1.85, against MP4's $1.95. Both ideal runs took 29–36 minutes, against MP4's 56.
- **Process.** Guarded runs ticked their checklists, showed tests failing before the fix and passing after, and ran the can-fail check. With the profile unset, every v4, v5 and v6 run named and followed `guarded`.

### Tuning, v1 to v6

- **v1 → v2:** the comparison's two recurring Medium patterns became explicit checks: stale spec text, and old tests switched to allowed inputs. This removed the Medium spec findings on Sonnet and Opus.
- **v2 → v3:**
  - **Reviewer model.** Following "run the reviewer on a stronger model if your tool lets you choose", Haiku started Opus reviewers and cost three to four times more. v3 makes the reviewer model an explicit setting.
  - **Listed values.** A Hermes run sampled the refused characters. v3 asks for every listed value to be tested on its own.
- **v3 → v4:**
  - an unset profile means `guarded`, after a DeepSeek run left to choose took the strong flow;
  - the guarded plan maps each human decision to where it lives, after a Haiku run missed two.
- **v4 → v5:**
  - **Portable.** The workflow no longer names a project. Commands, folders, homes, high-risk areas and the size budget moved into `project.md`, and an installer works on any Git repository.
  - **A named home for risks.** The decisions-and-risks home is now named, and the Haiku run recorded its residuals there.
- **v5 → v6:** three rules from v5's review findings:
  - record as accepted only what the human decided, and report anything new as an open question;
  - a claim that tests cover something must point to a test that does;
  - mock only what lies outside the change.

  On task 2, v6 on Sonnet ($2.20) and on Haiku ($1.85) had no High or Medium findings, where v5 had one Medium on each ($2.29 and $2.18). Both v6 runs were correct, and their tests caught every planted bug. That is one run each: enough to show the rules cost nothing, not that they reliably help.

## Deviations from the frozen method

1. **Pilot accounting.** After the pilot, the scoring script was fixed to read a headless session's several result records: cost is cumulative, while turns and API time are per segment. The run harness did not change, so the pilot counts as MP4 run 1.
2. **Blind-review rubric.** The first four task-1 reviews penalised missing plans and uncommitted changes, which the review setup leaves out on purpose. The rubric was corrected and those four reviewed again.
3. **Neighbouring runs.**
   - At 05:15 UTC, the Sonnet-builder run 1's builder listed other run folders. It read only a clean starting copy. The run folders were then made unlistable.
   - At 14:49 UTC, the v5 Haiku run on task 1 built paths from the session folder. Two searches returned lines from scratch files: gateway backups, older patches and copies of task 2's starting code. None was task 1's reference or hidden suite, so the run counts.
   - A stray copy of task 2's hidden suite sat in a listable scratch clone from about 14:00 to 14:55 UTC and was then deleted. No task-2 run's audit shows access to it.
   - Making the scratch folder unlistable broke Git checkouts beneath it, so it was reverted after about two minutes. One blind review failed in that window and was rerun.
   - On task 2, Haiku runs again built paths from the session folder (v5 21 times, MP4 27, v6 once). Those searches found nothing or hit paths that do not exist. One MP4 Haiku subagent wrote backup copies of the run's own two source files to the coordinator's scratch folder during its can-fail check, then restored them. Nothing came into any run from outside, so all three count.
4. **Audit allow-list.** Widened to allow a run's own session scratch folder and the add-on plugin folders. The headroom run's three flagged accesses on task 2 were a mistyped path to its own clone.
5. **One launcher failure.** MP4 run 3 on task 1 finished normally, but its launcher script was replaced on disk while it ran, so its end record was rebuilt from the run's own log.
6. **Planted bugs.** These were written per candidate, because each implemented the checks differently. The behaviours planted were the same in every candidate. For task 2, "labels compared as typed" was refined after the first candidates were read: the raw label is also stored as the key, because a unique-key backstop in some candidates still refused duplicates. It was applied to every task-2 candidate.
7. **The ideal-setup phase and task 2 were added after the comparison.** method.md fixed the task-1 comparison, and its "Second task" section fixed task 2 before any task-2 run ended. The ideal setup's versions were chosen during the experiment, each after reading the previous results; the two v6 runs were added after task 2's other results.
8. **Re-scoring.** The audit allow-list and the Codex and Hermes usage readers changed during the experiment. Every task-1 run was re-scored with the final `evaluate.py`, and the hidden-suite and verification results did not change.

## Limitations

- **Narrow evidence.** Two tasks in one Django project, both with the human's decisions given up front. Large or ambiguous work, where review has more to find, may rank the setups differently.
- **Few runs.** One to three runs per setup and task, so only large, consistent differences are worth reading.
- **Quality at the ceiling.** It was at the ceiling on both tasks, so the comparison mostly measures cost and time.
- **Who wrote what.** Opus wrote the hidden suites and the blind reviews, and built most candidates. The hidden suites and planted bugs are the objective checks.
- **Cost.** These are list prices from each tool's own report, and cache behaviour depends on the account's 1-hour cache.
- **Time.** Runs overlapped three or four at a time, so times include contention.

## Files

- [`method.md`](method.md): the method, fixed before the runs.
- `inputs/`: the two task prompts, the smoke-test prompt and the run queues.
- `harness/`:
  - `setup_arm.py` builds each setup;
  - `run_arm.sh` and `run_other.sh` launch runs in Claude Code, or in Codex and Hermes;
  - `schedule.py` runs a queue;
  - `evaluate.py`, `mutate.py` and `review.py` score each run;
  - `aggregate.py` and `analysis.py` build the result tables;
  - `build_presentation.py` builds the slides;
  - `test_hidden_direction_controls.py` and `test_hidden_retest.py` are the hidden suites.
- `results/`: `runs.csv`, `summary.json`, `analysis.json`, and the per-candidate planted-bug definitions in `mutations/`.
- `ideal/`: v1–v4, Relay-specific, installed by `install.py`; [`v5/`](ideal/v5/), the first portable package; and [`v6/`](ideal/v6/), v5 plus three rules, the package to use.
- [`presentation.html`](presentation.html): the slides.
