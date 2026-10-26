# Specify accounts, demo workspaces and abuse limits (#2, #3, #4)

Goal: specify sign-in by role, isolated demo workspaces and their abuse limits, as the base for every later route, before any code exists.

Tier: High, because it specifies sign-in, sessions and role/workspace permissions. Base: `03f7008`. Spec only: no code, tests, dependencies or guide changes. The Django project (#1) does not exist yet.

Decisions (human, zheng-jj): requirements live in [`accounts.md`](../specs/product/accounts.md) with prefix `ACC`: ACC-1 sign in and out by role (#2), ACC-2 create an isolated demo workspace (#3), ACC-3 limit abuse of sign-in and demo workspace creation (#4). Signed-out visitors can create a demo workspace with exactly 1 Test Coordinator and 2 Beta Testers; generated usernames and passwords are shown once, on the creation response, and stored only as hashes. Sign-in is by username and password; each user lands on their own role's page and is refused the other role's. A user never sees or changes another workspace's records. Abuse limits cover sign-in and demo creation. No self-registration, password reset, invitations, account changes, email, MFA or SSO. A new workspace's sample draft round belongs to the rounds spec (RND), written afterwards. The human raised the one-requirement budget for this spec-only PR; each requirement still fits one later code slice (ACC-1 has 8 criteria; ACC-2 and ACC-3 have 7 each).

| Requirement | Issue | Code slice |
| --- | --- | --- |
| ACC-1 | #2 | After #1 |
| ACC-2 | #3 | After ACC-1 |
| ACC-3 | #4 | After ACC-2 |

## Proposed defaults (confirm in PR review)

- Routes `/`, `/sign-in/`, `/sign-out/` (POST only), `/demo/` (POST only), `/coordinator/` and `/tester/`; page titles "Relay", "Coordinator home", "Tester home" and "Your demo workspace". No Django admin route.
- Messages: "Username or password is incorrect.", "You have signed out.", "You do not have access to this page." (403), "Page not found." (404), "Save these passwords now. They will not be shown again.", "Too many sign-in attempts. Try again later." and "Too many demo workspaces have been created recently. Try again later." (429), and "Relay is temporarily unavailable. Try again later." (503).
- One failure message for wrong password, unknown username and blank fields. Sign-in ignores `next` and always lands on the user's own role home.
- Usernames `coord-`, `tester1-` and `tester2-` plus a shared random 8-character lowercase-and-digit suffix; workspace name `Demo workspace <suffix>`. Passwords: 16 random characters from `a-z`, `A-Z`, `0-9`.
- Creation does not sign the visitor in; a signed-in user cannot create a workspace. The creation response is rendered directly with `Cache-Control: no-store`, so no GET page can show the passwords again.
- Sessions: Django database sessions, fixed 8-hour lifetime from sign-in, rotated at sign-in, deleted at sign-out. Session cookie `HttpOnly`; session and CSRF cookies `SameSite=Lax` and `Secure` outside local development. Django CSRF with its `Origin` check; refused requests get 403.
- Cross-role pages get 403; another workspace's record gets 404, identical to a missing record.
- Limits in fixed windows starting at the first counted request: 10 failed sign-ins per address per 15 minutes, then refused even with a correct password; 3 demo creations per address per hour; 50 demo creations overall per 24 hours. Successful sign-ins neither count nor reset.
- Client address: `REMOTE_ADDR`, IPv6 grouped by `/64`, never a client-supplied forwarding header; stored only as an HMAC keyed by `SECRET_KEY`. One counter row per scope and key, updated under a row lock; rows are not deleted.
- Storage or limit-count failure: 503, nothing created and no one signed in; creation, accounts, sample round and limit counts share one transaction.

## Out of scope

Everything the human excluded above; the sample round's contents (RND); deleting or expiring workspaces, sessions or limit rows; a cleanup subsystem; CAPTCHA; per-username lockout; any User Guide change.

## Open questions

- Not decided: workspace lifetime and retention of workspaces, accounts, limit rows and expired sessions, and behaviour when storage is full ([technical spec](../specs/TECHNICAL-SPEC.md#data-model)). With the overall cap, at most 50 workspaces a day accumulate until this is settled.
- Operator prerequisite: on Vercel, verify what `REMOTE_ADDR` and the provider's client-address header contain before relying on per-address limits. Until then, all clients may share one address's limits.
- For Whimsyturtle: whether the proposed limits, the 8-hour session and the 403-versus-404 split suit peer demos; whether an attacker using up the overall cap is acceptable.
- Order: if ACC-2 is implemented before RND's sample round exists, the RND slice adds the sample round to the creation transaction.
- Rotating `SECRET_KEY` resets limit counts and signs everyone out.

## Checklist

- [x] Write ACC-1 to ACC-3 in `accounts.md`; adjust the false sentence in `PRODUCT-SPEC.md`.
- [x] Add `### Accounts and workspaces` and `### Accounts routes` to `TECHNICAL-SPEC.md`; update "Sign-in and access control" in `SECURITY-SPEC.md`.
- [x] Read changed sections back; check criterion counts and IDs.
- [x] Run full verification and `git diff --check`.
- [ ] Verifier and security-reviewer review the fixed candidate.
- [ ] Human review of the proposed defaults and merge decision.

Check evidence (builder, macOS, `.venv`): Ruff lint and format passed; pytest reported 70 passed, 85 subtests passed. `git diff --check` is clean, and `check_scope.py builder --base 03f7008` reported all changes within scope.
