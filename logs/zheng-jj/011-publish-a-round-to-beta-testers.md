# Publish a round to Beta Testers

Slice: RND-3 (#11) · Tier: Standard · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5, effort unavailable (session model from the environment; effort not recorded) · Date: 2026-10-27

Tokens: 163,521,613 total (163,022,094 input, 499,519 output) for the interval 2026-10-26 15:53:48–17:59:40 UTC, including the orchestrator's shared usage.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `claude-opus-5-5`/unavailable, `claude:25cd8f33e8086febb5903412` | 150,532,451 | 149,619,426 | 354,509 | unavailable | 150,886,960 | 2h05m52s interval; shared with other slices (see below) |
| Builder — `claude-opus-5-5`/medium (requested), `claude:1e4487b7c9ee5f4dbafb4661` | 7,613,576 | 7,172,879 | 75,458 | unavailable | 7,689,034 | 17:25:27–17:57:16 UTC, five runs (four checkpoints, one repair round) |
| Verifier — `claude-opus-5-5`/high (requested), `claude:4a94479b2ce2cd63ead3c127` | 2,994,342 | 2,728,820 | 40,376 | unavailable | 3,034,718 | 17:47:12–17:59:21 UTC, two runs |
| Security-reviewer — `claude-opus-5-5`/high (requested), `claude:95144d4a0822ddb9c22e39a6` | 1,881,725 | 1,673,969 | 29,176 | unavailable | 1,910,901 | 17:47:12–17:59:06 UTC, two runs |

Three subagents ran; the two reviewers were resumed for the re-review. 1,825,950 cache-write tokens. One retry, by the builder; one repair round.

- **Orchestrator usage is not separable by slice.** The orchestrator coordinated this slice together with the earlier slices in logs [005](005-ask-before-agents-change-github-state.md) to [010](010-manage-criteria-and-test-cases.md) and with RND-6 (#18), all in one session. Its row covers the whole interval from the same baseline as those logs, so it overlaps their orchestrator rows and is not split.
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
  - It worked in the `relay-rnd3` worktree on `11-publish-round`, stacked on RND-2's `10-criteria-and-cases`.
  - It merged RND-2 twice, both cleanly: `303bd09` brought in RND-2's repair round 1, and `e371271` brought in RND-2's final head.
  - It briefed the builder checkpoint by checkpoint, checked scope after each run with `check_scope.py builder --since <snapshot>`, committed each unit, ran full verification on each candidate and froze snapshots.
  - It also:
    - wrote the README status line (`114bed1`) and a cosmetic plan correction (`1665ca0`);
    - computed the maximum NFC expansion for the security reviewer: 3, at U+1D1C0, in Unicode 15.1;
    - confirmed the test database's `server_encoding` is UTF8;
    - opened draft PR #54.
  - The session was started from the parent folder, so the repository's Claude adapters, hooks and ask rules did not apply. Role isolation came from the agent type and instructions, plus manual `check_scope.py` snapshots. Every test-database command went through a local lock script.
- **Builder** (general-purpose agent following `workflow/agents/builder.md`).
  - Checkpoint 1: spec `28db3e0` and plan `365e7b9`.
  - Checkpoint 2: `90b57cd` and plan `0099cf2`. It added the build models, the publish service and the publish form. Red first: an import error at collection.
  - Checkpoint 3: `ce7bfa3` and plan `a3c5e42`. It added the route, the Open round page and the tests.
    - Red first: 37 failed and 5 passed.
    - The race tests were made deterministic: the first request pauses for 0.3 s inside its lock.
    - Removing the publish lock made two races fail in 5 of 5 runs.
  - Checkpoint 4: spec `2224309`, guides `ef0cefe` and plan `98977ef`.
  - Repair round 1 changed tests, docs and the plan only: test `cd875c8`, docs `e527de1` and plan `ce2a2a6`. Each new test failed under a matching mutation, and the 7 race tests passed 5 runs in a row.
- **Verifier** (read-only agent type, no edit tools).
  - `57ac47e..98977ef`: 1 Medium, 3 Low and 3 Info. The Medium: case titles in the Builds list had no rendering test.
  - `98977ef..ce2a2a6`: resolved, with 2 Info notes.
- **Security-reviewer** (same setup).
  - Round 0: no Critical, High or Medium, 2 Low and 6 Info. The Lows were a retitle and delete race gap, and an untested worst-case key length.
  - Round 1: resolved, with nothing new.
- **Final candidate:** `ce2a2a6`, plus the plan correction `1665ca0`. Coordinator full verification passed: Django check, `makemigrations --check`, Ruff lint and format, and pytest (557 passed, 1 skipped). 144 of 400 budget lines.

## Decisions and corrections

- **Decisions under the delegation.** These are recorded in the plan and specs as the orchestrator's decisions, not the human's.
  - **Tier:** Standard, with a security review.
  - **Publish form and validation:**
    - The label is checked before the case count.
    - The publish form has no separate heading.
    - No database constraint ties `published_at` to the state.
    - Labels with line breaks are accepted and shown line by line.
  - **Publish flow:** the refusal comes before any write, and refusals are caught outside the committing transaction, as in RND-2.
  - **Repair round 1:**
    - add the missing rendering test, the races and the longest-key test, and fix the guide wording;
    - keep `race()` in `test_publish.py`, because RND-6 moves it.
- **Open for the human:**
  - Confirm the decisions above.
  - Decide on the deferred hardening: `Round`, `Criterion` and `Case` still return user text from `__str__`.
  - Rule on whether the `MARKUP` test payload must be stored escaped, as `AGENTS.md` says, and whether to share it once in `conftest.py`.
  - Notes for RND-5:
    - Check duplicate labels under the lock before inserting, so no `IntegrityError` DETAIL logs a label.
    - Check case IDs against the locked round.
    - `build_key` uses NFC, not NFKC.
  - Info items accepted as they stand:
    - "Round published." can surface on another page if the redirect fails; the text is fixed.
    - `maxlength` counts UTF-16 units.
    - X-Frame-Options belongs to #5.

## Problems

- **Template change for RND-1 tests.** The first green run of checkpoint 3 broke 12 RND-1 rendering tests, because the message slot separated the heading from the state line. The builder fixed this in the template.
- **Builder retry.** One Ruff formatting rerun.
- **Merge conflict expected with RND-6.** The `race()` helper changed in this slice, and RND-6 moves it into `conftest.py`. The orchestrator resolves this when merging.
- No scope violations or malicious instructions were seen. This log has not been checked by its human author.
