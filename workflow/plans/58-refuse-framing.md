# Slice 58: Refuse framing on every page (#58)

Goal: every response Django makes refuses framing (`X-Frame-Options: DENY`) in every environment, replacing the clickjacking residual that the RND-6 review left open for #5 ([security spec](../specs/SECURITY-SPEC.md#rounds-observations-and-history)).

Tier: Standard, with a security review. Base: `c3ff0f3`, branch `58-refuse-framing`, stacked on #57 and RND-5's #56. Owner: zheng-jj. Budget: at most 400 changed lines under `src/` outside tests; expected 1 to 3; actual 2.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27: add Django's `XFrameOptionsMiddleware` to the shared settings. HSTS and the other production-only settings stay with #5. No new dependency.

Builder's details within that scope (checkpoint 1):

- **No criterion added.** Refusing framing is a security control ([SECURITY-SPEC](../specs/SECURITY-SPEC.md#rounds-observations-and-history)) with its setting under [Configuration](../specs/TECHNICAL-SPEC.md#configuration); the production list keeps HSTS and a release check that framing is still refused. Tests are unmarked with a docstring naming the control, as the existing "never cached" tests are.
- **Placement:** first in `MIDDLEWARE`, not last as in Django's template. A middleware sees only responses made by those below it, so last would miss `SessionMiddleware`'s 400 for a failed session save and 500 for a failed new session row (#57), and second would miss `SecurityMiddleware`'s HTTPS redirect and a disallowed-host 400 raised there. Checkpoint 2 placed it second; repair round 1 (F1) moves it first. Responses served outside Django, such as platform error pages, are not covered (TECHNICAL-SPEC, Configuration).
- **Release check:** the production list under Configuration keeps an item that production keeps the shared middleware and sends `DENY` (repair F2).
- **Residual, accepted by the human (zheng-jj) on 2026-10-27, no code:** refusing framing does not stop UI redress without a frame, such as a double-click attack that navigates the opener to the round page between clicks; recorded in SECURITY-SPEC, mitigation deferred.
- **Default value:** in the installed Django 6.1.2, `X_FRAME_OPTIONS` defaults to `DENY`; the setting is not repeated.

## Checkpoints

1. **Specs and plan** (`spec:`/`plan:`): `workflow/specs/SECURITY-SPEC.md` (residual replaced by the control), `workflow/specs/TECHNICAL-SPEC.md` (Configuration), this plan. Check: `git diff --check`; read back.
2. **Middleware** (`feat:`): `src/relay/settings/base.py`, new `src/rounds/tests/test_framing.py` (uses the rounds fixtures and holds the middleware-order check too, so `src/accounts/tests/test_models.py` is unchanged). Red first with the middleware absent. Each response has `X-Frame-Options: DENY`:
   - public start page GET (200) and its POST (405);
   - sign-in GET (200);
   - tester home, signed in as a tester (200);
   - coordinator round page: Draft (delete buttons) and Open (close button), 200;
   - unknown URL 404, and another workspace's round 404;
   - close on a Closed round, 409;
   - a POST without a CSRF token, 403;
   - a rounds storage failure, 503 (the `test_views.py` patching pattern);
   - a close with `SessionStore.save` failing, 500 (client with `raise_request_exception=False`); fails if the middleware is placed below `SessionMiddleware`. Repair F6 replaces this unreachable path with the real one.
   - 429 is not reachable: ACC-3 is not built.
   - Guard: no file under `src/` outside tests names `xframe_options_exempt`, `xframe_options_sameorigin` or `xframe_options_deny`, scanned in Python; and the shared settings list the middleware right after `SecurityMiddleware`.
   Expected red: every header case and the settings case; the exemption scan passes beforehand (it fails only if an exemption is added). Mutation: move the middleware last; the 500 case fails. Checks: focused `pytest -q -p no:randomly src/rounds/tests/test_framing.py src/accounts/tests/test_models.py`; Ruff. Full verification is the coordinator's.
3. **Guides**, if needed: the Developer Guide names no middleware and the User Guide shows nothing new, so none expected.

4. **Repair round 1** (on `6f10ce5`, after the #57 repairs were merged), yielding after each:
   - A (`spec:`/`plan:`): SECURITY-SPEC framing bullet ("every response Django makes") and the double-click residual; TECHNICAL-SPEC Configuration (placement first, what is not covered, the production release item); this plan.
   - B (`fix:`): F1, `XFrameOptionsMiddleware` first in `src/relay/settings/base.py`, its comment and the settings test (`middleware[0]`); mutation: the middleware second makes the settings test fail, and last makes the session-save case fail.
   - C (`test:`): F2, extend `src/relay_tests/settings_probe.py` to print `MIDDLEWARE` and `X_FRAME_OPTIONS`, and check `relay.settings.local` with it beside the shared-settings check; F3, move `draft_with_case`, `open_with_case` and `close` to `src/rounds/tests/conftest.py`, imported by `test_messages.py` and `test_framing.py`, no behaviour change; F4, drop the `hasattr(base, "X_FRAME_OPTIONS")` assertion; F5, the scan also refuses `X-Frame-Options` (any case) and `X_FRAME_OPTIONS` in `src/` outside tests; F6, the session-save case patches `django.contrib.sessions.models.Session.save` with `OperationalError` and expects 400 with `DENY`, plus the sign-out new-row 500 with `DENY` if cheap.

Repairs after review are separate `fix:` or `test:` commits. Test expectation changes: F6 changes the session-save case from 500 to 400, because #57's repair showed that a failed save of an existing session row gives `SessionInterrupted`'s 400 and patching `SessionStore.save` reached a path production cannot; F4 drops an assertion on how the default is reached, keeping the effective `DENY` check.

## Size estimate

`src/` outside tests: 2 lines in `base.py` (the middleware and its comment); repair F1 moves them, net 0.

## Open issues

- Only `X-Frame-Options` is sent; a CSP `frame-ancestors` directive would be a further header, outside this request.

## Checklist

- [x] Checkpoint 1: specs and plan (`bb22bf4`, `03b5653`).
- [x] Checkpoint 2: middleware and tests. `XFrameOptionsMiddleware` second in `MIDDLEWARE` in `src/relay/settings/base.py` (2 lines with its comment). Tests: `src/rounds/tests/test_framing.py` (new, 9 tests; also covers the anonymous sign-in redirect, 302). Red, before the middleware (`pytest -q -p no:randomly src/rounds/tests/test_framing.py`): 8 failed, 1 passed. Header cases failed with `KeyError: 'x-frame-options'` after their status assertion passed; the settings case failed at index 1 (`SessionMiddleware`). The exemption scan passed beforehand: it fails only if an exemption decorator is added. Green, after: 9 passed; with `test_messages.py` and `test_models.py`, 31 passed. Mutation: middleware moved last on a temporary copy, restored and checked with `cmp`; the session-save 500 case and the settings case failed, 7 passed. Ruff clean.
- [x] Checkpoint 3: no guide changes; the Developer Guide names no middleware and the User Guide shows no new text.
- [ ] Repair A: specs and plan.
- [ ] Repair B: middleware first.
- [ ] Repair C: test-only repairs.
