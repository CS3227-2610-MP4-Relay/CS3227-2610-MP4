# Sweep and tidy the codebase before release

Slice: #67 (PRs #110 to #114) · Tier: Fast lane (#110), Standard (#111), High (#112 to #114) · Tool: Claude Code (VS Code extension) · Orchestrator model: claude-opus-5-5, effort unavailable (session model from the environment; effort not recorded) · Date: 2026-11-01

Tokens: 93,701,427 input, 592,463 output, 94,293,890 total, from about 11:04 UTC to 14:34 UTC.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — `claude-opus-5-5`/unavailable, `claude:180bc6733860a61379eb3052` | 44,520,531 | 43,979,126 | 107,446 | unavailable | 44,627,977 | 11:04 – 14:34 UTC |
| Sweep, `rounds` and `ai` — `claude-opus-5-5`/default, `claude:80840e70525be49f9ae12c4d` | 4,663,815 | 4,480,710 | 52,136 | unavailable | 4,715,951 | 11:10 – 11:19 UTC |
| Sweep, accounts, settings and scripts — `claude-opus-5-5`/default, `claude:bf8ccf0edf535d2ca4ade40a` | 5,267,412 | 5,111,284 | 45,479 | unavailable | 5,312,891 | 11:10 – 11:19 UTC |
| Sweep, tests and guides — `claude-opus-5-5`/default, `claude:617c9a309db3bf1dea19536b` | 8,536,573 | 8,355,092 | 54,034 | unavailable | 8,590,607 | 11:10 – 11:20 UTC |
| Builder, stale text — `claude-opus-5-5`/role default, `claude:c8ad8efdaf4507b500a82339` | 1,375,962 | 1,309,821 | 20,020 | unavailable | 1,395,982 | 11:22 – 11:26 UTC |
| Builder, test helpers — `claude-opus-5-5`/role default, `claude:663ed9fa3a5789d6360ed187` | 9,234,142 | 8,840,316 | 59,671 | unavailable | 9,293,813 | 11:22 – 13:39 UTC |
| Builder, accounts — `claude-opus-5-5`/role default, `claude:268b1897e0755f4d8d982f1e` | 1,848,965 | 1,668,556 | 25,266 | unavailable | 1,874,231 | 13:23 – 13:43 UTC |
| Builder, `rounds` — `claude-opus-5-5`/role default, `claude:0865cd18b883b95d93afe7e2` | 3,936,922 | 3,825,437 | 44,237 | unavailable | 3,981,159 | 13:33 – 14:06 UTC |
| Builder, `ai` — `claude-opus-5-5`/role default, `claude:ba25cfeceaef7b6e8cecfddd` | 5,350,092 | 5,124,384 | 50,902 | unavailable | 5,400,994 | 13:49 – 14:15 UTC |
| Verifier, test helpers — `claude-opus-5-5`/role default, `claude:68ced0a07928ab5d3d43a825` | 1,342,610 | 1,163,642 | 16,246 | unavailable | 1,358,856 | 13:32 – 13:43 UTC |
| Verifier, accounts — `claude-opus-5-5`/role default, `claude:f17c02dab3fe0b4f9364fa9b` | 1,304,212 | 1,231,772 | 22,209 | unavailable | 1,326,421 | 13:38 – 13:44 UTC |
| Verifier, `rounds` — `claude-opus-5-5`/role default, `claude:a61ba16f36fdab18ae8de3a8` | 1,849,668 | 1,662,543 | 24,219 | unavailable | 1,873,887 | 13:55 – 14:11 UTC |
| Verifier, `ai` — `claude-opus-5-5`/role default, `claude:2f43cae72b21c1cdd2974c8a` | 2,053,098 | 1,855,754 | 29,890 | unavailable | 2,082,988 | 14:04 – 14:34 UTC |
| Security-reviewer, accounts — `claude-opus-5-5`/role default, `claude:16f96038279ef9db99b5e740` | 548,014 | 504,782 | 10,297 | unavailable | 558,311 | 13:38 – 13:44 UTC |
| Security-reviewer, `rounds` — `claude-opus-5-5`/role default, `claude:131d872cafcff5e0442c6776` | 905,157 | 790,667 | 11,796 | unavailable | 916,953 | 13:55 – 14:11 UTC |
| Security-reviewer, `ai` — `claude-opus-5-5`/role default, `claude:b930295494525ac958c3689d` | 964,254 | 827,986 | 18,615 | unavailable | 982,869 | 14:04 – 14:33 UTC |

**How the figures were measured:**
- **Orchestrator:** `resource_usage.py report` against the baseline taken before #25 (10:18:47 UTC), less [log 026](026-close-the-route-access-matrix.md)'s orchestrator row, which was measured to 11:03:58. So the row also holds a few minutes of #107's delivery before the sweep began.
- **Subagents:** each row is `resource_usage.py snapshot` of that agent's transcript. Every agent ran only for #67.
- **Spans:** they show the first and last recorded activity and include waits for the shared test database.

Scale: 15 subagents. Each builder was continued across its checkpoints and its repair round, and each reviewer was continued once for its re-check. Repair rounds: 1 on each of #111 to #114, and none on #110. The cutoff is about 14:34 UTC, so the integration check, this log and the final PR updates are not counted. See [token reporting](../../workflow/README.md#token-reporting).

## Requests

- **"do that".** This was the orchestrator's suggestion to start #67 with a read-only sweep that scopes small cleanup PRs.
- **Ready and list.** "mark prs ready for review after u are done, and send me the list of prs for my teammate to approve".

## Agent runs

- **Orchestrator.**
  - **Sweep:** ran three read-only sweep agents, then grouped their findings into five behaviour-preserving slices, recorded in the [sweep plan](../../workflow/plans/67-cleanup-sweep.md) on #110. Findings that would change behaviour were held for the human.
  - **Branches:** gave each slice its own worktree from `045c33c` (`relay-67-docs`, `-accounts`, `-rounds`, `-ai`; the main checkout for test helpers).
  - **Shared database:** handed the one test database to one builder at a time.
  - **Delivery:** committed and pushed each checkpoint after a scope check, ran the reviews on frozen candidates, opened the draft PRs, and marked each ready once its reviews were clean and CI had passed.
  - **Own edits:** the README and product-site edits (with `maintain-docs`), plus a few summary-only plan and docstring fixes after review. Each is committed without an `Agent:` trailer.
- **Sweep agents** (general-purpose, read-only, on `045c33c`):
  - **Findings:** 16 in `rounds` and `ai`, 14 in accounts, settings and scripts, and tests and guides each.
  - **Coverage:** every checkable criterion has a marked test except PLT-2.6, and the User Guide matches the product.
  - **Isolation:** no authorization or workspace-isolation defect was found beyond `delete_criterion`'s link check, already known from #25.
- **#110, stale text** (Fast lane, [sweep plan](../../workflow/plans/67-cleanup-sweep.md)):
  - **Builder:** spec status text, the Developer Guide's status notes, a dead lint ignore and `src/.gitkeep`.
  - **Orchestrator:** the README and `docs/index.md`.
  - **Review:** human diff review is pending.
- **#111, test helpers** (Standard, [plan](../../workflow/plans/67-test-helpers.md)):
  - **Change:** one home for each duplicated helper, one primary-key-ordered snapshot of every `rounds` model, an e2e `sign_in` fixture, and two weak drafting tests replaced by the stronger ones that already covered them.
  - **Evidence:** a mutation shows the new snapshot catches a `Build` row the old helper missed.
  - **Verifier, on `045c33c..f80de41`:** 0 High, 0 Medium, 2 Low, 2 Nit. The repair moved the remaining inline copies onto the helpers; the re-check of `f80de41..979c19a` was clean.
- **#112, accounts and settings tidy** (High, [plan](../../workflow/plans/67-accounts-tidy.md)):
  - **Change:** the coordinator home as a plain view; the session expiry read from `SESSION_COOKIE_AGE`; `LOGIN_URL` and `BASE_DIR` removed; the dotenv and allowed-hosts checks simplified.
  - **Verifier, on `045c33c..de92041`:** 1 Low (the size record) and 3 Nit.
  - **Security reviewer:** 1 Nit.
  - **Repair:** text only. Both re-checks flagged one docstring word, which the orchestrator reworded (`d992718`).
  - **Security-reviewed range:** `045c33c..86c6b62`.
- **#113, `rounds` tidy** (High, [plan](../../workflow/plans/67-rounds-tidy.md)):
  - **Change:**
    - a typed `StateConflict`;
    - one `available_rounds`;
    - one round-scoped helper for cases and builds, shared by the tester round page and the coordinator results page;
    - `form_page` for every round form;
    - form limits read from the model fields.
  - **Test additions:** two template assertions, because without them two mutations of the conflict page survived.
  - **Verifier, on `045c33c..10ea124`:** 3 Low, including an untested back link, now asserted.
  - **Security reviewer:** 1 Nit and 1 Info. Its re-check found both callers of the shared helper guarded independently.
  - **Wording:** the orchestrator fixed the verifier's last three wording nits.
  - **Security-reviewed range:** `045c33c..7f610ae`.
- **#114, AI tidy** (High, [plan](../../workflow/plans/67-ai-tidy.md)):
  - **Change:**
    - the drafting view split, with a `@sensitive_variables()` `_suggest` helper;
    - the drafting form built on `RecordForm`;
    - shared strict reply decoding and gateway configuration, renamed `_configured()` after review;
    - two redundant checks removed.
  - **New tests:** 7 parser cases, which also pass on the base code.
  - **Verifier, on `045c33c..2025e81`:** 3 Low and 5 Nit.
  - **Security reviewer:** 1 Nit and 4 Info.
  - **Re-checks of `2025e81..935d530`:** clean. The verifier left an Info: the base-code check reported 11 passing tests where 9 were named.
  - **Security-reviewed range:** `045c33c..935d530`.
- **Integration check (orchestrator):** a detached worktree at `main` `505b95d`, which by then included #106, #107 and #109, with all five branches merged in, merged without conflicts. Full verification on it gave Ruff clean, 132 files formatted, and 2756 passed with 231 subtests.
- **Reviewer limits:** reviewers could not run commands. They checked the builders' mutation claims against the code without rerunning them, and the orchestrator supplied Git and check results.

## Decisions and corrections

- **Human decisions:** run #67; mark the PRs ready when done.
- **Orchestrator decisions within that request:**
  - **Slicing:** five slices, keeping behaviour changes out of all of them.
  - **Tiers:** Fast lane for text, Standard for tests only, High for authorization, sessions, isolation and AI.
  - **Shared code:** the drafting form subclasses `RecordForm` without editing it, and the AI slice's only edit to `rounds/services.py` is one constant.
  - **Builders' choices accepted:** keeping the `rounds` builder's template assertions; inlining `BASE_DIR` rather than renaming it.
- **Size estimates:** "about 40/70/115 lines" came from the orchestrator's briefs, not from the human, and each plan now records the measured size against the 400-line budget.
- **Held for the human:**
  - production `LOGGING`, since Django's error records are dropped with `DEBUG` off;
  - the start page's "coming soon" text, which PLT-1.1 fixes;
  - the unused `compose.yaml`, which pins PostgreSQL 18.6;
  - PLT-2.6, which has no marked test;
  - `close_round` not mapping `RoundNotOpen`;
  - `delete_criterion`'s unfiltered link check.
- **Deferred:** splitting `resource_usage.py`'s `collect` until after release.
- **Open, pre-existing:** `_endpoint()` can raise `ValueError` outside `_transport`'s `try` ([AI tidy plan](../../workflow/plans/67-ai-tidy.md)).

## Problems

- **Scope script in worktrees.** `check_scope.py` finds its repository from its own path. The stale-text builder's first scope check, and the orchestrator's first snapshot of that worktree, ran the main checkout's copy. That copy checked the wrong tree and reported "HEAD moved". Both were rerun with the worktree's own script, and each builder used that from then on.
- **Shared test database.** The fixed test database name meant only one builder could run database tests at a time, so builders waited between checkpoints.
- **Commit bundling.** Reviewers noted that `3cc920b`, `504dd3b`, `ab51510` and `f7fda6f` each bundle several independently reviewable changes. They were planned that way, not split afterwards, and are recorded as lessons in their plans.
- **Denied commands.** The builders' `git archive` and an out-of-repo test collection were denied. They used temporary edits instead, restored and hash-checked.
- **Harness flag.** The harness flagged one sweep report for "settings-json" text. It only mentioned the hooks in `.claude/settings.json`, and nothing was acted on.
- **Untrusted content.** None acted on. Issue #67's text, code comments and test payloads were treated as data.

This log has not been checked by its human author.
