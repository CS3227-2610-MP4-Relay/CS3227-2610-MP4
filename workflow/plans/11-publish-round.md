# Slice 11: Publish a round to Beta Testers (#11)

Goal: implement [RND-3](../specs/product/rounds.md#rnd-3-publish-a-round-to-beta-testers) under the [rules for every round action](../specs/product/rounds.md#rules-for-every-round-action), the third rounds code slice.

Tier: Standard, as the issue says. The slice adds one state transition (Draft to Open) and its concurrency, but no new role, workspace or permission rule: the publish route reuses RND-1's `coordinator_view` and `own_round` checks, takes no form-submitted record IDs and no build ID. Because it adds a route and renders new user text, the [security-reviewer trigger](../skills/slice.md) for Standard applies, so the security reviewer runs alongside the verifier. Base: `3557050`, branch `11-publish-round`, stacked on RND-2's `10-criteria-and-cases` (which contains RND-1, ACC-2 and ACC-1); the PR base is `10-criteria-and-cases`. Owner: zheng-jj. Budget: one requirement (RND-3, 6 existing criteria, none added or changed); at most 400 changed lines under `src/` outside tests and migrations.

## Decisions

Made by the coordinator on 2026-10-27 under the human's (zheng-jj) delegation, "make my decisions for me":

- **Scope:** RND-3 only: the build model (label, comparison key with its unique constraint, covered cases) and migration; the round's publication time; the publish service (round row lock, state and case-count re-check, first build covering every case); the publish route as a POST form on the round page with the label field; "Round published." once; the Open round page (each case's current build, the builds list oldest first with label and covered cases, no edit or delete controls); RND-3.5 race tests (an edit racing a publish, two publishes).
- **Reuse:** RND-1 and RND-2's `coordinator_view(methods)`, `own_round`, `show_round`, `state_conflict`, `RoundTextField`, `Refused`, `isolated_lines`, `title_isolate`, the 409 page and `test_routes.py`'s route walk.
- **Not included:** tester views and results (RES, Whimsyturtle), closing (RND-6), retests (RND-5), the sample round (RND-7). The 10-build cap and duplicate-label message belong to RND-5; the first build cannot hit either.
- **Merge:** RND-2 (#53) is under review; if its repairs change shared code, the coordinator merges them before checkpoint 3. Checkpoint 2 stays out of `views.py`, `urls.py`, templates and view tests.

Builder's spec details within that scope (checkpoint 1), for the coordinator to confirm:

- Page text in the [RND-3 introduction](../specs/product/rounds.md#rnd-3-publish-a-round-to-beta-testers): while Draft, a "Build label" field and a "Publish round" button after the "Test cases" section, before "Coordinator home", shown even with no cases so RND-3.3 is reachable; "Round published." once, directly under the heading; a refused publish keeps the entered label and shows its message next to "Build label"; the label is checked before the case count, so an invalid label on a round without cases gets only the label message; each case's "Current build" after its linked criteria; a "Builds" heading after "Test cases", each build's label as a subheading, then "Covered test cases" and the covered case titles in creation order; no "Edit round" link, RND-2 controls or publish form once Open; build labels never in a page title, so the round page keeps the round title as its page title.
- [Technical details](../specs/TECHNICAL-SPEC.md#rounds): `Round.published_at` (empty while Draft); `rounds.Build` (label at most 100, key at most 300 since NFC can triple length, creation time) and an explicit `rounds.BuildCase` link with `PROTECT` keys and a unique pair constraint, as for `CaseCriterion`; `rounds.services.build_key(label)`; builds ordered by ascending ID, a case's current build being the highest-ID build covering it; the publish flow (form, lock, Draft re-check, `publish(round_, label)`, message after commit, redirect). Under [Rounds routes](../specs/TECHNICAL-SPEC.md#rounds-routes): a refused publish re-renders the round page with status 200, and RND-3's delivery-order sentence. The security spec needs no change: its rounds section already names RND-3.4 freezing and the RND-3.5 lock.
- No check constraint ties `published_at` to the state; the publish service sets both under the lock, and RND-6 will add the closing time the same way.

## Checkpoints

1. **Specs and plan** (this checkpoint, `spec:`/`plan:`): `workflow/specs/product/rounds.md`, `workflow/specs/TECHNICAL-SPEC.md`, this plan. Check: `git diff --check`; read changed sections back.
2. **Build model, migration and publish service** (`feat:`): `src/rounds/models.py` (`Round.published_at`, `Build`, `BuildCase`), `src/rounds/migrations/0003_builds.py`, `src/rounds/services.py` (`build_key`, `publish`), `src/rounds/forms.py` (`PublishForm`), `src/rounds/tests/test_publish_services.py` (new). `publish(round_, label)` runs in the caller's transaction after the lock and Draft re-check, and raises `Refused(<RND-3.3 message>, "label")` for a round with no cases. Tests, marked: RND-3.1 a round with cases becomes Open with `published_at` set and one build whose cases are exactly all the round's cases; RND-3.3 no cases raises with the round Draft, no build and `published_at` empty; RND-3.4 criteria, cases and links compare equal before and after; RND-3.2 the form accepts 100 characters (also after trimming) and rejects empty, invisible-only and 101 with "Enter 1 to 100 characters.". Unmarked data-model tests: `build_key` removes Cf characters (U+200B), applies NFC (decomposed and composed forms give one key) and stays case-sensitive; the unique constraint refuses a second build with the same key in one round and allows it in another; the 100 and 300 database limits; `PROTECT` refuses deleting a covered case or a build with links. Red first. Checks: `makemigrations --check`, `pytest src/rounds -q` through the shared test-database lock.
3. **Route, round page and RND-3 tests** (`feat:`): `src/rounds/{views,urls}.py` (`publish_round` view; `show_round` adds the publish form while Draft, the builds with their cases, and each case's current build), `src/rounds/templates/rounds/round.html`, `src/rounds/tests/test_publish.py` (new), `src/rounds/tests/test_routes.py` (the walk picks the new route up by its pattern; confirm it posts an empty label and gets the 200 round page, extending the fixture only if needed). Tests, each marked:
   - RND-3.1 publishing redirects to the round page showing "Round published." once (gone on reload), "State: Open", the label as every case's current build, the "Builds" list with the label and every case title, and the criteria and cases without "Edit round", edit, delete or publish controls.
   - RND-3.2 a 100-character label (and one padded with spaces) publishes; empty, invisible-only (zero-width space only) and 101 characters each get "Enter 1 to 100 characters." next to "Build label", the label kept in the field, status 200, round Draft, no build.
   - RND-3.3 a round with criteria but no cases gets "Add at least one test case before publishing.", status 200, round Draft, no build; with an invalid label too, only the label message shows.
   - RND-3.4 after publishing, the round page lists exactly the criteria, cases and links saved before, and the records compare equal to a snapshot taken before publishing.
   - RND-3.5 threaded races, as RND-2.5, with `services.publish` patched to pause 0.1 s inside the locked transaction: an add-case and a retitle each racing a publish either save first and appear in the published round (the new case covered by the build) or get 409 with nothing saved; two publishes give exactly one 302 and one 409, one build, and the round Open with the first label.
   - RND-3.6 rules: 405 for GET, HEAD and PUT; 403 for a missing CSRF token and a foreign `Origin`, nothing changed; signed-out redirect and tester 403 for existing and missing round IDs alike; 404 "Page not found." for another workspace's round in Draft, Open and Closed, never 409; 409 with the exact message for an Open and a Closed round; a state change between the first check and the locked write (patched) gives 409; `DatabaseError` in `publish` gives the 503 with the round Draft and no build; never-cached responses. Rendering of build labels in the current-build line and builds list (markup escaped; a label posted with line breaks, which a single-line input does not stop, shown as per-line `<span dir="auto">` elements; bidi and zero-width characters kept inside those elements), in the publish field's value attribute after a refused publish, and absent from the page `<title>`.
   Red first, recording the failures. Checks: focused `pytest src/rounds -q`, then full verification.
4. **Guides and status** (`docs:`): `docs/UserGuide.md` (publishing, its messages and the Open round page, in the product's exact words), `docs/DeveloperGuide.md` (build model, publish service, current-build computation), the status sentences of `rounds.md`, `TECHNICAL-SPEC.md` and, if it names built requirements, `SECURITY-SPEC.md`. Check: read back; `git diff --check`; builder scope check.

Repairs after review are separate `fix:` commits.

## Size estimate

Non-test, non-migration `src/` lines: models ~35 (`published_at`, `Build` ~18, `BuildCase` ~14), services ~30, forms ~8, views ~35 (publish view ~22, round-page context ~13), urls ~1, templates ~25 (message, current build, builds section, publish form); about 135 of 400. Reported with real numbers at checkpoints 2 and 3.

## Open issues

- Browser check of the per-line `dir="auto"` rendering of build labels: open for the human (automated tests check the markup only).
- RND-2 (#53) is still in review; its repairs may change `views.py` or `round.html` before checkpoint 3.
- Whether testers can see an Open round, and how, is RES's (Whimsyturtle's); RND-3.1's "published to Beta Testers" has no tester-side check in this slice.

## Checklist

- [x] Checkpoint 1: specs and plan.
- [ ] Checkpoint 2: build model, migration, publish service and tests.
- [ ] Checkpoint 3: route, round page and RND-3 tests.
- [ ] Checkpoint 4: guides and status.
- [ ] Full verification, size budget and builder scope check.
