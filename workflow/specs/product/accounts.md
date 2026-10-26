# Accounts

Planning area `ACC`. The criteria below are specified but not implemented yet. See the [roles](../PRODUCT-SPEC.md#roles); routes, storage and limit details are in the [technical spec](../TECHNICAL-SPEC.md#accounts-routes), and controls in the [security spec](../SECURITY-SPEC.md#sign-in-and-access-control).

Every account belongs to exactly one workspace and has exactly one role, Test Coordinator or Beta Tester. Accounts exist only through demo workspace creation (ACC-2). Self-registration, password reset, invitations, adding or removing accounts, email, MFA and SSO are not part of Relay.

Each criterion is labelled happy, boundary, failure, adversarial or ambiguous.

## ACC-1 Sign in and out by role

A user signs in with a username and password and works on their own role's home page: "Coordinator home" for a Test Coordinator, "Tester home" for a Beta Tester. A home page shows the user's username and workspace name.

- **ACC-1.1** (happy) Signing in with a valid username and password opens the user's own role home page, whatever `next` value or other redirect target the request carries.
- **ACC-1.2** (failure) A wrong password, an unknown username or a blank field shows the sign-in page again with "Username or password is incorrect." and leaves the visitor signed out. The response does not reveal which field was wrong.
- **ACC-1.3** (failure) A signed-out visitor requesting a role home page is redirected to the sign-in page.
- **ACC-1.4** (adversarial) A signed-in user requesting the other role's home page gets a 403 page saying "You do not have access to this page." It shows no workspace data, and the user stays signed in.
- **ACC-1.5** (happy) Signing out ends the session on the server and shows the sign-in page with "You have signed out." Requesting a role home page afterwards, even with the old session cookie, redirects to the sign-in page. A GET request to the sign-out route does not sign out.
- **ACC-1.6** (boundary) A session ends 8 hours after sign-in, whatever the activity. Just before that time a role home page opens; at or after it, the request is redirected to the sign-in page.
- **ACC-1.7** (ambiguous) Signing in while already signed in, as the same or another user, ends the earlier session and starts a new one with a new session identifier. The earlier identifier no longer authenticates.
- **ACC-1.8** (adversarial) A sign-in or sign-out request without a valid CSRF token, or whose `Origin` header names another site, is refused with 403 and changes nothing.

## ACC-2 Create an isolated demo workspace

A signed-out visitor can choose "Create a demo workspace" on the home page to get a fresh workspace for trying both roles. A new demo workspace also contains a sample draft round, specified in [rounds](rounds.md).

- **ACC-2.1** (happy) Creating a demo workspace shows a "Your demo workspace" page listing the workspace name and, for each account, its role, username and password, with "Save these passwords now. They will not be shown again." The visitor stays signed out.
- **ACC-2.2** (boundary) The workspace has exactly 1 Test Coordinator and 2 Beta Testers. Each listed username and password signs in to that account's role home page, which shows the new workspace's name.
- **ACC-2.3** (adversarial) Passwords are stored only as password hashes. No GET page, later response, log entry or database field shows a generated password again, and the creation response tells the browser not to cache it.
- **ACC-2.4** (adversarial) Two workspaces share no accounts or records. A user's pages show only their own workspace's records, and a request naming another workspace's record gets the same "Page not found." 404 as a record that does not exist.
- **ACC-2.5** (failure) If storage fails during creation, no part of the workspace, its accounts or its sample round remains, no credentials are shown, and the visitor sees a 503 page saying "Relay is temporarily unavailable. Try again later."
- **ACC-2.6** (ambiguous) A signed-in user cannot create a demo workspace: the home page and the creation route redirect them to their own role home page and create nothing.
- **ACC-2.7** (adversarial) A creation request by GET, without a valid CSRF token, or whose `Origin` header names another site, is refused and creates nothing.

## ACC-3 Limit abuse of sign-in and demo workspace creation

Limits are counted per client address, as defined in the [technical spec](../TECHNICAL-SPEC.md#accounts-and-workspaces), in a window that starts at the first counted request.

- **ACC-3.1** (boundary) The 10th failed sign-in from one client address within 15 minutes still gets the normal failure message. Any further sign-in from that address in the window, even with a correct password, gets a 429 sign-in page saying "Too many sign-in attempts. Try again later." and does not sign in.
- **ACC-3.2** (boundary) Once the 15-minute window has elapsed, sign-in from that address is checked normally again.
- **ACC-3.3** (ambiguous) Successful sign-ins neither count toward nor reset the failed sign-in count.
- **ACC-3.4** (boundary) The 4th demo workspace creation from one client address within 1 hour, and the 51st creation from all addresses within 24 hours, get a 429 page saying "Too many demo workspaces have been created recently. Try again later." and create nothing.
- **ACC-3.5** (adversarial) Varying the username or sending a forged `X-Forwarded-For` header does not escape a limit, and one address reaching its limit does not limit another address.
- **ACC-3.6** (adversarial) Concurrent requests cannot exceed a limit: with 2 demo creations left for an address, 5 simultaneous requests create at most 2 workspaces.
- **ACC-3.7** (failure) If a limit count cannot be read or recorded, the request is refused with the 503 page from ACC-2.5, signs no one in and creates nothing.
