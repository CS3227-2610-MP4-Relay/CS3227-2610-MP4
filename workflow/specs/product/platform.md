# Platform

Platform area `PLT`; see the [product spec](../PRODUCT-SPEC.md).

## PLT-1: Django foundation and continuous verification

- **PLT-1.1:** A signed-out visitor can GET `/` without an account and receive an HTML page titled `Relay`, headed `Relay`, with the text `A beta-testing portal for small software teams.` and `Testing workflows are coming soon.` A HEAD request succeeds with an empty body. The page has a "Sign in" link to `/sign-in/` and a "Create a demo workspace" button that POSTs to `/demo/`, and no other links, forms or actions. A signed-in user is redirected to their own role home ([ACC-2.6](accounts.md#acc-2-create-an-isolated-demo-workspace)).
- **PLT-1.2:** `/` accepts only GET and HEAD. Other HTTP methods return 405 and advertise GET and HEAD; requests do not create application state.
- **PLT-1.3:** With debug disabled, unknown routes return a generic 404 and unexpected server failures return a generic 500, without reflecting request data, exception details or source paths.
- **PLT-1.4:** Local startup uses explicit local settings, requires a nonblank environment secret key, permits only loopback hosts/database connections, and rejects malformed debug or host configuration. No production startup configuration is supplied.
- **PLT-1.5:** Automated tests select fixed test-only settings, with debug disabled and a separate PostgreSQL database, ignoring inherited runtime secrets, debug, hosts, database and provider variables. Settings never read dotenv files or call an AI provider.
- **PLT-1.6:** Database tests can create an isolated PostgreSQL test database, write/read synthetic data, and roll back test writes without changing the normal local database.
- **PLT-1.7:** Pull requests and pushes to `main` run lint, formatting, Django system checks and the complete pytest suite in the existing `verify` CI job against throwaway PostgreSQL, with pinned actions, read-only repository access and no stored secrets or deployment.

## Planned work

- Shared storage, authorization and bounded SoC LLM access.
- Controlled deployment with smoke checks, extending the local/test foundation.
- GitHub Pages product site and accurate user/developer documentation.

Before each slice, define its observable behaviour, important boundaries, denied actions and failure cases. Architecture and delivery decisions belong in the [technical spec](../TECHNICAL-SPEC.md); threats and controls belong in the [security spec](../SECURITY-SPEC.md).
