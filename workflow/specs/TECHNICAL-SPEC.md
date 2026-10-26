# Technical spec

How Relay will be built and run. What it will do is in [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md). This is a planning scaffold: no application, schema or hosted environment is implemented yet.

## Architecture

- One Django project that renders HTML on the server, with no separate front end. Application code and its tests will live under `src/`.
- PostgreSQL for application storage and database-backed tests.
- Configuration from environment variables, with no committed credentials.
- SoC LLM through one shared gateway; feature code selects authorized context before invoking it. The planned boundary is in [`ai/llm-gateway.md`](ai/llm-gateway.md).

Keep shared storage, authorization, AI transport and presentation responsibilities separate, and reuse shared components. Package boundaries and entry points will be specified with the first implementation slices. Runtime and dependency pins belong in the root configuration files.

## Data model

Only the subsections below are specified. Design workspaces, role-based accounts, rounds, requirements, cases, build references and results around the [product areas](PRODUCT-SPEC.md#areas). Before schema implementation, settle ownership, state transitions, published-case edits, submitted-observation edits and result-history/version rules. Do not infer these from a proposed screen or table name.

Before implementing persistence, decide retention for accumulated business records, workspace lifetime, expired-session handling and behaviour when shared storage capacity is exhausted, including failed writes and preservation of required result history. These are open design decisions; no cleanup subsystem or retention duration is prescribed yet.

### Accounts and workspaces

For [ACC](product/accounts.md). The demo slice deletes nothing: workspace lifetime, retention of workspaces and limit rows, and expired-session handling remain the open decisions above.

- **Workspace:** a unique name, `Demo workspace <suffix>`, and its creation time. Every workspace-owned record has a non-null workspace reference. Record lookups go through one shared helper that filters by the signed-in user's workspace before reading, so another workspace's record is indistinguishable from a missing one.
- **Account:** a custom Django user model from the first migration, with a globally unique username, a Django password hash, a non-null workspace and a role of `coordinator` or `tester`, all fixed at creation. Accounts are never staff or superusers, and every account can sign in.
- **Generated credentials:** usernames are `coord-<suffix>`, `tester1-<suffix>` and `tester2-<suffix>`, sharing the workspace's suffix of 8 random lowercase letters and digits; a suffix collision is retried. Each password is 16 random characters from `a-z`, `A-Z` and `0-9`, generated with `secrets`. Plain passwords exist only in memory while rendering the creation response.
- **Creation:** the workspace, its accounts and its sample round are written in one transaction, together with the limit counts.
- **Limit counter:** one row per scope and key, holding a window start and a count, unique on scope and key. Scopes are failed sign-in per address (15 minutes, 10), demo creation per address (1 hour, 3) and demo creation overall (24 hours, 50, one fixed key). A request reads and updates its row under a row lock; once the window has elapsed, the row restarts its window and count. The key is an HMAC of the client address keyed by Django's `SECRET_KEY`, never the address itself. Rows are not deleted.
- **Client address:** `REMOTE_ADDR`, never a client-supplied forwarding header. IPv4 addresses count individually and IPv6 addresses by their `/64` prefix. Using a hosting provider's client-address header requires a verified setting naming it; until then, a proxy address shared by all clients makes the per-address limits shared too.
- **Sessions:** Django's database-backed sessions, ending 8 hours after sign-in regardless of activity; sign-out deletes the session row.

### Rounds

For [RND](product/rounds.md). Nothing here deletes a round, build or result; retention stays with the open decisions above. A round belongs to one workspace and every other record below to one round; every lookup goes through the workspace helper and then checks that the record is in the round named by the URL.

- **Round:** a non-null workspace, a title (1 to 120 characters), a state of `draft`, `open` or `closed`, and its creation, publication and closing times. At most 20 per workspace, the sample round included.
- **Acceptance criterion:** a round and its text (1 to 500 characters). At most 20 per round.
- **Test case:** a round, a title (1 to 120), steps (1 to 2000) and an expected result (1 to 1000). At most 30 per round.
- **Case–criterion link:** a many-to-many link between a case and criteria of the same round, checked by the form and again inside the write transaction. A case always has at least one link; a linked criterion cannot be deleted.
- **Build:** a round, a label (1 to 100 characters, unique within the round), its creation time and the cases it covers. Publishing creates the first build covering every case; each retest request is a build covering the selected cases. A case's current build is the newest build covering it. At most 10 per round.
- **Results (RES):** a result will reference one case and one build covering that case, so its criteria are the case's frozen links. Foreign keys from results, builds and links use `PROTECT`; criteria and cases are deleted only while Draft, when no build or result can reference them. The result itself is specified in [RES](product/results.md).
- **Writes:** every round change runs in one transaction that locks the round row (`select_for_update`), then re-checks the state, limits, label uniqueness and that linked records are in the round. Creating a round locks the workspace row to check the round limit. Concurrent Draft edits to the same record are not merged; the last saved edit wins.
- **Sample round:** "Sample round" with 3 criteria and 4 cases of fixed synthetic text, written by the shared round code inside the [demo creation](#accounts-and-workspaces) transaction.

## Routes

Only the subsections below are specified. Each route contract must name its method, role/workspace/ownership checks, input validation, state preconditions, success result and denied/failure behaviour before implementation.

### Accounts routes

For [ACC](product/accounts.md). Every POST uses Django's CSRF protection, which also rejects an `Origin` header naming another site; a refused request gets 403 and changes nothing. A route that cannot reach storage, including its limit counts, returns 503 "Relay is temporarily unavailable. Try again later." and changes nothing. There is no Django admin route.

| Route | Method | Access | Validation and success | Denied or failed |
| --- | --- | --- | --- | --- |
| `/` | GET | Signed out | Page "Relay" with a sign-in link and the "Create a demo workspace" button | Signed in: redirect to own role home |
| `/sign-in/` | GET, POST | Anyone | If the failed sign-in limit allows it, Django's authentication checks the username and password. Success rotates the session and redirects to own role home; `next` is ignored | Invalid: form again, "Username or password is incorrect."; limited: 429 |
| `/sign-out/` | POST | Anyone | Flushes the session; redirects to `/sign-in/` with "You have signed out." | Other methods: 405 |
| `/demo/` | POST | Signed out | Checks both demo limits, creates the workspace in one transaction, then renders "Your demo workspace" with `Cache-Control: no-store`; no redirect | Signed in: redirect to own role home; other methods: 405; limited: 429 |
| `/coordinator/` | GET | Test Coordinator | Page "Coordinator home" with username and workspace name | Signed out: redirect to `/sign-in/`; Beta Tester: 403 |
| `/tester/` | GET | Beta Tester | Page "Tester home" with username and workspace name | Signed out: redirect to `/sign-in/`; Test Coordinator: 403 |

The session cookie is `HttpOnly`; session and CSRF cookies are `SameSite=Lax`, and `Secure` outside local development. Later workspace routes require a signed-in user of the route's role, look records up through the workspace helper and return 404 "Page not found." for another workspace's record.

### Rounds routes

For [RND](product/rounds.md). Every route requires a signed-in Test Coordinator and follows the [rules for every round action](product/rounds.md#rules-for-every-round-action): signed out redirects to `/sign-in/`, a Beta Tester gets 403, a missing, other-workspace or other-round record gets 404, a POST without a valid CSRF token or with a cross-site `Origin` gets 403, a request in a state not listed gets 409, and a storage failure gets 503. Invalid input re-renders the form, and a refused delete the round page, with status 200 and the message. A successful POST redirects to the round page, which shows the success message once. The Coordinator home (`/coordinator/`) also lists the workspace's rounds. `<round>`, `<criterion>` and `<case>` are integer IDs.

| Route | Method | States | Page title or result |
| --- | --- | --- | --- |
| `/coordinator/rounds/new/` | GET, POST | — | "New round"; creates a Draft round |
| `/coordinator/rounds/<round>/` | GET | Any | The round's title, its state and, once Open, each case's current build |
| `/coordinator/rounds/<round>/edit/` | GET, POST | Draft | "Edit round"; changes the title |
| `/coordinator/rounds/<round>/criteria/new/` | GET, POST | Draft | "New acceptance criterion" |
| `/coordinator/rounds/<round>/criteria/<criterion>/edit/` | GET, POST | Draft | "Edit acceptance criterion" |
| `/coordinator/rounds/<round>/criteria/<criterion>/delete/` | POST | Draft | Deletes an unlinked criterion |
| `/coordinator/rounds/<round>/cases/new/` | GET, POST | Draft | "New test case" |
| `/coordinator/rounds/<round>/cases/<case>/edit/` | GET, POST | Draft | "Edit test case" |
| `/coordinator/rounds/<round>/cases/<case>/delete/` | POST | Draft | Deletes the case and its links |
| `/coordinator/rounds/<round>/publish/` | POST | Draft | Build label form on the round page; creates the first build and opens the round |
| `/coordinator/rounds/<round>/results/` | GET | Open, Closed | "Results: <title>" |
| `/coordinator/rounds/<round>/retest/` | GET, POST | Open | "Request a retest"; creates a build covering the selected cases |
| `/coordinator/rounds/<round>/close/` | POST | Open | Button on the round page; closes the round |

## Configuration

The `.env.example` file may contain only empty placeholders and throwaway local database values. Runtime settings and validation will be specified with the application scaffold. Tests must use isolated configuration and fake provider responses, without inheriting production credentials or contacting SoC LLM.

## Environments

| Environment | Planned runtime | Database | Configuration |
| --- | --- | --- | --- |
| Local development | Python virtual environment running Django; Docker optional for the database | Local PostgreSQL, separate from production | Developer configuration; local debug only |
| CI validation | GitHub Actions running lint, formatting and tests | Throwaway PostgreSQL when app tests exist | Fixed non-secret test values; fake LLM provider |
| Production | Vercel's native Django/Python runtime | Separate managed PostgreSQL | Production-only credentials; debug off |

No dedicated staging environment or Docker app image is planned. Development and production use separate databases and credentials. The team manages deployment through GitHub Actions; a build-and-host environment supplied by an AI tool is not part of the delivery plan.

## Product website

The static GitHub Pages site uses `docs/index.md`, `docs/Reflections.md` and `docs/_config.yml`, with GitHub's Cayman theme. Its configured organization URL is `https://cs3227-2610-mp4-relay.github.io` and repository base path is `/CS3227-2610-MP4`; this configuration does not establish that the site is published. The guides link to their source in the [team repository](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4) and are excluded from the site build. Check rendered links before publishing.

## Release verification

Delivery will verify the final candidate before a controlled production deployment, then run smoke checks. Deployment workflows, migration handling, checked-source provenance, failure recovery and smoke-check contracts remain to be designed and tested. The scaffold does not claim any release controls are configured.

### Review decisions and operator prerequisites

Default-branch protection and secret scanning are configured under the [CI and dependencies](SECURITY-SPEC.md#ci-and-dependencies) control.

Future work:

- Verify the [team repository](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4) is publicly accessible; confirm role ownership and initial slice issues/milestones.
- Configure and verify hosted environment restrictions.
- Configure GitHub Pages and verify its built artifact and links before publication.
- Create the Vercel project and separate managed PostgreSQL database; confirm the actual provider runtime, limits, secure database connection and least-privilege deployment access.
- Keep production credentials in protected production settings, outside development, CI validation and untrusted builds. Design and verify migrations and deployment approvals before enabling releases.
- Verify the team's SoC LLM model availability and limits before fixing model and quota settings.
