# Create an isolated demo workspace

Slice: ACC-2 (#3) · Tier: High · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5, effort unavailable (session model from the environment; effort not recorded) · Date: 2026-10-27

Tokens: 87,092,021 total (86,698,830 input, 393,191 output) for the interval 2026-10-26 15:53:48–16:57:25 UTC, including the orchestrator's shared usage.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `claude-opus-5-5`/unavailable, `claude:25cd8f33e8086febb5903412` | 70,265,904 | 69,703,026 | 206,502 | unavailable | 70,472,406 | 1h03m37s interval; shared with other slices (see below) |
| Builder — `claude-opus-5-5`/medium (requested), `claude:8458d6de861ffa6b11b80524` | 10,178,838 | 9,703,753 | 88,835 | unavailable | 10,267,673 | 16:19:55–16:55:51 UTC, six runs (four checkpoints, two repair rounds) |
| Verifier — `claude-opus-5-5`/high (requested), `claude:d32d35c220e3e844392b952d` | 3,969,072 | 3,719,713 | 54,782 | unavailable | 4,023,854 | 16:36:42–16:57:11 UTC, three runs |
| Security-reviewer — `claude-opus-5-5`/high (requested), `claude:12faa18bd2389d1130d86490` | 2,285,016 | 1,943,907 | 43,072 | unavailable | 2,328,088 | 16:36:42–16:57:08 UTC, three runs |

Three subagents ran, each resumed for later rounds. 1,627,673 cache-write tokens. Three retries, all by the builder; two repair rounds.

- **Orchestrator usage is not separable by slice.** The orchestrator coordinated this slice together with #40, ACC-1 (#2), RND-1 (#9) and ACC-3 (#4) in one session. Its row covers the whole interval from the same baseline as [log 005](005-ask-before-agents-change-github-state.md) and [log 006](006-sign-in-and-out-by-role.md), so it overlaps their orchestrator rows and is not split.
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
  - It worked in the `relay-acc2` worktree on `3-demo-workspace`, stacked on ACC-1's `2-sign-in-by-role`.
  - It briefed the builder checkpoint by checkpoint and checked scope after each run with `check_scope.py builder --since <snapshot>`.
  - It committed each unit, ran full verification on each candidate and froze snapshots.
  - It wrote the README status line (`9e973da`), because `README.md` is outside the builder's scope.
  - It merged ACC-1's later commits three times: `fea7923` and `46e8a86` brought in ACC-1's repair rounds 1 and 2, and `c02fc69` brought in ACC-1's log. The first two merges conflicted. It resolved them by keeping both imports in `src/accounts/views.py` and, in the TECHNICAL-SPEC accounts-routes table, ACC-2's `/` row and ACC-1's `/sign-in/` row.
  - It opened draft PR #50 with base `2-sign-in-by-role`.
  - The session was started from the parent folder, so the repository's Claude adapters, hooks and ask rules did not apply. Role isolation came from the agent type and instructions, plus manual `check_scope.py` snapshots. Every test-database command went through a local lock script, because other slices' builders ran in parallel.
- **Builder** (general-purpose agent following `workflow/agents/builder.md`). Checkpoints:
  - 1: spec `b6f0aa7`, plan `f384753`;
  - 2: `e5b4ec7`, the creation service and lookup helper. Red first: both test modules failed to import. Then green.
  - 3: `c7c4aca`, the `/demo/` view, the start-page button and redirect, and the 404 and 503 pages. Red first: 17 failed, 8 passed.
  - 4: spec `ab8f9c9`, guides `ee516fd`, plan `015673b`.
  - Repair round 1:
    - spec `b2037c8`, fix `e3087e3`, docs `5ce253d`, plan `11d7649`;
    - red: 2 failed (the all-or-nothing and repr tests);
    - mutation checks showed the isolation, sensitive-variable and repr tests catch their defects.
  - Repair round 2: fix `5e69530` and plan `33bc8cb`. The new mid-table rendering-failure test failed before the change.
- **Verifier** (read-only agent type, no edit tools). It reviewed these ranges:
  - `1492c0b..46e8a86`: 1 Medium (no test would catch a home page showing another workspace), 7 Low, 2 Info;
  - `c02fc69..11d7649`: all fixed except the `home_url` refactor, which the orchestrator chose not to adopt. 1 new Low: template frames could still hold passwords in error reports.
  - `11d7649..33bc8cb`: resolved, nothing new.
- **Security-reviewer** (same setup). It reviewed the same ranges:
  - round 0:
    - 1 Medium: refused demo creations would still pay for three password hashes once ACC-3's limits exist;
    - 2 Low: passwords could reach reprs and frame variables, and the real commit failure was untested;
    - 4 Info;
  - round 1: resolved, 4 Info;
  - round 2: resolved, 1 Info.
- **Final candidate:** `33bc8cb`. Coordinator full verification: Django check, `makemigrations --check`, Ruff lint and format, and pytest (196 passed, 1 skipped) were all green. Budget: 197 of 400 lines by the official command, which includes 12 lines of `src/relay_tests` test code.

## Decisions and corrections

- **Decisions under the delegation.** These are recorded in the plan and specs as the orchestrator's decisions, not the human's:
  - **Pages:** the 404 page serves every 404, and the PLT-1.3 test text was changed to match. The credentials page keeps a "Sign in" link.
  - **Creation:**
    - up to 3 suffix draws, then the unique constraint gives the 503;
    - any exception in the creation block gives the 503;
    - the workspace helper is used only by tests in ACC-2.
  - **Guides:** the Developer Guide's shell recipe for accounts is removed.
  - **Round 0:**
    - fix every finding except the `home_url` refactor, because RND-1 was editing `views.py` in parallel;
    - framing protection is left for #5;
    - the security Medium is settled in ACC-3's spec on `4-limit-abuse` (`480530a`): an unlocked limit pre-check runs before hashing.
  - **Round 1:** hide every variable below the `/demo/` view from error reports.
- **Open for the human:**
  - Confirm the decisions above.
  - Settle at the ACC-3 merge: ACC-2's `/demo/` turns any exception in the creation block into the 503, while ACC-3's spec gives the 503 for database errors. The ACC-3 builder has been told to keep ACC-2's rule for `/demo/`.
  - Accepted Info:
    - the three duplicated role-home redirects;
    - `generate_passwords`' sensitive variables are untested;
    - local `DEBUG` error pages are unredacted, which is Django's design;
    - `Credential` is still a tuple, so indexing it gives the password, and only its repr hides it;
    - the comment on `create_demo`'s decorator and the plan overstate its reach, because nested functions keep their own named lists. Those lists still cover every plain password.
  - Accepted residuals from the specs:
    - resubmitting the page creates another workspace;
    - the back button may show the old credentials;
    - no production deploy before ACC-3;
    - the sample round arrives with RND-7.

## Problems

- **Line endings.** The builder's scripted edits saved five tracked files with LF endings. It restored CRLF before handing back.
- **Mutation checks.** One template-only mutation raised an error instead of leaking, so it was replaced by a view-context mutation and not counted. One mutation script with an invalid `sed` was redone.
- **Retries.** These are the three counted in the table: a Ruff formatting retry, a Ruff import-sorting fix, and the redone mutation.
- **Merge conflicts.** The orchestrator resolved the two merge conflicts with ACC-1 by hand, and the verifier checked both resolutions.
- No scope violations or malicious instructions were seen. This log has not been checked by its human author.
