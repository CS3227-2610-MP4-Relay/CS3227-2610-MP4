# Slice 9: Prepare a test round (#9)

Goal: implement [RND-1](../specs/product/rounds.md#rnd-1-prepare-a-test-round) under the [rules for every round action](../specs/product/rounds.md#rules-for-every-round-action), the first rounds code slice.

Tier: High (role and workspace permissions on a new persisted record type). Base: `9dc41a7`, branch `9-prepare-round`, stacked on ACC-1's `2-sign-in-by-role`. Owner: zheng-jj. Budget: one requirement (RND-1, 7 existing criteria, none added or changed); at most 400 changed lines under `src/` outside tests and migrations.

## Decisions

Made by the coordinator on 2026-10-27 under the human's (zheng-jj) delegation, "make my decisions for me":

- **Persistence:** build on the settled [data-model decisions](../specs/TECHNICAL-SPEC.md#data-model); not reopened.
- **Scope:** RND-1 only: the round model with the fields and cap RND-1 needs, the new-round, round and edit-round pages and routes, the Coordinator home's round list, and the shared rules those pages must satisfy, including the escaping and direction-isolation tests. Lookups use the shared workspace helper.
- **Round creation** takes an explicit workspace argument, only ever `request.user.workspace` here.
- **Not included:** criteria and cases (RND-2), publishing (RND-3), closing (RND-6), retests (RND-5), the sample round (RND-7), tester views (RES).

Builder's spec details within that scope (checkpoint 1), for the coordinator to confirm:

- Page text and layout in the [RND-1 introduction](../specs/product/rounds.md#rnd-1-prepare-a-test-round): "Rounds" heading, "(Draft)"-style states, "No rounds yet.", "Title" field, "Create round" and "Save" buttons, "State: <state>", "Edit round" link while Draft, "Coordinator home" links, no success message, every message next to the "Title" field. The shared rules now name Django's null-character message.
- [Technical details](../specs/TECHNICAL-SPEC.md#rounds): the `rounds` app; the round has only workspace, title, state and creation time (RND-3 and RND-6 add their times); `rounds.services.create_round(workspace, title)`; trimming, code-point length and the visible-character definition; 503 on `DatabaseError` for rounds routes; a title filter for page titles. [Rounds routes](../specs/TECHNICAL-SPEC.md#rounds-routes): exact methods (HEAD 405 on GET-only routes), the 409 page's title "Action not available", and RND-1's delivery order.
- One [security](../specs/SECURITY-SPEC.md#rounds-observations-and-history) sentence: round creation never takes its workspace from request data.
- The Coordinator home is an accounts route, so a storage failure while listing rounds keeps the accounts routes' rule (generic 500 until ACC-3) rather than the rounds 503.

## Merge points with ACC-2 (`3-demo-workspace`)

ACC-2's committed spec (`b6f0aa7`, not on this base) defines the workspace lookup helper, `404.html` and `503.html`. RND-1 needs all three, so it adds the smallest identical versions and takes ACC-2's at merge:

- `src/accounts/workspaces.py` with `workspace_records(user, model)`, same name and contract, and the identical "Workspace lookup helper" bullet in the technical spec, without ACC-2's "only tests use the helper" sentence.
- `src/relay/templates/404.html` ("Page not found.") and `503.html` ("Relay is temporarily unavailable. Try again later."), extending `base.html`.
- The PLT-1.3 test expectation `b"Not Found"` becomes `b"Page not found."`, as in ACC-2's plan (for the verifier).

## Checkpoints

1. **Specs and plan** (this checkpoint, `spec:`/`plan:`): `workflow/specs/product/rounds.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`, this plan. Check: `git diff --check`; read changed sections back.
2. **Model, helper and creation service** (`feat:`): `src/rounds/{__init__,apps,models,services}.py`, `src/rounds/migrations/0001_initial.py`, `src/accounts/workspaces.py`, `src/relay/settings/base.py` (add `rounds`), `src/rounds/tests/test_services.py`, `src/accounts/tests/test_workspaces.py`. Tests: state check constraint; `create_round` creates a Draft round in the given workspace; the 20th round is created and the 21st raises with nothing created (RND-1.4 at service level); the helper returns own records only and `get_object_or_404` on it raises the same `Http404` for another workspace's and a missing ID. Red first. Checks: `makemigrations --check`, `pytest src/rounds src/accounts -q` (through the test-database lock).
3. **Pages, routes and rules tests** (`feat:`): `src/rounds/{forms,views,urls}.py`, `src/rounds/templatetags/{__init__,rounds_text}.py`, `src/rounds/templates/rounds/{round,round_form,conflict}.html`, `src/relay/templates/{404,503}.html`, `src/relay/urls.py`, `src/accounts/views.py` and `src/accounts/templates/accounts/home.html` (round list on the Coordinator home only), `src/rounds/tests/test_views.py`, `src/rounds/tests/test_rendering.py`, `src/relay_tests/test_pages.py` (PLT-1.3 text). Tests, each marked with its ID:
   - RND-1.1 create opens the round page (title, "State: Draft", no criteria or cases) and the home lists it; newest first; "No rounds yet.".
   - RND-1.2 retitle shows the new title on the round page and home.
   - RND-1.3 title of 120 saved (also after trimming surrounding spaces); empty, whitespace-only, zero-width-only (U+200B, U+2060, U+FEFF), control-only and 121 characters each get "Enter 1 to 120 characters."; a null character gets "Null characters are not allowed."; each on create and retitle, with nothing changed.
   - RND-1.4 the 20th created, the 21st refused with the message and no new round; another workspace's rounds don't count.
   - RND-1.5 five threaded POSTs with 19 existing rounds (`django_db(transaction=True)`, a barrier, one connection per thread): exactly one round created, four get the message.
   - RND-1.6 a tester gets an identical 403 for an existing and a missing round ID on every RND-1 route; the Tester home does not show a Draft round's title.
   - RND-1.7 rules: 405 (PUT on new, POST and HEAD on the round page, PUT on edit); signed-out redirect to `/sign-in/` on GET and on POST with a valid token; 403 for missing/invalid CSRF token and a foreign `Origin` with nothing created or changed; another workspace's round (Draft, Open and Closed) and a missing ID get an identical 404 "Page not found." on view and edit, never 409; retitling an Open or Closed own round gets 409 with the exact message on GET and POST, title unchanged; the creation workspace comes from the user even if the POST carries a `workspace` field; a `DatabaseError` on create and on retitle gives the 503 text with nothing changed. Rendering: titles with markup (`<script>`, `"><img onerror>`) are escaped in the round page heading, the home list and the edit form's `value` attribute; the page title wraps the cleaned title in U+2068/U+2069 and drops bidi controls, including a stray U+2069 followed by U+202E; a line break renders as `<br>` inside the `dir="auto"` element; U+202E and U+200B stay inside the element that wraps only the title, with the surrounding page text unchanged; no `unicode-bidi` in served pages. RND-1 shows no success message, so that part of the rule has no RND-1 case.
   Red first, recording the failures. Checks: focused `pytest src/rounds src/accounts src/relay_tests/test_pages.py -q`, then full verification.
4. **Guides** (`docs:`): `docs/UserGuide.md` (round list, new round, round page, edit, in the product's exact words), `docs/DeveloperGuide.md` (`rounds` app, `create_round`, workspace helper, rendering filter). Check: read back; `git diff --check`; builder scope check.

Repairs after review are separate `fix:` commits.

## Size estimate

Non-test, non-migration `src/` lines: models and apps ~40, services ~30, workspace helper ~12, forms ~40, views ~90, urls ~12, template filter ~20, templates ~65 (round ~15, round form ~20, conflict ~6, `404`/`503` ~10, home list ~14), accounts view and settings and root urls ~12; about 320 of 400. Reported again with real numbers at checkpoints 2 and 3.

## Open issues

- Coordinator to confirm the builder's spec details above, in particular the Coordinator home's storage-failure rule and the merge points.
- Merge order with ACC-2 decides who resolves the duplicated helper, templates and PLT-1.3 test; whichever lands second takes the first's files.
- The status line "specified but not implemented yet" in `rounds.md` is left as is, as `accounts.md` did for ACC-1.
- Human review and merge remain pending.

## Checklist

- [x] Checkpoint 1: specs and plan.
- [ ] Checkpoint 2: model, helper, creation service and tests (red evidence first).
- [ ] Checkpoint 3: pages, routes, rules and rendering tests (red evidence first).
- [ ] Checkpoint 4: guides.
- [ ] Full verification, size budget and builder scope check.
- [ ] Independent verifier and security review; human review and merge.
