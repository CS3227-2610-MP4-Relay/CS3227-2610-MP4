# Slice 4: Limit abuse of sign-in and demo workspace creation (#4)

Goal: implement [ACC-3](../specs/product/accounts.md#acc-3-limit-abuse-of-sign-in-and-demo-workspace-creation), the per-address and overall limits on failed sign-ins and demo creations.

Tier: High (abuse limits on authentication and account creation, concurrency, client-address handling). Base: `46e8a86`, branch `4-limit-abuse`, stacked on ACC-2's `3-demo-workspace`, which contains ACC-1. Owner: zheng-jj. Budget: one requirement (ACC-3, 8 existing criteria, none added or changed); at most 400 changed lines under `src/` outside tests and migrations.

## Decisions

Made by the coordinator on 2026-10-27 under the human's (zheng-jj) delegation, "make my decisions for me":

- **Scope:** ACC-3 only: the limit-counter model and its migration (with the overall creation row), client-address keying, counting and checking inside the sign-in and demo-creation transactions in the specified order, the 429 pages, the lock, statement and idle-in-transaction timeouts, and the 503 for any limit read or record failure (ACC-3.7).
- **Not included:** trusted-proxy header settings, CAPTCHA, per-username lockout, cleanup or expiry of limit rows, production deploy and the release-gate verification itself (#5, Whimsyturtle; see below).
- **Tests:** ACC-3.6 and ACC-3.8 are PostgreSQL threaded tests (`django_db(transaction=True)`, a `threading.Barrier`, one connection per thread); time is controlled with `unittest.mock`; no new dependency.
- **Demo pre-check** (from the ACC-2 security review): `/demo/` reads both creation counts without locking before generating and hashing passwords and refuses early with the ACC-3.4 429; the locked re-check in the transaction stays, so ACC-3.6 holds. Both 429s are returned outside ACC-2's generic `except Exception` handler, and tests assert status 429 for each.

Builder's spec details within that scope (checkpoint 1), confirmed by the coordinator on 2026-10-27 under the delegation (the narrowed 503 sentence, the IPv4-mapped rule, the timeouts with a function limit of at least 30 s, and the two 429 messages in the User Guide at checkpoint 4; also catching `django.db.Error` in sign-in, one insert-or-lock statement for all scopes, `serialized_rollback=True` where needed, no `Retry-After`):

- Model, limit service contract, timeouts (lock 5 s, statement 10 s, idle in transaction 10 s, set per transaction with `set_config(..., true)`), window rules and client keying under [Accounts and workspaces](../specs/TECHNICAL-SPEC.md#accounts-and-workspaces). An IPv4-mapped IPv6 address counts as its IPv4 address, so a dual-stack server does not put every IPv4 client in one `/64`.
- "A refused sign-in does not extend its window": refused requests change no count or window start, and only a counted request after a window has ended restarts it. The lock statement inserts a missing row with count 0 or locks an existing row unchanged.
- The same insert-or-lock statement serves all three scopes; the migration still creates the `demo-total` row. A transactional test's flush therefore cannot break later creations.
- Sign-in (as changed in repair round 1) reads its count unlocked, then validates and authenticates outside any lock, then locks, re-checks and records a failure in one transaction, and starts the session only after it commits, so a 503 signs no one in. Any `django.db.Error` there (and in the pre-check) gives the 503; non-database exceptions in sign-in remain PLT-1.3's 500. Storage failures outside limited transactions (sign-out, role homes, the session write after a successful sign-in) remain the 500: the accounts-routes sentence that said every storage failure gives the 503 is narrowed to match ACC-3.7.
- Page text: the limited sign-in is the sign-in page ("Sign in") with status 429 and the ACC-3.1 message in place of the failure message; the limited creation renders `429.html` with only its message as heading ([ACC-3](../specs/product/accounts.md#acc-3-limit-abuse-of-sign-in-and-demo-workspace-creation)). No `Retry-After` header.

## Checkpoints

1. **Specs and plan** (`spec:`/`plan:`): `workflow/specs/product/accounts.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`, this plan. Check: `git diff --check`; read changed sections back.
2. **Counter model, migration, keying and limit service** (`feat:`): `src/accounts/models.py` (`LimitCounter`), `src/accounts/migrations/0002_*.py` (model plus `RunPython` creating the `demo-total` row), `src/accounts/limits.py` (`client_key`, `peek`, `start`, `lock`, `reached`, `record`, the three limits), `src/accounts/tests/test_limits.py`. Tests: ACC-3.5 keying (same IPv4 same key; different IPv4 or different `/64` differ; same `/64` same key; IPv4-mapped equals IPv4; missing, empty and unparseable all give one key; `X-Forwarded-For` ignored; the key is 64 hex characters and contains no address), ACC-3.2 windows (just before the end reached, at and after the end not reached; recording after the end restarts at 1), ACC-3.3 (`lock` leaves window start and count unchanged; `peek` on a missing row is 0 and writes nothing), the migration row exists, `start()` sets the three timeouts (checked with `SHOW` inside the transaction). Red first: run them before `limits.py` and the model exist. Checks: `pytest src/accounts/tests/test_limits.py -q`, `python src/manage.py makemigrations --check --settings=relay.settings.test`, `ruff check src && ruff format --check src`.
3. **Wiring, 429 pages, timeouts and 503** (`feat:`): `src/accounts/views.py` (`sign_in`: atomic block, `start`, `lock`, `reached` → 429, form and authenticate, `record` on failure, login after commit, `django.db.Error` → 503; `create_demo`: pre-check with `peek` → 429, hash, atomic block with `start`, `lock` per-address then overall, re-check → 429, create, render, `record` both), `src/relay/templates/429.html`, `src/accounts/tests/test_limit_views.py`. Tests marked by criterion:
   - ACC-3.1: 29 then 30 failures give the normal message (200); the 31st request, wrong and then correct password, gets 429 with the message and does not sign in; varied usernames.
   - ACC-3.2: sign-in at 15 min minus 1 s refused, at 15 min checked normally; creation at 1 h and overall at 24 h, just before and at the end.
   - ACC-3.3: blank fields count; a success neither counts nor resets; 429, 403 (CSRF) and 503 requests count nothing; a refused sign-in leaves the window start unchanged (so the window ends on time); a failed creation (forced storage or render failure) counts nothing; GET `/sign-in/` is never limited.
   - ACC-3.4: 10th creation from one address succeeds, 11th gets 429 and creates nothing; overall 200th succeeds and 201st gets 429 from a new address; both the pre-check and the in-transaction re-check (pre-check patched to pass) return 429, not 503, and hash no password on the pre-check path.
   - ACC-3.5: varied usernames and forged `X-Forwarded-For` do not escape; a limited address does not limit another; requests without `REMOTE_ADDR` share the `unknown` count.
   - ACC-3.6 (threaded, `transaction=True`): with 2 creations left, 5 simultaneous requests create at most 2 workspaces, the rest get 429.
   - ACC-3.7: `peek`, `lock` and `record` raising `OperationalError`, and a real lock timeout (another connection holds the row; the timeout constant patched short), each give the 503 for sign-in and creation, sign no one in, create nothing and record nothing.
   - ACC-3.8 (threaded): with 1 failure left, 5 simultaneous wrong-password sign-ins give at most 1 normal failure and the rest 429.
   Red first: run them before the views change. Checks: focused `pytest src/accounts -q`, then full verification (serialised with other builders on the shared test PostgreSQL).
4. **Guides and status** (`docs:`): `docs/DeveloperGuide.md` (design note on `limits.py`, the timeouts and the threaded tests), the opening status sentences of `accounts.md`, `TECHNICAL-SPEC.md` and `SECURITY-SPEC.md`. `docs/UserGuide.md`: the two 429 messages in the product's exact words (confirmed; the [accounts-spec](accounts-spec.md) exclusion applied only to that spec-only PR). Check: read back; `git diff --check`; builder scope check.

Repairs after review are separate `fix:` commits.

## Size estimate

Non-test, non-migration `src/` lines: model ~20, `limits.py` ~85, views ~45, `429.html` ~5; about 155 of 400. The migration is about 40 lines. Reported again with real numbers at checkpoints 2 and 3.

## What #5's release gate must verify

- `REMOTE_ADDR` on Vercel is the real client address (not a proxy address shared by all clients, and not missing, which would put everyone in `unknown`); if not, a trusted-proxy setting is a separate decision.
- The function time limit is at least 30 seconds (the lock and idle timeouts plus a password hash), as stated under [Release verification](../specs/TECHNICAL-SPEC.md#release-verification).
- The production database role may set `lock_timeout`, `statement_timeout` and `idle_in_transaction_session_timeout` per transaction, and the `demo-total` row exists after migrating.
- The client-address source by observation: from two external clients, forged `X-Forwarded-For`, `X-Real-IP` and `Forwarded` headers leave each stored key following the real address, and no production request uses the `unknown` key.
- The production database's connection limit and pooler mode are recorded.
- Optional logging of refusals and of the `unknown` key is deferred to #5.
- ACC-2 is not deployed to production without ACC-3.

## Open issues

- Resolved (coordinator, 2026-10-27): the builder's spec details above.
- ACC-2's repair round 1 changes `views.py`, `demo.py`, the Creation bullet and the delivery-order sentence; the coordinator merges it into this branch before checkpoint 3.
- Transactional tests flush the database, which deletes the migration's `demo-total` row; `lock` recreates it with count 0, and no test relies on it surviving a flush. `serialized_rollback=True` is not used anywhere (coordinator, 2026-10-27): mixed with other suites' non-serialised transactional tests, its reload collided on `django_content_type`.
- Idle-in-transaction timeouts set with `SET LOCAL` persist to the end of a `TestCase` test's outer transaction; a test idle for over 10 s between queries would lose its connection.
- After an idle timeout kills the connection, the 503 page must still render; repair round 1 added real idle- and statement-timeout tests for this (round 0 found the earlier claim untested).
- PostgreSQL 17's `transaction_timeout` was considered and not adopted: the statement and idle timeouts already guarantee that a lock is released.
- Human review and merge remain pending.

## Checklist

- [x] Checkpoint 1: specs and plan.
- [x] Checkpoint 2: model, migration, keying, limit service and tests (red evidence first). Red: `test_limits.py` failed to import (`accounts.limits` missing). Green: 27 passed; full verification 217 passed, 1 skipped, 85 subtests passed; Ruff clean; `makemigrations --check` clean. 138 of 400 budget lines (`models.py` +23, `limits.py` 115); migration 42 lines. The guards in `start` and `lock` refuse to run outside a transaction, where a lock would be released at once.
- [x] Checkpoint 3: views, 429 pages, timeouts, 503 and criterion tests incl. threaded ones (red evidence first). Red: `test_limit_views.py` 28 failed, 5 passed (no 429s, no 503 on limit failures, threaded runs all 200; the 5 passing tests check that refusals and other addresses are not limited, which already held). Green: 159 passed in `src/accounts`; threaded and lock-timeout tests passed 5 runs in a row; full verification twice, 255 passed, 1 skipped, 85 subtests passed. `create_demo` uses `@sensitive_variables()` as in ACC-2 round 2; password hashing sits inside the 503 handler with the pre-check and creation block (spec sentence updated). 228 of 400 budget lines since `11d7649`.
- [x] Checkpoint 4: guides (User Guide's two 429 messages; Developer Guide's `limits.py`, timeouts and threaded PostgreSQL tests), the opening status sentences of `accounts.md`, `TECHNICAL-SPEC.md` and `SECURITY-SPEC.md`, and a separate fix to the comment above `create_demo`'s `@sensitive_variables()`.
- [x] Full verification, size budget and builder scope check (checkpoint 4, Windows, on `39d40d3` plus the checkpoint 4 edits): `manage.py check` and `makemigrations --check` clean; Ruff clean; 256 passed, 1 skipped, 85 subtests passed. `git diff --check` clean; `check_scope.py builder --base 39d40d3` clean. Budget: 228 of 400 lines since ACC-2's head `b1d0397` (211 insertions, 17 deletions).
- [x] Review round 0 on `f3db310`: verifier 2 Medium, 4 Low, Info; security-reviewer 0 Critical/High/Medium, 6 Low, 4 Info (the ACC-2 Medium, hashing before the limit, verified fixed).
- [x] Repair round 1 (coordinator decisions, 2026-10-27, under the delegation):
  - Sign-in hashed under its address's lock (verifier Medium): sign-in now peeks unlocked first (429 without validating or hashing), authenticates outside any lock, then locks, re-checks (429 even for a correct password) and records a failure in one transaction. Specs updated (`/sign-in/` row, Limited transactions, Limit service, security controls).
  - User Guide: "Successful sign-ins do not add to this count and do not reset it."
  - Real timeout tests (`transaction=True`): idle-in-transaction and statement timeouts patched to 100 ms, with a sleep or `pg_sleep(0.5)` inside the limited transaction, for a wrong password, a correct password and `/demo/`; each gives the 503 with no session, no counter change, the timeout reason logged and no password logged.
  - New tests: a failing `generate_passwords`, a render failure and a commit failure on `/demo/` give the 503 and count nothing; the locked re-check refusal leaves counts unchanged; a limited sign-in never calls `authenticate`; a correct password racing to the limit gets 429 from the locked re-check; the password is checked outside any transaction; the migration test re-runs the forward function after deleting the row, so it no longer depends on test order. The threaded tests pause 0.1 s under the lock to widen any race.
  - Developer Guide links to the Limit service bullet for the timeout values.
  - Security residuals and gates: the multi-address cost of the overall cap and of spread sign-in guessing, the unlocked pre-check burst, unlimited successful sign-ins, `SECRET_KEY` rotation; the release gate adds the observed client-address check and the database connection limit and pooler mode; the sign-in 503 log says "Sign-in failed in storage."
  - Red: on the pre-repair `views.py` (swapped in temporarily, then restored and compared), 2 failed, 170 passed: the racing correct-password test (`authenticate` never called) and the outside-a-transaction test. The other new tests pass on the old code because they cover behaviour it already had (refusal before authentication, 503 on timeouts and generation, render or commit failures).
  - Mutation evidence (temporary edits to `limits.py`, restored and confirmed identical with `cmp`): (i) `lock` as `ON CONFLICT DO NOTHING` plus a plain `SELECT` (no row lock): the threaded ACC-3.6 and ACC-3.8 tests failed in 5 of 5 runs each; (ii) `start` as a no-op: both lock-timeout tests, all six idle/statement timeout tests and `test_start_sets_the_transaction_timeouts` failed (9 failed, 1 passed).
  - Green: full verification twice under one lock: `manage.py check` and `makemigrations --check` clean, Ruff clean, 268 passed, 1 skipped, 85 subtests passed (both runs). `git diff --check` clean; `check_scope.py builder --base f3db310` clean. Budget: 233 of 400 lines since `b1d0397` (216 insertions, 17 deletions).
- [x] Re-review of repair round 1 on `59795e6`: security-reviewer all resolved, 1 Info; verifier all resolved, 3 Low, 2 Info. Both agree ACC-3.1, 3.3 and 3.8 hold under the new sign-in order. Info 5 (commit granularity) is noted; history is not rewritten.
- [x] Repair round 2, the last (coordinator decisions, 2026-10-27, under the delegation): the sign-in 503 sentence now covers the pre-check through the transaction, authentication included, and the accounts-routes 503 sentence matches it; the security residual states the real pre-check bound (a burst sent below the limit all hashes, bounded only by how many requests arrive before the count fills); the sign-in storage-failure test adds `peek`; the migration test also asserts that `0002_limit_counter` runs `create_overall_row` through `RunPython`. Both new test assertions pass on the current code, which already behaved this way, so there was no red run; they guard against regressions. Full verification under one lock: `manage.py check` and `makemigrations --check` clean, Ruff clean, 269 passed, 1 skipped, 85 subtests passed. `git diff --check` clean; `check_scope.py builder --base 59795e6` clean. No `src/` change outside tests, so the budget stays 233 of 400.
- [ ] Human review and merge.
