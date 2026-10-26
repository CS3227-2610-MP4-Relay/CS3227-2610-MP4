# Accounts

Planning area `ACC`. ACC-1 is implemented; ACC-2 and ACC-3 are specified but not implemented yet. See the [roles](../PRODUCT-SPEC.md#roles); storage and routes are in the [technical spec](../TECHNICAL-SPEC.md#accounts-and-workspaces), and controls in the [security spec](../SECURITY-SPEC.md#sign-in-and-access-control).

Every account belongs to exactly one workspace and has exactly one role, Test Coordinator or Beta Tester. Accounts exist only through demo workspace creation (ACC-2). Self-registration, password reset, invitations, adding or removing accounts, email, MFA and SSO are not part of Relay.

Each criterion is labelled happy, boundary, failure, adversarial or ambiguous.

## ACC-1 Sign in and out by role

A user signs in with a username and password and works on their own role's home page: "Coordinator home" for a Test Coordinator, "Tester home" for a Beta Tester. A home page shows the user's username and workspace name. The Relay start page, at `/`, is separate from both.

- **ACC-1.1** (happy) Signing in with a valid username and password opens the user's own role home page, whatever `next` value or other redirect target the request carries.
- **ACC-1.2** (failure) A wrong password, an unknown username or a blank field shows the sign-in page again with "Username or password is incorrect." The response does not reveal which field was wrong. A signed-out visitor stays signed out, and a signed-in user's existing session is unchanged.
- **ACC-1.3** (failure) A signed-out visitor requesting a role home page is redirected to the sign-in page.
- **ACC-1.4** (adversarial) A signed-in user requesting the other role's home page gets a 403 page saying "You do not have access to this page." It shows no workspace data, and the user stays signed in.
- **ACC-1.5** (happy) Signing out ends the session on the server and shows the sign-in page with "You have signed out." Requesting a role home page afterwards, even with the old session cookie, redirects to the sign-in page. A GET request to the sign-out route does not sign out.
- **ACC-1.6** (boundary) A session ends 8 hours after sign-in, whatever the activity, including requests that change the session in between. Just before that time a role home page opens; at or after it, the request is redirected to the sign-in page.
- **ACC-1.7** (adversarial) Every successful sign-in, whether the visitor was signed out or signed in as anyone, starts a session with a new identifier. Any identifier held before that sign-in no longer authenticates.
- **ACC-1.8** (adversarial) A sign-in or sign-out request without a valid CSRF token, or whose `Origin` header names another origin, is refused with 403 and changes nothing.

## ACC-2 Create an isolated demo workspace

A signed-out visitor can choose "Create a demo workspace" on the Relay start page to get a fresh workspace for trying both roles. The workspace also contains a sample draft round, which is RND-7 in [rounds](rounds.md).

The "Your demo workspace" page, titled and headed "Your demo workspace", shows "Workspace: <workspace name>", then a table with the columns "Role", "Username" and "Password" and one row per account: the Test Coordinator first, then the two Beta Testers. Below it are "Save these passwords now. They will not be shown again." and a "Sign in" link to the sign-in page. The 503 page and the 404 page show only their message as their heading.

- **ACC-2.1** (happy) Creating a demo workspace shows a "Your demo workspace" page listing the workspace name and, for each account, its role, username and password, with "Save these passwords now. They will not be shown again." The visitor stays signed out.
- **ACC-2.2** (boundary) The workspace has exactly 1 Test Coordinator and 2 Beta Testers. Each listed username and password signs in to that account's role home page, which shows the new workspace's name.
- **ACC-2.3** (adversarial) Passwords are stored only as password hashes. No GET page, later response, log entry or database field shows a generated password again, and the creation response tells the browser not to cache it.
- **ACC-2.4** (adversarial) Two workspaces share no accounts, and a user's pages show only their own workspace. Every lookup of a workspace record goes through one shared helper, which treats another workspace's record as not existing. A record named in the URL then gives a 404 page saying "Page not found."; an ID submitted in a form gets that form's validation message.
- **ACC-2.5** (failure) If storage or rendering the response fails during creation, no part of the workspace, its accounts or its sample round remains, no credentials are shown, and the visitor sees a 503 page saying "Relay is temporarily unavailable. Try again later."
- **ACC-2.6** (ambiguous) A signed-in user cannot create a demo workspace: the Relay start page and the creation route redirect them to their own role home page and create nothing.
- **ACC-2.7** (adversarial) A creation request by GET, without a valid CSRF token, or whose `Origin` header names another origin, is refused and creates nothing.

## ACC-3 Limit abuse of sign-in and demo workspace creation

Failed sign-ins and demo creations are limited per client address, as defined in the [technical spec](../TECHNICAL-SPEC.md#accounts-and-workspaces), and demo creations also in total across all addresses. Each limit's window starts at its first counted request. The limits allow for peers in one lab sharing an address.

- **ACC-3.1** (boundary) The 30th failed sign-in from one client address within 15 minutes still gets the normal failure message. Any further sign-in from that address in the window, even with a correct password, gets a 429 sign-in page saying "Too many sign-in attempts. Try again later." and does not sign in.
- **ACC-3.2** (boundary) Just before a limit's window ends, its refused requests are still refused; at or after the end, they are checked normally again.
- **ACC-3.3** (ambiguous) Only failed sign-ins, including blank fields, and completed demo creations count. Successful sign-ins neither count nor reset the failed count. Refused (403, 429 or 503) requests and failed creations count toward no limit, and a refused sign-in does not extend its window. Viewing the sign-in page is never limited.
- **ACC-3.4** (boundary) The 11th demo workspace creation from one client address within 1 hour, and the 201st from all addresses within 24 hours, get a 429 page saying "Too many demo workspaces have been created recently. Try again later." and create nothing.
- **ACC-3.5** (adversarial) Varying the username or sending a forged `X-Forwarded-For` header does not escape a limit, and one address reaching its limit does not limit another address. Requests with a missing or unparseable client address share one "unknown" count instead of failing.
- **ACC-3.6** (adversarial) Concurrent creations cannot exceed a limit: with 2 demo creations left for an address, 5 simultaneous requests create at most 2 workspaces.
- **ACC-3.7** (failure) If a limit count cannot be read or recorded, including a lock or statement timeout, the request gets the 503 page from ACC-2.5, signs no one in and creates nothing.
- **ACC-3.8** (adversarial) Concurrent sign-ins cannot exceed the limit: with 1 failed sign-in left for an address, 5 simultaneous wrong-password sign-ins give at most 1 normal failure, and the rest get the 429 page.
