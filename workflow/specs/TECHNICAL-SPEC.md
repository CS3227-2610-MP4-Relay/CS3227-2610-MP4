# Technical spec

How Relay will be built and run. What it will do is in [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md). This is a planning scaffold: no application, schema or hosted environment is implemented yet.

## Architecture

- One Django project that renders HTML on the server, with no separate front end. Application code and its tests will live under `src/`.
- PostgreSQL for application storage and database-backed tests.
- Configuration from environment variables, with no committed credentials.
- SoC LLM through one shared gateway; feature code selects authorized context before invoking it. The planned boundary is in [`ai/llm-gateway.md`](ai/llm-gateway.md).

Keep shared storage, authorization, AI transport and presentation responsibilities separate, and reuse shared components. Package boundaries and entry points will be specified with the first implementation slices. Runtime and dependency pins belong in the root configuration files.

## Data model

Not specified yet. Design workspaces, role-based accounts, rounds, requirements, cases, build references and results around the [product areas](PRODUCT-SPEC.md#areas). Before schema implementation, settle ownership, state transitions, published-case edits, submitted-observation edits and result-history/version rules. Do not infer these from a proposed screen or table name.

Before implementing persistence, decide retention for accumulated business records, workspace lifetime, expired-session handling and behaviour when shared storage capacity is exhausted, including failed writes and preservation of required result history. These are open design decisions; no cleanup subsystem or retention duration is prescribed yet.

## Routes

Not specified yet. Each route contract must name its method, role/workspace/ownership checks, input validation, state preconditions, success result and denied/failure behaviour before implementation.

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
