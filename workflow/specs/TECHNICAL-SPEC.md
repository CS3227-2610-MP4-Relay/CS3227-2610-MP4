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

For [ACC](product/accounts.md). The retention, workspace-lifetime and expired-session decisions above are a precondition of the first ACC code slice (ACC-1). Until they are made, nothing is deleted, and hashed addresses are kept indefinitely.

- **Workspace:** a unique name, `Demo workspace <suffix>`, and its creation time. Every workspace-owned record has a non-null workspace reference. Routes check the role first, then look records up through one shared helper that filters by the signed-in user's workspace before reading and gives the 404 of [ACC-2.4](product/accounts.md#acc-2-create-an-isolated-demo-workspace) for any other workspace's record.
- **Account:** a custom Django user model, present from #1's first migration, with a globally unique username, a Django password hash, a non-null workspace and a role of `coordinator` or `tester`, all fixed at creation. The model has no staff, superuser or permission fields, and `django.contrib.admin` is not installed, so there is no admin route.
- **Generated credentials:** usernames are `coord-<suffix>`, `tester1-<suffix>` and `tester2-<suffix>`, sharing the workspace's suffix of 8 random lowercase letters and digits; a suffix collision is retried. Each password is 16 random characters from `a-z`, `A-Z` and `0-9`, generated with `secrets` and hashed before any lock is taken. Plain passwords exist only in memory while rendering the creation response.
- **Creation:** one transaction holds the limit counts, the workspace, its accounts, its sample round and the rendering of the creation response, so any failure rolls everything back ([ACC-2.5](product/accounts.md#acc-2-create-an-isolated-demo-workspace)).
- **Limit counter:** one row per scope and key, holding a window start and a count, unique on scope and key; scopes, numbers and windows are in [ACC-3](product/accounts.md#acc-3-limit-abuse-of-sign-in-and-demo-workspace-creation). A migration creates the overall creation row; per-address rows are inserted or updated in one statement. A creation locks its per-address row, then the overall row. A sign-in reserves a failure with a conditional increment before checking the password and releases it on success, so concurrent attempts cannot overshoot. These transactions set lock and statement timeouts, which give the 503 of ACC-3.7. Once a window has elapsed, the row restarts its window and count.
- **Client address:** `REMOTE_ADDR`, never a client-supplied forwarding header. IPv4 addresses count individually and IPv6 addresses by their `/64` prefix; a missing or unparseable address uses the fixed key `unknown`. The stored key is Django's `salted_hmac` of the address with its own salt, never the address itself. Production depends on the client-address gate under [Release verification](#release-verification); a trusted-proxy header setting is a separate decision, needed only if that verification shows it.
- **Sessions:** Django's database-backed sessions. Sign-in sets an absolute expiry time, so later session writes cannot extend it ([ACC-1.6](product/accounts.md#acc-1-sign-in-and-out-by-role)); sign-out deletes the session row.

## Routes

Only the subsections below are specified. Each route contract must name its method, role/workspace/ownership checks, input validation, state preconditions, success result and denied/failure behaviour before implementation.

### Accounts routes

For [ACC](product/accounts.md). Every POST uses Django's CSRF protection, which also rejects an `Origin` header naming another origin, with 403 ([ACC-1.8](product/accounts.md#acc-1-sign-in-and-out-by-role), [ACC-2.7](product/accounts.md#acc-2-create-an-isolated-demo-workspace)). A route that cannot reach storage, including its limit counts, gives the 503 page of [ACC-2.5](product/accounts.md#acc-2-create-an-isolated-demo-workspace) and changes nothing.

| Route | Method | Access | Validation and success | Denied or failed |
| --- | --- | --- | --- | --- |
| `/` | GET | Signed out | Relay start page, titled "Relay", with a sign-in link and the "Create a demo workspace" button | Signed in: redirect to own role home |
| `/sign-in/` | GET, POST | Anyone | GET shows the form, unlimited. POST reserves a failure, then Django's authentication checks the username and password; success starts a new session and redirects to own role home, ignoring `next` ([ACC-1.1, 1.2, 1.7](product/accounts.md#acc-1-sign-in-and-out-by-role)) | Invalid: [ACC-1.2](product/accounts.md#acc-1-sign-in-and-out-by-role); limited: [ACC-3.1](product/accounts.md#acc-3-limit-abuse-of-sign-in-and-demo-workspace-creation) |
| `/sign-out/` | POST | Anyone | Flushes the session and redirects to `/sign-in/` ([ACC-1.5](product/accounts.md#acc-1-sign-in-and-out-by-role)) | Other methods: 405 |
| `/demo/` | POST | Signed out | Checks both creation limits, then creates and renders "Your demo workspace" in one transaction, with `Cache-Control: no-store` and no redirect ([ACC-2.1 to 2.3](product/accounts.md#acc-2-create-an-isolated-demo-workspace)) | Signed in: [ACC-2.6](product/accounts.md#acc-2-create-an-isolated-demo-workspace); other methods: 405; limited: [ACC-3.4](product/accounts.md#acc-3-limit-abuse-of-sign-in-and-demo-workspace-creation) |
| `/coordinator/` | GET | Test Coordinator | "Coordinator home" | Signed out: redirect to `/sign-in/`; Beta Tester: 403 of [ACC-1.4](product/accounts.md#acc-1-sign-in-and-out-by-role) |
| `/tester/` | GET | Beta Tester | "Tester home" | Signed out: redirect to `/sign-in/`; Test Coordinator: 403 of ACC-1.4 |

The session cookie is `HttpOnly`; session and CSRF cookies are `SameSite=Lax`, and `Secure` outside local development.

## Configuration

The `.env.example` file may contain only empty placeholders and throwaway local database values. Runtime settings and validation will be specified with the application scaffold. Tests must use isolated configuration and fake provider responses, without inheriting production credentials or contacting SoC LLM.

Production settings, checked before release:

- `DEBUG` off; `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` list only the production host and origin, with no wildcard.
- HTTPS is detected through `SECURE_PROXY_SSL_HEADER` only once Vercel's forwarded-protocol header is verified under the [release gate](#release-verification).
- Every page is refused framing (`X-Frame-Options: DENY`), and HSTS is on.

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

Release gate: production is not released until Vercel's actual client-address source and forwarded-protocol header are verified and recorded, and the production settings under [Configuration](#configuration) are checked.

### Review decisions and operator prerequisites

Default-branch protection and secret scanning are configured under the [CI and dependencies](SECURITY-SPEC.md#ci-and-dependencies) control.

Future work:

- Verify the [team repository](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4) is publicly accessible; confirm role ownership and initial slice issues/milestones.
- Configure and verify hosted environment restrictions.
- Configure GitHub Pages and verify its built artifact and links before publication.
- Create the Vercel project and separate managed PostgreSQL database; confirm the actual provider runtime, limits, secure database connection and least-privilege deployment access.
- Keep production credentials in protected production settings, outside development, CI validation and untrusted builds. Design and verify migrations and deployment approvals before enabling releases.
- Verify the team's SoC LLM model availability and limits before fixing model and quota settings.
