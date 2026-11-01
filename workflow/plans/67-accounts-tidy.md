# Accounts and settings tidy (#67)

Remove dead or duplicated code in the accounts views/URLs/limits and the settings modules without changing observable behaviour.

## Scope and decisions

- High tier (role checks, session expiry, settings); branch `67-accounts-tidy`, base `045c33c`. Behaviour-preserving refactor under existing ACC-1, ACC-3 and PLT-1.4; no spec, criterion, test, dependency or guide change. Budget: the slice's 400 non-test source lines; the sweep's rough estimate of about 40 was not a human-confirmed figure. Measured at `de92041`: non-test source +33/-37 (70 lines touched, 4 fewer overall), well within budget. Any item found to change observable behaviour stops with `needs-decision`.
- **F1 adopt.** `coordinator_home` becomes a plain `@never_cache @require_GET` view with the same body (sign-in redirect, role 403, `rounds/coordinator_home.html` with `title` and `rounds`); `_role_home` and the `tester_home` alias go, `urls.py` routes `tester.home` directly and `views.py` drops `from rounds import tester`. No test or template names `views.tester_home` or `_role_home`; `accounts/home.html` stays, since both role-home templates extend it. Not moved to `rounds.views.coordinator_view`, whose 503 would replace the specified 500 ([Accounts routes](../specs/TECHNICAL-SPEC.md#accounts-routes); `test_coordinator_home_keeps_the_accounts_storage_rule`).
- **F2 adopt.** `limits.py` docstring names all six public functions views call and says `peek` is the unlocked pre-check.
- **F3 adopt.** Module docstrings: `urls.py` also routes the tester round, results, result and feedback pages; `views.py` holds the coordinator home only (the tester home is `rounds.tester.home`).
- **F4 adopt.** Sign-in sets expiry to `timezone.now() + timedelta(seconds=settings.SESSION_COOKIE_AGE)`; `SESSION_LIFETIME` goes (only `views.py` uses it). The `base.py` comment keeps the ACC-1.6 link. The [data model](../specs/TECHNICAL-SPEC.md#data-model) and [accounts and workspaces](../specs/TECHNICAL-SPEC.md#accounts-and-workspaces) sections already tie both lifetimes to 8 hours.
- **F5 adopt.** Drop `LOGIN_URL`: no `login_required`, `redirect_to_login` or auth views are used, and no spec or guide lists it (only historic plan/log notes call it unused).
- **F9 adapt.** Inline the one use: `"DIRS": [Path(__file__).resolve().parents[1] / "templates"]`; `BASE_DIR` is named nowhere else, nor in specs or guides.
- **F10 adopt.** One split via an assignment expression, with a comment that a known name followed by stray text is malformed.
- **F11 adopt.** Drop `not ALLOWED_HOSTS or`: `split(",")` always yields at least one item and `""` already fails the subset check.

## Commit checkpoints

1. **Plan** (`plan:`): this file. Checks: `git diff --check`, builder scope.
2. **Accounts** (`refactor:`, F1-F4): `src/accounts/{views,urls,limits}.py`.
3. **Settings** (`refactor:`, F5, F9-F11): `src/relay/settings/{base,local,dotenv}.py`.

Each code checkpoint: `ruff check .`, `ruff format --check .`, builder scope, collected node IDs unchanged against the 2703-ID baseline, then the guarding tests below unchanged (database tests only once the coordinator frees the test database), then full verification at the end.

## Behaviour guards

Existing tests must pass unchanged; each would fail if its refactor broke the behaviour named.

| Item | Guarding tests | Breakage caught |
| --- | --- | --- |
| F1 | `accounts/tests/test_sign_in.py` (own home 96, other role 403 220, never cached 546, ACC-1.4/1.6/1.7 home requests); `rounds/tests/test_views.py` 91, 113, 500; `accounts/tests/test_demo_views.py` 120; `relay/tests/test_access_matrix.py` (`/coordinator/`, `/tester/` rows incl. 405); `rounds/tests/test_framing.py`; `e2e/test_accounts.py` | wrong route, template, context, role check, method or cache headers, 503 instead of 500 |
| F2, F3 | none (docstrings only); reviewed by diff | n/a |
| F4 | `test_sign_in.py` ACC-1.6 boundary (8h minus 1s, 8h, 8h plus 1s after a 4h session write); `accounts/tests/test_models.py` 105 pins `SESSION_COOKIE_AGE` to 8h | wrong or relative expiry |
| F5, F9 | every rendering test (template `DIRS`); `relay/tests/test_configuration.py` settings probes; access matrix sign-in redirects | missing project templates, changed redirects |
| F10 | `relay/tests/test_dotenv.py` malformed `export SOC_LLM_API_KEY synthetic-sensitive`, unknown-name and valid-line cases | stray-text line accepted, valid line refused |
| F11 | `test_configuration.py` `test_local_settings_reject_invalid_values` (`""`, `*`, mixed hosts) and loopback acceptance | empty or foreign hosts accepted |

Planned mutations, run on a temporary copy and restored from a copy and confirmed byte-identical with `cmp` afterwards:

- F4: add one second to the derived expiry; the ACC-1.6 8-hour case must fail. Then remove `set_expiry`; the 8-hour cases must fail.
- F1: drop the role check; `test_other_role_home_is_forbidden` must fail.
- F10: existing tests do not cover an empty name (`=x`) or an unknown multi-word name; a scratchpad script compares the old and new predicate over those and the tested inputs instead of adding tests.

## Status and next steps

- [x] Checkpoint 1, plan: `32346d4`. Collection baseline 2703 node IDs, captured outside the repository.
- [x] Checkpoint 2, accounts (F1-F4): `504dd3b`, +29/-32 in three files. Guard tests unchanged: `src/accounts`, `rounds/tests/{test_views,test_framing,test_sample_round}.py` and the access matrix, 1038 passed; `e2e/test_accounts.py`, 6 passed. Mutations: expiry plus one second gave 1 failed of the 3 ACC-1.6 cases; no `set_expiry` gave 2 failed; no role check failed `test_other_role_home_is_forbidden`. Each was restored and confirmed byte-identical; collection unchanged.
- [x] Checkpoint 3, settings (F5, F9-F11): `8209d57`, +4/-5 in three files. The F10 predicates agree on 45 inputs (empty and blank names, unknown single and multi-word names, every allowed name alone, with stray text and lower-cased), checked by a script outside the repository. Collection unchanged; full verification `ruff check . && ruff format --check . && pytest`: 2703 passed, 231 subtests passed.
- [x] Plan record: `de92041`.
- [ ] Independent verification and security review of `045c33c..` the final head, then PR delivery (coordinator).
- Open: none.

## Review round 1

- Candidate `045c33c..de92041`. Verifier: 0 High, 0 Medium, 1 Low, 3 Nit, 4 Info. Security reviewer: 0 High, 0 Medium, 0 Low, 1 Nit.
- Fixed (text only, no behaviour change): the measured size against the budget (Low 1); the `views.py` module docstring (Nit 2); the commit for checkpoint 3 (Nit 3); section links instead of spec line numbers (Nit 4); the `base.py` session comment now names `SESSION_COOKIE_AGE` as the expiry (security Nit, verifier Info 5); the mutation-restore note now records the `cmp` check actually used. Re-reviews of `de92041..86c6b62` found nothing above Nit; both flagged "Both" in the new docstring as ambiguous, and the coordinator reworded it to name sign-in and demo creation.
- Not adopted: Info 8, since the Developer Guide accounts paragraph predates this slice; Info 7, on commit bundling, is kept as a lesson for later slices rather than repaired, since existing commits are not rewritten.
