# Technical spec

How Relay will be built and run. What it will do is in [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md). The application foundation is local/CI only; business schema and hosted environments remain planned.

## Architecture

- One Django project that renders HTML on the server, with no separate front end. Application code and its tests will live under `src/`.
- PostgreSQL for application storage and database-backed tests.
- Configuration from environment variables, with no committed credentials.
- SoC LLM through one shared gateway; feature code selects authorized context before invoking it. The planned boundary is in [`ai/llm-gateway.md`](ai/llm-gateway.md).

`src/manage.py` starts the `relay` Django project; `relay.wsgi` is its WSGI entry point and `relay.pages` owns public presentation. Shared templates live in `src/relay/templates/`. The `accounts` app (`src/accounts/`) owns the [workspace and account models](#accounts-and-workspaces) and the accounts routes, with Django's `auth`, `contenttypes`, `sessions` and `messages` apps; `django.contrib.admin` is never installed. ACC-1 adds them; until then no auth/session apps or business models are installed. Runtime and dependency pins belong in the root configuration files.

## Data model

Only the subsections below are specified. Design workspaces, role-based accounts, rounds, requirements, cases, build references and results around the [product areas](PRODUCT-SPEC.md#areas). Before schema implementation, settle ownership, state transitions, published-case edits, submitted-observation edits and result-history/version rules. Do not infer these from a proposed screen or table name.

Persistence and retention, decided for ACC-1 (see its [plan](../plans/2-sign-in-by-role.md)):

- Workspaces, accounts, rounds, results, limit rows and their hashed address keys are kept for the life of the course deployment. Nothing expires or is deleted automatically, and there is no cleanup subsystem.
- An expired session is refused by its absolute expiry; its row is not deleted automatically. Sign-out deletes its own session row.
- When shared storage is exhausted, a failed write rolls back its transaction and the user gets that route's existing error page: the generic 500 of [PLT-1.3](product/platform.md#plt-1-django-foundation-and-continuous-verification), or the 503 page that [ACC-2.5](product/accounts.md#acc-2-create-an-isolated-demo-workspace) and [ACC-3.7](product/accounts.md#acc-3-limit-abuse-of-sign-in-and-demo-workspace-creation) define. Existing records, including result history, are never deleted or overwritten to make room.
- Before peer testing, an operator checks the hosting database's storage use. Exhaustion and unbounded session and counter growth are [accepted residual risks](SECURITY-SPEC.md#sign-in-and-access-control) for the course deployment.

### Accounts and workspaces

For [ACC](product/accounts.md). Retention follows the [persistence decision](#data-model) above.

- **Workspace:** a unique name, `Demo workspace <suffix>`, and its creation time. Every workspace-owned record has a non-null workspace reference. Routes check the role first, then look records up through one shared helper that filters by the signed-in user's workspace before reading and gives the 404 of [ACC-2.4](product/accounts.md#acc-2-create-an-isolated-demo-workspace) for any other workspace's record.
- **Account:** a custom Django user model (`accounts.User`, the `AUTH_USER_MODEL`), added by ACC-1 before any persistent database (in particular production, under #5) is migrated. It has a globally unique username, a Django password hash, a non-null workspace (`PROTECT`) and a role of `coordinator` or `tester`, all fixed at creation, plus Django's last-sign-in time. The model has no staff, superuser or permission fields, and `django.contrib.admin` is not installed, so there is no admin route.
- **Generated credentials:** usernames are `coord-<suffix>`, `tester1-<suffix>` and `tester2-<suffix>`, sharing the workspace's suffix of 8 random lowercase letters and digits; a suffix collision is retried. Each password is 16 random characters from `a-z`, `A-Z` and `0-9`, generated with `secrets` and hashed before any lock is taken. Plain passwords exist only in memory while rendering the creation response.
- **Creation:** one transaction holds the limit counts, the workspace, its accounts, its sample round and the rendering of the creation response, so any failure rolls everything back ([ACC-2.5](product/accounts.md#acc-2-create-an-isolated-demo-workspace)).
- **Limit counter:** one row per scope and key, holding a window start and a count, unique on scope and key; scopes, numbers and windows are in [ACC-3](product/accounts.md#acc-3-limit-abuse-of-sign-in-and-demo-workspace-creation). A migration creates the overall creation row; per-address rows are inserted or updated in one statement. A creation locks its per-address row, then the overall row. A sign-in locks its per-address row, checks the count, checks the password and records any failure in one transaction, so concurrent attempts cannot overshoot and a rollback records nothing. These transactions set a 5-second lock timeout and a statement timeout, and PostgreSQL's `idle_in_transaction_session_timeout` is set so an abandoned transaction cannot keep a lock. That timeout must be longer than the work done while a lock is held, because PostgreSQL counts the session as idle while Python works: one password hash during sign-in, and writing and rendering during demo creation, whose passwords are hashed first. Any timeout gives the 503 of ACC-3.7. The idle timeout, and lock wait plus the work under the lock, must stay below the platform's function time limit, which is verified under the [release gate](#release-verification). Once a window has elapsed, the row restarts its window and count.
- **Client address:** `REMOTE_ADDR`, never a client-supplied forwarding header. IPv4 addresses count individually and IPv6 addresses by their `/64` prefix; a missing or unparseable address uses the fixed key `unknown`. The stored key is Django's `salted_hmac` of the address with its own salt, never the address itself. Production depends on the client-address gate under [Release verification](#release-verification); a trusted-proxy header setting is a separate decision, needed only if that verification shows it.
- **Sessions:** Django's database-backed sessions. Sign-in sets an absolute expiry time 8 hours ahead, so later session writes cannot extend it ([ACC-1.6](product/accounts.md#acc-1-sign-in-and-out-by-role)); sign-out deletes the session row. Expired rows are not deleted automatically ([persistence decision](#data-model)).

### Rounds

For [RND](product/rounds.md). Field limits, caps and messages are in its criteria. Nothing here deletes a round, build or result; retention and full storage follow the [persistence decision](#data-model). A round belongs to one workspace and every other record below to one round. URL records are looked up through the workspace helper, then checked to be in the round the URL names; form-submitted IDs are checked against the round in the form's validation ([checking order](product/rounds.md#rules-for-every-round-action)).

- **Round:** a non-null workspace, a title, a state of `draft`, `open` or `closed`, and its creation, publication and closing times.
- **Acceptance criterion** and **test case:** a round and their text fields ([RND-2.4](product/rounds.md#rnd-2-manage-acceptance-criteria-and-test-cases)), validated with Django's null-character validator and a visible-character check.
- **Case–criterion link:** a many-to-many link between a case and criteria of the same round, checked by the form and again inside the write transaction.
- **Build:** a round, a label, a comparison key (the label with format characters, Unicode category Cf, removed and then NFC-normalised), its creation time and the cases it covers, with a database unique constraint on round and comparison key ([RND-5.3](product/rounds.md#rnd-5-request-a-retest)). Publishing creates the first build covering every case; a retest request is stored as a build covering the selected cases. A case's current build is the newest build covering it.
- **Results (RES), provisional:** a result will reference one case and one build of the same round that covers the case, so its criteria are the case's frozen links. The result itself is specified in [RES](product/results.md).
- **Deletion:** every foreign key here, including those from results, uses `PROTECT`. Deleting a case first deletes its links explicitly in the same transaction; a linked criterion is not deleted. Criteria and cases can be deleted only while Draft, before any build or result exists.
- **Writes:** every round change runs in one transaction that locks the round row (`select_for_update`), then re-checks the state, caps, label uniqueness and that submitted records are in the round. Creating a round locks the workspace row to check the round cap. Provisionally, creating or changing a result (RES) also locks the round row, then re-checks the state, that the build is in the round and covers the case, and that it is the case's current build. Concurrent Draft edits to the same record are not merged; the last saved edit wins.
- **Sample round:** fixed synthetic text, written by the shared round-creation code inside the [demo creation](#accounts-and-workspaces) transaction ([RND-7](product/rounds.md#rnd-7-sample-draft-round-in-a-new-demo-workspace)).

## Routes

### Foundation route

`/` is a public, stateless GET/HEAD route rendering `home.html`, with no input or role/workspace/state preconditions. Other methods return 405; unresolved paths and uncaught exceptions use Django's generic nondebug 404/500 responses. Its observable contract is [PLT-1](product/platform.md#plt-1-django-foundation-and-continuous-verification); from ACC-1 the page also links to `/sign-in/` (PLT-1.1). Future routes must define authorization, validation and state contracts before implementation.

The accounts and rounds routes below are planned for their implementation slices; ACC-2 turns `/` into the accounts start page in the table below. Each route contract must name its method, role/workspace/ownership checks, input validation, state preconditions, success result and denied/failure behaviour before implementation.

### Accounts routes

For [ACC](product/accounts.md). Every POST uses Django's CSRF protection, which also rejects an `Origin` header naming another origin, with 403 ([ACC-1.8](product/accounts.md#acc-1-sign-in-and-out-by-role), [ACC-2.7](product/accounts.md#acc-2-create-an-isolated-demo-workspace)). A route that cannot reach storage, including its limit counts, gives the 503 page of [ACC-2.5](product/accounts.md#acc-2-create-an-isolated-demo-workspace) and changes nothing.

| Route | Method | Access | Validation and success | Denied or failed |
| --- | --- | --- | --- | --- |
| `/` | GET | Signed out | Relay start page, titled "Relay", with a sign-in link and the "Create a demo workspace" button | Signed in: redirect to own role home |
| `/sign-in/` | GET, POST | Anyone | GET shows the form, unlimited. POST locks the per-address count, then Django's authentication checks the username and password in the same transaction; success starts a new session and redirects to own role home, ignoring `next` ([ACC-1.1, 1.2, 1.7](product/accounts.md#acc-1-sign-in-and-out-by-role)) | Invalid: [ACC-1.2](product/accounts.md#acc-1-sign-in-and-out-by-role); limited: [ACC-3.1](product/accounts.md#acc-3-limit-abuse-of-sign-in-and-demo-workspace-creation) |
| `/sign-out/` | POST | Anyone | Flushes the session and redirects to `/sign-in/`, which shows "You have signed out." once through Django's messages ([ACC-1.5](product/accounts.md#acc-1-sign-in-and-out-by-role)) | Other methods: 405 |
| `/demo/` | POST | Signed out | Checks both creation limits, then creates and renders "Your demo workspace" in one transaction, with `Cache-Control: no-store` and no redirect ([ACC-2.1 to 2.3](product/accounts.md#acc-2-create-an-isolated-demo-workspace)) | Signed in: [ACC-2.6](product/accounts.md#acc-2-create-an-isolated-demo-workspace); other methods: 405; limited: [ACC-3.4](product/accounts.md#acc-3-limit-abuse-of-sign-in-and-demo-workspace-creation) |
| `/coordinator/` | GET | Test Coordinator | "Coordinator home" | Signed out: redirect to `/sign-in/`; Beta Tester: 403 of [ACC-1.4](product/accounts.md#acc-1-sign-in-and-out-by-role) |
| `/tester/` | GET | Beta Tester | "Tester home" | Signed out: redirect to `/sign-in/`; Test Coordinator: 403 of ACC-1.4 |

The session cookie is `HttpOnly`; session and CSRF cookies are `SameSite=Lax`, and `Secure` outside local development (shared settings set `Secure`; `relay.settings.local` turns it off).

Signed-out redirects go to `/sign-in/` with no `next` parameter.

Delivery order: ACC-1 builds `/sign-in/` (page title "Sign in"), `/sign-out/`, `/coordinator/` and `/tester/`, and adds the sign-in link to the foundation's `/` (PLT-1.1). ACC-2 adds `/demo/`, the start page's button and its signed-in redirect, and the 503 page; ACC-3 adds the sign-in count and its lock. Until then, a storage failure on an accounts route gives the generic 500 of PLT-1.3.

### Rounds routes

For [RND](product/rounds.md). Every route requires a signed-in Test Coordinator and applies the [rules for every round action](product/rounds.md#rules-for-every-round-action) in their order; a state not listed below gets their 409. Invalid input re-renders the form, and a refused delete the round page, with status 200 and the message. A successful POST redirects to the round page, which shows the success message once. The Coordinator home (`/coordinator/`) also lists the workspace's rounds. `<round>`, `<criterion>` and `<case>` are integer IDs; no route takes a build ID.

| Route | Method | States | Page title or result |
| --- | --- | --- | --- |
| `/coordinator/rounds/new/` | GET, POST | — | "New round"; creates a Draft round |
| `/coordinator/rounds/<round>/` | GET | Any | The round's title as page title, its state, criteria and cases and, from publishing, builds ([RND-2](product/rounds.md#rnd-2-manage-acceptance-criteria-and-test-cases), [RND-3](product/rounds.md#rnd-3-publish-a-round-to-beta-testers)) |
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

The `.env.example` file may contain only empty placeholders and throwaway local database values. Settings never load dotenv files. `relay.settings.local` reads `DJANGO_SECRET_KEY` (required/nonblank), `DJANGO_DEBUG` (strict true/false; defaults false), `DJANGO_ALLOWED_HOSTS` (comma-separated localhost/127.0.0.1/[::1] only), and `POSTGRES_HOST/PORT/DB/USER/PASSWORD` (defaults localhost/5432/relay/relay/relay). Database host must be localhost, 127.0.0.1 or ::1. These local settings cannot configure a hosted runtime. `manage.py` and WSGI default to local settings; explicit `DJANGO_SETTINGS_MODULE` remains supported.

`relay.settings.test` imports only shared settings and uses fixed non-secret values: PostgreSQL database/user/password `relay_test`, host 127.0.0.1, port 55432, test database `test_relay_test`, debug false and hosts testserver/localhost/127.0.0.1. `pytest.ini` selects these settings; tests use no provider. The test role needs database creation permission on its throwaway server. ACC-1 adds the first business migrations.

Both database configurations explicitly set libpq `hostaddr` through Django's database `OPTIONS`, preventing inherited `PGHOSTADDR` from redirecting connections. Local localhost/127.0.0.1 map to 127.0.0.1; local ::1 maps to ::1. Tests fix the address to 127.0.0.1.

Production settings, checked before release:

- `DEBUG` off; `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` list only the production host and origin, with no wildcard.
- HTTPS is detected through `SECURE_PROXY_SSL_HEADER` only once Vercel's forwarded-protocol header is verified under the [release gate](#release-verification).
- Every page is refused framing (`X-Frame-Options: DENY`), and HSTS is on.

## Environments

| Environment | Planned runtime | Database | Configuration |
| --- | --- | --- | --- |
| Local development | Python virtual environment running Django; Docker optional for the database | Local PostgreSQL, separate from production | Developer configuration; local debug only |
| CI validation | GitHub Actions running lint, formatting, Django checks and tests | Throwaway PostgreSQL 17 on loopback port 55432 | Fixed test settings; no provider calls |
| Production | Vercel's native Django/Python runtime | Separate managed PostgreSQL | Production-only credentials; debug off |

No dedicated staging environment or Docker app image is planned. Development and production use separate databases and credentials. The team manages deployment through GitHub Actions; a build-and-host environment supplied by an AI tool is not part of the delivery plan.

## Product website

The static GitHub Pages site uses `docs/index.md`, `docs/Reflections.md` and `docs/_config.yml`, with GitHub's Cayman theme. Its configured organization URL is `https://cs3227-2610-mp4-relay.github.io` and repository base path is `/CS3227-2610-MP4`; this configuration does not establish that the site is published. The guides link to their source in the [team repository](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4) and are excluded from the site build. Check rendered links before publishing.

## Release verification

Delivery will verify the final candidate before a controlled production deployment, then run smoke checks. Deployment workflows, migration handling, checked-source provenance, failure recovery and smoke-check contracts remain to be designed and tested. The scaffold does not claim any release controls are configured.

Release gate: production is not released until Vercel's actual client-address source, forwarded-protocol header and function time limit are verified and recorded, and the production settings under [Configuration](#configuration) are checked.

### Review decisions and operator prerequisites

Default-branch protection and secret scanning are configured under the [CI and dependencies](SECURITY-SPEC.md#ci-and-dependencies) control.

Future work:

- Verify the [team repository](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4) is publicly accessible; confirm role ownership and initial slice issues/milestones.
- Configure and verify hosted environment restrictions.
- Configure GitHub Pages and verify its built artifact and links before publication.
- Create the Vercel project and separate managed PostgreSQL database; confirm the actual provider runtime, limits, secure database connection and least-privilege deployment access.
- Keep production credentials in protected production settings, outside development, CI validation and untrusted builds. Design and verify migrations and deployment approvals before enabling releases.
- Verify the team's SoC LLM model availability and limits before fixing model and quota settings.
