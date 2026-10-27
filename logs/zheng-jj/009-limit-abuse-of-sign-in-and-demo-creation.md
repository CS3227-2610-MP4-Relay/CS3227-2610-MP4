# Limit abuse of sign-in and demo creation

Slice: ACC-3 (#4) · Tier: High · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5, effort unavailable (session model from the environment; effort not recorded) · Date: 2026-10-27

Tokens: 122,926,713 total (122,434,005 input, 492,708 output) for the interval 2026-10-26 15:53:48–17:25:36 UTC, including the orchestrator's shared usage.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `claude-opus-5-5`/unavailable, `claude:25cd8f33e8086febb5903412` | 105,024,577 | 104,281,179 | 283,145 | unavailable | 105,307,722 | 1h31m48s interval; shared with other slices (see below) |
| Builder — `claude-opus-5-5`/medium (requested), `claude:18c6094d79a89e6d4764e67b` | 12,274,007 | 11,909,096 | 111,326 | unavailable | 12,385,333 | 16:40:46–17:23:06 UTC, six runs (four checkpoints, two repair rounds) |
| Verifier — `claude-opus-5-5`/high (requested), `claude:db1553b9bc78f4303deda784` | 3,084,596 | 2,805,549 | 54,943 | unavailable | 3,139,539 | 17:04:42–17:25:26 UTC, three runs |
| Security-reviewer — `claude-opus-5-5`/high (requested), `claude:12ad241ba69be94202511caf` | 2,050,825 | 1,826,155 | 43,294 | unavailable | 2,094,119 | 17:04:42–17:25:20 UTC, three runs |

Three subagents ran, each resumed for later rounds. 1,611,112 cache-write tokens. Three retries, all by the builder; two repair rounds.

- **Orchestrator usage is not separable by slice.** The orchestrator coordinated this slice together with #40, ACC-1 (#2), ACC-2 (#3), RND-1 (#9), RND-2 (#10) and RND-3 (#11) in one session. Its row covers the whole interval from the same baseline as logs [005](005-ask-before-agents-change-github-state.md) to [008](008-prepare-a-test-round.md), so it overlaps their orchestrator rows and is not split.
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
  - It worked in the `relay-acc3` worktree on `4-limit-abuse`, stacked on ACC-2's `3-demo-workspace`.
  - It briefed the builder checkpoint by checkpoint, checked scope after each run with `check_scope.py builder --since <snapshot>`, committed each unit, ran full verification on each candidate and froze snapshots.
  - It merged ACC-2's repairs twice:
    - `b81dfff`: it resolved the TECHNICAL-SPEC Creation bullet and the delivery-order sentence by hand.
    - `39d40d3`: a one-line comment conflict.
  - It wrote the README status line (`1e97a66`) and opened draft PR #52.
  - The session was started from the parent folder, so the repository's Claude adapters, hooks and ask rules did not apply. Role isolation came from the agent type and instructions, plus manual `check_scope.py` snapshots. Every test-database command went through a local lock script.
- **Builder** (general-purpose agent following `workflow/agents/builder.md`).
  - Checkpoint 1: spec `480530a` and plan `465d30c`. The spec included the unlocked pre-check decision from ACC-2's security review.
  - Checkpoint 2: feat `84e9ff0` and plan `aefc058`. These add the counter model, migration, address keying and limit service, with 27 unit tests. Red first: an import error.
  - Checkpoint 3: spec `d281c4d` and feat `d5af676`.
    - Red first: 28 failed, 5 passed.
    - It removed `serialized_rollback`, which had broken when mixed with other transactional tests.
  - Checkpoint 4: fix `b924e2c`, spec `00be9f8`, guides `1733a53` and plan `f3db310`.
  - Repair round 1: spec `36c49fa`, fix `4e108ed`, test `8587c3c`, docs `cd5f060` and plan `59795e6`.
    - Red: 2 failed with the old view.
    - Mutation checks:
      - with the lock taken without a row lock, both threaded tests failed in 5 of 5 runs;
      - with `start` as a no-op, 9 tests failed.
  - Repair round 2: spec `3a616bd`, test `8d16040` and plan `b77ce98`.
- **Verifier** (read-only agent type, no edit tools). It reviewed these ranges:
  - `b1d0397..f3db310`: 2 Medium, 4 Low and Info. One Medium was that sign-in hashed under its address's lock, so a lab signing in together could get 503s; the other was a wrong User Guide sentence.
  - `f3db310..59795e6`: all resolved; 3 Low and 2 Info.
  - `59795e6..b77ce98`: resolved, with nothing new.
- **Security-reviewer** (same setup). It reviewed the same ranges:
  - round 0: no Critical, High or Medium, 6 Low and 4 Info. It also confirmed the ACC-2 Medium (hashing before the limit) was fixed by the pre-check.
  - round 1: all resolved, 1 Info.
  - round 2: resolved, with 1 Info for the human.
- **Final candidate:** `b77ce98`. Coordinator full verification passed: Django check, `makemigrations --check`, Ruff lint and format, and pytest (269 passed, 1 skipped). 233 of 400 budget lines.

## Decisions and corrections

- **Decisions under the delegation.** These are recorded in the plan and specs as the orchestrator's decisions, not the human's:
  - **Pre-checks:** an unlocked pre-check runs before any password hash in `/demo/`, and, from round 1, in sign-in too. Each is followed by a locked re-check.
  - **429s and 503s:**
    - 429s are returned outside the generic exception handler;
    - `/demo/` keeps ACC-2's rule that any exception gives the 503, now including hashing;
    - sign-in gives the 503 for database errors from the pre-check through its transaction;
    - the 503 sentence for the accounts routes is narrowed to match.
  - **Addresses and timeouts:**
    - an IPv4-mapped IPv6 address counts as its IPv4 address;
    - timeouts are 5 s for locks, 10 s for statements and 10 s for idle transactions, and the function time limit must be at least 30 s;
    - PostgreSQL 17's `transaction_timeout` was considered and not adopted.
  - **Tests and guides:** no `serialized_rollback`, and the User Guide gives the two 429 messages.
  - **Residuals recorded rather than changed:**
    - one address fills the 200-a-day demo cap in 20 hours, and twenty addresses or one IPv6 /56 within an hour;
    - spread-out sign-in guessing;
    - a pre-check burst;
    - unlimited successful sign-ins;
    - rotating `SECRET_KEY` resets every count.
- **Open for the human:**
  - Confirm the decisions above.
  - Decide on the residuals: IPv6 aggregation at /56 to /48, a per-username cap, and logging of refusals and of the "unknown" key.
  - Accept or reword one Info item: "changes nothing" in the accounts routes' 503 sentence. After a correct password, an upgraded password hash may already have been saved.
  - #5's release gate must:
    - observe from two external clients that forged forwarding headers don't change the stored key, and that no production request uses "unknown";
    - check that the function time limit is at least 30 s;
    - check the permission to set per-transaction timeouts;
    - record the connection limit and pooler mode;
    - not deploy ACC-2 without ACC-3.

## Problems

- **Failing tests after a merge.** After the first ACC-2 merge, 3 tests errored, because `serialized_rollback` conflicted with ACC-2's new transactional test. The builder removed `serialized_rollback` in checkpoint 3.
- **Builder retries.** There were three:
  - a heredoc edit failed on quoting and was redone as a Python script;
  - a test helper kept `RequestFactory`'s default `REMOTE_ADDR`;
  - a test read `client.session`, which created a session row.
- **Builder slip.** The builder once ran `git add -N` with no paths. It changed nothing, and the index stayed empty.
- **Bundled commits.** Two commits bundle independent work: `4e108ed` (repair round 1) and `d281c4d`/`d5af676`, which share a timestamp. The verifier noted this, and history was not rewritten.
- No scope violations or malicious instructions were seen. This log has not been checked by its human author.
