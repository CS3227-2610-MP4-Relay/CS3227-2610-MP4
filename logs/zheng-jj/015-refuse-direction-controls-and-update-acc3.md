# Refuse direction controls and update ACC-3

Slice: #68 (and the #52 merge with main) · Tier: Standard · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5, effort unavailable (session model from the environment; effort not recorded) · Date: 2026-10-27

Tokens: 35,096,196 total (34,885,897 input, 210,299 output) for the interval 2026-10-27 05:31:34–06:24:08 UTC.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `claude-opus-5-5`/unavailable, `claude:180bc6733860a61379eb3052` | 20,798,858 | 20,694,764 | 36,671 | unavailable | 20,835,529 | 52m34s interval |
| Builder #68 — `claude-opus-5-5`/medium (requested), `claude:8bdf4275e72e2876b4dbcf7c` | 10,078,201 | 9,782,607 | 83,694 | unavailable | 10,161,895 | six runs (three checkpoints, two repair rounds) |
| Verifier #68 — `claude-opus-5-5`/high (requested), `claude:007ff5d1e35d042343025391` | 1,983,288 | 1,665,261 | 38,925 | unavailable | 2,022,213 | three runs |
| Security-reviewer #68 — `claude-opus-5-5`/high (requested), `claude:841defb689c6b1e67ecd2d2c` | 1,431,530 | 1,137,562 | 37,434 | unavailable | 1,468,964 | three runs |
| Verifier, #52 merge — `claude-opus-5-5`/high (requested), `claude:f85443a8c0b6936eb16e81a7` | 594,020 | 533,758 | 13,575 | unavailable | 607,595 | one run |

Four subagents ran. 1,071,491 cache-write tokens. No retries; two repair rounds on #68.

- **Interval cutoff.** The interval ends before this log, the #68 PR and its CI. The earlier part of this session is in [log 014](014-close-the-open-review-gaps.md).

See [token reporting](../../workflow/README.md#token-reporting).

## Requests

- **Review comments.** The human asked the orchestrator to look at the comments Whimsyturtle left on #49 and #51.
- **Decisions on the comments:**
  - round text: refuse hidden direction characters rather than all Unicode;
  - usernames: leave as they are;
  - replies: post them.
- **Pull.** The human asked for another pull, then said "do what u think works", then to resolve the conflicts on the two open PRs (#52, #65).
- **Decisions during #68 review:**
  - allow LRM, RLM and ALM, so that only the embedding, override and isolate characters are refused;
  - record other invisible characters as a residual, to be handled with the AI input rules (#22);
  - accept look-alike build labels as a residual once the marks' real reach was known.

## Agent runs

- **Orchestrator.**
  - It opened issue #68 and posted replies on #51 and #49.
  - It merged main into `4-limit-abuse` in a separate worktree (`4559dc3`) and resolved five conflicts with a rule script kept in the scratchpad. The rules kept both sides' facts.
  - It ran full verification: 805 passed, 85 subtests.
  - It added the wording fix `258710b` itself, after the merge review.
  - It confirmed that #65 merges cleanly.
  - It checked the bidi classes of the residual characters with Python's `unicodedata` (Unicode 16.0).
- **#68 builder.**
  - Spec `e6160c4`, plan `81c2e12`.
  - Feat `536f1a6`: red 29 failed and 33 passed; removing the check failed the same 29.
  - Docs `e1171ee`.
  - Repair 1:
    - spec `32df56c` and `1231629` (the count is 9, not 10);
    - fix `f7a26b6`: direction marks allowed, plus tests for neighbouring code points, check interactions and encodings. Putting LRM back in the set failed 4 tests.
  - Repair 2:
    - spec `a569951`: the marks' reach, the look-alike residual, the fillers;
    - refactor `fb600df`: one shared `DIRECTION_CONTROLS`;
    - docs `49e466a`.
- **Verifier #68.**
  - `3bda6e1..e1171ee`: 1 Medium (literal invisible characters in the plan) and 5 Low.
  - `e1171ee..e9d1ea7`: 2 Low (the marks' reach understated; the set defined twice).
  - `e9d1ea7..64effbf`: nothing above Info.
- **Security-reviewer #68.**
  - Round 0: 1 Low (other invisible characters, which needed a decision) and 3 Info.
  - Round 1: 1 Low (the marks can reorder digits and words, so labels can look alike).
  - Round 2: no open findings.
- **Verifier, #52 merge.** 1 Low (the session-save 400 was missing from the accounts routes paragraph) and 2 Info. Both were fixed in `258710b`.
- **Final checks.**
  - #68 `64effbf`: 814 passed, 85 subtests; Django check, `makemigrations --check` and Ruff clean.
  - The scan for literal invisible characters outside `.venv` finds nothing.
  - #52 `258710b`: hosted CI passed.

## Decisions and corrections

- **Correction.** The orchestrator described the narrowed set as 10 characters; the builder counted 9.
- **Orchestrator's decisions:**
  - #68 branches from #64's head and targets main once #64 merges;
  - the set of characters to refuse;
  - the escaping-only approach for literal characters in files.
- **Open for the human:**
  - #61, the browser check, is still pending on the locally seeded round;
  - the reordering claims rest on the reviewers working through UAX #9 by hand, not on a browser run.

## Problems

- **Literal characters in files.** The builder's file tools turned `\u` escapes into literal invisible characters twice: once in the plan and once in a test file. Both were caught: by Ruff for the test, by the verifier for the plan. The builder switched to a placeholder substitution helper.
- **Wrong claim.** The first SECURITY-SPEC sentence about the direction marks was wrong. The security re-review caught it, and the human decided again on the corrected facts.
- No scope violations or malicious instructions were seen. This log has not been checked by its human author.
