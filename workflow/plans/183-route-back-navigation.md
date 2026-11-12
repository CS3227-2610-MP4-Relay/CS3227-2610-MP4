# Slice 183: route-back navigation

Give coordinator and feedback conflicts, standalone error pages and tester-account pages visible top navigation ([PLT-4.15–PLT-4.18](../specs/product/platform.md#plt-4-shared-application-presentation)).

Why: Issue #183 found refusal and error pages with no route back, and tester-account links below long content; the User Guide tells users to press the browser's Back button.

## Scope and decisions

- Standard tier; PLT-4 is the single changed requirement: PLT-4.7 and PLT-4.14 clauses adjusted, PLT-4.15–PLT-4.18 added (six criteria). One-line prose links only in ACC-2/ACC-3/ACC-4 descriptions and round-action rule 4. Budget: at most 400 non-test source lines under `src/`.
- Human decision: defer the persistent navbar (no `base.html` navbar, no Sign out on every page).
- Human decision: 403, 404, 429 and 503 pages get one static secondary "Back to home" link to `/` before their heading, reusing the sign-in page's `page-navigation` markup. It must not evaluate `user`, session or database; signed-in users reach their role home through ACC-2.6. Messages and statuses unchanged.
- Coordinator choice (routine): feedback 409s mirror PLT-4.14 with "Tester home" and "Back to round".
- No new route, capability, dependency or control; 400/405 pages and the demo page are unchanged. All new links point to fixed, already authorized destinations, so no security review is planned unless the implementation touches authorization or queries.

## Commit checkpoints

1. `spec: Define route-back navigation for conflicts, errors and tester accounts (#183)` — `workflow/specs/product/platform.md`, `accounts.md`, `rounds.md` and this plan. Read back changed sections; run builder scope/diff checks. Yield.
2. `fix: Add navigation to round and feedback conflicts (#183)` — `src/rounds/views.py` (`state_conflict` passes `back=reverse("rounds:detail", ...)`), `src/ai/feedback_views.py` (back to `accounts:tester-round`), conflict template only if needed; tests in `src/rounds/tests/test_views.py`, `src/ai/tests/` and `src/e2e/test_navigation.py` or `test_presentation.py`. Red first: one link each before the message, exact destinations, unchanged message/status/no-store/rows, no form, no gateway call, foreign round still 404.
3. `fix: Add home links to error pages (#183)` — `src/relay/templates/{403,404,429,503}.html`; tests in `src/relay/tests/test_pages.py` and accounts tests. Red first: one "Back to home" to `/` before the `h1`; rendering with a user object that fails on access and under `assertNumQueries(0)` (or `django_assert_num_queries(0)`); CSRF 403 shows no workspace data; release smoke text `<h1>Page not found.</h1>` still matches.
4. `fix: Move tester-account links to the top (#183)` — `src/accounts/templates/accounts/{tester_passwords,tester_added,tester_password_reset,tester_limit}.html`; explicit links, not `page_navigation.html` (two pages render via `render_to_string` without a request). Tests in `src/accounts/tests/` and the existing tester-account browser journey in `src/e2e/test_accounts.py`; recapture `src/e2e/screenshots.py` images only if they show these pages. Red first: each link once, inside the top navigation before the `h1`, none after content; credentials/status/no-store unchanged.
5. `docs: Describe route-back navigation (#183)` — `docs/UserGuide.md` (replace the line ~103 browser-Back advice: a failed publish/retest shows the 503 page, whose "Back to home" reaches Coordinator home; describe conflict links) via maintain-docs; screenshots only if a captured image shows changed content.

Each code checkpoint runs focused server and browser tests red then green; checkpoint 5 is followed by `ruff check . && ruff format --check . && pytest` in the configured test environment (PostgreSQL 17 at 127.0.0.1:55432, Chromium, root `.venv`).

## Open issues and next steps

- Deferred: persistent navigation bar across pages (human decision, #183).
- TECHNICAL-SPEC rounds routes say rounds' "403 and 404 pages show fixed text only"; a static link keeps them fixed content, so no change is planned.
- Next: coordinator commits checkpoint 1, then assigns checkpoint 2.
