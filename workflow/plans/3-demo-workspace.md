# Slice 3: Create an isolated demo workspace (#3)

Goal: implement [ACC-2](../specs/product/accounts.md#acc-2-create-an-isolated-demo-workspace) and the changed [PLT-1.1](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification) start page.

Tier: High (account creation, passwords, workspace isolation). Base: `9dc41a7`, branch `3-demo-workspace`, stacked on ACC-1's `2-sign-in-by-role`. Owner: zheng-jj. Budget: one requirement (ACC-2, 7 existing criteria) plus the PLT-1.1 text change; at most 400 changed lines under `src/` outside tests and migrations.

## Decisions

Made by the coordinator on 2026-10-27 under the human's (zheng-jj) delegation, "make my decisions for me":

- **Scope:** ACC-2 only: the POST-only `/demo/` route, the start page's "Create a demo workspace" button, the "Your demo workspace" page with `Cache-Control: no-store` rendered inside the creation transaction, generated usernames, suffixes and passwords, the shared workspace lookup helper (ACC-2.4, used only by its tests for now), the 503 page (ACC-2.5) and the signed-in redirect from `/` and `/demo/` (ACC-2.6).
- **Not included:** the sample draft round (RND-7; its slice adds the round inside `create_demo_workspace`, with no placeholder now), the abuse limits (ACC-3, next slice; it adds the counter locks at the start of the creation transaction) and production deploy.
- **PLT-1.1** keeps its ID; the start page has only the "Sign in" link and the "Create a demo workspace" button.
- **Guides:** the User Guide says accounts come from demo workspaces; the Developer Guide's manual-account section points to the button.

Builder's spec details within that scope (checkpoint 1), confirmed by the coordinator on 2026-10-27 under the delegation:

- Page text and layout of "Your demo workspace" in [ACC-2](../specs/product/accounts.md#acc-2-create-an-isolated-demo-workspace), including a "Sign in" link to `/sign-in/`; creation, lookup helper, collision handling and the 503 handling under [Accounts and workspaces](../specs/TECHNICAL-SPEC.md#accounts-and-workspaces).
- Suffix collisions: up to 3 suffix draws checked by query; a final collision or a concurrent race fails on the unique constraint and gives the 503. No savepoint retry loop.
- A `404.html` saying "Page not found." serves every 404, as ACC-2.4 states its text. PLT-1.3 stays generic, but its test's `b"Not Found"` assertion becomes `b"Page not found."` (listed for the verifier).
- Any exception inside the creation block, including a rendering failure, gives the 503 and is logged with its traceback only (confirmed again after checkpoint 3, because ACC-2.5 names rendering failures).
- `/` stays CSRF-exempt so PLT-1.2's 405s are unchanged; checkpoint 3 confirms the button's CSRF token still renders and its cookie is set.
- The Developer Guide's shell recipe is removed: the button now gives the same accounts, so it is not useful.

## Checkpoints

1. **Specs and plan** (`spec:`/`plan:`): `workflow/specs/product/accounts.md`, `workflow/specs/product/platform.md`, `workflow/specs/TECHNICAL-SPEC.md`, this plan. Check: `git diff --check`; read changed sections back.
2. **Creation service and lookup helper** (`feat:`): `src/accounts/demo.py` (`generate_passwords`, suffix/username generation with `secrets`, `create_demo_workspace(hashes)` writing the workspace and 3 accounts with pre-hashed passwords), `src/accounts/workspaces.py` (`workspace_records`), `src/accounts/tests/test_demo.py`, `src/accounts/tests/test_workspaces.py`. Tests: ACC-2.2 (1 coordinator, 2 testers, shared suffix, name format, each password checks against its account), password length 16 and alphabet, ACC-2.3 (no stored field equals a password), collision boundary (2 colliding draws then success; 3 colliding draws raise `IntegrityError`, with existing records unchanged), ACC-2.4 (own record found; another workspace's record and a missing ID both raise `Http404`; a `ModelChoiceField` on the helper's queryset rejects another workspace's ID with "Select a valid choice."; two workspaces share no accounts). Red first: run them before the modules exist. Checks: `pytest src/accounts -q`, `ruff check src && ruff format --check src`.
3. **Routes, start page, templates and 503** (`feat:`): `src/accounts/views.py` (`create_demo`: `require_POST`, signed-in redirect, hash, atomic block, render to string, 503 on any exception), `src/accounts/urls.py`, `src/relay/pages.py` (signed-in redirect, reusing ACC-1's role-home mapping), `src/relay/templates/{home,404,503}.html`, `src/accounts/templates/accounts/demo.html`, `src/accounts/tests/test_demo_views.py`, `src/relay_tests/test_pages.py`. Tests: ACC-2.1 (page text, table order, stays signed out), ACC-2.2 (each credential signs in through `/sign-in/` and the home shows the workspace name), ACC-2.3 (`no-store`; later GETs of `/`, `/sign-in/` and both homes, and captured logs, never show a password), ACC-2.4 (test URLconf route on the helper: another workspace's record and a missing ID give identical "Page not found." 404s), ACC-2.5 (an account write failing after the workspace is written, and rendering failing, each give the 503 text, leave no workspace or account and show no credentials), ACC-2.6 (each role on `/` GET/HEAD and `/demo/` POST with a valid token is redirected to its own home; nothing created), ACC-2.7 (GET 405; missing token, invalid token and foreign `Origin` give 403; nothing created), PLT-1.1 (exactly one link and one form, posting to `/demo/` with the button), PLT-1.2 unchanged, PLT-1.3 404 text. A commit failure is not separately simulated: it raises inside the same `try` as the writes. Red first. Checks: focused `pytest src/accounts src/relay_tests/test_pages.py -q`, then full verification.
4. **Guides** (`docs:`): `docs/UserGuide.md` (start page button, the credentials page in the product's exact words, accounts come from demo workspaces), `docs/DeveloperGuide.md` (manual accounts via the button; design note on `demo.py` and `workspaces.py`). Check: read back; `git diff --check`; builder scope check.

Repairs after review are separate `fix:` commits.

## Size estimate

Non-test, non-migration `src/` lines: `demo.py` ~55, `workspaces.py` ~12, views and urls ~45, `pages.py` ~8, templates ~40 (`demo.html` ~25, `home.html` +5, `404.html` and `503.html` ~5 each); about 160 of 400. No migration is expected. Reported again with real numbers at checkpoints 2 and 3.

## Open issues

- Resolved (coordinator, 2026-10-27): the builder's spec details above, including the `404.html` change to the PLT-1.3 test expectation.
- Resolved (coordinator, `9e973da`): `README.md` status line, which is outside the builder's scope.
- ACC-2 is not deployed to production before ACC-3 ([accounts-spec](accounts-spec.md)).
- Human review and merge remain pending.

## Review round 0 and repair round 1

Candidate `46e8a86`. Verifier: 1 Medium, 7 Low, 2 Info. Security reviewer: 1 Medium, 2 Low, 4 Info. Decisions by the coordinator on 2026-10-27 under the human's delegation:

- Deferred to ACC-3 (security Medium): an unlocked limit pre-check before hashing, now in the ACC-3 spec.
- Adopted, tests: a two-workspace isolation test through the real sign-in (verifier Medium); the taken-suffix 503 proves 3 draws and an `IntegrityError`; exact alphabets; the "Demo workspace creation failed." record with `exc_info`; `ac("ACC-2.6", "PLT-1.1")` on the signed-in redirect test; a `transaction=True` test where the real outermost commit fails.
- Adopted, code: `create_demo_workspace` runs in its own `transaction.atomic()` (a savepoint inside the view's block); `Credential.__repr__` hides the password; `sensitive_variables` on `create_demo`, `generate_passwords` and `create_demo_workspace`; the ACC-2.3 log test captures `django` and `django.template` DEBUG records (security Low 2).
- Adopted, spec and docs: the delivery-order exception for `/demo/`'s creation block; the `accounts.md` status line names RND-7's sample round; the Creation bullet says what a logged constraint violation may name; the User Guide's resubmission and back-button sentence.
- Not adopted: a `home_url(user)` refactor of the three role-home redirects (minor duplication; RND-1 is editing `accounts/views.py` in parallel). Framing protection (`X-Frame-Options`) stays with #5's production settings.

Repair round 1 evidence (builder, Windows):

- Red: `test_creation_outside_a_transaction_writes_all_or_nothing` (left `(1, 1)` rows) and `test_credential_repr_hides_the_password` failed before the fix. The other new tests passed against existing behaviour, so their detection was shown by temporary mutations, each restored with no diff left: a home view that also rendered another workspace's name failed the isolation test; removing `create_demo`'s `sensitive_variables` failed the three ACC-2.5 error-report checks; a repr showing the password failed the rendering-failure check and the repr test. The commit-failure test asserts the patched commit ran.
- The error-report check uses Django's HTML report, because its text report omits frame variables.
- Green: full verification passed: 195 passed, 1 skipped, 85 subtests. Budget: 184 of 400 lines since `1492c0b`.

## Checklist

- [x] Checkpoint 1: specs and plan.
- [x] Checkpoint 2: creation service, lookup helper and tests (red evidence first). Red: both test modules failed to import (`accounts.demo`, `accounts.workspaces` missing). Green: `pytest src/accounts -q` 63 passed; Ruff clean. 92 of 400 budget lines.
- [x] Checkpoint 3: routes, start page, templates, 503 page and tests (red evidence first). Red: 17 failed, 8 passed (`/demo/` gave 404, `/` set no CSRF cookie, Django's default 404 page). Green: full verification 174 passed, 1 skipped; Ruff clean. 169 of 400 budget lines since `9dc41a7`. Expectation changes for the verifier: PLT-1.1 now requires one form posting to `/demo/` (was no form); PLT-1.3 requires "Page not found." (was "Not Found").
- [x] Checkpoint 4: guides, and the opening status sentences of `accounts.md`, `TECHNICAL-SPEC.md` and `SECURITY-SPEC.md`. The shell recipe is removed.
- [x] Full verification, size budget and builder scope check (checkpoint 4, Windows, on `fea7923` plus the checkpoint 4 edits): `manage.py check` and `makemigrations --check` clean; Ruff clean; 188 passed, 1 skipped, 85 subtests passed. `git diff --check` clean; `check_scope.py builder --base fea7923` clean. Budget: 169 of 400 lines since `9dc41a7` for ACC-2; the raw `src/` diff is 197, including 28 lines from the merged ACC-1 repair.
- [x] Review round 0 (verifier and security reviewer).
- [x] Repair round 1.
- [ ] Re-review of repair round 1; human review and merge.
