# Slice 9: Prepare a test round (#9)

Goal: implement [RND-1](../specs/product/rounds.md#rnd-1-prepare-a-test-round) under the [rules for every round action](../specs/product/rounds.md#rules-for-every-round-action), the first rounds code slice.

Tier: High (role and workspace permissions on a new persisted record type). Base: `4a11fc9`, branch `9-prepare-round`, stacked on ACC-2's `3-demo-workspace` (which contains ACC-1); the PR base is `3-demo-workspace`. Owner: zheng-jj. Budget: one requirement (RND-1, 7 existing criteria, none added or changed); at most 400 changed lines under `src/` outside tests and migrations.

## Decisions

Made by the coordinator on 2026-10-27 under the human's (zheng-jj) delegation, "make my decisions for me":

- **Persistence:** build on the settled [data-model decisions](../specs/TECHNICAL-SPEC.md#data-model); not reopened.
- **Scope:** RND-1 only: the round model with the fields and cap RND-1 needs, the new-round, round and edit-round pages and routes, the Coordinator home's round list, and the shared rules those pages must satisfy, including the escaping and direction-isolation tests. Lookups use the shared workspace helper.
- **Round creation** takes an explicit workspace argument, only ever `request.user.workspace` here.
- **Not included:** criteria and cases (RND-2), publishing (RND-3), closing (RND-6), retests (RND-5), the sample round (RND-7), tester views (RES).

Builder's spec details within that scope (checkpoint 1), confirmed by the coordinator on 2026-10-27:

- Page text and layout in the [RND-1 introduction](../specs/product/rounds.md#rnd-1-prepare-a-test-round): "Rounds" heading, "(Draft)"-style states, "No rounds yet.", "Title" field, "Create round" and "Save" buttons, "State: <state>", "Edit round" link while Draft, "Coordinator home" links, no success message, every message next to the "Title" field. The shared rules now name Django's null-character message.
- [Technical details](../specs/TECHNICAL-SPEC.md#rounds): the `rounds` app; the round has only workspace, title, state and creation time (RND-3 and RND-6 add their times); `rounds.services.create_round(workspace, title)`; trimming, code-point length and the visible-character definition; 503 on `DatabaseError` for rounds routes; a title filter for page titles. [Rounds routes](../specs/TECHNICAL-SPEC.md#rounds-routes): exact methods (HEAD 405 on GET-only routes), the 409 page's title "Action not available", and RND-1's delivery order.
- One [security](../specs/SECURITY-SPEC.md#rounds-observations-and-history) sentence: round creation never takes its workspace from request data.
- The Coordinator home is an accounts route, so a storage failure while listing rounds keeps the accounts routes' rule (generic 500 until ACC-3) rather than the rounds 503; the rounds 503 applies to `/coordinator/rounds/...` routes (decision (a), confirmed).

## Stacking on ACC-2

Decision (b), coordinator, 2026-10-27: RND-1 is stacked on ACC-2 instead of copying its files, to avoid duplicate files and merge conflicts. The coordinator removed the duplicate "Workspace lookup helper" bullet from checkpoint 1 and merged `origin/3-demo-workspace` (`fea7923`) as `4a11fc9`. RND-1 therefore reuses ACC-2's `accounts.workspaces.workspace_records`, `404.html`, `503.html` and PLT-1.3 test as they are.

Builder's implementation details (checkpoint 3), confirmed by the coordinator on 2026-10-27:

- Rounds pages are never cached, like the role homes; one line added under [Rounds routes](../specs/TECHNICAL-SPEC.md#rounds-routes).
- The Coordinator home keeps ACC-1's view and decorators; `_role_home` takes an optional template and a sections function, and the coordinator's template `rounds/coordinator_home.html` extends `accounts/home.html` through a new empty `sections` block.
- The title input carries `dir="auto"`, since it holds only user text.

## Checkpoints

1. **Specs and plan** (this checkpoint, `spec:`/`plan:`): `workflow/specs/product/rounds.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`, this plan. Check: `git diff --check`; read changed sections back.
2. **Model and creation service** (`feat:`): `src/rounds/{__init__,apps,models,services}.py`, `src/rounds/migrations/0001_initial.py`, `src/relay/settings/base.py` (add `rounds`), `src/rounds/tests/test_services.py`. Tests: state check constraint; title limit of 120 in the database; `create_round` creates a Draft round in the given workspace; the 20th round is created and the 21st raises with nothing created, and another workspace's rounds don't count (RND-1.4 at service level); `workspace_records(user, Round)` returns only the user's workspace's rounds (ACC-2's helper tests cover the 404 and form behaviour generically). Red first. Checks: `makemigrations --check`, `pytest src/rounds src/accounts -q` (through the test-database lock).
3. **Pages, routes and rules tests** (`feat:`): `src/rounds/{forms,views,urls}.py`, `src/rounds/templatetags/{__init__,rounds_text}.py`, `src/rounds/templates/rounds/{round,round_form,conflict}.html`, `src/relay/urls.py`, `src/accounts/views.py` and `src/accounts/templates/accounts/home.html` (round list on the Coordinator home only), `src/rounds/tests/test_views.py`, `src/rounds/tests/test_rendering.py`. Tests, each marked with its ID:
   - RND-1.1 create opens the round page (title, "State: Draft", no criteria or cases) and the home lists it; newest first; "No rounds yet.".
   - RND-1.2 retitle shows the new title on the round page and home.
   - RND-1.3 title of 120 saved (also after trimming surrounding spaces); empty, whitespace-only, zero-width-only (U+200B, U+2060, U+FEFF), control-only and 121 characters each get "Enter 1 to 120 characters."; a null character gets "Null characters are not allowed."; each on create and retitle, with nothing changed.
   - RND-1.4 the 20th created, the 21st refused with the message and no new round; another workspace's rounds don't count.
   - RND-1.5 five threaded POSTs with 19 existing rounds (`django_db(transaction=True)`, a barrier, one connection per thread): exactly one round created, four get the message.
   - RND-1.6 a tester gets an identical 403 for an existing and a missing round ID on every RND-1 route; the Tester home does not show a Draft round's title.
   - RND-1.7 rules: 405 (PUT on new, POST and HEAD on the round page, PUT on edit); signed-out redirect to `/sign-in/` on GET and on POST with a valid token; 403 for missing/invalid CSRF token and a foreign `Origin` with nothing created or changed; another workspace's round (Draft, Open and Closed) and a missing ID get an identical 404 "Page not found." on view and edit, never 409; retitling an Open or Closed own round gets 409 with the exact message on GET and POST, title unchanged; the creation workspace comes from the user even if the POST carries a `workspace` field; a `DatabaseError` on create and on retitle gives the 503 text with nothing changed. Rendering: titles with markup (`<script>`, `"><img onerror>`) are escaped in the round page heading, the home list and the edit form's `value` attribute; the page title wraps the cleaned title in U+2068/U+2069 and drops bidi controls, including a stray U+2069 followed by U+202E; a line break renders as `<br>` inside the `dir="auto"` element; U+202E and U+200B stay inside the element that wraps only the title, with the surrounding page text unchanged; no `unicode-bidi` in served pages. RND-1 shows no success message, so that part of the rule has no RND-1 case.
   Red first, recording the failures. Checks: focused `pytest src/rounds src/accounts -q`, then full verification.
4. **Guides** (`docs:`): `docs/UserGuide.md` (round list, new round, round page, edit, in the product's exact words), `docs/DeveloperGuide.md` (`rounds` app, `create_round`, workspace helper, rendering filter). Check: read back; `git diff --check`; builder scope check.

Repairs after review are separate `fix:` commits.

## Size estimate

Non-test, non-migration `src/` lines: models and apps ~40, services ~30, forms ~40, views ~90, urls ~12, template filter ~20, templates ~55 (round ~15, round form ~20, conflict ~6, home list ~14), accounts view and settings and root urls ~12; about 300 of 400. Reported again with real numbers at checkpoints 2 and 3.

## Open issues

- Browser check of the per-line `dir="auto"` rendering with bidi and paragraph-separator titles: open for the human (automated tests check the markup only).
- Human review and merge remain pending; ACC-2 (the PR base) merges first.

## Review round 0 and repair round 1

Review round 0 on candidate `1d7e414`: verifier 1 Medium (F1), Low and evidence findings F2 to F7, and Info; security-reviewer 0 Critical, High or Medium, 2 Low and Info.

Coordinator decisions (2026-10-27, under the human's delegation), all implemented in repair round 1 on `3831e9f`:

1. F1 and security Low 2: rules 1 and 2 in [`rounds.md`](../specs/product/rounds.md#rules-for-every-round-action) and the [Rounds routes](../specs/TECHNICAL-SPEC.md#rounds-routes) intro now put Django's CSRF and `Origin` check first for unsafe methods (403), so 405 and the sign-in redirect apply to safe methods and to unsafe requests with a valid token. Criterion IDs and text unchanged.
2. F2: `coordinator_view` runs the sign-in and role checks inside its `try`, so a `DatabaseError` loading the session or user gives the rounds 503, before any lookup. The Coordinator home keeps the accounts rule (generic 500).
3. F4: 503 tests for the GET round page and edit form; the failure is logged with `exc_info`; RND-1.1 checks the home listing of a round created through the route; `ac("RND-1.1")` on the tie-break ordering test; `test_round_pages_are_never_cached` unmarked (a spec detail, not a criterion).
4. F3: mutation evidence, below.
5. F5 and security Info 3: `never_cache` is outermost, so 405, 409 and 503 responses are `private, no-store`; 403 and 404 pages, raised as exceptions, show fixed text only (technical spec sentence updated).
6. Security Low 1: each line of user text is escaped into its own `<span dir="auto">`, split at every `str.splitlines()` separator and joined by `<br>` (filter `isolated_lines`); page titles join lines with a space, because a paragraph separator would end the U+2068 isolate. Technical spec Rendering bullet and the rounds rendering rule updated. The edit form's `value` attribute keeps the stored title unchanged so it round-trips; the input carries `dir="auto"`.
7. F6: stale text fixed (helper users in the technical spec, this plan's checkpoint 2 name and open issues).
8. F7: the User Guide no longer presents Open or Closed or their 409 messages; "spaces or line breaks at either end".

Accepted as Info: the sign-in and role check is duplicated between the role homes and `coordinator_view`; `accounts.views` imports `rounds.models` for the `sections` decision, so `rounds` must never import `accounts.views`; `create_round` counts by workspace, as specified; browsers count the input's `maxlength` in UTF-16 units while the server counts code points; for RND-5 and RES, constraint-violation log lines can include user text, so later unique constraints on user text need log care; lock order stays workspace, then round.

Test expectation changes (for the verifier): the round heading and home links changed from `<h1 dir="auto">` and `<a ... dir="auto">` with `<br>` to `<span dir="auto">` per line inside a plain `<h1>` or `<a>`, following decision 6.

Repair round 1 evidence (Windows, test-database lock):

- Red: with the checkpoint 3 views, filter and templates restored temporarily, `pytest src/rounds` gave 19 failed, 96 passed: the per-line rendering tests (10 separators, markup, line breaks, bidi), the two RND-1.1 markup assertions, the 405 Cache-Control test (signed in and out) and the user-load 503 test (3 routes). Already passing, as Django or the existing code already did it: the tokenless 403 tests, the GET 503 tests, the logging assertion and the Coordinator home's 500.
- Mutations on temporary copies, each restored and checked with `cmp`: (i) unscoped lookup with the state check first in `edit_round`: the 404-not-409 test failed for Open and Closed (Draft and missing passed, as expected); (ii) visible-character check removed: 8 RND-1.3 invisible-title cases failed; (iii) locked re-check removed: the "opened after the state check" test failed; (iv) `-id` dropped from ordering: the tie test failed 5 of 5 runs.
- Final: check and `makemigrations --check` clean, Ruff clean, 310 passed, 1 skipped; `git diff --check` clean; scope clean against `3831e9f`; 338 of 400 budget lines (`git diff 11d7649` of `src/` outside tests and migrations).

## Checklist

- [x] Checkpoint 1: specs and plan.
- [x] Checkpoint 2: model, creation service and tests. Red: `pytest src/rounds -q` failed at collection with `ImportError: cannot import name 'services' from 'rounds'`; green: 7 passed; full verification 195 passed, 1 skipped; 79 budget lines.
- [x] Checkpoint 3: pages, routes, rules and rendering tests. Red: `pytest src/rounds -q` stopped at collection with `ModuleNotFoundError: No module named 'rounds.forms'`; `pytest src/rounds/tests/test_rendering.py` gave 7 failed (404s, no routes), 1 passed (`unicode-bidi` absent: nothing sets it yet; it guards future CSS). Mutation check: with the workspace lock removed from `create_round`, the RND-1.5 test failed 3 of 3 runs.
- [x] Checkpoint 4: guides and the status sentences of `rounds.md`, `TECHNICAL-SPEC.md` and `SECURITY-SPEC.md`.
- [x] Full verification, size budget and builder scope check (checkpoint 4, Windows): check and `makemigrations --check` clean, Ruff clean, 264 passed, 1 skipped; 312 of 400 budget lines since `46e8a86`; scope clean against `4cace95`.
- [x] Review round 0 (verifier and security-reviewer) and repair round 1.
- [ ] Review of repair round 1; human review and merge.
