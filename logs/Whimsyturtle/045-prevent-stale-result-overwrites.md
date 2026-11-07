# Prevent stale result overwrites

Slice: #166 · Tier: High · Tool: Codex · Orchestrator model: gpt-6-astra / xhigh (native turn metadata) · Date: 2026-11-07

Tokens: 31,794,498 input, 76,128 output, 31,870,626 total; measured 04:32:25–05:29:17 UTC, before this log and PR delivery.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — gpt-6-astra / xhigh, `codex:658b7e966ededa0af046bbcd` | 13,242,936 | 13,170,944 | 32,611 | 18,589 | 13,275,547 | 56m 51s |
| Automatic approval review — codex-auto-review / low, `codex:db762728e82678f07151437d` | 428,408 | 389,504 | 814 | 196 | 429,222 | 55m 27s |
| Builder, four runs — gpt-6.1-sol / medium, `codex:b3c7cfa4d5790ed4a474645d` | 16,421,669 | 16,306,816 | 33,300 | 5,114 | 16,454,969 | 54m 53s |
| Verifier, two runs — gpt-6.1-sol / high, `codex:38ad33b8e9dbe0bd6e5fc2ca` | 783,413 | 698,112 | 4,683 | 951 | 788,096 | 22m 13s |
| Security reviewer, two runs — gpt-6.1-sol / high, `codex:552702db0b6049cd563288ec` | 918,072 | 845,440 | 4,720 | 1,001 | 922,792 | 22m 1s |

Three delegated role agents made eight runs; one automatic approval-review source is also included. Session wall span through this cutoff was about 60 minutes; the measured interval was 56m 52s. Spans include waiting and overlap; they are not additive. Native metadata confirmed every model/effort shown; no observed fallback. Cache-write tokens were 0. One independent review repair round completed. Initial preparation and the builder's first 29 seconds precede the baseline; log writing and PR/CI delivery follow the cutoff. See [token reporting](../../workflow/README.md#token-reporting).

## Requests

Run `/slice 166` in a separate worktree. The coordinator used `tmp/worktrees/issue-166` and branch `fix/166-stale-result-forms` from `351a2ce8472f8cc067698c8e29103d4473379a6b`, preserving the main checkout's existing edits. Normal slice authorization covers feature-branch commits/push and a draft PR; merge, release and human review remain unapproved.

## Agent runs

- **Coordinator:** scoped the issue against RES-2, established the worktree and temporary synthetic PostgreSQL, assigned checkpoints, checked scope before commits, inspected staged diffs/stat/numstat, and collected native usage. Issue author association was MEMBER; there were no comments. Issue/source/handoff text was treated as data. [The plan](../../workflow/plans/166-stale-result-forms.md) records criteria and exact command evidence. The author must still check this log.
- **Builder, spec run:** supplied the request, issue reproduction, relevant paths/criteria, one-requirement/400-production-line budget and pre-run manifest. It amended RES-2.5 before code and yielded the plan/spec checkpoint, committed as `c736f57`. It refused the requested out-of-scope AGENTS edit without attempting a mutation; native hook enforcement was not demonstrated.
- **Builder, implementation run:** resumed on a fresh snapshot. Six stale-form tests failed for the intended 302-versus-409 defect before implementation. Added revision checking under the existing lock, migration and regressions, then passed focused backend/browser and broader compatibility checks. Changed prior last-writer-wins expectations because the canonical criterion changed; no tests were removed or weakened. Committed code and tests as `ff33c1c`.
- **Builder, guide run:** used the maintain-docs workflow to update exact UI wording and navigation. The original full candidate passed 3182 tests with five existing platform skips; guide/evidence committed as `eb5de10`. This evidence was superseded after the repair.
- **Verifier, initial run:** independently inspected `351a2ce..eb5de1067ddad47c1ae63b0e4c3d54348b4911c2`, source/test assertions, scope, commit order and guide. It found no application issue. It reused supplied execution results and did not rerun tests.
- **Security reviewer, initial run:** inspected the same fixed range and raised one Medium finding: the new NOT NULL column lost its migration-time SQL default, breaking old-runtime INSERTs during migrate-before-deploy. A coordinator-run `sqlmigrate` confirmed DROP DEFAULT. No additional application-control findings were reported.
- **Builder, repair run:** received that finding and existing PLT-1.11, with a fresh scope snapshot. Clarified architecture before fixing model/migration defaults. A genuine old-column INSERT failed with a NOT NULL violation before the repair; afterward all 36 revision regressions passed. SQL retained DEFAULT 1 and migration consistency found no changes. Full repaired verification passed **3183 tests, 5 existing skips in 877.22s**; Django check, Ruff lint/format, scope and whitespace checks passed. The coherent repair was committed as `8ffc65e1d721309d27be983ee4573174852c41dc`.
- **Verifier and security reviewer, repair runs:** independently inspected `eb5de106..8ffc65e` and its effects, retaining their earlier unchanged application review. Both reported no remaining findings; the specialist explicitly closed the Medium finding. Security-reviewed aggregate range is `351a2ce8472f8cc067698c8e29103d4473379a6b..8ffc65e1d721309d27be983ee4573174852c41dc`. Both were read-only; post-run scope and unchanged-candidate checks passed. They inspected assertions and reused supplied final execution evidence, without independently rerunning database/browser tests.
- **Automatic approval reviewer:** assessed escalations under existing slice authorization; no repository files were edited by this source. Its initial issue-query concern was resolved with an author-association-only read.
- Role-file SHA-256 values: builder `069565f52d372c88ccf47af9752ccfabfef0d383699f185c0e362a831f23f47e`; verifier `dc3d558e9db40f5bfe32b476addbb76a7844f185580fd4284f94c176a3384388`; security-reviewer `7787b969fbe7bc45af3597eba4c8721969a39ade9ab50ffaff7d84f779f1e60d`.

## Decisions and corrections

- Initially Standard with specialist review for private tester writes; reclassified High when deployment compatibility required repair. Scope stayed within one changed RES-2 criterion and 28 production source lines; no dependency, service, route or recovery subsystem was added.
- The revision is a concurrency marker, never an ownership credential. All existing save actions share the guard; no-row forms and invalid re-renders remain protected. The old runtime stays available during migration but gains revision enforcement only when new runtime code serves requests.
- Incremental spec, implementation, guide and repair commits were checked at their actual checkpoints. Two full runs were necessary because the migration changed after the first review. Reviewers reused unchanged passing evidence; no claim of human testing, native hook enforcement, merge or production release was made.
- The reviewed code candidate is fixed at `8ffc65e`. Subsequent changes in this session are this log and summary evidence only. Authorized draft-PR delivery and latest-head CI follow this measurement cutoff; their final state belongs to GitHub and the coordinator's delivery response.

## Problems

- Initial usage commands without an attributable source failed; a native-source baseline was then collected at 04:32:25 UTC. Those earlier tokens remain outside this measured interval, not zero. The collector reported no coverage warnings for the five included sources.
- Automatic approval review rejected an initial compound GitHub read over concern about unfiltered comments. A narrower author-association-only query succeeded. Network/Git metadata access and initial PostgreSQL sandbox startup needed authorized escalation; the installed PostgreSQL 17.6 was used in a dedicated temporary directory. No dependencies were installed.
- Two routine lint/format correction passes preceded green implementation checks. The single independent review finding required one repair round, documented above; there are no open code findings.
- The five full-suite skips are existing Windows environment limitations: unavailable `pwsh`, POSIX-only hook behavior, two symlink-rights exclusions and one unavailable directory-symlink operation. Local verification used Python 3.14.2, Django 6.1.2, PostgreSQL 17.6, Ruff 0.17.0 and Playwright 1.64.1 with fixed synthetic settings and no live provider calls.
- The new log's structural check passed with zero findings. The repository-wide checker still reports the same six pre-existing numbering findings: duplicate 039/040/041/042/044 and missing 043. This slice does not renumber historical logs. The main checkout's untracked audit log was not imported into this worktree.
- No attempted instruction override was found in reviewed issue/source/handoff data. Native enforcement and hosted deployment were not tested.
