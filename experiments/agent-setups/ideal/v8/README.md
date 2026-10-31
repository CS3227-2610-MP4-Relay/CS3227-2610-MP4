# Portable agent workflow

A small workflow for coding agents that you can drop into any repository, new or existing. It runs the same way in Claude Code, Codex, Hermes or any tool that reads `AGENTS.md`, on any model. It came out of the [agent-setups experiment](../../README.md). This is version 8.

**Tested and not adopted: use [version 7](../v7/README.md).** Version 8 is version 7 plus four rules. On task 3 it cost more than version 7 on every model, and its reviews found no fewer problems; the [version 7 README](../v7/README.md#version-8-tested-and-not-adopted) gives the figures. It is kept as it ran.

## How it works

One session builds the change, and one separate, read-only session reviews it. The steps are in [`agent-workflow/slice.md`](agent-workflow/slice.md):

0. **Set up.** On first use, the session fills [`agent-workflow/project.md`](agent-workflow/project.md) from what the repository shows, and asks you to confirm anything it can't see.
1. **Prepare.** The session finds what the existing requirements already ask of this change, and which tests the project's rules require.
2. **Specify.** It updates the requirements first. It then writes a short plan with the **requirement delta** (each requirement added, changed or removed) and two to four commit checkpoints. Before building, it reads the delta against the existing requirements.
3. **Build.** For each checkpoint, it:
   - writes the tests and sees them fail;
   - makes the smallest complete change;
   - breaks the new check once, to prove the tests can fail;
   - commits.
4. **Check consistency.** Every statement about what changed is still true. Every old test still tests what it did. Every decision and every earlier requirement has a home.
5. **Freeze.** The session runs the full verification once, on the final candidate.
6. **Review.** One independent reviewer checks the commit range. A security reviewer is added for the high-risk areas listed in `project.md`.
7. **Repair.** At most two repair rounds, each re-reviewed.
8. **Report.**

The session doesn't need to know how strong its model is. Every model follows the same steps, and the reviewer runs on the session's own model unless you set `AGENT_REVIEW_MODEL`.

## What you fill in

Everything particular to a repository lives in `agent-workflow/project.md`:
- the full verification and focused test commands;
- source, test and docs folders;
- the **test rules**, such as "a browser test for each new user journey";
- where requirements, plans, and decisions and accepted risks live;
- the high-risk areas;
- a size budget;
- the commit format;
- the paths agents must never edit.

In a new repository, leave the placeholders in place: step 0 fills what it can and asks about the rest. [`examples/relay-project.md`](examples/relay-project.md) is a filled-in example.

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
| Build in one session, not through builder subagents | Builder hand-offs were the main cost of the multi-agent setups, which re-read the repository in each subagent. Single-session setups cost less and finished sooner, with the same correctness. |
| Keep one independent reviewer | Self-review missed scope, ownership and integration problems. One reviewer costs far less than repeated builder and reviewer cycles. |
| One workflow for every model | A setup can't know which model is weaker. v7 dropped v6's model profiles, and DeepSeek v4.1 Flash in Codex and in Hermes still passed task 3's whole hidden suite, at $0.30 and $0.47. |
| Reviewer on the session's model unless set | Left to choose, Haiku started Opus reviewers on its own and tripled its cost. |
| Find what is already required (v8) | Five task-3 runs turned an existing "results must be capped" requirement into an open risk. Another dropped tests the security spec assigned to the feature. |
| Follow the project's test rules (v8) | v7's "test at the lowest level" led one run to skip the browser test the repository requires for a new journey, and another to skip the display tests its security spec requires. |
| Wait for what you start (v8) | Three task-3 runs of the multi-agent setups ended mid-slice because the session ended its turn while a background builder was still working. |
| Requirement delta, then a consistency read | Every Medium or High finding on tasks 1 and 2 was one of three kinds: a spec statement left stale, an old test whose input was switched to an allowed one, or a decision left out of its home. |
| Test each listed value | One DeepSeek run sampled the refused characters, and a planted bug that allowed one of them survived. |
| Accept only what the person decided | Runs recorded residual risks as accepted that the human never accepted. |
| Mock only outside the change | A Haiku run mocked the whole service under test, so its failure test checked nothing. |
| Show the arithmetic | One run understated its own storage estimate by about 11 times. |
| No add-ons | caveman, ponytail and headroom did not improve quality, and their task-1 savings did not hold on later tasks. headroom passes your credentials through a third-party proxy. |

## Limits

- **Evidence base:** one Django project and four tasks, with one to three runs per setup and task. Version 8's rules come from task-3 reviews, and its own runs are on tasks 3 and 4.
- **Read-only reviewer:** this is enforced only in Claude Code, by the adapter's tool list. In Codex and Hermes it is an instruction.
- **Delivery:** the workflow does not push, open pull requests or wait for CI. Delivery follows the repository's own rules.
