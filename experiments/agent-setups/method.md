# Agent setups: frozen method

Owner: zheng-jj · Issue: #31 · Frozen: 2026-10-30, before the first counted run

This file records the method as fixed before results were seen. The [README](README.md) reports the results and any deviations. If the two disagree, this file states what was planned, and the README states what happened.

## Question

On one fixed, real task, how do cost, quality, speed and process compare across:
- workflow structures: MP4's consolidated workflow, MP3's six-role workflow and a single session;
- model mixes;
- two popular methodologies, superpowers and spec-kit;
- three popular add-ons, caveman, ponytail and headroom, each on top of the MP4 workflow?

The answers then inform an "ideal" setup, which is evaluated afterwards. That evaluation adds DeepSeek v4.1 Flash runs in Codex and Hermes and Haiku runs in Claude Code, and is not part of this comparison.

## Task

Every run delivers issue #68, "Refuse hidden text-direction characters in round text". It starts from `01f9a24`, the commit the original #68 slice started from, plus one harness commit. The merged result, PR #71 at `d794dd5`, is the reference. It is never visible to a run.

The prompt is [`inputs/task-prompt.md`](inputs/task-prompt.md), identical for every arm. It contains:
- the issue text;
- the human's three decisions from the original slice, given up front so that no run needs a human;
- local-only constraints;
- environment notes.

The prompt is workflow-neutral. Each arm's own `AGENTS.md` and workflow files say how to work.

## Arms

| Arm | Workflow | Orchestrator | Subagents | Add-on |
| --- | --- | --- | --- | --- |
| `mp4` (baseline) | MP4 slice: builder, verifier, security-reviewer | Opus 5.5 | Opus 5.5: builder medium effort, reviewers high | none |
| `mp3` | MP3 slice at `97ad991`: spec-writer, spec-critic, test-writer, implementer, reviewer, security-reviewer | Opus 5.5 | Opus 5.5: writers medium, critics and reviewers high | none |
| `solo` | MP4 slice, one session plays every role | Opus 5.5 | none (the subagent tool is removed) | none |
| `mp4-sonnet-builder` | MP4 slice | Opus 5.5 | Sonnet 5.5 builder, Opus reviewers | none |
| `mp4-sonnet` | MP4 slice | Sonnet 5.5 | Sonnet 5.5 everywhere | none |
| `superpowers` | superpowers methodology (obra/superpowers `2ce8aa1`) | Opus 5.5 | whatever superpowers dispatches | its plugin |
| `spec-kit` | spec-kit Spec-Driven Development (github/spec-kit `2a23a84`, `specify init --integration claude`) | Opus 5.5 | none prescribed | its skills |
| `caveman` | MP4 slice | Opus 5.5 | as baseline | caveman plugin (JuliusBrussee/caveman `9b68f7e`) |
| `ponytail` | MP4 slice | Opus 5.5 | as baseline | ponytail plugin (dietrichgebert/ponytail `96608e0`) |
| `headroom` | MP4 slice | Opus 5.5 | as baseline | headroom 0.42.0 proxy (headroomlabs-ai/headroom `1fe8549`), one per run |
| `stack` | MP4 slice | Opus 5.5 | as baseline | caveman, ponytail and headroom together |

The workflow arms change only workflow files, in one setup commit; the [setup script](harness/setup_arm.py) records the exact changes. In the MP3 arm:
- MP3's `AGENTS.md` is used, with Relay's one-line description;
- so are its workflow README, role files, skills, adapters and scope scripts;
- an MP4-only test of MP4's Codex approval rules is removed.

In the spec-kit arm, the adapter test is told to ignore spec-kit's own skills. Every arm's starting commit passes full verification.

## Fixed settings

- **Claude Code:** 2.1.312, from a pinned copy of the binary, run headless (`-p`) with `--effort high` for the orchestrator.
- **Settings:** project and local settings only, so the user's personal settings are excluded. No MCP servers.
- **Tools:** Task (subagents), Bash, Read, Edit, Write, Glob, Grep, Skill, TodoWrite and NotebookEdit.
- **Blocked:** web access, `gh`, `git push`/`fetch`/`pull`/`clone`/`remote`, `curl`, `wget`, `docker` and package installs.
- **Permissions:** edits accepted. The repository's own deny rules and scope hook still apply.
- **Budget:** a cost cap of US$200 per run (`--max-budget-usd`). A run that hits it is reported as unfinished, not discarded.
- **Isolation:** each run works in its own clone, which holds only the history up to the start, with no remote, its own test database (`TOX_PARALLEL_ENV`) and a shared virtual environment.
- **Add-ons:** loaded per session with `--plugin-dir`, never installed into the user's configuration. Each headroom run gets its own proxy and state folder, with telemetry beacons off. Add-on hooks write small marker files under `~/.claude`; they are listed before the experiment and removed after it.

## Runs and order

- Each arm runs twice and the baseline three times: 23 runs.
- The first baseline run doubles as the pilot. It counts unless the harness changes after it.
- Order: the pilot, then round 1 in a seeded order (`random.Random(31)`), then round 2 in a seeded order, then the third baseline run. Up to 3 runs go at once.
  - Round 1: superpowers, mp4-sonnet-builder, spec-kit, stack, headroom, mp4-sonnet, caveman, solo, ponytail, mp3.
  - Round 2: caveman, headroom, mp4-sonnet, mp3, spec-kit, mp4, superpowers, stack, solo, mp4-sonnet-builder, ponytail.
- A run lost to an infrastructure fault is rerun and the fault is reported: a usage limit, an API outage, or a harness bug that affects every arm alike.

## Measures

**Cost:**
- the session's reported cost (`total_cost_usd`, at API list prices);
- tokens by type (input, cache read, cache write, output), per model;
- the number of subagent runs.

**Speed:** wall-clock time from launch to exit, and the number of model turns. Runs that overlap share API capacity, so speed is reported with that caveat.

**Quality**, scored on the run's final commit, with uncommitted changes included:
1. **Hidden acceptance suite (132 tests):** [`harness/test_hidden_direction_controls.py`](harness/test_hidden_direction_controls.py), written from the issue and decisions only. It drives all 12 round-text inputs over HTTP:
   - 108 refusal tests: each of the 9 controls in each of the 12 inputs;
   - 24 over-blocking tests: direction marks, joiners, a zero-width space and other scripts are still accepted.

   On the starting commit, 108 fail and 24 pass. On the reference, all 132 pass.
2. **Full verification:** Django check, `makemigrations --check`, Ruff lint and format, and the full pytest suite.
3. **Test strength:** five behavioural mutants are planted in the candidate's own implementation:
   - M1, no check at all;
   - M2, U+2069 dropped from the refused set;
   - M3, U+202B dropped;
   - M4, LRM added (over-blocking);
   - M5, build labels unchecked.

   A mutant counts as killed when the candidate's own test suite fails. Each mutant is confirmed to be live by the hidden suite failing.
4. **Blind review:** one fresh Opus 5.5 session per candidate, with read-only tools and high effort, using the same rubric:
   - inputs: the issue, the decisions and the candidate's diff from its arm's starting commit, limited to source, tests, specs and docs, so that workflow artifacts that would reveal the arm are left out;
   - output: findings by severity, and 1–5 scores for correctness, test adequacy, spec and docs accuracy, simplicity and maintainability.

   Candidates are labelled with random IDs.

**Process**, from transcripts and Git:
- whether spec changes came before code;
- commit count and messages;
- scope-check violations;
- repair rounds;
- questions recorded instead of asked;
- blocked or forbidden actions attempted;
- any access outside the run's own clone, which is a leakage check;
- diff size by area.

## Analysis plan

- Report each run, and each arm's median and range. With 2–3 runs per arm, no significance tests: differences are called clear only when the arms' ranges do not overlap.
- **Primary outcome:** quality, measured as the hidden-suite pass rate, full verification and blind-review findings of Medium or above.
- **Secondary outcomes:** cost and time.
- An arm is better than the baseline only if its quality is at least the baseline's and its cost or time is lower, or its quality is clearly higher at a similar cost.
- A cost-against-quality chart shows which arms are dominated. The ideal setup is built from the arms that are not dominated, and is then evaluated separately.

## Known limitations, stated in advance

- One task, of Standard tier and small size. The results may not hold for large or ambiguous work.
- 2–3 runs per arm detect only large effects.
- The decisions are given up front, so the discovery the original slice did through review is not measured.
- Opus grades Opus-built work in the blind review. The hidden suite and mutants are the objective checks.
- Headless runs have no human, so "stops to ask" is measured as decisions recorded in the final report.

## Second task

Added on 2026-10-30, after task 1 was reported. Its method was fixed before any of its runs ended, and its mutants before any candidate was read.

Task 1 was small. Task 2 is larger and has more ways to be wrong, to test whether task 1's findings hold.

- **Task:** issue #16, "Request a retest" (RND-5). It starts from `99169c7`, the commit before RND-5 work began, plus the same harness commit. It needs:
  - a new route, page, form and service;
  - checks under the round-row lock;
  - a build cap and label normalisation;
  - rules for rendering user text.

  No merged reference exists.
- **Prompt:** [`inputs/task-prompt-2.md`](inputs/task-prompt-2.md), with eight decisions given up front.
- **Runs:** 14, in the order of [`inputs/queue-task2.txt`](inputs/queue-task2.txt), up to four at once:
  - one run each of caveman, ponytail, headroom, superpowers, spec-kit, mp3 and ideal v1 (Opus, `strong`);
  - two runs each of mp4 and the portable ideal v5 on Opus (`strong`);
  - one run of v5 on Sonnet (`strong`);
  - one run of v5 on Haiku with no profile set, which tests the guarded default;
  - one run of mp4 on Haiku, as the weak-model reference.

  Left out:
  - the stack arm, because each add-on is compared on its own;
  - solo and the Sonnet mixes, which task 1 already placed and the ideal replaces.

  DeepSeek is not rerun. Its task-1 runs are the reference for weaker models, with Haiku standing in on task 2.
- **Hidden suite (27 tests):** written from RND-5, the route table and the decisions only, and added to `harness/` once every task-2 run has ended. It drives the coordinator's pages over HTTP and covers:
  - the page and the link;
  - 409 for Draft and Closed rounds;
  - sign-in, 403 and 404;
  - escaping;
  - the happy path and the singular;
  - duplicates and label boundaries;
  - used labels: equal, with a format character, and decomposed;
  - labels that stay distinct: case and full width;
  - the cap of 10 builds;
  - repeated retests;
  - foreign cases.

  RND-5.7's races are not covered. On the starting commit, 25 fail and 2 pass, both of them about pages that must not change.
- **Mutants, task 2:**
  - M1, foreign cases accepted: every check that the chosen cases belong to the round is removed;
  - M2, the cap off by one: an eleventh build is allowed;
  - M3, labels compared as typed: the used-label check skips the comparison key;
  - M4, any round state accepted: every Open check for the retest is removed;
  - M5, the label unescaped: the success message renders the label as HTML.

  They are planted, scored and confirmed live as in task 1.
- **Blind review:** the same rubric, with the task-2 issue and decisions, focused on RND-5.
- **Limitation:** most arms run once, so task 2 shows whether task 1's pattern holds. It cannot rank arms that are close.
