# Slice 3: Create an isolated demo workspace (#3)

Goal: implement [ACC-2](../specs/product/accounts.md#acc-2-create-an-isolated-demo-workspace) and the changed [PLT-1.1](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification) start page.

Tier: High (account creation, passwords, workspace isolation). Base: `9dc41a7`, branch `3-demo-workspace`, stacked on ACC-1's `2-sign-in-by-role`. Owner: zheng-jj. Budget: one requirement (ACC-2, 7 existing criteria) plus the PLT-1.1 text change; at most 400 changed lines under `src/` outside tests and migrations.

## Decisions

Made by the coordinator on 2026-10-27 under the human's (zheng-jj) delegation, "make my decisions for me":

- **Scope:** ACC-2 only: the POST-only `/demo/` route, the start page's "Create a demo workspace" button, the "Your demo workspace" page with `Cache-Control: no-store` rendered inside the creation transaction, generated usernames, suffixes and passwords, the shared workspace lookup helper (ACC-2.4, used only by its tests for now), the 503 page (ACC-2.5) and the signed-in redirect from `/` and `/demo/` (ACC-2.6).
- **Not included:** the sample draft round (RND-7; its slice adds the round inside `create_demo_workspace`, with no placeholder now), the abuse limits (ACC-3, next slice; it adds the counter locks at the start of the creation transaction) and production deploy.
- **PLT-1.1** keeps its ID; the start page has only the "Sign in" link and the "Create a demo workspace" button.
- **Guides:** the User Guide says accounts come from demo workspaces; the Developer Guide's manual-account section points to the button.

Builder's spec details within that scope (checkpoint 1), for the coordinator to confirm:

- Page text and layout of "Your demo workspace" in [ACC-2](../specs/product/accounts.md#acc-2-create-an-isolated-demo-workspace), including a "Sign in" link to `/sign-in/`; creation, lookup helper, collision handling and the 503 handling under [Accounts and workspaces](../specs/TECHNICAL-SPEC.md#accounts-and-workspaces).
- Suffix collisions: up to 3 suffix draws checked by query; a final collision or a concurrent race fails on the unique constraint and gives the 503. No savepoint retry loop.
- A `404.html` saying "Page not found." serves every 404, as ACC-2.4 states its text. PLT-1.3 stays generic, but its test's `b"Not Found"` assertion becomes `b"Page not found."` (listed for the verifier).
- Any exception inside the creation block gives the 503 and is logged with its traceback only.
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

- Coordinator to confirm the builder's spec details above, in particular the `404.html` change to the PLT-1.3 test expectation.
- ACC-2 is not deployed to production before ACC-3 ([accounts-spec](accounts-spec.md)).
- Human review and merge remain pending.

## Checklist

- [x] Checkpoint 1: specs and plan.
- [ ] Checkpoint 2: creation service, lookup helper and tests (red evidence first).
- [ ] Checkpoint 3: routes, start page, templates, 503 page and tests (red evidence first).
- [ ] Checkpoint 4: guides.
- [ ] Full verification, size budget and builder scope check.
- [ ] Independent verifier and security review; human review and merge.
