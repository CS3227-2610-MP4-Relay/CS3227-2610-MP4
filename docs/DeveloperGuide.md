# Developer Guide

## Setup

Relay contains a local Django application with demo workspaces and sign-in by role, and CI checks. Its architecture, configuration and environments are in [`TECHNICAL-SPEC.md`](../workflow/specs/TECHNICAL-SPEC.md).

Install Python 3.14, as selected by [`.python-version`](../.python-version), before creating the local tooling environment. On Windows, use the Python launcher to select it explicitly; an unqualified `python` may select another installed version. From the repository root in Git Bash:

```bash
py -3.14 -m venv .venv
source .venv/Scripts/activate
python --version
python -m pip install -r requirements-dev.txt
```

Confirm that `python --version` reports 3.14.x before installing. If `py -3.14` cannot find it, install Python 3.14 or use the explicit path to that interpreter. On macOS/Linux, create the environment with `python3.14 -m venv .venv` and activate it with `source .venv/bin/activate`.

### Run locally

Use a local PostgreSQL database and role matching the configuration contract in the [technical spec](../workflow/specs/TECHNICAL-SPEC.md#configuration). For example, if Docker is already installed, start a throwaway local database:

```bash
docker run --rm -d --name relay-local-db \
  -e POSTGRES_DB=relay -e POSTGRES_USER=relay -e POSTGRES_PASSWORD=relay \
  -p 127.0.0.1:5432:5432 postgres:17.6
```

Wait for PostgreSQL to accept connections, then run from the repository root with `.venv` active:

```bash
export DJANGO_SECRET_KEY='throwaway-local-development-only'
python src/manage.py check
python src/manage.py migrate
python src/manage.py runserver 127.0.0.1:8000
```

Open <http://127.0.0.1:8000/>. Stop Django with Ctrl+C. If you started the optional database container above, stop it with `docker stop relay-local-db`; its contents are discarded, so run `migrate` again after restarting it. Run `migrate` whenever a pull request adds migrations; the first ones create workspaces, accounts and database sessions.

Settings read exported environment variables, not `.env` files; [`.env.example`](../.env.example) lists local variable names. Debug defaults off; set `DJANGO_DEBUG=true` only for local debugging. Never use production credentials for development or tests. Separate production setup is in the [deployment checklist](#production-deployment).

### Create accounts for manual testing

While signed out, choose **Create a demo workspace** on the start page. It creates a workspace in your local database with one Test Coordinator, two Beta Testers and a Draft "Sample round", and shows their generated passwords once; only the password hashes are stored. There is no admin site or superuser.

### Verify

The pytest suite uses the fixed isolated [test environment](../workflow/specs/TECHNICAL-SPEC.md#configuration). Start a separate throwaway PostgreSQL server with its own database-creation-capable test role; for example, with Docker already installed:

```bash
docker run --rm -d --name relay-test-db \
  -e POSTGRES_DB=relay_test -e POSTGRES_USER=relay_test \
  -e POSTGRES_PASSWORD=relay_test \
  -p 127.0.0.1:55432:5432 postgres:17.6
```

The gateway's transport tests also need the `openssl` command-line tool ([SoC LLM](#soc-llm)). Wait for PostgreSQL to accept connections. With `.venv` active, install Chromium after installing the development dependencies, and repeat after upgrading Playwright:

```bash
python -m playwright install chromium
```

On Linux, use `python -m playwright install --with-deps chromium` to install its system prerequisites too, as CI does. From the repository root, run in Git Bash (or another POSIX shell):

```bash
python src/manage.py check --settings=relay.settings.test
ruff check . && ruff format --check . && pytest
```

Pytest creates and destroys `test_relay_test`, applying all migrations; it never selects the normal local database. Test settings use a fast password hasher; other settings keep Django's default. Stop the optional test container with `docker stop relay-test-db`. CI provisions its own PostgreSQL service and runs the same checks. The workflow's own tests under `workflow/scripts/` still need no database. A local pass does not establish that hosted CI has run.

To run only the browser journeys against the same test database:

```bash
pytest src/e2e -q
```

Failed browser tests save `browser-failure.png` and `browser-trace.zip` in their pytest temporary directory, normally beneath the system temporary directory's `pytest-of-<user>/pytest-<run>/` folder. Open the screenshot directly; inspect the trace with its actual path:

```bash
python -m playwright show-trace "/path/to/browser-trace.zip"
```

In CI, download the `browser-failure-diagnostics` artifact from the failed workflow run; its files come from `${RUNNER_TEMP}/relay-pytest/`. These checks use synthetic data on loopback HTTP; their limits and diagnostic retention are in [Browser verification](../workflow/specs/TECHNICAL-SPEC.md#browser-verification).

## Production deployment

The repository supplies production settings and an opt-in Actions delivery job; no public application release is verified yet. Reuse existing projects or create them if needed, then complete the [release gate](../workflow/specs/TECHNICAL-SPEC.md#release-verification). Keep repository variable `PRODUCTION_DEPLOY_ENABLED` unset or `false` throughout setup and the protected bootstrap.

### 1. Create the Neon database

1. In the [Neon console](https://console.neon.tech), create a project for Relay production, choosing PostgreSQL **17** and AWS Singapore (`aws-ap-southeast-1`). Use a database and role dedicated to Relay, with the schema privileges needed for its migrations; keep local/test databases separate. [Neon project setup](https://neon.com/docs/manage/projects) and [regions](https://neon.com/docs/introduction/regions) describe the current controls.
2. Open **Connect**, select the production branch, database and role, and privately save two URLs: with connection pooling on for Vercel, and off for migrations/GitHub. The pooled hostname contains `-pooler`; the direct hostname does not. Both URLs must point to the same database/branch. Record the provider's actual connection limit and transaction pooler mode for the release gate; [Neon pooling](https://neon.com/docs/connect/connection-pooling) explains the distinction.
3. For this application's URL parser, remove the console's query string, or replace it with exactly `?sslmode=verify-full`. In particular, do not leave `sslmode=require` or `channel_binding` query options in the saved URL. The application enforces certificate-verified TLS with system roots itself; see the [configuration contract](../workflow/specs/TECHNICAL-SPEC.md#configuration). Keep URL-encoded user/password characters intact. Never paste either URL into repository files, issue comments or terminal commands/history.

### 2. Create and protect the Vercel project

1. Use the existing empty project under the intended owning team/account and keep it **unlinked from Git**. For new users only, Node **24.18.0** and the pinned ephemeral CLI can sign in and create an empty project using the private-terminal commands below; replace the team slug/project name and stop on any failure. Interactive login instructions remain visible in that private terminal; project output stays in a private temporary directory. These commands do not deploy. [CLI login](https://vercel.com/docs/cli/login) and [project creation](https://vercel.com/docs/cli/project) describe the operations.
2. Before adding any credentials, open **Settings → Deployment Protection** and enable **Vercel Authentication → All Deployments**. Confirm it covers production and generated URLs. This is the protected bootstrap; do not generate an automation-bypass secret. [Vercel protection](https://vercel.com/docs/deployment-protection) describes these controls.
3. Set the project root to `.`, native **Django** framework detection and Python **3.14**, leaving custom build/output commands unset. In Functions settings, select Singapore (`sin1`) to colocate with Neon and confirm the WSGI limit in [`vercel.json`](../vercel.json). The pinned CLI uploads source; Git auto-deployment also stays disabled by that file. [Vercel regions](https://vercel.com/docs/regions) and the [native Django guide](https://vercel.com/docs/frameworks/full-stack/django) describe these settings; no extra static-file package is needed.
4. Choose the stable production hostname, normally the project's assigned `*.vercel.app` domain. Add the following **Production-only** environment values, marking the secret key/database URL sensitive where supported. Do not copy them to Preview or Development.

For step 1 only, new users can run the following before loading any production secrets. Skip it when the project already exists:

```bash
umask 077
relay_setup=$(mktemp -d)
npx --yes --package=vercel@64.3.1 vercel login || exit 1
npx --yes --package=vercel@64.3.1 vercel project add your-project --scope your-team >"$relay_setup/project-out.txt" 2>"$relay_setup/project-errors.txt" || exit 1
```

For step 4, enter these values in the dashboard:

| Vercel variable | Value to enter |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `relay.settings.production` |
| `DJANGO_SECRET_KEY` | A password-manager-generated random key of at least 50 characters; retain privately for the GitHub setting below |
| `DJANGO_PRODUCTION_HOST` | The single production hostname, lowercase, without scheme, port, slash or wildcard |
| `DATABASE_URL` | Normalized **pooled** Neon URL from step 1 |
| `DJANGO_TRUST_PROXY_SSL_HEADER` | `false` for bootstrap; change to `true` only after observing the actual proxy behavior |

### 3. Configure GitHub release access

In repository **Settings → Environments**, create or open `production`: restrict deployments to selected branch `main` and leave **Required reviewers** unchecked. Do not add a wait timer or another manual deployment gate. The workflow alone does not create these restrictions. Keep the default branch's pull request review and verification controls; leave the existing `github-pages` environment unchanged. Add these environment entries; do not use repository-wide production secrets.

| Location in GitHub | Name | Value |
| --- | --- | --- |
| `production` secret | `DJANGO_SECRET_KEY` | Same private key as Vercel |
| `production` secret | `DATABASE_URL` | Normalized **direct** Neon URL |
| `production` secret | `VERCEL_TOKEN` | Expiring Vercel API token scoped to the owning team with the narrowest available access |
| `production` variable | `DJANGO_PRODUCTION_HOST` | Same hostname as Vercel |
| `production` variable | `VERCEL_PROJECT_ID` | Project Settings ID, beginning `prj_` |
| `production` variable | `VERCEL_TEAM_ID` | Owning team Settings ID, beginning `team_` |
| Repository Actions variable | `PRODUCTION_DEPLOY_ENABLED` | Leave unset or `false` until the initial release gate and explicit public activation approval are complete |

Create the token through [Vercel account token settings](https://vercel.com/account/settings/tokens); [Vercel's token guidance](https://vercel.com/kb/guide/how-do-i-use-a-vercel-api-access-token) explains team scope. Store it in GitHub's production secret, not the application runtime. Keep `VERCEL_TEAM_ID` as the external setting: the helper maps it to CLI `VERCEL_ORG_ID`. Source assurance comes from the tested commit's clean archive, not provider Git metadata. No GitHub token, repository-ID variable or Neon API key is needed.

### 4. Migrate and create the protected bootstrap

After the human authorizes the initial protected deployment, choose an exact reviewed commit with passing application/site checks on `main`. Use a separate checkout of that commit and its installed pinned requirements in a dedicated operator terminal; do not run development or test commands in this terminal. Review migration compatibility with any version already serving before applying migrations.

First initialize Neon while the Actions opt-in remains off and Vercel's proxy-trust flag remains `false`. Activate the checkout's `.venv` as in [Setup](#setup). From the repository root in Git Bash, replace the example hostname and enter secrets at the hidden prompts, not as command text:

```bash
set +x
export DJANGO_PRODUCTION_HOST='your-project.vercel.app'
export DJANGO_TRUST_PROXY_SSL_HEADER=false
read -r -s -p 'Production Django secret key: ' DJANGO_SECRET_KEY
printf '\n'
export DJANGO_SECRET_KEY
read -r -s -p 'Direct Neon URL: ' DATABASE_URL
printf '\n'
export DATABASE_URL
unset PGHOST PGHOSTADDR PGSERVICE PGSERVICEFILE PGSSLMODE PGSSLROOTCERT
if python src/manage.py check --settings=relay.settings.production >/dev/null 2>&1 &&
   python src/manage.py migrate --noinput --settings=relay.settings.production >/dev/null 2>&1; then
  printf '%s\n' 'Bootstrap database ready.'
else
  printf '%s\n' 'Bootstrap migration failed; inspect privately before retrying.' >&2
fi
unset DATABASE_URL DJANGO_SECRET_KEY DJANGO_PRODUCTION_HOST DJANGO_TRUST_PROXY_SSL_HEADER
```

Use the checkout's Python environment and close this operator terminal afterwards. Output is deliberately suppressed because database errors can contain connection details; inspect any failure privately before retrying. The normal system check above permits the protected bootstrap; the stricter deployment check is reserved for verified proxy configuration below. Do not use `release.py migrate` at this stage: that command requires the proxy flag already verified and enabled.

Continue only after `Bootstrap database ready.`; otherwise stop and inspect the failure privately. In a fresh terminal with the checkout's `.venv` active and **no production secrets loaded**, install the operator CLI first, then prepare source using the same helper as Actions. Replace the SHA with the exact verified 40-character commit and both project/team IDs. The destination must be new; the helper reads committed inputs, excludes local/dotenv artifacts and never copies a dirty checkout. After preparation, enter the token at the hidden prompt and upload only that directory:

```bash
set +x
umask 077
relay_bootstrap=$(mktemp -d)
if ! npm install --prefix "$relay_bootstrap/tools" --no-save vercel@64.3.1 >"$relay_bootstrap/install-out.txt" 2>"$relay_bootstrap/install-errors.txt"; then
  printf '%s\n' 'CLI installation failed; stop and inspect privately.' >&2
  exit 1
fi
export GITHUB_SHA='replace-with-verified-40-character-sha'
python src/release.py prepare "$relay_bootstrap/source" || exit 1
export VERCEL_PROJECT_ID='prj_replace'
export VERCEL_TEAM_ID='team_replace'
export VERCEL_ORG_ID="$VERCEL_TEAM_ID"
read -r -s -p 'Vercel deployment token: ' VERCEL_TOKEN
printf '\n'
export VERCEL_TOKEN
if "$relay_bootstrap/tools/node_modules/.bin/vercel" deploy --prod --yes --no-wait --force --cwd "$relay_bootstrap/source" --global-config "$relay_bootstrap/config" --token "$VERCEL_TOKEN" >"$relay_bootstrap/deployment-url.txt" 2>"$relay_bootstrap/deployment-errors.txt"; then
  printf '%s\n' 'Protected upload submitted; inspect deployment in Vercel.'
else
  printf '%s\n' 'Upload failed or outcome unknown; inspect Vercel before any retry.' >&2
fi
unset VERCEL_TOKEN VERCEL_ORG_ID VERCEL_PROJECT_ID VERCEL_TEAM_ID GITHUB_SHA
```

Keep captured files private and outside the checkout; do not print/share raw error output or upload it as an artifact. A submitted upload is not a completed release: inspect the deployment ID, intended project, Production target, readiness and All Deployments authentication in Vercel. Keep the Actions opt-in off while authorized observers collect evidence. Do not run `release.py deploy` to claim bootstrap success: its anonymous public smoke must fail while protection is on. Migrations remain the explicit operator step above for bootstrap and the protected GitHub step for normal delivery, never a Vercel build command.

### 5. Complete the live gate, then approve public release

Follow the existing [release-verification checklist](../workflow/specs/TECHNICAL-SPEC.md#release-verification) and privately inspect the protected application/database. Record commit, URL and pass/fail observations, excluding secrets, credentials, raw addresses and stored hashes:

- From two external clients, verify the actual client-address behavior under the specified forged forwarding headers and establish that requests never use the `unknown` counter key. Keep `REMOTE_ADDR` behavior unchanged; if it fails, stop release and agree the smallest needed adapter separately.
- Observe the actual forwarded-protocol behavior before changing proxy trust. After it passes, change Vercel's flag to `true` and repeat the protected pinned-CLI upload of the same prepared commit so the new environment value takes effect, within the authorized bootstrap and only after reconciling the previous outcome. In a fresh secret-loaded operator terminal, set the corresponding flag true and run `python src/manage.py check --deploy --fail-level WARNING --settings=relay.settings.production` with output suppressed as above; require success.
- Confirm actual function timeout, database connection limit/pooler mode and the database-side **`demo-total` lock-hold duration**, including sample-round creation. Whole HTTP request duration is not a substitute for lock-hold time. This repository supplies no measurement/diagnostics service; if the required observation cannot be established, keep release disabled and arrange a bounded measurement procedure separately.
- Inspect actual application HTTPS responses for the [required production headers/cookies and smoke contract](../workflow/specs/TECHNICAL-SPEC.md#release-verification). [Vercel adds response headers](https://vercel.com/docs/headers/response-headers), so its platform defaults do not prove the Django response matches the contract. Authorized browser inspection is distinct from anonymous public smoke verification; do not run the local synthetic browser harness against production.

Hosted observations and initial public activation approval remain pending until actually recorded. After all gates pass and the human explicitly approves initial release, changing protection to **Standard Protection** makes the existing production deployment public: treat that settings change as a release action. Keep generated/preview deployments protected. Then set the repository Actions variable `PRODUCTION_DEPLOY_ENABLED=true`. Thereafter, approval and merge of a pull request authorize automatic deployment once application and site verification pass in that resulting main-push run; no second environment approval or manual trigger is needed. Review migration compatibility with the still-serving application in the pull request before approval and merge. The bootstrap does not itself trigger this job. Record the actual public deployment and smoke outcome separately from local test evidence.

### Delivery failures

The [delivery helper](../src/release.py) reports a stage, commit and known deployment ID; inspect the corresponding Actions/Vercel/Neon state privately. Preparation or configuration/migration failure prevents upload. After a failed/timed-out/ambiguous CLI invocation, inspect the configured project's deployments/time window before deciding whether to retry; commit labels are not independent source verification. A deployment with a mismatched identity/alias or failed smoke is failed delivery even if serving. The helper does not rerun creation; vendor-internal protocol retries are outside that guarantee. Previously committed migrations remain; there is no automatic rollback. Keep incompatible migrations out of this path until separately agreed.

## Development workflow

How we work, and what each file in `workflow/` is for, is in [`workflow/README.md`](../workflow/README.md). Product behaviour belongs in [`workflow/specs/`](../workflow/specs/PRODUCT-SPEC.md); short slice plans belong in `workflow/plans/`. Tool adapters in `.claude/`, `.codex/` and `.agents/skills/` load the shared role and skill files. Workflow scripts and their tests live in `workflow/scripts/`.

Verified interaction summaries belong in `logs/<github-user>/`; experiment methods and evidence belong in [`experiments/`](../experiments/README.md). The team writes [`Reflections.md`](Reflections.md), with individual contributions under [`reflections/`](../reflections/README.md). Record observations and missing telemetry honestly; a scaffold or a proposed control is not evidence that the control ran.

### Coding standards

Ruff checks public class, method and function docstrings (`D101`–`D103`), 88-character lines (`E501`), top-level imports (`PLC0415`) and unused imports; the exact rules and exceptions are in [`pyproject.toml`](../pyproject.toml). Formatting is checked with `ruff format --check .`.

### Agent scope controls

Role write scopes live in `workflow/agents/`. The scope checker and tool hooks are described in [`workflow/README.md`](../workflow/README.md). Claude Code reviewers have a read-tool allowlist; Codex subagents inherit the parent session's permissions, so their role instructions do not establish a separate read-only sandbox. Hooks and post-run diff checks do not establish protection from arbitrary shell commands or malicious agents. Verify adapter loading and hook behaviour in each tool before relying on them.

## Design

The Django/PostgreSQL architecture, environment separation and planned delivery work are in [`TECHNICAL-SPEC.md`](../workflow/specs/TECHNICAL-SPEC.md). The `accounts` app (`src/accounts/`) holds the workspace and account models, sign-in, sign-out, the role home pages and demo workspace creation; its storage, routes and session rules are under [Accounts and workspaces](../workflow/specs/TECHNICAL-SPEC.md#accounts-and-workspaces) and [Accounts routes](../workflow/specs/TECHNICAL-SPEC.md#accounts-routes). `accounts/demo.py` generates the credentials and writes a demo workspace inside the `/demo/` view's single transaction; its sample round comes from `rounds/sample.py`, whose constants hold the fixed sample text and whose `create_sample_round` writes it through `create_round`, `add_criterion` and `add_case`, so the round caps and link checks apply. `accounts/workspaces.py` holds `workspace_records`, the one helper every workspace record lookup goes through. `accounts/limits.py` is the abuse-limit service: it keys counts by a salted hash of `REMOTE_ADDR`, and the sign-in and `/demo/` transactions call it to lock, check and record the `LimitCounter` rows, after setting the per-transaction timeouts listed under [Limit service](../workflow/specs/TECHNICAL-SPEC.md#accounts-and-workspaces). The concurrency tests in `accounts/tests/test_limit_views.py` (ACC-3.6, ACC-3.7 lock timeout, ACC-3.8) run threads with one database connection each in `transaction=True` tests, so they need the PostgreSQL test server; they do not use `serialized_rollback`. The `rounds` app (`src/rounds/`) holds the round, acceptance criterion, test case, build and case–criterion link models and the coordinator's round pages, under [Rounds](../workflow/specs/TECHNICAL-SPEC.md#rounds) and [Rounds routes](../workflow/specs/TECHNICAL-SPEC.md#rounds-routes). `rounds/services.py` has `create_round(workspace, title)`, which locks the workspace row to enforce the 20-round cap and takes its workspace only from the caller, never from request data. Its criterion and case services (`add_criterion`, `save_criterion`, `add_case`, `save_case`, `delete_case`, `delete_criterion`) run inside the view's transaction after it locks the round row; they enforce the 20-criterion and 30-case caps, re-check that linked criteria belong to the round, delete a case's links before the case, and raise `Refused` with the user-facing message and the form field it belongs to. `publish(round_, label)` also runs after the view's lock and Draft re-check: it refuses a round with no cases before any write, then creates the round's first `Build`, covering every case through `BuildCase` links, and sets the state to Open and `published_at`. `close(round_)` runs after the view's lock and Open re-check and only sets the state to Closed and `closed_at`, through one update that matches only an Open round; if no row changes it raises `RoundNotOpen`, so even a caller that skipped the re-check cannot close a Draft round or move a closing time. `build_key(label)` gives a build's comparison key (format characters removed, then NFC), which the database keeps unique within a round. Links use the explicit `CaseCriterion` and `BuildCase` models so every foreign key stays `PROTECT`. `rounds/views.py` checks sign-in and role first through `coordinator_view(methods)`, reads rounds through `workspace_records`, then checks the round's state, and turns storage errors into the 503 page; `record_form` and `delete_record` serve all six criterion and case routes, with the record kind given in `rounds/urls.py`, and `round_form.html` renders every round form. `publish_round` validates `PublishForm`, then locks the round, re-checks Draft and calls `services.publish`, catching `Refused` outside the committing transaction; on success it adds "Round published." through Django's messages. `close_round` takes no form: it locks the round, re-checks Open (409 for Draft or Closed, so the second of two racing closes is refused), calls `services.close` and adds "Round closed."; nothing returns a round to Open or Draft. `RetestForm` offers only the URL round's cases as checkboxes, with the same "Build label" field as `PublishForm` (both from `build_label()`). `retest_round` (GET, POST) gives the 409 for a Draft or Closed round before the form, validates `RetestForm`, then locks the round, re-checks Open and calls `services.request_retest(round_, label, case_ids)`, catching `Refused` and `RoundNotOpen` (the 409) outside the committing transaction; it renders the retest page with `round_form.html`. `request_retest` checks, before any write and in this order, that the round is still Open in the database (`RoundNotOpen`), the 10-build cap, that every case ID is in the round (the database does not enforce it for `BuildCase`), and that the label's `build_key` is unused in the round, so racing duplicates never reach the unique constraint; then it creates the build and one `BuildCase` per distinct case. On success the view adds `retest_message(count, label)` through Django's messages with the extra tag `retest`. `show_round` draws the round page, giving each case its current build, the last of the round's builds (in ascending-ID order) that covers it. The case form's criteria choices are the URL round's criteria only. In `rounds/templatetags/rounds_text.py`, the `isolated_lines` filter escapes each line of a title, criterion or case field into its own `dir="auto"` span, and the `title_isolate` filter removes the text-direction controls (`DIRECTION_CONTROLS`, defined in `rounds/forms.py` and refused there) and line breaks and wraps a title in U+2068/U+2069 for the page `<title>`. The round page and the sign-in page show messages through `status_message`, which splits a message only when it is tagged `retest` and its whole text matches the fixed RND-5.1 form (1 singular, 2 or more plural, " on build ", the label, a final full stop); only the label then goes through `isolated_lines`, and any other message is shown as plain escaped text. Threats and controls are in [`SECURITY-SPEC.md`](../workflow/specs/SECURITY-SPEC.md).

## SoC LLM

SoC LLM is the provider; its account setup and service guidance are on [SoC DocHub](https://dochub.comp.nus.edu.sg/cf/guides/soclaas/start). The `ai` app (`src/ai/`) holds the shared gateway (`gateway.py`), its rows (`ai.CallSlot`, `ai.CallRecord`), RND-8's drafting pages and `drafting.py`, which cleans text and validates replies. The gateway's controls, all proposals pending confirmation, are in [`llm-gateway.md`](../workflow/specs/ai/llm-gateway.md); what drafting sends and accepts is in [`test-drafting.md`](../workflow/specs/ai/test-drafting.md).

- **Live switch.** `SOC_LLM_LIVE = False` in `src/relay/settings/base.py`, so no provider call is made and drafting shows its unavailable message. It is not read from the environment: turning it on is a reviewed code change, allowed only once the [live switch's conditions](../workflow/specs/ai/llm-gateway.md#live-switch) are met.
- **Settings.** With live calls on, the gateway reads `SOC_LLM_ENDPOINT`, `SOC_LLM_MODEL` and `SOC_LLM_API_KEY` from the environment at each call ([configuration](../workflow/specs/TECHNICAL-SPEC.md#configuration)). `.env.example` lists them empty; never commit a real key.
- **Tests.** An autouse fixture in `src/conftest.py` removes every `SOC_LLM_*` variable and blocks the transport's network step, so no test reaches a provider even if your shell sets them. Gateway tests pass `ai.fakes.FakeProvider` to it, and the drafting view tests replace `gateway.complete`. Tests marked `llm_transport` (`src/ai/tests/test_transport.py`) run the real transport against a local HTTPS server; they generate a throwaway certificate with the `openssl` command-line tool, which must be on `PATH` (macOS and Linux include it; on Windows, Git Bash provides it).
- **Live evaluation.** An operator step, not CI ([test drafting](../workflow/specs/ai/test-drafting.md#live-evaluation)).

## Product website

The landing page source is [`index.md`](index.md), with [`_config.yml`](_config.yml). The [CI workflow](../.github/workflows/ci.yml) builds and checks the existing Cayman site before gated static publication; its design is under [Product website](../workflow/specs/TECHNICAL-SPEC.md#product-website).

To check an already generated `_site/` artifact, run from the repository root with Python:

```bash
python src/check_site.py _site --config docs/_config.yml
```

The [product website](https://cs3227-2610-mp4-relay.github.io/CS3227-2610-MP4/) is published; its hosting configuration is documented under [Product website](../workflow/specs/TECHNICAL-SPEC.md#product-website).

## Acknowledgements

Relay's development workflow, tooling and repository conventions were adapted from the [MP3 Deskmate baseline](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/tree/97ad99155307825a4b53925906e42f663647a70b), then streamlined for MP4.

The product-site scaffold uses GitHub's [Cayman theme](https://github.com/pages-themes/cayman). Relay uses [Django](https://www.djangoproject.com/) and [PostgreSQL](https://www.postgresql.org/) and plans to use [SoC LLM](https://dochub.comp.nus.edu.sg/cf/guides/soclaas/start). Local/CI container examples use the [official PostgreSQL image](https://hub.docker.com/_/postgres), whose [17.6 tag](https://hub.docker.com/layers/library/postgres/17.6/) was verified for this slice. Record any further reused external ideas, code or documentation here as they are adopted.

Static-site delivery uses GitHub's official [Jekyll build](https://github.com/actions/jekyll-build-pages), [artifact upload](https://github.com/actions/upload-pages-artifact) and [Pages deployment](https://github.com/actions/deploy-pages) actions.

Browser verification uses Microsoft's [Playwright Python library](https://github.com/microsoft/playwright-python) and GitHub's official [artifact upload action](https://github.com/actions/upload-artifact).

Production setup follows Vercel's [native Django deployment](https://vercel.com/docs/frameworks/full-stack/django), [CLI deploy](https://vercel.com/docs/cli/deploy), [deployment lookup](https://vercel.com/docs/rest-api/deployments/get-a-deployment-by-id-or-url), [alias API](https://vercel.com/docs/rest-api/aliases/get-an-alias) and [deployment protection](https://vercel.com/docs/deployment-protection) documentation, and Neon's [project](https://neon.com/docs/manage/projects) and [pooled/direct connection](https://neon.com/docs/connect/connection-pooling) guidance.

The tool adapters follow the official [Codex agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents). Usage collection draws on [Codex JSONL output](https://learn.chatgpt.com/docs/non-interactive-mode), [Claude Code output](https://code.claude.com/docs/en/headless) and [Claude cache accounting](https://platform.claude.com/docs/en/build-with-claude/prompt-caching). Local session-file parsing also depends on observed runtime formats and must be rechecked when clients change.
