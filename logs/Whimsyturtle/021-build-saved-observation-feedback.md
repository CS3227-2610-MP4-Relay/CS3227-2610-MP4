# Build saved observation feedback

Slice: #23 · Tier: High · Tool: Codex · Orchestrator model: GPT-6 family (session instructions; exact execution ID/effort unavailable) · Date: 2026-10-31

Tokens: 21,216,817 input, 71,705 output, 21,288,522 total across selected sources; cutoff 2026-10-31 13:49:48 +08:00.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — exact model/effort unavailable; `codex:cc0145dfd42582a124f4d84c` | 11,728,842 | 11,605,248 | 20,569 | 6,479 | 11,749,411 | 1,660.425 s task window |
| Runtime guardian — model/effort unavailable; `codex:980757a8186e15260da13178` | 1,031,753 | 963,712 | 1,944 | 666 | 1,033,697 | per-source span unavailable |
| Builder — configured GPT-6.1 Sol/medium; `codex:eb10a2893b0c05143aa57aa0` | 6,858,786 | 6,709,120 | 42,249 | 4,783 | 6,901,035 | per-source span unavailable |
| Verifier — configured GPT-6.1 Sol/high; `codex:1a2065cdbcb24c3d91279bba` | 931,488 | 846,592 | 3,823 | 987 | 935,311 | per-source span unavailable |
| Security-reviewer — configured GPT-6.1 Sol/high; `codex:5cdcb349737e3f62486a54f1` | 665,948 | 599,424 | 3,120 | 571 | 669,068 | per-source span unavailable |

Three delegated role sessions plus one runtime guardian were collected with the coordinator. The private baseline/report interval is 13:22:08–13:49:48 +08:00; it excludes initial preparation and later summary/delivery work. All five sources were measured with no collector warnings; cache-write tokens were zero. Role models are adapter configuration, not independently observed execution metadata. Per-source elapsed spans for the aggregate interval are unavailable. Role-local late baselines were not added to these totals. See [accounting definitions](../../workflow/README.md#token-reporting).

## Requests

The human requested `/slice 23`, authorizing a feature branch, incremental commits, push, draft PR and configured validation. Issue 23's author association was verified as MEMBER through `gh`; it points to the planned observation-feedback contract. No merge or production release was authorized.

The IDE selection exposed a credential. The coordinator advised revocation/rotation, did not repeat or use the value, and did not open `.env`. No live provider call was made.

## Agent runs

- **Coordinator:** resolved scope and chose High tier for AI and tester ownership; started from clean `main` at `a8d6da759163da7d6307ae0b491cfb104ea911e0`. Created `feat/23-observation-feedback`, supplied role-specific paths and compact task context, checked every role snapshot and staged checkpoint, and opened [draft PR 95](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/95). Uses slice, maintain-docs, log and create-pull-request skills. Prepared an isolated installed PostgreSQL 17.6 cluster on loopback 55432; existing Python 3.14.2 and Chromium were reused without installation. Django's fixed-test-settings system check passed.
- **Builder:** one session reused for five checkpoints, with the role file at the starting commit and fresh scope snapshots each time. Inputs were the scoped request, relevant RES/AI/technical/security contracts, existing helpers, plan and budget. Produced specs first (`8a80463`), helper/parser plus tests (`a17d210`), route/UI plus tests (`9bae694`), browser journeys (`c463b5e`), and guides/status wording (`60dc348`). All builder scope checks passed. Red-before-code and focused green evidence are in the [plan](../../workflow/plans/23-observation-feedback.md#verification-and-next-steps); browser tests were added after committed runtime behaviour, with the exception justified. The final application diff is 231 additions and one deletion outside tests/migrations, within the 400-line budget. The builder reported three patch retries across checkpoints and one oversized test-title fixture correction; no test assertion was weakened.
- **Verifier:** independently inspected fixed `60dc348ef623be3d952d46eea87db4366efa3617` against the starting commit, the RES-4 criteria, source, test assertions, guides and incremental commit history under the unchanged verifier role. Found no findings requiring repair; confirmed all eight criteria have meaningful coverage. Did not rerun pytest concurrently against the shared database. Scope and candidate-stability checks passed.
- **Security-reviewer:** independently inspected the same candidate/range under the unchanged role, focusing on authorization, source selection and rechecks, schema bounds, injection boundaries, rendering, storage failures and private error handling. No findings within that boundary; scope/stability passed. Direct and coordinator-authored escaped payloads cover markup, direction controls and URLs; malformed schemas and forged IDs have separate tests. Live model obedience/usefulness, production operation and unchanged development/synthetic-secret enforcement were not verified. Neither reviewer claimed independent execution of the supplied tests.
- **Runtime guardian:** metadata identifies a related `guardian` source collected during automatic approval review. No repository implementation responsibility was assigned; its execution model is unavailable.

The review manifest's SHA-256 is `07940c56fbba7e85c8d5c11b3d1db9143d1823cd6e73a02ad4d3d14c1fc455ff`. It stayed unchanged through reviews and full local execution. Review reports initially noted full/hosted checks pending; the coordinator subsequently supplied the actual same-candidate results below. No review repair rounds occurred.

Validation observed:

- Focused parser/drafting: 120 passed. Feedback/parser/access/result regressions: 895 passed; three later changed/new checks passed. Chromium journeys: two passed, including peer isolation, ignored unsaved edits, unchanged stored values and manual save/submission after feedback or AI failure.
- Required local Git Bash/venv command: `ruff check . && ruff format --check . && pytest -q --basetemp="$TEMP/relay-23-full"`. Lint passed and all 121 Python files were formatted. Pytest: **3 failed, 2339 passed, 1 skipped, 231 subtests passed**, two cache-write warnings, in 440.82 seconds. The command did not include skip-reason reporting. Local full verification is not successful.
- Exact local failures: `src/accounts/tests/test_limit_views.py::test_timeout_inside_a_limited_transaction_gives_503[wrong password-idle]`, `[correct password-idle]` and `[demo-idle]`, all at line 564. Expected `idle-in-transaction timeout` was absent; native PostgreSQL/psycopg returned `server closed the connection unexpectedly`. HTTP 503, session and rollback assertions preceding that log-text assertion passed.
- Baseline proof: exported untouched `a8d6da7` with `git archive`, then used the same venv/database with `pytest src/accounts/tests/test_limit_views.py -q -k idle --tb=short --show-capture=no` and a private cache directory. The same three failures reproduced: 3 failed, 43 deselected in 5.10 seconds. No account implementation or test was changed to address them.
- [Hosted CI 217](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/41173597685) on `60dc348` passed `verify` and `site`. Its log reports Django checks, Ruff and format passed, then **2340 passed, 3 skipped in 160.82 seconds**. Deployment jobs were skipped. The summary-only head will be checked after this log is committed; no older run will be substituted for that final result.

## Decisions and corrections

The coordinator chose the narrow saved-draft workflow within the existing planned feature: a separate explicit-request page, transient questions and manual editing. The authoritative behaviour, prompt/schema and controls live in [RES-4](../../workflow/specs/product/results.md#res-4-suggest-missing-details-in-a-draft-observation) and its linked AI contract. No new dependency, service, credential, schema or cache was added.

Live feedback usefulness remains unmeasured. Schema-valid questions may mislead; the UI asks the tester to review them. The draft PR remains for human review, with author-log/manual-review boxes unticked. Merge and release remain human decisions.

## Problems

The connector's normalized issue response omitted author association, so `gh` supplied the MEMBER check. Connector PR creation returned403 `Resource not accessible by integration`; authenticated `gh pr create` completed the authorized action. Sandbox restrictions required elevated Git/database/verification commands. The first native database initialization failed in the sandbox; the first hidden launcher waited on its server tree, so it was stopped and restarted detached. No new software was installed.

The local three-failure result and two pytest cache warnings remain explicit; passing Linux CI does not make local execution green. The unrelated account failures were reproduced, not repaired as part of this slice. No raw transcripts, credential values or private provider text were saved in the repository.

Untrusted content seen: fixed feature instructions and escaped synthetic requests to ignore instructions or change outcomes were handled as application/test data. No issue, source text or review handoff granted extra authority.
