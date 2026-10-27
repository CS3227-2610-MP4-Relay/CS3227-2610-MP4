# Slice 58: Refuse framing on every page (#58)

Goal: every response refuses framing (`X-Frame-Options: DENY`) in every environment, replacing the clickjacking residual that the RND-6 review left open for #5 ([security spec](../specs/SECURITY-SPEC.md#rounds-observations-and-history)).

Tier: Standard, with a security review. Base: `c3ff0f3`, branch `58-refuse-framing`, stacked on #57 and RND-5's #56. Owner: zheng-jj. Budget: at most 400 changed lines under `src/` outside tests; expected 1 to 3.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27: add Django's `XFrameOptionsMiddleware` to the shared settings. HSTS and the other production-only settings stay with #5. No new dependency.

Builder's details within that scope (checkpoint 1):

- **No criterion added.** Refusing framing is a security control ([SECURITY-SPEC](../specs/SECURITY-SPEC.md#rounds-observations-and-history)) with its setting under [Configuration](../specs/TECHNICAL-SPEC.md#configuration); the production list keeps only HSTS. Tests are unmarked with a docstring naming the control, as the existing "never cached" tests are.
- **Placement:** right after `SecurityMiddleware`, not last as in Django's template. Middleware lower in the list sees only responses made inside it, so a 500 from a failed session save after a view (#57's accepted residual) or a 400 from `SessionInterrupted`, made by `SessionMiddleware`, would lack the header if the middleware were last.
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
   - a close with `SessionStore.save` failing, 500 (client with `raise_request_exception=False`); fails if the middleware is placed below `SessionMiddleware`.
   - 429 is not reachable: ACC-3 is not built.
   - Guard: no file under `src/` outside tests names `xframe_options_exempt` or `xframe_options_sameorigin` (all three decorators), scanned in Python; and the shared settings list the middleware right after `SecurityMiddleware`.
   Expected red: every header case and the settings case; the exemption scan passes beforehand (it fails only if an exemption is added). Mutation: move the middleware last; the 500 case fails. Checks: focused `pytest -q -p no:randomly src/rounds/tests/test_framing.py src/accounts/tests/test_models.py`; Ruff. Full verification is the coordinator's.
3. **Guides**, if needed: the Developer Guide names no middleware and the User Guide shows nothing new, so none expected.

Repairs after review are separate `fix:` commits. Test expectation changes: none expected.

## Size estimate

`src/` outside tests: 1 to 2 lines in `base.py`.

## Open issues

- Only `X-Frame-Options` is sent; a CSP `frame-ancestors` directive would be a further header, outside this request.

## Checklist

- [x] Checkpoint 1: specs and plan (`bb22bf4`, `03b5653`).
- [x] Checkpoint 2: middleware and tests. `XFrameOptionsMiddleware` second in `MIDDLEWARE` in `src/relay/settings/base.py` (2 lines with its comment). Tests: `src/rounds/tests/test_framing.py` (new, 9 tests; also covers the anonymous sign-in redirect, 302). Red, before the middleware (`pytest -q -p no:randomly src/rounds/tests/test_framing.py`): 8 failed, 1 passed. Header cases failed with `KeyError: 'x-frame-options'` after their status assertion passed; the settings case failed at index 1 (`SessionMiddleware`). The exemption scan passed beforehand: it fails only if an exemption decorator is added. Green, after: 9 passed; with `test_messages.py` and `test_models.py`, 31 passed. Mutation: middleware moved last on a temporary copy, restored and checked with `cmp`; the session-save 500 case and the settings case failed, 7 passed. Ruff clean.
- [ ] Checkpoint 3: guides, if needed.
