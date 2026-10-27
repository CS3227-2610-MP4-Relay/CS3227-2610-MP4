# Slice 57: Keep flash messages on the server (#57)

Goal: store Django's messages in the server-side session instead of a cookie, replacing the messages-cookie residual that the RND-5 security review left open ([security spec](../specs/SECURITY-SPEC.md#sign-in-and-access-control)).

Tier: High (session and cookie handling), so the verifier and security reviewer both run. Base: `a8ce46f`, branch `57-server-side-messages`, stacked on RND-5's `16-request-retest` (#56). Owner: zheng-jj. Budget: at most 400 changed lines under `src/` outside tests and migrations; expected about 2.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27: set `MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"` in the shared settings. Nothing else; no new dependency, service or capability.

Builder's spec details within that scope (checkpoint 1):

- **No criterion added or changed.** ACC-1.5, RND-3.1, RND-5.1 and RND-6.1 already say each message shows once; where it is kept is a security control (SECURITY-SPEC, sign-in and access control) with its setting in the [accounts routes](../specs/TECHNICAL-SPEC.md#accounts-routes). Tests are marked with the criterion whose message they check.
- **Sign-out's storage effect** (checked with a scratch probe against the test database, not kept): `logout()` deletes the old session row, then "You have signed out." starts a new anonymous row and session cookie; the sign-in page shows it and leaves that row empty but present for 8 hours, until the browser's next sign-in replaces it. A scripted `/sign-out/` POST without a session cookie also creates a row each time. A plain sign-in page visit creates none. Recorded beside the existing storage-growth residual and in the [persistence decision](../specs/TECHNICAL-SPEC.md#data-model).
- **The old residual goes:** with session storage, a message cannot be minted or planted as a cookie, and sign-out discards an unread retest message with the session (probe: after an unread "Round closed.", the sign-in page showed only "You have signed out."). The SECURITY-SPEC retest bullet now says so, and notes that planting a whole session cookie is a general threat, not a message one.
- **New residual, accepted by the human (zheng-jj) on 2026-10-27, option (a), corrected in repair round 1 (D1):** the session is saved by Django's session middleware after the view, outside `coordinator_view`'s 503 handling. Django turns a failure to save an existing session row into `SessionInterrupted`, so the response is its default "Bad Request (400)" page, logged as a warning, with a change already committed kept and its message lost; only a failure to create a new row, as at sign-out, gives the generic 500. Checkpoint 1 said 500: its probe patched `SessionStore.save`, above that conversion. This is an exception to the rounds rule "no part of the change remains", recorded in `rounds.md`, TECHNICAL-SPEC (persistence decision, rounds routes) and SECURITY-SPEC. Options presented: (a) accept it, no extra code, plus one test pinning the status with the change kept; (b) store and save the message inside the action's transaction (about 20 lines, a scope expansion); (c) keep cookie storage. The human chose (a).

## Checkpoints

1. **Specs and plan** (this checkpoint, `spec:`/`plan:`): `workflow/specs/SECURITY-SPEC.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/product/rounds.md`, this plan. Check: `git diff --check`; read changed sections back.
2. **Session message storage** (`feat:`): `src/relay/settings/base.py` (`MESSAGE_STORAGE`), tests below, `docs/DeveloperGuide.md` only if a settings line is needed (none expected: it names no message settings). Tests red first with the setting absent, synthetic data:
   - `src/accounts/tests/test_models.py`: the shared settings name `SessionStorage` (extend `test_sessions_and_cookies_use_shared_settings`).
   - `src/accounts/tests/test_sign_in.py`, ACC-1.5: sign-out sets no `messages` cookie; its session cookie is a new key, the old row is gone and the old cookie still redirects; the new row holds the message; the sign-in page shows it once and sets no `messages` cookie. A `messages` cookie forged with the cookie storage's signing (`CookieStorage._encode`, test `SECRET_KEY`) is ignored by the sign-in page, alone and alongside a real sign-out message. A plain sign-in page visit sets no session cookie and creates no row (guards the growth residual).
   - `src/rounds/tests/test_messages.py` (new), one parametrised case each for publish (RND-3.1), close (RND-6.1) and retest (RND-5.1): the redirect sets no `messages` cookie and keeps the session key, the session row holds the message, the round page shows it once and sets no `messages` cookie. A forged `messages` cookie carrying a `retest`-tagged message is ignored by the round page (RND-5.8). An unread close or retest message is not shown on the sign-in page after sign-out, which shows only "You have signed out." (RND-5.8, ACC-1.5).
   - Pinning, for decision (a): with `SessionStore.save` failing, a close gives 500 (client with `raise_request_exception=False`) and the round is Closed. Red first too: with cookie storage the close never saves the session, so it gives 302.
   Expected red: every "no `messages` cookie", "row holds the message", forged-cookie and settings assertion; the unread-message-after-sign-out test (the cookie survives sign-out today). Already green, kept as guards: shows-once and the plain-visit test. Checks: focused `pytest src/accounts/tests/test_sign_in.py src/accounts/tests/test_models.py src/rounds/tests/test_messages.py src/rounds/tests/test_retest.py -q`, one command at a time; Ruff. Mutation: remove the setting, the new tests fail.
3. **Status and guides** (`docs:`), if needed: the Developer Guide names no message storage today; the User Guide is unchanged (no visible text changes). Read back; `git diff --check`; builder scope check. Full verification is the coordinator's.

Repairs after review are separate `fix:` commits.

Test expectation changes: none expected; `test_sign_out_ends_server_session` and the RND-3/5/6 message tests keep their assertions.

## Size estimate

`src/` outside tests: 1 to 2 lines in `base.py` (setting and comment).

## Review round 0 (candidate `c3ff0f3`) and repair round 1

Verifier and security reviewer findings R1 to R7; decisions by the human on 2026-10-27, relayed by the coordinator:

- **D1 (R1):** the residual as corrected above. The pin moves to a model-level failure (`Session.save` raising `OperationalError`): a close gives 400 with the round Closed; a sign-out whose new row cannot be created gives 500.
- **D2 (R2):** sign-out adds "You have signed out." only when the visitor was signed in, so a signed-out visitor's POST lands on the sign-in page with no message and creates no session row. ACC-1.5 is reworded under its ID; the storage-growth residual, the TECHNICAL-SPEC persistence decision, sessions bullet and sign-out route row follow.
- **D3 (R3):** the sign-in page renders messages through the rounds `status_message` tag, so a retest label is direction-isolated there too; SECURITY-SPEC's retest bullet and TECHNICAL-SPEC's retesting bullet say so.
- **R4:** SECURITY-SPEC's sessions bullet now says a message can be planted only with a whole session cookie, linking to the retest bullet; the growth residual's sign-out clause is rewritten.
- **R5:** forged-cookie tests also assert status 200 and the page heading, with a positive control under `FallbackStorage`.
- **R6:** the close case of the unread-message test is marked RND-6, not RND-5.8. The new behaviours stay security controls, with no new criteria (coordinator's decision); the persistence decision and growth residual now state that viewing the sign-in page creates no row, which the unmarked guard test checks.
- **R7:** ACC-1.2 now says a failed sign-in shows, and so consumes, any unread message. ACC-3 is recorded below.
- Criterion text changed (IDs kept): ACC-1.2, ACC-1.5. Affected tests: none of the existing assertions change; new tests for D2 and D3 are marked ACC-1.5 and RND-5.8.

Repair checkpoints, one commit each: (A) specs and plan; (B) D2 code and tests, red first; (C) D3 code and tests, red first, with the Developer Guide's `status_message` sentence; (D) test-only repairs for the R1 pin, R5 and R6. The helpers `close`, `open_with_case` and `draft_with_case` in `test_messages.py` keep their names and signatures (#58 imports them).

## Open issues

- ACC-3: signing out a signed-in user writes twice (deletes the old row, then creates the new one), so a failure in between leaves the user signed out with the generic 500; ACC-3's "503 and changes nothing" storage rule, when ACC-3 is built, needs a sign-out exception.

- Planting a whole session cookie (cookie tossing from a same-site subdomain, or a network attacker before HSTS) signs a browser into the planter's account; it is noted in the security spec as not message-specific and is not addressed here.

## Checklist

- [x] Checkpoint 1: specs and plan (`51abcd8`, `1eaf42f`).
- [x] Checkpoint 2: setting and tests. `MESSAGE_STORAGE` in `src/relay/settings/base.py` (2 lines with its comment). Tests: `src/rounds/tests/test_messages.py` (new; the RND-3.1, RND-5.1 and RND-6.1 actions, the forged round-page cookie and the unread message after sign-out under RND-5.8, and the decision (a) pin under RND-6.5), `src/accounts/tests/test_sign_in.py` (ACC-1.5: the sign-out session, a forged cookie with and without a real message; an unmarked plain-visit guard), `src/accounts/tests/test_models.py` (the setting). Red, before the setting (`pytest -q -p no:randomly src/rounds/tests/test_messages.py src/accounts/tests/test_sign_in.py src/accounts/tests/test_models.py`): 11 failed, 67 passed. Failures: a `messages` cookie on the publish, close, retest and sign-out redirects; both forged cookies shown; "Round closed." and the retest message still shown on the sign-in page after sign-out; the pin gave 302, not 500; the setting absent. The plain-visit guard passed beforehand: it fails only if a sign-in page visit starts a session. Green, after: the same command gave 78 passed. One test expectation was corrected before green: the round page shows the retest label inside its `dir="auto"` span, so the page check uses that markup while the session check uses the plain sentence; the red failure for that case was the cookie assertion, before the page check. Related modules (`test_retest.py`, `test_close.py`, `test_publish.py`, `test_views.py`, `src/accounts`): 346 passed. Mutation: removing the setting on a temporary copy, restored and checked with `cmp`, failed the same 11. Ruff clean. No Developer Guide change: it names no session or message settings.
- [ ] Checkpoint 3: guides and status, if needed.
- [x] Repair (A): specs and plan (`1a19a26`, `5d75b5c`).
- [x] Repair (B): D2 sign-out. `sign_out` in `src/accounts/views.py` adds "You have signed out." only if the user was signed in before `logout()`. Test (ACC-1.5) in `src/accounts/tests/test_sign_in.py`: a signed-out visitor's POST, with no session cookie and with the cookie of a deleted session, redirects to the sign-in page, issues no new session identifier, creates no session row, and the sign-in page shows no message. Red (`pytest -q src/accounts/tests/test_sign_in.py -k signed_out_visitor_signing_out`): 2 failed, each on `assert not Session.objects.exists()` after the POST. Green: `pytest -q src/accounts src/rounds/tests/test_messages.py` 113 passed, the signed-in ACC-1.5 tests unchanged; Ruff clean.
- [ ] Repair (C): D3 sign-in page.
- [ ] Repair (D): test-only repairs.
