# Agent setups: what a coding-agent workflow costs, and what it buys

Owner: zheng-jj · Issue: #31 · Run on 2026-10-30 to 2026-11-01 · Method fixed in advance in [method.md](method.md) · Slides: [presentation.html](presentation.html)

**Question.** Coding agents can be set up in many ways: one session or a team of subagents, a strong or a cheap model, a methodology plugin, a token-saving add-on. On real tasks, with everything else held fixed, how do these setups compare on cost, quality and speed? And can one setup do well with any model, in any tool, on any project?

**Answer.**
1. **Quality did not separate the setups on the tests.** On four tasks of rising difficulty, every counted run passed its hidden acceptance suite and full verification. In all but two runs, the candidate's own tests caught all five planted bugs. Blind reviews found mostly records drifting apart. Only on the two hardest tasks did they find behaviour the hidden tests missed, and then in several setups alike.
2. **Hand-offs are the cost.** On Opus, the setups that build in one session cost 43–65% less than the multi-agent MP4 workflow on average, and took 45–60% less time. About half of each MP4 run's money went on subagents re-reading the repository.
3. **Add-ons and extra roles do not pay.** caveman, ponytail and headroom ranged from 32% cheaper to 4% dearer than MP4 on average, and their savings moved from task to task. MP3's six roles cost as much as MP4 and found nothing extra.
4. **A cheaper model was enough, even on the hardest task.** Holding the setup fixed, Sonnet, Haiku and DeepSeek v4.1 Flash passed every task's hidden suite, at a fraction of Opus's cost.
5. **Teams of subagents can stop halfway.** In 3 of 18 multi-agent runs on tasks 3 and 4, the coordinator ended its turn while a background builder was still working, and the unattended run ended with it.
6. **The ideal setup: one session builds, one independent reviewer checks, the same steps in any tool, model or repository.** Version 7 is the one to use. On Opus, the setup's latest versions cost 27% less than MP4 on average: v5 45% less on task 1, v6 47% on task 2 and v7 35% on task 3. But v8 cost about the same as MP4 on the hardest task, where review and repair rounds cost Opus prices. Its main saving is making the cheaper models safe to use. Version 8 added four rules, cost more and found no less, so it was not adopted.

## Takeaways

If you run coding agents on a real repository:

1. **Build in one session.** Builder subagents doubled the cost and time here, with no quality gain. Each one starts cold and reads the repository again.
2. **Keep exactly one independent reviewer.** A session cannot review its own work independently, and one reviewer costs a fraction of repeated review cycles.
3. **Try the cheaper model first, even for hard work.** Every model passed every task's hidden suite under the same setup.
4. **Check consistency before review.** Most review findings were records drifting apart: spec text claiming more than the code or tests do, a decision out of its home, an old test weakened, or an earlier requirement quietly dropped or rewritten.
5. **Write the project's facts down once.** One file of commands, folders, homes and budgets let the same workflow move between repositories, tools and models, including an empty repository.
6. **Add a rule only when it pays.** Version 8's four extra rules made runs dearer without fewer findings.

Skip, or measure on your own work first:
- **Output-compression and proxy add-ons.** The savings were small or absent, and a proxy sees your credentials.
- **More roles.** MP3's six roles found nothing extra.
- **Builder subagents in unattended runs.** They can be cut off mid-change.
- **Letting the model pick its reviewer.** Haiku chose Opus and tripled its cost.
- **Conclusions from one task.** Task 1 made the add-ons look useful; the later tasks did not.

## What was compared

Fourteen setups, each run headless with the same prompt, permissions and test environment, in Claude Code 2.1.312 unless the row says otherwise:

| Group | Setup | What it is |
| --- | --- | --- |
| Workflow | **MP4 baseline** | MP4's slice: a coordinator with builder, verifier and security-reviewer subagents |
| Workflow | MP3 six roles | spec-writer, spec-critic, test-writer, implementer, reviewer, security-reviewer |
| Workflow | Solo session | MP4's slice, with one session playing every role |
| Model mix | MP4, Sonnet builder | Sonnet builder; Opus coordinator and reviewers |
| Model | MP4, all Sonnet / all Haiku / DeepSeek | every role on that model; DeepSeek v4.1 Flash runs in Codex 0.165.0 and Hermes Agent 0.21.3 |
| Methodology | superpowers | obra/superpowers skills, at a pinned commit |
| Methodology | spec-kit | GitHub's Spec-Driven Development toolkit |
| Methodology | OpenSpec | OpenSpec 1.14.3's propose, apply and archive flow |
| Add-on | MP4 + caveman | terse-output plugin |
| Add-on | MP4 + ponytail | smallest-change plugin |
| Add-on | MP4 + headroom | context-compressing local proxy |
| Ideal | Ideal v1 | the first lean slice built from the task-1 results |
| Ideal | Ideal, latest | the portable package, v5 to v8, the latest version run on each task |

Every comparison is between runs on the same model. The setup comparison is on Opus; the model comparison holds the setup fixed.

## The four tasks

| | Task 1 · #68 | Task 2 · #16 | Task 3 · #13 | Task 4 · #4 |
| --- | --- | --- | --- | --- |
| Change | Refuse hidden text-direction characters in 12 round-text inputs | Request a retest: a page, form and service under a row lock, with a build cap, label rules and escaping | Record test results: a model, page and state rules, with privacy between testers; only the interface was given, so each run wrote the requirements | Limit sign-in and demo-creation abuse: per-address windows under simultaneous requests, IPv6 ranges, a forged-header trap |
| Typical diff (median, non-test code) | 16 lines | 119 lines | 332 lines | 251 lines |
| Hidden suite | 132 tests | 27 tests | 46 tests | 26 tests |
| Planted bugs | no check; two controls allowed; a mark refused; labels unchecked | foreign cases; cap off by one; labels compared as typed; any state; label unescaped | another tester's result; Fail without observation; Closed round; submitted result changeable; 2,001 characters | sign-in limit off by one; correct password at the limit; forged header trusted; success resets the count; demo limit off by one |

Every prompt gave the team's decisions up front, so no run needed a human. Each run worked in its own clone, with its own test database and no web or GitHub access. Tasks 3 and 4 were added when the first two proved too easy to separate the setups.

**Scoring** ([method](method.md#measures)):
- **Hidden suite:** written from the issue and decisions only, before any run of that task ended; [method.md](method.md) records how each was checked.
- **Full verification:** Django check, `makemigrations --check`, Ruff and the full pytest suite.
- **Planted bugs:** five per candidate, planted in its own code; its own tests must fail. Each was confirmed to fail the hidden suite.
- **Blind review:** a fresh Opus session with a random label, reading only the product diff.
- **Transcript audit:** spec before code, commits, and any access outside the run's clone.

Cost is each tool's own report at API list prices; a subscription bills differently. Time is wall-clock, with up to four runs overlapping.

## Results

### Quality

Correct runs · planted bugs caught by the run's own tests · High / Medium review findings, all on Opus:

<!-- table:quality -->
| Setup (Opus) | Task 1 | Task 2 | Task 3 | Task 4 |
| --- | --- | --- | --- | --- |
| MP4 baseline | 3/3 · bugs 15/15 · 0 / 1 | 3/3 · bugs 15/15 · 0 / 0 | 2/2 · bugs 10/10 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 2 |
| MP3 six roles | 2/2 · bugs 10/10 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 1 |
| Solo session | 2/2 · bugs 10/10 · 0 / 0 | not run | not run | 1/1 · bugs 5/5 · 0 / 0 |
| MP4, Sonnet builder | 2/2 · bugs 10/10 · 0 / 2 | not run | not run | not run |
| superpowers | 2/2 · bugs 10/10 · 0 / 2 | 3/3 · bugs 15/15 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 2 |
| spec-kit | 2/2 · bugs 10/10 · 0 / 1 | 3/3 · bugs 15/15 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 0 |
| OpenSpec | 2/2 · bugs 10/10 · 0 / 0 | 3/3 · bugs 15/15 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 1 | 1/1 · bugs 5/5 · 0 / 0 |
| MP4 + caveman | 2/2 · bugs 10/10 · 0 / 0 | 3/3 · bugs 15/15 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 0 |
| MP4 + ponytail | 2/2 · bugs 10/10 · 0 / 1 | 3/3 · bugs 15/15 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 0 |
| MP4 + headroom | 2/2 · bugs 10/10 · 0 / 1 | 3/3 · bugs 15/15 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 0 | 1/1 · bugs 5/5 · 0 / 0 |
| Ideal v1 | 1/1 · bugs 5/5 · 0 / 1 | 1/1 · bugs 5/5 · 0 / 0 | not run | not run |
| Ideal, latest run | v5: 1/1 · bugs 5/5 · 0 / 0 | v6: 3/3 · bugs 15/15 · 0 / 0 | v8: 1/1 · bugs 5/5 · 0 / 1 | v8: 1/1 · bugs 5/5 · 0 / 1 |
<!-- /table -->

"Correct" means the whole hidden suite and full verification passed. Tasks 2, 3 and 4 have one to three runs per setup.

**What the blind reviews found.** Across every counted run, on every model, there were 58 findings of Medium or above, 5 of them High. Sorted by hand into kinds:
- **An earlier requirement dropped, left unmet or rewritten (16).** On task 3, six runs left the security spec's "RES must cap results" open as a risk, two of them on v8, whose first rule was meant to prevent it. On task 4, several runs rewrote the technical notes to fit their code instead of building to them.
- **Spec text claiming more than the code or tests do (13).**
- **An old test weakened, or a coverage gap (12).** For example, race tests that would pass with the lock removed, and a storage-failure path never exercised.
- **A decision or accepted risk missing or misrecorded (8).** Including residuals recorded as accepted that no human accepted.
- **Behaviour missing or wrong where the hidden tests don't look (7).** All on tasks 3 and 4: a fresh result page opening with a validation error, IPv4-mapped addresses sharing one counter, and storage failures giving 500 where the spec asks for 503.
- **A reviewer false positive (2).** On task 4, one reviewer marked a run down for giving the 503 that the starting spec asks for, while two others marked runs down for not giving it. With one blind review per run, review findings are noisier than the tests.

**Reports were accurate.** 115 of the 135 counted runs stated a full-suite test count in their final report, and every one matched the count we measured.

### Cost and time

Medians, with ranges in brackets, all on Opus; "vs MP4" is the average, over the tasks a setup ran, of its median against MP4's on the same task:

<!-- table:cost -->
| Setup (Opus) | Task 1: US$ · min | Task 2: US$ · min | Task 3: US$ · min | Task 4: US$ · min | Cost vs MP4 | Time vs MP4 |
| --- | --- | --- | --- | --- | ---: | ---: |
| MP4 baseline | 8.97 (7.26–9.23) · 30 (27–30) | 10.99 (10.92–12.00) · 37 (36–40) | 15.16 (11.97–18.34) · 55 (46–63) | 13.38 · 46 | — | — |
| MP3 six roles | 5.77 (5.50–6.04) · 22 (21–23) | 11.88 · 37 | 17.24 · 63 | 16.32 · 70 | +2% | +9% |
| Solo session | 3.35 (3.27–3.44) · 13 (12–14) | — | — | 4.39 · 17 | −65% | −60% |
| MP4, Sonnet builder | 5.72 (4.17–7.28) · 22 (17–27) | — | — | — | −36% | −26% |
| superpowers | 4.14 (3.99–4.30) · 12 (11–14) | 5.60 (5.09–5.65) · 17 (16–18) | 6.99 · 19 | 7.03 · 31 | −51% | −53% |
| spec-kit | 4.40 (3.96–4.84) · 12 (11–13) | 6.28 (5.48–7.13) · 20 (17–23) | 8.85 · 29 | 8.36 · 34 | −43% | −45% |
| OpenSpec | 4.96 (3.54–6.37) · 15 (14–17) | 5.39 (4.29–5.62) · 17 (14–18) | 7.17 · 20 | 9.27 · 33 | −45% | −49% |
| MP4 + caveman | 6.13 (5.45–6.82) · 24 (23–25) | 10.85 (10.09–12.53) · 38 (34–41) | 10.92 · 46 | 16.62 · 66 | −9% | +2% |
| MP4 + ponytail | 4.54 (3.93–5.14) · 17 (13–20) | 9.32 (8.13–10.20) · 31 (24–36) | 8.46 · 30 | 10.82 · 42 | −32% | −29% |
| MP4 + headroom | 5.85 (5.21–6.48) · 24 (23–26) | 12.36 (9.98–12.55) · 40 (33–44) | 14.40 · 46 | 19.12 · 77 | +4% | +10% |
| Ideal v1 | 4.23 · 12 | 6.35 · 25 | — | — | −48% | −46% |
| Ideal, latest run | 4.96 · 19 | 5.80 (5.49–6.64) · 19 (18–22) | 12.72 · 43 | 13.26 · 37 | −27% | −31% |
<!-- /table -->

Per-run data is in [`results/runs.csv`](results/runs.csv).

### Why: the money goes on hand-offs

Claude Code caches the context it sends. A cache write costs about 20 times a cache read, and a subagent always starts with an empty context. Every MP4 subagent therefore reads `AGENTS.md`, its role, the specs and the code again, and caches all of it afresh. MP4 runs started 9 to 12 subagents on each task.

Splitting each Opus run's cost with rates fitted to its reported costs:
- **MP4:** 53–55% of an average run's money went on subagent context on every task, 17–23% on its main session and 24–30% on output.
- **One session:** a solo run spent 75–81% in its main session, which reads the repository once and keeps its cache.
- **The ideal setup:** 47–53% in its main session and 26–28% on its reviewers.

### The add-ons, one at a time

| Add-on | Promise | Measured, on Opus | Verdict |
| --- | --- | --- | --- |
| caveman | Fewer output tokens | Output 107k vs 160k on task 1. Cost against MP4: −32%, −1%, −28%, +24% on tasks 1–4. | Real but small. Output is about a fifth of cost, and the coordinator's choices outweighed it. |
| ponytail | Smaller changes | Test lines 126 vs 240 on task 1. Cost: −49%, −15%, −44%, −19%. | Leaner tests, same quality, an inconsistent saving. |
| headroom | Compressed context | 0.7–2.6% of request traffic compressed, in every run. Cost: −35%, +12%, −5%, +43%. | Too little compression to matter, and it routes your credentials through a third-party proxy. |

Cost followed how many subagents the coordinator started more than the add-on: the task-4 caveman and headroom runs started 15 and 16, against MP4's 9.

### Workflows, models and methodologies

- **MP3's six roles** cost as much as MP4 on average and found nothing extra.
- **A solo session** playing every MP4 role was the cheapest Opus setup on both tasks it ran. Its weakness is that it reviews its own work.
- **superpowers, spec-kit and OpenSpec** each built in one session and cost what a single session costs, with the same quality. They bring planning and test-first habits; none starts an independent reviewer unless asked.
- **Reliability.** Three multi-agent runs on task 3 ended mid-change: the coordinator handed the build to a background subagent, then ended its turn to wait, which ends an unattended run. They were rerun and are reported separately ([method](method.md#fourth-task-cut-short-runs-and-ideal-setup-v8)).

### Same setup, different model

<!-- table:models -->
| Model · task | MP4 workflow: US$ · min · quality | Ideal setup, latest version: US$ · min · quality |
| --- | --- | --- |
| Opus · 1 | 8.97 (7.26–9.23) · 30 (27–30) · 3/3 · bugs 15/15 · 0 / 1 | v5: 4.96 · 19 · 1/1 · bugs 5/5 · 0 / 0 |
| Opus · 2 | 10.99 (10.92–12.00) · 37 (36–40) · 3/3 · bugs 15/15 · 0 / 0 | v6: 5.80 (5.49–6.64) · 19 (18–22) · 3/3 · bugs 15/15 · 0 / 0 |
| Opus · 3 | 15.16 (11.97–18.34) · 55 (46–63) · 2/2 · bugs 10/10 · 0 / 0 | v8: 12.72 · 43 · 1/1 · bugs 5/5 · 0 / 1 |
| Opus · 4 | 13.38 · 46 · 1/1 · bugs 5/5 · 0 / 2 | v8: 13.26 · 37 · 1/1 · bugs 5/5 · 0 / 1 |
| Sonnet · 1 | 2.25 (1.99–2.50) · 14 (12–16) · 2/2 · bugs 10/10 · 0 / 1 | v5: 1.47 · 10 · 1/1 · bugs 5/5 · 0 / 1 |
| Sonnet · 2 | 3.91 · 24 · 1/1 · bugs 5/5 · 0 / 0 | v6: 2.20 · 12 · 1/1 · bugs 5/5 · 0 / 0 |
| Sonnet · 3 | 5.03 · 32 · 1/1 · bugs 5/5 · 0 / 1 | v8: 5.32 · 21 · 1/1 · bugs 5/5 · 0 / 1 |
| Sonnet · 4 | 4.83 · 25 · 1/1 · bugs 5/5 · 0 / 0 | v8: 3.71 · 24 · 1/1 · bugs 5/5 · 0 / 1 |
| Haiku · 1 | 0.97 · 18 · 1/1 · bugs 5/5 · 0 / 0 | v5: 1.46 · 27 · 1/1 · bugs 5/5 · 0 / 0 |
| Haiku · 2 | 1.95 · 56 · 1/1 · bugs 5/5 · 0 / 1 | v6: 1.85 · 36 · 1/1 · bugs 5/5 · 0 / 0 |
| Haiku · 3 | 2.29 · 21 · 1/1 · bugs 5/5 · 0 / 1 | v8: 2.85 · 40 · 1/1 · bugs 5/5 · 0 / 0 |
| Haiku · 4 | 1.24 · 42 · 1/1 · bugs 5/5 · 0 / 1 | v8: 1.59 · 26 · 1/1 · bugs 5/5 · 1 / 1 |
| DeepSeek · Codex · 1 | 0.19 · 16 · 1/1 · bugs 5/5 · 0 / 1 | v4: 0.21 · 20 · 1/1 · bugs 5/5 · 0 / 0 |
| DeepSeek · Codex · 3 | 0.65 · 52 · 1/1 · bugs 5/5 · 0 / 0 | v8: 0.44 · 36 · 1/1 · bugs 5/5 · 1 / 2 |
| DeepSeek · Codex · 4 | 0.40 · 28 · 1/1 · bugs 5/5 · 1 / 2 | v8: 0.27 · 22 · 1/1 · bugs 5/5 · 0 / 4 |
| DeepSeek · Hermes · 1 | 0.33 · 68 · 1/1 · bugs 5/5 · 0 / 0 | v4: 0.13 · 10 · 1/1 · bugs 5/5 · 0 / 0 |
| DeepSeek · Hermes · 3 | not run | v7: 0.47 · 30 · 1/1 · bugs 5/5 · 0 / 0 |
| DeepSeek · Hermes · 4 | 0.26 · 26 · 1/1 · bugs 3/5 · 0 / 2 | v8: 0.30 · 46 · 1/1 · bugs 5/5 · 0 / 1 |
<!-- /table -->

Holding the setup fixed, every model passed every task's hidden suite. On task 4, the hardest, the ideal setup cost $13.26 on Opus, $3.71 on Sonnet, $1.59 on Haiku and $0.27–0.30 on DeepSeek. The cheapest models tended to draw more review findings, and both runs whose own tests missed planted bugs were on DeepSeek.

## The ideal setup

The package to use is [`ideal/v7/`](ideal/v7/); its [README](ideal/v7/README.md) covers installing and running it. Versions v1 to v4 were Relay-specific steps towards it; v5 made it portable; v8 was tested and not adopted.

### How it works

One session builds the change; one independent, read-only reviewer checks it. The workflow, in [`agent-workflow/slice.md`](ideal/v7/agent-workflow/slice.md):
0. **Set up:** on first use, fill `project.md` from what the repository shows, and ask the person about anything it can't see.
1. **Prepare:** note the starting commit, create a branch, read only what the change touches.
2. **Specify:** update the requirements first, then write a short plan with the requirement delta (from OpenSpec), the person's decisions and two to four checkpoints. Read the delta against the existing requirements before building (from spec-kit).
3. **Build:** write the tests first and see them fail; test each behaviour once, at the lowest level that shows it (from ponytail), and every listed value; mock only what lies outside the change; make the smallest complete change; prove the tests can fail; commit as you go.
4. **Check consistency:** every mention of what changed is updated, every old test still tests what it did, every decision has a home, and nothing is recorded as accepted that the person did not decide.
5. **Freeze:** run the project's full verification once, on the final candidate.
6. **Review:** one independent read-only reviewer on the frozen commit range, plus a security reviewer for high-risk areas.
7. **Repair:** at most two repair rounds.
8. **Report.**

Every model follows the same steps. The reviewer runs on the session's model unless `AGENT_REVIEW_MODEL` names another; the model never chooses one itself. Everything particular to a repository is in one file, `agent-workflow/project.md`. The installer adds a marked block to `AGENTS.md` and adapters for Claude Code, Codex and Hermes. The [package README](ideal/v7/README.md#why-it-is-shaped-this-way) gives the evidence for each rule.

### How it was evaluated

The same scoring as the comparison, on five model and tool combinations, each with a reference run of the MP4 workflow on the same model where one was made:

<!-- table:platforms -->
| Platform · task | Setup | Runs | Cost (US$) | Time (min) | Quality |
| --- | --- | ---: | --- | --- | --- |
| Opus · 1 | MP4 workflow | 3 | 8.97 (7.26–9.23) | 30 (27–30) | 3/3 · bugs 15/15 · 0 / 1 |
| Opus · 1 | Ideal v1 | 1 | 4.23 | 12 | 1/1 · bugs 5/5 · 0 / 1 |
| Opus · 1 | Ideal v2 | 1 | 4.47 | 17 | 1/1 · bugs 5/5 · 0 / 0 |
| Opus · 1 | Ideal v5 | 1 | 4.96 | 19 | 1/1 · bugs 5/5 · 0 / 0 |
| Opus · 2 | MP4 workflow | 3 | 10.99 (10.92–12.00) | 37 (36–40) | 3/3 · bugs 15/15 · 0 / 0 |
| Opus · 2 | Ideal v1 | 1 | 6.35 | 25 | 1/1 · bugs 5/5 · 0 / 0 |
| Opus · 2 | Ideal v5 | 2 | 5.97 (5.94–6.00) | 19 (18–20) | 2/2 · bugs 10/10 · 0 / 0 |
| Opus · 2 | Ideal v6 | 3 | 5.80 (5.49–6.64) | 19 (18–22) | 3/3 · bugs 15/15 · 0 / 0 |
| Opus · 3 | MP4 workflow | 2 | 15.16 (11.97–18.34) | 55 (46–63) | 2/2 · bugs 10/10 · 0 / 0 |
| Opus · 3 | Ideal v6 | 2 | 6.99 (6.97–7.02) | 24 (24–25) | 2/2 · bugs 10/10 · 0 / 2 |
| Opus · 3 | Ideal v7 | 1 | 9.78 | 30 | 1/1 · bugs 5/5 · 0 / 1 |
| Opus · 3 | Ideal v8 | 1 | 12.72 | 43 | 1/1 · bugs 5/5 · 0 / 1 |
| Opus · 4 | MP4 workflow | 1 | 13.38 | 46 | 1/1 · bugs 5/5 · 0 / 2 |
| Opus · 4 | Ideal v8 | 1 | 13.26 | 37 | 1/1 · bugs 5/5 · 0 / 1 |
| Sonnet · 1 | MP4 workflow | 2 | 2.25 (1.99–2.50) | 14 (12–16) | 2/2 · bugs 10/10 · 0 / 1 |
| Sonnet · 1 | Ideal v1 | 2 | 1.35 (1.32–1.39) | 8 (8–8) | 2/2 · bugs 10/10 · 0 / 1 |
| Sonnet · 1 | Ideal v2 | 2 | 1.71 (1.65–1.76) | 11 (11–11) | 2/2 · bugs 10/10 · 0 / 0 |
| Sonnet · 1 | Ideal v3 | 1 | 1.70 | 13 | 1/1 · bugs 5/5 · 0 / 1 |
| Sonnet · 1 | Ideal v4 | 1 | 1.75 | 14 | 1/1 · bugs 5/5 · 0 / 0 |
| Sonnet · 1 | Ideal v5 | 1 | 1.47 | 10 | 1/1 · bugs 5/5 · 0 / 1 |
| Sonnet · 2 | MP4 workflow | 1 | 3.91 | 24 | 1/1 · bugs 5/5 · 0 / 0 |
| Sonnet · 2 | Ideal v5 | 1 | 2.29 | 14 | 1/1 · bugs 5/5 · 0 / 1 |
| Sonnet · 2 | Ideal v6 | 1 | 2.20 | 12 | 1/1 · bugs 5/5 · 0 / 0 |
| Sonnet · 3 | MP4 workflow | 1 | 5.03 | 32 | 1/1 · bugs 5/5 · 0 / 1 |
| Sonnet · 3 | Ideal v6 | 2 | 4.41 (3.66–5.16) | 22 (22–23) | 2/2 · bugs 10/10 · 0 / 1 |
| Sonnet · 3 | Ideal v7 | 1 | 2.39 | 18 | 1/1 · bugs 5/5 · 0 / 0 |
| Sonnet · 3 | Ideal v8 | 1 | 5.32 | 21 | 1/1 · bugs 5/5 · 0 / 1 |
| Sonnet · 4 | MP4 workflow | 1 | 4.83 | 25 | 1/1 · bugs 5/5 · 0 / 0 |
| Sonnet · 4 | Ideal v8 | 1 | 3.71 | 24 | 1/1 · bugs 5/5 · 0 / 1 |
| Haiku · 1 | MP4 workflow | 1 | 0.97 | 18 | 1/1 · bugs 5/5 · 0 / 0 |
| Haiku · 1 | Ideal v1 | 2 | 0.85 (0.68–1.03) | 22 (18–26) | 2/2 · bugs 10/10 · 1 / 1 |
| Haiku · 1 | Ideal v2 | 2 | 2.87 (2.44–3.29) | 31 (24–39) | 2/2 · bugs 10/10 · 0 / 1 |
| Haiku · 1 | Ideal v3 | 2 | 0.92 (0.91–0.93) | 17 (15–19) | 2/2 · bugs 10/10 · 0 / 0 |
| Haiku · 1 | Ideal v4 | 1 | 0.88 | 20 | 1/1 · bugs 5/5 · 1 / 0 |
| Haiku · 1 | Ideal v5 | 1 | 1.46 | 27 | 1/1 · bugs 5/5 · 0 / 0 |
| Haiku · 2 | MP4 workflow | 1 | 1.95 | 56 | 1/1 · bugs 5/5 · 0 / 1 |
| Haiku · 2 | Ideal v5 | 1 | 2.18 | 29 | 1/1 · bugs 5/5 · 0 / 1 |
| Haiku · 2 | Ideal v6 | 1 | 1.85 | 36 | 1/1 · bugs 5/5 · 0 / 0 |
| Haiku · 3 | MP4 workflow | 1 | 2.29 | 21 | 1/1 · bugs 5/5 · 0 / 1 |
| Haiku · 3 | Ideal v6 | 1 | 3.25 | 43 | 1/1 · bugs 5/5 · 0 / 1 |
| Haiku · 3 | Ideal v7 | 1 | 2.63 | 43 | 1/1 · bugs 5/5 · 0 / 1 |
| Haiku · 3 | Ideal v8 | 1 | 2.85 | 40 | 1/1 · bugs 5/5 · 0 / 0 |
| Haiku · 4 | MP4 workflow | 1 | 1.24 | 42 | 1/1 · bugs 5/5 · 0 / 1 |
| Haiku · 4 | Ideal v8 | 1 | 1.59 | 26 | 1/1 · bugs 5/5 · 1 / 1 |
| DeepSeek · Codex · 1 | MP4 workflow | 1 | 0.19 | 16 | 1/1 · bugs 5/5 · 0 / 1 |
| DeepSeek · Codex · 1 | Ideal v1 | 2 | 0.17 (0.13–0.20) | 11 (10–13) | 2/2 · bugs 10/10 · 0 / 0 |
| DeepSeek · Codex · 1 | Ideal v2 | 3 | 0.23 (0.23–0.24) | 21 (20–26) | 3/3 · bugs 15/15 · 0 / 0 |
| DeepSeek · Codex · 1 | Ideal v3 | 1 | 0.15 | 14 | 1/1 · bugs 5/5 · 0 / 0 |
| DeepSeek · Codex · 1 | Ideal v4 | 1 | 0.21 | 20 | 1/1 · bugs 5/5 · 0 / 0 |
| DeepSeek · Codex · 3 | MP4 workflow | 1 | 0.65 | 52 | 1/1 · bugs 5/5 · 0 / 0 |
| DeepSeek · Codex · 3 | Ideal v7 | 1 | 0.30 | 28 | 1/1 · bugs 5/5 · 0 / 0 |
| DeepSeek · Codex · 3 | Ideal v8 | 1 | 0.44 | 36 | 1/1 · bugs 5/5 · 1 / 2 |
| DeepSeek · Codex · 4 | MP4 workflow | 1 | 0.40 | 28 | 1/1 · bugs 5/5 · 1 / 2 |
| DeepSeek · Codex · 4 | Ideal v8 | 1 | 0.27 | 22 | 1/1 · bugs 5/5 · 0 / 4 |
| DeepSeek · Hermes · 1 | MP4 workflow | 1 | 0.33 | 68 | 1/1 · bugs 5/5 · 0 / 0 |
| DeepSeek · Hermes · 1 | Ideal v1 | 2 | 0.15 (0.15–0.16) | 14 (14–15) | 2/2 · bugs 10/10 · 0 / 1 |
| DeepSeek · Hermes · 1 | Ideal v2 | 2 | 0.26 (0.21–0.30) | 28 (17–40) | 2/2 · bugs 9/10 · 0 / 1 |
| DeepSeek · Hermes · 1 | Ideal v3 | 1 | 0.15 | 14 | 1/1 · bugs 5/5 · 0 / 0 |
| DeepSeek · Hermes · 1 | Ideal v4 | 1 | 0.13 | 10 | 1/1 · bugs 5/5 · 0 / 0 |
| DeepSeek · Hermes · 3 | Ideal v7 | 1 | 0.47 | 30 | 1/1 · bugs 5/5 · 0 / 0 |
| DeepSeek · Hermes · 4 | MP4 workflow | 1 | 0.26 | 26 | 1/1 · bugs 3/5 · 0 / 2 |
| DeepSeek · Hermes · 4 | Ideal v8 | 1 | 0.30 | 46 | 1/1 · bugs 5/5 · 0 / 1 |
<!-- /table -->

A further v3 Haiku run with an Opus reviewer cost $2.55, against about $0.90 without one, with the same result.

**On a new project.** v8 was installed into an empty repository and asked to build a small command-line tool, once in Claude Code on Sonnet and once in Codex on DeepSeek. In about five minutes each, step 0 filled `project.md` from the empty folder, and each run wrote requirements and a plan, built the tool with tests, had it reviewed and committed the repairs. v7 has the same step 0.

### Tuning, v1 to v8

- **v1 → v2:** the comparison's two recurring Medium patterns became explicit checks: stale spec text, and old tests switched to allowed inputs.
- **v2 → v3:** the reviewer model became an explicit setting, after Haiku hired Opus reviewers on its own; and every listed value is tested on its own, after a run sampled them.
- **v3 → v4:** an unset profile means `guarded`; the plan maps each decision to its home.
- **v4 → v5:** portable. Commands, folders, homes, high-risk areas and the size budget moved into `project.md`, with an installer for any Git repository.
- **v5 → v6:** accept only what the human decided; claims about tests point to a test; mock only outside the change.
- **v6 → v7:** one workflow for every model, with no profiles, because a setup can't tell which model is weak; a set-up step for new projects; the requirement delta, the consistency read, "test each behaviour once" and terse working notes, borrowed from the compared tools.
- **v7 → v8, not adopted:** look for existing requirements addressed to the change; follow the project's own test rules; never end the turn while something you started is running; show the arithmetic of estimates. On task 3, v8 cost more than v7 on every model (Opus $12.72 against $9.78, Sonnet $5.32 against $2.39, Haiku $2.85 against $2.63, Codex $0.44 against $0.30), and the problem its first rule targeted still appeared on Opus and Sonnet. Its Haiku run was the one with a cleaner review than version 7's.

## Deviations from the frozen method

1. **Pilot accounting.** After the pilot, the scoring script was fixed to read a headless session's several result records. The run harness did not change, so the pilot counts as MP4 run 1.
2. **Blind-review rubric.** The first four task-1 reviews penalised missing plans and uncommitted changes, which the review setup leaves out on purpose. The rubric was corrected and those four reviewed again.
3. **Runs left out, each kept under a prefix and, except the last two, rerun:**
   - **`nocli-`:** three OpenSpec runs whose OpenSpec command-line tool was missing.
   - **`trunc-`:** three task-3 runs cut short when the coordinator ended its turn ([finding](#workflows-models-and-methodologies)).
   - **`paused-`:** six runs interrupted when the human paused the experiment.
   - **`leak-`:** two runs that saw scratch files: the first task-3 Haiku run of v6 saw two lines of a backup of the original RES-2 code, and a task-4 MP4 Haiku run saw the file paths of other candidates' copies left by the planted-bug checks.
   - **`billing-`:** two Hermes runs on task 3, mp4 and v8, stopped when the OpenRouter key reached its spending limit. They were not rerun, so task 3 has no Hermes run of either.
4. **Neighbouring runs.** Every counted access outside a run's own clone was read in its transcript. The rest found nothing, were refused, read the run's own files, or read Django's and Python's own source.
5. **Same-model references and a fourth task were added during the experiment.** method.md fixed each addition before any of its runs ended. The ideal setup's versions were chosen during the experiment, each after reading the previous results.
6. **Planted bugs were written per candidate,** by helper sessions, because each candidate implemented the checks differently. The behaviours planted were the same in every candidate of a task, and each was confirmed to fail the hidden suite.
7. **Hidden suites for tasks 3 and 4** were kept out of this repository until every run had ended, then copied into `harness/`.

## Limitations

- **Narrow evidence.** Four tasks in one Django project, all with the team's decisions given up front.
- **Few runs.** One to three runs per setup and task, so only large, consistent differences are worth reading.
- **Quality at the ceiling on the tests.** Every counted run passed its hidden suite, so the comparison mostly measures cost, time and review findings.
- **Noisy reviews.** One blind review per run, by Opus; on task 4, reviewers judged the same spec rule in opposite directions.
- **Who wrote what.** Opus wrote the hidden suites, the planted bugs and the blind reviews, and built most candidates. The hidden suites and planted bugs are the objective checks.
- **Cost.** List prices from each tool's own report; cache behaviour depends on the account's 1-hour cache.
- **Time.** Runs overlapped up to four at a time, so times include contention.

## Files

- [`method.md`](method.md): the method, fixed before the runs, with each later addition fixed before its runs ended.
- `inputs/`: the task prompts, the smoke-test prompt and the run queues.
- `harness/`:
  - `setup_arm.py` builds each setup;
  - `run_arm.sh` and `run_other.sh` launch runs in Claude Code, or in Codex and Hermes;
  - `schedule.py` runs a queue;
  - `evaluate.py`, `mutate.py` and `review.py` score each run;
  - `aggregate.py` and `analysis.py` build the result tables;
  - `slide_data.py` refreshes the slides' data;
  - `test_hidden_*.py` are the four hidden suites.
- `results/`: `runs.csv`, `summary.json`, `analysis.json`, and the per-candidate planted-bug definitions in `mutations/`.
- `ideal/`: v1–v4, Relay-specific; [`v5/`](ideal/v5/) and [`v6/`](ideal/v6/), the first portable packages; [`v7/`](ideal/v7/), the package to use; and [`v8/`](ideal/v8/), tested and not adopted.
- [`presentation.html`](presentation.html): the slides.
