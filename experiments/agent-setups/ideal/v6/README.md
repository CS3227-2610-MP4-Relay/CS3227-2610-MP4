# Portable agent workflow

A small, project-independent workflow for coding agents. It runs the same way in Claude Code, Codex, Hermes or any tool that reads `AGENTS.md`. It came out of the [agent-setups experiment](../../README.md): twelve setups compared on two real tasks, then tuned over six versions on strong models (Opus, Sonnet) and weak ones (Haiku, DeepSeek v4.1 Flash). This is version 6: version 5 plus three rules taken from version 5's own review findings.

## How it works

The workflow has five steps, in [`agent-workflow/slice.md`](agent-workflow/slice.md):

1. **Specify:** update the requirements first, and write a short plan.
2. **Build in one session:** write the tests first and see them fail, mocking only what lies outside the change. Make the smallest complete change, and commit as you go.
3. **Check consistency:** every mention of what changed is updated, and every claim that tests cover something points to a test that does. Every old test still tests what it did. Every human decision has a home, and nothing is recorded as accepted that the human did not decide.
4. **Freeze:** run the project's full verification once, on the final candidate.
5. **One independent, read-only review:** a separate reviewer session checks the frozen commit range, with at most two repair rounds.

Two switches tune it to the model:
- **`AGENT_PROFILE`:**
  - `strong` (Opus, Sonnet, GPT-5-class) follows the slice as written;
  - anything else, or unset, gets [`guarded`](agent-workflow/profiles/guarded.md): a ticked checklist, hard stops before scope or rule changes, tests shown to fail first, a check that the tests can fail, and numbers only from commands actually run.
- **`AGENT_REVIEW_MODEL`:** optionally runs the reviewer on a stronger model. Otherwise the reviewer uses the session's model, and the model never picks one itself.

Everything particular to a repository lives in [`agent-workflow/project.md`](agent-workflow/project.md): its verification command, folders, requirements and docs, where decisions and accepted risks are recorded, its high-risk areas and its size budget.

## Why it is shaped this way

Each rule answers something the experiment measured:

| Rule | Evidence |
| --- | --- |
| Build in one session, not through builder subagents | Builder hand-offs were MP4's main cost: about 55% of its money went on subagents re-reading the repository. Single-session setups cost 45–63% less and took 40–66% of the time, with the same correctness, on both tasks. |
| Keep one independent reviewer | Self-review missed scope, ownership and integration problems in the earlier weaker-model run. One reviewer costs far less than MP4's repeated builder and reviewer cycles. |
| Reviewer on the session's model unless set | Left to choose, Haiku started Opus reviewers on its own and tripled its cost. |
| The three consistency checks | Every Medium or High review finding across the runs was one of three things: a spec statement left stale, an old test whose input was switched to an allowed one, or a decision or accepted risk left out of its home. |
| Test each listed value | One DeepSeek run sampled the refused characters, and a planted bug that allowed one of them survived. |
| Accept only what the human decided | Two runs recorded a residual as accepted that the human never accepted. |
| Claims about tests point to a test | The commonest review finding was spec text saying tests covered something they did not. |
| Mock only outside the change | A Haiku run mocked the whole service under test, so its failure test checked nothing. |
| Unset profile means guarded | A DeepSeek run left to pick its own profile took the strong flow. |
| No add-ons | caveman, ponytail and headroom did not improve quality, and their task-1 savings did not survive task 2. headroom compressed about 1% of traffic and passes your credentials through a third-party proxy. |

## Install

```bash
python install.py /path/to/repo                       # then fill in agent-workflow/project.md
python install.py /path/to/repo --project my-project.md
```

The installer:
- copies `agent-workflow/`;
- adds adapters: `.claude/agents/aw-reviewer.md` and `aw-security-reviewer.md`, `.claude/skills/aw-slice/`, `.codex/agents/aw-*.toml`, and `.agents/skills/aw-slice/`, which Codex and Hermes read;
- puts a marked block at the top of `AGENTS.md`, saying the workflow takes precedence over any other feature workflow described there;
- makes sure `CLAUDE.md` loads `AGENTS.md`.

It changes nothing else. [`examples/relay-project.md`](examples/relay-project.md) is a filled-in example.

## Run

```bash
AGENT_PROFILE=strong  claude --model sonnet
AGENT_PROFILE=guarded codex -m <model>
AGENT_PROFILE=guarded hermes -m <model> --provider <provider>
AGENT_PROFILE=guarded AGENT_REVIEW_MODEL=opus claude --model haiku   # stronger reviewer, at a cost
```

Then ask for the change. The session reads `AGENTS.md`, its profile, `agent-workflow/slice.md` and `project.md`.

## Limits

- **Evidence base:** tested on two tasks in one Django project, with 1–3 runs per setup. Version 6's three rules were checked in one Sonnet and one Haiku run, which had no Medium or High findings and cost no more than version 5.
- **Cost on small models:** on Haiku, this workflow is not reliably cheaper than a multi-agent one, because those subagents are cheap too, but it finished in about half the time.
- **Read-only reviewer:** it is enforced only in Claude Code, by the adapter's tool list. In Codex and Hermes it is an instruction.
- **Commits:** the workflow does not push, open pull requests or wait for CI. Delivery follows the repository's own rules.
