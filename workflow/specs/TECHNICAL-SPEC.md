# Technical spec

How Relay will be built and run. What it will do is in [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md). The application foundation is local/CI only; business schema and hosted environments remain planned.

## Architecture

- One Django project that renders HTML on the server, with no separate front end. Application code and its tests will live under `src/`.
- PostgreSQL for application storage and database-backed tests.
- Configuration from environment variables, with no committed credentials.
- SoC LLM through one shared gateway; feature code selects authorized context before invoking it. The planned boundary is in [`ai/llm-gateway.md`](ai/llm-gateway.md).

`src/manage.py` starts the `relay` Django project; `relay.wsgi` is its WSGI entry point and `relay.pages` owns public presentation. Shared templates live in `src/relay/templates/`. No auth/session/admin apps or business models are installed. Runtime and dependency pins belong in the root configuration files.

## Data model

Not specified yet. Design workspaces, role-based accounts, rounds, requirements, cases, build references and results around the [product areas](PRODUCT-SPEC.md#areas). Before schema implementation, settle ownership, state transitions, published-case edits, submitted-observation edits and result-history/version rules. Do not infer these from a proposed screen or table name.

Before implementing persistence, decide retention for accumulated business records, workspace lifetime, expired-session handling and behaviour when shared storage capacity is exhausted, including failed writes and preservation of required result history. These are open design decisions; no cleanup subsystem or retention duration is prescribed yet.

## Routes

`/` is a public, stateless GET/HEAD route rendering `home.html`, with no input or role/workspace/state preconditions. Other methods return 405; unresolved paths and uncaught exceptions use Django's generic nondebug 404/500 responses. Its observable contract is [PLT-1](product/platform.md#plt-1-django-foundation-and-continuous-verification). Future routes must define authorization, validation and state contracts before implementation.

## Configuration

The `.env.example` file may contain only empty placeholders and throwaway local database values. Settings never load dotenv files. `relay.settings.local` reads `DJANGO_SECRET_KEY` (required/nonblank), `DJANGO_DEBUG` (strict true/false; defaults false), `DJANGO_ALLOWED_HOSTS` (comma-separated localhost/127.0.0.1/[::1] only), and `POSTGRES_HOST/PORT/DB/USER/PASSWORD` (defaults localhost/5432/relay/relay/relay). Database host must be localhost, 127.0.0.1 or ::1. These local settings cannot configure a hosted runtime. `manage.py` and WSGI default to local settings; explicit `DJANGO_SETTINGS_MODULE` remains supported.

`relay.settings.test` imports only shared settings and uses fixed non-secret values: PostgreSQL database/user/password `relay_test`, host 127.0.0.1, port 55432, test database `test_relay_test`, debug false and hosts testserver/localhost/127.0.0.1. `pytest.ini` selects these settings; tests use no provider. The test role needs database creation permission on its throwaway server. No business migrations exist.

Both database configurations explicitly set libpq `hostaddr` through Django's database `OPTIONS`, preventing inherited `PGHOSTADDR` from redirecting connections. Local localhost/127.0.0.1 map to 127.0.0.1; local ::1 maps to ::1. Tests fix the address to 127.0.0.1.

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

### Review decisions and operator prerequisites

Default-branch protection and secret scanning are configured under the [CI and dependencies](SECURITY-SPEC.md#ci-and-dependencies) control.

Future work:

- Verify the [team repository](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4) is publicly accessible; confirm role ownership and initial slice issues/milestones.
- Configure and verify hosted environment restrictions.
- Configure GitHub Pages and verify its built artifact and links before publication.
- Create the Vercel project and separate managed PostgreSQL database; confirm the actual provider runtime, limits, secure database connection and least-privilege deployment access.
- Keep production credentials in protected production settings, outside development, CI validation and untrusted builds. Design and verify migrations and deployment approvals before enabling releases.
- Verify the team's SoC LLM model availability and limits before fixing model and quota settings.
