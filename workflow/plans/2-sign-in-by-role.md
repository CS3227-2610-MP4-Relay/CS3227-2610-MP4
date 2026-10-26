# Slice 2: Sign in and out by role (#2)

Goal: implement [ACC-1](../specs/product/accounts.md#acc-1-sign-in-and-out-by-role) and the changed [PLT-1.1](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification) start-page link.

Tier: High (sign-in, passwords, sessions, role permissions). Base: `9fe329a`, branch `2-sign-in-by-role`. Owner: zheng-jj. Budget: one requirement (ACC-1, 8 existing criteria) plus the PLT-1.1 text change; at most 400 changed lines under `src/` outside tests and migrations.

## Decisions

Made by the coordinator on 2026-10-26 under the human's (zheng-jj) explicit delegation, "make my decisions for me"; the human confirmed the request and tier.

- **Persistence and retention** (the precondition in [accounts-spec](accounts-spec.md#open-questions)): recorded under [Data model](../specs/TECHNICAL-SPEC.md#data-model). The matching [security residual risks](../specs/SECURITY-SPEC.md#sign-in-and-access-control) now read as accepted.
- **Start page:** PLT-1.1 keeps its ID; `/` gains a "Sign in" link to `/sign-in/`. ACC-2 later adds "Create a demo workspace" and the signed-in redirect.
- **Scope:** ACC-1 only. Custom user model and workspace model (no admin, staff, superuser or permission fields), sign-in, POST-only sign-out, two role homes, the 403 page, database sessions with an absolute 8-hour expiry and a new identifier at every sign-in, CSRF/`Origin` checks, cookie settings and the start-page link. Not included: demo creation and the 503 page (ACC-2), the shared workspace-lookup helper (ACC-2.4), abuse limits (ACC-3), production settings and deploy (#5). Tests create workspaces and users directly. Anything else returns `needs-decision`.

Builder's spec details within that scope (checkpoint 1): `accounts` app in `src/accounts/` with Django's `auth`, `contenttypes`, `sessions` and `messages` apps; account→workspace `PROTECT`; sign-in page title "Sign in"; "You have signed out." carried through Django's messages; signed-out redirects to `/sign-in/` without `next`; `Secure` cookies in shared settings, off in local settings; until ACC-2/ACC-3, an accounts-route storage failure gives PLT-1.3's generic 500.

## Checkpoints

1. **Specs and plan** (this commit, `spec:`/`plan:`): `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`, `workflow/specs/product/platform.md`, this plan. Check: `git diff --check`; read changed sections back.
2. **Models and settings** (`feat:`): `src/accounts/{__init__,apps,models}.py`, `src/accounts/migrations/`, `src/relay/settings/{base,local}.py` (apps, `AUTH_USER_MODEL`, session/auth/messages middleware and context processor, cookie flags, DB session engine), `src/accounts/tests/test_models.py`. User: `AbstractBaseUser` with `BaseUserManager`, unique username, workspace FK, role choices; no `PermissionsMixin`. Checks: `python src/manage.py makemigrations --check --settings=relay.settings.test`, `python src/manage.py check --settings=relay.settings.test`, `pytest src/accounts -q`, existing `pytest src/relay_tests -q` (settings tests may need updated expectations; list any).
3. **Sign-in, sign-out, role homes, 403, start-page link** (`feat:`): `src/accounts/{forms,views,urls}.py`, `src/accounts/templates/accounts/*.html`, `src/relay/templates/{home,403}.html`, `src/relay/urls.py`, `src/accounts/tests/test_sign_in.py`, `src/relay_tests/test_pages.py` (PLT-1.1). Sign-in uses `authenticate`/`login` (which cycles the key), then `set_expiry(now + 8 h)`; sign-out is `require_POST` + `logout`. Red first: run the new ACC-1.1–1.8 and PLT-1.1 tests before the views exist and record the failures. Time control with `unittest.mock` (ACC-1.6 just before/at/after 8 h, with a session write in between). ACC-1.8 uses `Client(enforce_csrf_checks=True)`, missing/invalid token and a foreign `Origin`. Checks: focused `pytest src/accounts src/relay_tests/test_pages.py -q`, then full verification.
4. **Guides** (`docs:`): `docs/UserGuide.md` (start-page link, sign-in, sign-out, role homes in the product's exact words), `docs/DeveloperGuide.md` (accounts app, migrations, settings). Check: read back; `git diff --check`.

Repairs after review are separate `fix:` commits.

## Size estimate

Non-test, non-migration `src/` lines: models/apps ~60, settings ~25, forms/views/urls ~110, templates ~90, start-page link ~3; about 290 of 400. Reported again with real numbers at checkpoints 2 and 3.

## Open issues

- Resolved (coordinator, checkpoint 2 review): CSRF refusals use the ACC-1.4 `403.html` through `CSRF_FAILURE_VIEW`.
- Resolved (coordinator, checkpoint 3): `relay.settings.test` uses Django's MD5 hasher, because the default hasher made the focused tests take 46 s instead of 2 s; shared and local settings keep Django's default.
- Checkpoint 3 finding: Django's `login()` keeps the session identifier when the same user signs in again, so sign-in calls `cycle_key()` first (ACC-1.7, caught by its test).
- PLT-1.1 test expectation changed (checkpoint 3): "no `<a `" became "exactly one link, `<a href="/sign-in/">Sign in</a>`"; the no-form assertion stays. For the verifier.
- From [accounts-spec](accounts-spec.md#notes-for-the-code-slices) for Whimsyturtle: production settings and their release check stay with #5.
- For #5 (Whimsyturtle), from the repair-round-1 review; no ACC-1 code: HTTPS detection through the verified forwarded-protocol header (`SECURE_PROXY_SSL_HEADER`); frame blocking; `Cache-Control: private, no-store` on `/coordinator/` and `/tester/`; `LOGIN_URL` is set but unused, because the role homes redirect explicitly.
- Human review and merge remain pending.

## Checklist

- [x] Checkpoint 1: specs and plan.
- [x] Checkpoint 2: models, settings, migrations, model tests.
- [x] Checkpoint 3: views and ACC-1/PLT-1.1 tests (red evidence first).
- [x] Checkpoint 4: guides.
- [x] Full verification, size budget and builder scope check (checkpoint 4, Windows): 147 passed, 1 skipped; 232 of 400 budget lines since `9fe329a`; scope clean against the coordinator's snapshot `0b6ecf9`.
- [x] Independent verifier and security review of `9dc41a7`: no High, two Medium, several Low.
- [x] Repair round 1 (separate units): spec wording; sign-in form validation (NUL gave 500), no `required` attributes, sensitive password and `never_cache`, stronger ACC-1.2 test; hasher guard and real-response tests (cookie flags, HTTPS `Origin`/`Referer`); these #5 notes.
- [ ] Re-review of repair round 1; human review and merge.
