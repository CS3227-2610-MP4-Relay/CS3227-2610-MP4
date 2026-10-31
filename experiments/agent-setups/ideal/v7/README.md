# Portable agent workflow

A small workflow for coding agents that you can drop into any repository, new or existing. It runs the same way in Claude Code, Codex, Hermes or any tool that reads `AGENTS.md`, on any model. It came out of the [agent-setups experiment](../../README.md), which compared fourteen setups on four real tasks and tuned this one over eight versions on Opus, Sonnet, Haiku and DeepSeek v4.1 Flash.

This is version 7, the version to use. [Version 8](../v8/README.md) added four rules and was tested on two tasks. It cost more and drew no fewer review findings, so it was not adopted; see [below](#version-8-tested-and-not-adopted).

## How it works

One session builds the change, and one separate, read-only session reviews it. The steps are in [`agent-workflow/slice.md`](agent-workflow/slice.md):

0. **Set up.** On first use, the session fills [`agent-workflow/project.md`](agent-workflow/project.md) from what the repository shows, and asks you to confirm anything it can't see.
1. **Prepare.** The session notes the starting commit, creates a branch and reads only the requirements and code the change touches.
2. **Specify.** It updates the requirements first, then writes a short plan. The plan holds:
   - the **requirement delta**: each requirement added, changed or removed;
   - your decisions, and where each one lives;
   - two to four commit checkpoints.

   Before building, it reads the delta against the existing requirements.
3. **Build.** For each checkpoint, it:
   - writes the tests and sees them fail, testing each behaviour once at the lowest level that shows it;
   - makes the smallest complete change;
   - breaks the new check once, to prove the tests can fail;
   - commits.
4. **Check consistency.** Every statement about what changed is still true, every old test still tests what it did, and every decision has a home.
5. **Freeze.** The session runs the full verification once, on the final candidate.
6. **Review.** One independent reviewer checks the commit range. A security reviewer is added for the high-risk areas listed in `project.md`.
7. **Repair.** At most two repair rounds, each re-reviewed.
8. **Report.**

The session doesn't need to know how strong its model is. Every model follows the same steps, and the reviewer runs on the session's own model unless you set `AGENT_REVIEW_MODEL`.

## What you fill in

Everything particular to a repository lives in `agent-workflow/project.md`:
- the full verification and focused test commands;
- source, test and docs folders;
- where requirements, plans, and decisions and accepted risks live;
- the high-risk areas;
- a size budget;
- the commit format;
- the paths agents must never edit.

In a new repository, leave the placeholders in place: step 0 fills what it can and asks about the rest. [`examples/relay-project.md`](examples/relay-project.md) is a filled-in example. If your project requires particular kinds of test, such as a browser test for each new user journey, say so in its requirements or `AGENTS.md`; the reviewer checks against them.

## Install

```bash
python install.py /path/to/repo                       # then fill in, or let step 0 fill, agent-workflow/project.md
python install.py /path/to/repo --project my-project.md
```

The installer:
- copies `agent-workflow/`;
- adds the adapters:
  - `.claude/agents/aw-reviewer.md` and `aw-security-reviewer.md`, and `.claude/skills/aw-slice/`, for Claude Code;
  - `.codex/agents/aw-*.toml`, for Codex;
  - `.agents/skills/aw-slice/`, which Codex and Hermes read;
- puts a marked block at the top of `AGENTS.md`;
- makes sure `CLAUDE.md` loads `AGENTS.md`.

It changes nothing else.

## Run

```bash
claude --model sonnet                      # or opus
codex -m <model>                           # e.g. a DeepSeek model through OpenRouter
hermes -m <model> --provider <provider>
AGENT_REVIEW_MODEL=opus claude --model sonnet   # optional: a stronger reviewer, at a cost
```

Then ask for the change. The session reads `AGENTS.md`, then `agent-workflow/slice.md` and `project.md`.

## Why it is shaped this way

Each rule answers something the experiment measured. Fuller figures are in the [experiment's README](../../README.md).

| Rule | Evidence |
| --- | --- |
| Build in one session, not through builder subagents | On Opus, single-session setups cost 43–65% less than the multi-agent MP4 workflow on average across the tasks, with the same correctness. Most of MP4's extra money went on subagents re-reading the repository. |
| Keep one independent reviewer | Self-review missed scope, ownership and integration problems. One reviewer costs far less than repeated builder and reviewer cycles. |
| No builder subagents running in the background | Three task-3 runs of the multi-agent setups ended mid-change because the coordinator ended its turn while a background builder was still working. |
| One workflow for every model | A setup can't know which model is weaker. Version 7 dropped version 6's model profiles, and DeepSeek v4.1 Flash in Codex and in Hermes still passed task 3's whole hidden suite, at $0.30 and $0.47. |
| Reviewer on the session's model unless set | Left to choose, Haiku started Opus reviewers on its own and tripled its cost. |
| Requirement delta, then a consistency read | Most Medium or High review findings were records drifting apart: a spec statement left stale, an old test whose input was switched to an allowed one, or a decision left out of its home. |
| Test each listed value | One DeepSeek run sampled the refused characters, and a planted bug that allowed one of them survived. |
| Accept only what the person decided | Runs recorded residual risks as accepted that the human never accepted. |
| Mock only outside the change | A Haiku run mocked the whole service under test, so its failure test checked nothing. |
| No add-ons | caveman, ponytail and headroom did not improve quality, and their task-1 savings did not hold on later tasks. headroom passes your credentials through a third-party proxy. |

## Version 8, tested and not adopted

Version 8 added four rules, each from a version 7 or version 6 review finding on task 3:
- look for existing requirements addressed to the change, and meet them or ask;
- follow the project's own test rules before "test each behaviour once";
- never end the turn while something you started is still running;
- write out the arithmetic behind any estimate.

On task 3, where both versions ran, version 8 cost more on every model: $12.72 against $9.78 on Opus, $5.32 against $2.39 on Sonnet, $2.85 against $2.63 on Haiku and $0.44 against $0.30 in Codex. Its Sonnet run took 166 turns against version 7's 51. Its reviews were no better: the problem its first rule targeted, an existing "results must be capped" requirement left open, still appeared on Opus and Sonnet, and its Codex run had a High finding. On task 4, every version 8 run drew at least one Medium finding. These are one run per model and task, and blind reviewers disagreed on one task-4 rule, so the evidence shows the extra rules cost something, not that they make things worse.

## Limits

- **Evidence base:** one Django project and four tasks, with one to three runs per setup and task.
- **Cost on the cheapest models:** with Haiku or DeepSeek, the multi-agent workflow's subagents are cheap too, so this workflow is not reliably cheaper there. It was usually faster.
- **Read-only reviewer:** this is enforced only in Claude Code, by the adapter's tool list. In Codex and Hermes it is an instruction.
- **Delivery:** the workflow does not push, open pull requests or wait for CI. Delivery follows the repository's own rules.
