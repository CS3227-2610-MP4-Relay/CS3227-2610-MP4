# Manage criteria and test cases

Slice: RND-2 (#10) · Tier: High · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5, effort unavailable (session model from the environment; effort not recorded) · Date: 2026-10-27

Tokens: 142,808,417 total (142,299,105 input, 509,312 output) for the interval 2026-10-26 15:53:48–17:40:20 UTC, including the orchestrator's shared usage.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `claude-opus-5-5`/unavailable, `claude:25cd8f33e8086febb5903412` | 124,719,428 | 123,894,615 | 315,557 | unavailable | 125,034,985 | 1h46m32s interval; shared with other slices (see below) |
| Builder — `claude-opus-5-5`/medium (requested), `claude:796b94a2528263ec3f682766` | 12,462,142 | 12,071,225 | 115,891 | unavailable | 12,578,033 | 17:03:10–17:38:56 UTC, six runs (four checkpoints, two repair rounds) |
| Verifier — `claude-opus-5-5`/high (requested), `claude:c076ea868097e3d442869a4e` | 3,005,391 | 2,706,490 | 47,031 | unavailable | 3,052,422 | 17:24:09–17:40:10 UTC, three runs |
| Security-reviewer — `claude-opus-5-5`/high (requested), `claude:ba272cf44d1a8e793437d2bc` | 2,112,144 | 1,891,147 | 30,833 | unavailable | 2,142,977 | 17:24:09–17:40:06 UTC, three runs |

Three subagents ran, each resumed for later rounds. 1,734,634 cache-write tokens. Four retries, all by the builder; two repair rounds.

- **Orchestrator usage is not separable by slice.** The orchestrator coordinated this slice together with #40, ACC-1 (#2), ACC-2 (#3), ACC-3 (#4), RND-1 (#9), RND-3 (#11) and RND-6 (#18) in one session. Its row covers the whole interval from the same baseline as logs [005](005-ask-before-agents-change-github-state.md) to [009](009-limit-abuse-of-sign-in-and-demo-creation.md), so it overlaps their orchestrator rows and is not split.
- **Interval cutoff.** The interval ends before this log and the PR delivery, so later usage is not included.

See [token reporting](../../workflow/README.md#token-reporting).

## Requests

- The human asked the orchestrator to "start working on them all" (their unblocked issues) and to "make my decisions for me".
- Overnight instructions:
  - "i should wake up to all unblocked prs complete";
  - "there might be new mergers, so remember to pull along the way";
  - when a PR is done, and only then, assign the teammate as reviewer;
  - work on several issues at once.

## Agent runs

- **Orchestrator.**
  - It worked in the `relay-rnd2` worktree on `10-criteria-and-cases`, stacked on RND-1's `9-prepare-round`.
  - It briefed the builder checkpoint by checkpoint and checked scope after each run with `check_scope.py builder --since <snapshot>`. It committed each unit, ran full verification on each candidate and froze snapshots.
  - It merged RND-1's final head cleanly, as `b309acc`.
  - It wrote the README status line in `e6afdc3`.
  - It opened draft PR #53, with base `9-prepare-round`.
  - The session was started from the parent folder, so the repository's Claude adapters, hooks and ask rules did not apply. Role isolation came from the agent type and instructions, plus manual `check_scope.py` snapshots. Every test-database command went through a local lock script.
- **Builder** (general-purpose agent following `workflow/agents/builder.md`).
  - Checkpoint 1: spec `51e0919` and plan `3336a50`.
  - Checkpoint 2: `096d86d`, the models, link model, migration, capped services and the shared-field CR LF change, plus its plan commit.
    - Red first: `test_forms` gave 1 failed, and the service tests failed on an import error.
    - Three service mutations each made their tests fail.
  - Checkpoint 3: `dad6ce6`, the shared record views, six routes, round-page sections and tests, plus plan `3e2d6d6`.
    - Red first: an import error, then 7 failed and 92 passed.
    - Removing the round lock made the race test fail in only 2 of 3 runs. The pause added in `7f3c8cf` raised that to 5 of 5.
  - Checkpoint 4: spec `f460eae`, guides `d44eae9` and plan `3557050`.
  - Repair round 1: spec `553f42a`, fix `686be05`, test `d834a2d`, docs `fae50c4` and plan `0643e52`.
    - Red: 7 failed and 31 passed.
    - Mutations made the choices test, the Open/Closed 404 test and the case race (5 of 5) fail.
  - Repair round 2: docs `057be86`, test `760d422` and plan `d0c4d87`. Removing the write transaction made the three mid-write tests fail.
- **Verifier** (read-only agent type, no edit tools).
  - `6f4ab10..3557050`: 2 Medium, 5 Low and 1 nit. The Mediums were that a criterion ID of 0 was treated as "no record", and that no test checked the case form offers only the round's criteria.
  - `3557050..0643e52`: all resolved, with 2 nits and 1 check not yet evidenced.
  - `0643e52..d0c4d87`: resolved, with nothing new.
- **Security-reviewer** (same setup).
  - Round 0: no High or Medium. 1 Low (the zero ID) and 4 Info.
  - Round 1: resolved, with 1 display-only Info.
  - Round 2: nothing new.
- **Final candidate:** `d0c4d87`. Coordinator full verification passed: Django check, `makemigrations --check`, Ruff lint and format, and pytest (484 passed, 1 skipped). 347 of 400 budget lines.

## Decisions and corrections

- **Decisions under the delegation.** These are recorded in the plan and specs as the orchestrator's decisions, not the human's:
  - **Round page:** the criteria and cases sections show in every state, with controls only while Draft.
  - **Linked criteria:** they are chosen and shown by their full text.
  - **Line breaks:** CR LF counts as one line break, including in round titles.
  - **Naming and messages:** the model is called `Case`, and cap messages appear next to Text or Title.
  - **Repair round 1:**
    - record IDs are taken by kind;
    - refusals are caught outside the write transaction;
    - all writes are services;
    - the test gaps are filled.
  - **Repair round 2:** the guide nits and an oversized submitted-ID test.
- **Open for the human:**
  - Confirm the decisions above.
  - Check the per-line `dir="auto"` rendering in a browser, checkbox labels included.
  - Accepted Info:
    - A model's `__str__`/repr carries record text. This is a hardening note for RND-3 and RES: keep records out of exception messages and logs.
    - A refused-delete page is drawn after the rollback, so it can show changes made in between. This affects display only.
  - Process notes, with no history rewrite:
    - `096d86d` bundles the CR LF change with the data layer.
    - `686be05` bundles the zero-ID fix with two refactors.
  - The plan's round-1 record mis-describes the verifier's note on `686be05`: it says "the fix with its tests", where the note was "the fix with two refactors".

## Problems

- **Wrong finding on case IDs.** Both reviewers' round-0 reports said case ID 0 was affected. It was not: only criterion IDs were. Both corrected this in round 1.
- **Builder retries.** There were four:
  - a Ruff formatting rerun;
  - patching services that had been captured at import;
  - a `<maximum>` placeholder in the User Guide that HTML would swallow;
  - a Ruff unused-variable fix.
- **Escape-sequence slip.** A line-ending and escape slip while writing `forms.py` was corrected before any test run.
- No scope violations or malicious instructions were seen. This log has not been checked by its human author.
