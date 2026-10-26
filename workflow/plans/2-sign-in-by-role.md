# Slice 2: Sign in and out by role (#2)

Goal: implement [ACC-1](../specs/product/accounts.md#acc-1-sign-in-and-out-by-role) and the changed [PLT-1.1](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification) start-page link.

Tier: High (sign-in, passwords, sessions, role permissions). Base: `9fe329a`, branch `2-sign-in-by-role`. Owner: zheng-jj. Budget: one requirement (ACC-1, 8 existing criteria) plus the PLT-1.1 text change; at most 400 changed lines under `src/` outside tests and migrations.

## Decisions

Made by the coordinator on 2026-10-26 under the human's (zheng-jj) explicit delegation, "make my decisions for me"; the human confirmed the request and tier.

- **Persistence and retention** (the precondition in [accounts-spec](accounts-spec.md#open-questions)): recorded under [Data model](../specs/TECHNICAL-SPEC.md#data-model). Records are kept for the life of the course deployment with no automatic deletion or cleanup subsystem; expired sessions are refused by expiry, not deleted; a write that fails on full storage rolls back and gets the route's existing 500/503 page, never deleting or overwriting records; an operator checks storage use before peer testing. The matching [security residual risks](../specs/SECURITY-SPEC.md#sign-in-and-access-control) now read as accepted.
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

- CSRF refusals: Django's default non-debug CSRF failure page (403) or the ACC-1.4 403 template via `CSRF_FAILURE_VIEW`; a routine choice at checkpoint 3, both meet ACC-1.8.
- PLT-1.1 test expectation changes from "no account actions" to the "Sign in" link; listed for the verifier at checkpoint 3.
- From [accounts-spec](accounts-spec.md#notes-for-the-code-slices) for Whimsyturtle: production settings and their release check stay with #5.
- Human review and merge remain pending.

## Checklist

- [x] Checkpoint 1: specs and plan.
- [ ] Checkpoint 2: models, settings, migrations, model tests.
- [ ] Checkpoint 3: views and ACC-1/PLT-1.1 tests (red evidence first).
- [ ] Checkpoint 4: guides.
- [ ] Full verification, size budget and `check_scope.py builder --base 9fe329a`.
