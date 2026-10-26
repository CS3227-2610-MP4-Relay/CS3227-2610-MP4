# Specify accounts, demo workspaces and abuse limits (#2, #3, #4)

Goal: specify sign-in by role, isolated demo workspaces and their abuse limits, as the base for every later route, before any code exists.

Tier: High, because it specifies sign-in, sessions and role/workspace permissions. Base: `03f7008`. Spec only: no code, tests, dependencies or guide changes. The Django project (#1) does not exist yet.

Decisions (human, zheng-jj):

- Requirements live in [`accounts.md`](../specs/product/accounts.md) with prefix `ACC`: ACC-1 sign in and out by role (#2), ACC-2 create an isolated demo workspace (#3), ACC-3 limit abuse of sign-in and demo workspace creation (#4).
- Signed-out visitors can create a demo workspace with exactly 1 Test Coordinator and 2 Beta Testers; generated usernames and passwords are shown once, on the creation response, and stored only as hashes.
- Sign-in is by username and password; each user lands on their own role's page and is refused the other role's. A user never sees or changes another workspace's records. Abuse limits cover sign-in and demo creation.
- No self-registration, password reset, invitations, account changes, email, MFA or SSO. The sample draft round belongs to RND (RND-7). Rounds follow Draft → Open → Closed, as confirmed in [rounds-spec](rounds-spec.md).
- From the rounds review: a record named in the URL from another workspace gets the 404, but an ID submitted in a form gets a form message instead. A GET to a POST-only route gets 405 everywhere. The coordinator applied the ACC-2.4 wording.
- The human raised the one-requirement budget for this spec-only PR; each requirement still fits one later code slice (ACC-1 has 8 criteria, ACC-2 has 7, ACC-3 has 8).
- Repair round 1: limits are loosened for shared networks, because peers in one lab share an address: 30 failed sign-ins per address per 15 minutes, 10 demo creations per address per hour and 200 overall per 24 hours.
- Repair round 1: production is not released until Vercel's real client-address source is verified and recorded ([release gate](../specs/TECHNICAL-SPEC.md#release-verification)). A missing or unparseable address counts in one shared "unknown" counter instead of giving a 503.
- Repair round 1: the retention, workspace-lifetime and expired-session decision is a precondition of ACC-1's code slice. Until then, hashed addresses are kept indefinitely. Unbounded session and counter rows are recorded as residual risks in the [security spec](../specs/SECURITY-SPEC.md#sign-in-and-access-control).

| Requirement | Issue | Code slice |
| --- | --- | --- |
| ACC-1 | #2 | After #1 and the retention decision |
| ACC-2 | #3 | After ACC-1; not deployed to production before ACC-3 |
| ACC-3 | #4 | After ACC-2 |

## Proposed defaults (confirm in PR review)

- Routes `/` (the Relay start page), `/sign-in/`, `/sign-out/` (POST only), `/demo/` (POST only), `/coordinator/` and `/tester/`; page titles "Relay", "Coordinator home", "Tester home" and "Your demo workspace".
- The messages, the 403, 404, 429 and 503 pages, and the 8-hour session lifetime are as written in the criteria.
- One failure message for a wrong password, an unknown username and blank fields; a signed-in user who submits wrong credentials gets it, and their session is unchanged. Sign-in ignores `next`.
- Usernames `coord-`, `tester1-` and `tester2-` plus a shared random 8-character lowercase-and-digit suffix; workspace name `Demo workspace <suffix>`. Passwords: 16 random characters from `a-z`, `A-Z`, `0-9`.
- Creation does not sign the visitor in, and a signed-in user cannot create a workspace. The creation response is rendered inside the creation transaction with `Cache-Control: no-store`. Reload resubmission and the back/forward cache are accepted [residual gaps](../specs/SECURITY-SPEC.md#sign-in-and-access-control).
- Sessions: Django database sessions with an absolute expiry set at sign-in, a new identifier at every sign-in, and deletion at sign-out. Session cookie `HttpOnly`; session and CSRF cookies `SameSite=Lax` and `Secure` outside local development. Django CSRF with its `Origin` check; refused requests get 403.
- Production settings: exact `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`, HTTPS detection only through a verified forwarded-protocol header, frame blocking and HSTS.
- Cross-role pages get 403, and another workspace's record gets a 404 identical to a missing record. Routes check the role before looking records up.
- Limits use fixed windows starting at the first counted request. Bursts across a window boundary are accepted. Refused or failed requests count toward nothing.
- Client address: `REMOTE_ADDR`, with IPv6 grouped by `/64`, and never a client-supplied forwarding header. Addresses are stored only as `salted_hmac` keys with their own salt.
- Counters: a migration creates the overall row, and per-address rows use insert-or-update. Creation hashes passwords first, then locks the per-address row and then the overall row. Sign-in locks its per-address row and checks the count and password in one transaction (repair round 2), so a rollback or timeout leaves no counted failure. Cost: sign-ins from one address are serialised, each holding the lock for about one password hash, so a lab signing in together queues; the lock timeout must allow for that queue. Because nothing is reserved, a concurrent attempt is never refused one attempt early. A lock or statement timeout gives the 503 page.
- The custom user model has no staff, superuser or permission fields, and `django.contrib.admin` is not installed.

## Notes for the code slices

- The custom user model must exist from #1's first migration; flag this for Whimsyturtle's #1.
- ACC-2.4 is tested through the shared lookup helper in unit tests. Later record routes test isolation under their own criteria. Ownership filtering of testers' private records is RES's job (for Whimsyturtle).
- Time control uses `unittest.mock`, with no new dependency. ACC-3.6 and ACC-3.8 need PostgreSQL `TransactionTestCase` tests with threads.
- If ACC-2 is implemented before RND-7, the RND slice adds the sample round to the creation transaction.
- The production settings under [Configuration](../specs/TECHNICAL-SPEC.md#configuration) come with #1's settings module, and their check runs under the release gate for #5's deploy; both are Whimsyturtle's, so flag this for Whimsyturtle.

## Out of scope

Everything the human excluded above; the sample round's contents (RND); deleting or expiring workspaces, sessions or limit rows; a cleanup subsystem; CAPTCHA; per-username lockout; any User Guide change. A trusted-proxy header setting is also out of ACC-3, unless the release-gate verification shows it is needed; that would be a separate decision.

## Open questions

- Not decided, and needed before ACC-1's code slice: workspace lifetime, retention of workspaces, accounts, limit rows and expired sessions, and behaviour when storage is full ([technical spec](../specs/TECHNICAL-SPEC.md#data-model)). Until then, up to 200 workspaces a day can accumulate, plus unbounded session and counter rows.
- For Whimsyturtle: whether the limits, the 8-hour session and the 403-versus-404 split suit peer demos, and whether an attacker using up the overall cap is acceptable.
- Rotating `SECRET_KEY` resets limit counts and signs everyone out.

## Checklist

- [x] Write ACC-1 to ACC-3 in `accounts.md`; adjust the false sentence in `PRODUCT-SPEC.md`.
- [x] Add `### Accounts and workspaces` and `### Accounts routes` to `TECHNICAL-SPEC.md`; update "Sign-in and access control" in `SECURITY-SPEC.md`.
- [x] Read changed sections back; check criterion counts and IDs.
- [x] Run full verification and `git diff --check`.
- [x] Round 0: verifier and security-reviewer review the candidate.
- [x] Repair round 1: apply the human's decisions and the review findings.
- [x] Verifier and security-reviewer re-review the repaired range.
- [x] Repair round 2: transactional sign-in counting, residual gaps moved to the security spec, production-settings owners.
- [ ] Verifier and security-reviewer re-review the round-2 range.
- [ ] Human review of the proposed defaults and merge decision.

Check evidence, repair round 1 (builder, macOS, `.venv`): Ruff lint and format passed; pytest reported 70 passed, 85 subtests passed. `git diff --check` is clean, and `check_scope.py builder --base 83a821f` reported all changes within scope.

Check evidence, repair round 2 (builder, macOS, `.venv`): Ruff lint and format passed; pytest reported 70 passed, 85 subtests passed. `git diff --check` is clean, and `check_scope.py builder --base 8e7d180` reported all changes within scope.
