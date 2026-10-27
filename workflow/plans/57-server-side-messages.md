# Slice 57: Keep flash messages on the server (#57)

Goal: store Django's messages in the server-side session instead of a cookie, replacing the messages-cookie residual that the RND-5 security review left open ([security spec](../specs/SECURITY-SPEC.md#sign-in-and-access-control)).

Tier: High (session and cookie handling), so the verifier and security reviewer both run. Base: `a8ce46f`, branch `57-server-side-messages`, stacked on RND-5's `16-request-retest` (#56). Owner: zheng-jj. Budget: at most 400 changed lines under `src/` outside tests and migrations; expected about 2.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27: set `MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"` in the shared settings. Nothing else; no new dependency, service or capability.

Builder's spec details within that scope (checkpoint 1):

- **No criterion added or changed.** ACC-1.5, RND-3.1, RND-5.1 and RND-6.1 already say each message shows once; where it is kept is a security control (SECURITY-SPEC, sign-in and access control) with its setting in the [accounts routes](../specs/TECHNICAL-SPEC.md#accounts-routes). Tests are marked with the criterion whose message they check.
- **Sign-out's storage effect** (checked with a scratch probe against the test database, not kept): `logout()` deletes the old session row, then "You have signed out." starts a new anonymous row and session cookie; the sign-in page shows it and leaves that row empty but present for 8 hours, until the browser's next sign-in replaces it. A scripted `/sign-out/` POST without a session cookie also creates a row each time. A plain sign-in page visit creates none. Recorded beside the existing storage-growth residual and in the [persistence decision](../specs/TECHNICAL-SPEC.md#data-model).
- **The old residual goes:** with session storage, a message cannot be minted or planted as a cookie, and sign-out discards an unread retest message with the session (probe: after an unread "Round closed.", the sign-in page showed only "You have signed out."). The SECURITY-SPEC retest bullet now says so, and notes that planting a whole session cookie is a general threat, not a message one.
- **New residual, accepted by the human (zheng-jj) on 2026-10-27, option (a):** the session is saved by Django's session middleware after the view, outside `coordinator_view`'s 503 handling. If that save fails after a round action committed, the response is the generic 500 with the change kept and its message lost (probe: close with `SessionStore.save` failing gave 500, round Closed); a GET that shows a message gets 500 instead of 503; a session ended by a concurrent sign-out gives Django's 400 (`SessionInterrupted`). This contradicts the rounds rule "no part of the change remains", so the specs record the exception in `rounds.md`, TECHNICAL-SPEC (rounds routes) and SECURITY-SPEC as accepted. Options presented: (a) accept it, no extra code, plus one test pinning the 500 with the change kept; (b) store and save the message inside the action's transaction (about 20 lines, a scope expansion); (c) keep cookie storage. The human chose (a).

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

## Open issues

- Planting a whole session cookie (cookie tossing from a same-site subdomain, or a network attacker before HSTS) signs a browser into the planter's account; it is noted in the security spec as not message-specific and is not addressed here.

## Checklist

- [x] Checkpoint 1: specs and plan (`51abcd8`, `1eaf42f`).
- [x] Checkpoint 2: setting and tests. `MESSAGE_STORAGE` in `src/relay/settings/base.py` (2 lines with its comment). Tests: `src/rounds/tests/test_messages.py` (new; the RND-3.1, RND-5.1 and RND-6.1 actions, the forged round-page cookie and the unread message after sign-out under RND-5.8, and the decision (a) pin under RND-6.5), `src/accounts/tests/test_sign_in.py` (ACC-1.5: the sign-out session, a forged cookie with and without a real message; an unmarked plain-visit guard), `src/accounts/tests/test_models.py` (the setting). Red, before the setting (`pytest -q -p no:randomly src/rounds/tests/test_messages.py src/accounts/tests/test_sign_in.py src/accounts/tests/test_models.py`): 11 failed, 67 passed. Failures: a `messages` cookie on the publish, close, retest and sign-out redirects; both forged cookies shown; "Round closed." and the retest message still shown on the sign-in page after sign-out; the pin gave 302, not 500; the setting absent. The plain-visit guard passed beforehand: it fails only if a sign-in page visit starts a session. Green, after: the same command gave 78 passed. One test expectation was corrected before green: the round page shows the retest label inside its `dir="auto"` span, so the page check uses that markup while the session check uses the plain sentence; the red failure for that case was the cookie assertion, before the page check. Related modules (`test_retest.py`, `test_close.py`, `test_publish.py`, `test_views.py`, `src/accounts`): 346 passed. Mutation: removing the setting on a temporary copy, restored and checked with `cmp`, failed the same 11. Ruff clean. No Developer Guide change: it names no session or message settings.
- [ ] Checkpoint 3: guides and status, if needed.
