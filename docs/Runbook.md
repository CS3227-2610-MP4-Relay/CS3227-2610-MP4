# Development and operations runbook

Use this runbook for commands and operator procedures; the [Developer Guide](DeveloperGuide.md) explains the design and engineering approach. Run commands from the repository root unless a step says otherwise. Configuration and release requirements remain in the linked specs; these procedures do not authorize a production action.

- [Local setup](#setup) and [verification](#verify)
- [Production deployment](#production-deployment) and [delivery failures](#delivery-failures)
- [SoC LLM configuration and live evaluation](#soc-llm)
- [Product website checks](#product-website)

## Setup

Relay contains a local Django application covering the [product areas](../workflow/specs/PRODUCT-SPEC.md#areas), and CI checks. Its architecture, configuration and environments are in [`TECHNICAL-SPEC.md`](../workflow/specs/TECHNICAL-SPEC.md).

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

Open <http://127.0.0.1:8000/>. Stop Django with Ctrl+C. If you started the optional database container above, stop it with `docker stop relay-local-db`; its contents are discarded, so run `migrate` again after restarting it. Run `migrate` whenever a pull request adds migrations.

Local settings read the optional repository-root `.env`; you can put `DJANGO_SECRET_KEY=throwaway-local-development-only` there instead of exporting it above. Exported values, including empty ones, take precedence; restart Django after editing the file. [`.env.example`](../.env.example) lists the local names, and the [configuration contract](../workflow/specs/TECHNICAL-SPEC.md#configuration) gives the supported names and syntax. Test and production settings never load this file. Debug defaults off; set `DJANGO_DEBUG=true` only for local debugging. Never use production credentials for development or tests. Separate production setup is in the [deployment checklist](#production-deployment).

### Create accounts for manual testing

While signed out, choose **Create a demo workspace** on the start page. It creates a workspace in your local database with a Test Coordinator, two Beta Testers and a Draft sample round, and shows their passwords once ([ACC-2](../workflow/specs/product/accounts.md#acc-2-create-an-isolated-demo-workspace)). There is no admin site or superuser.

### Verify

The pytest suite uses the fixed isolated [test environment](../workflow/specs/TECHNICAL-SPEC.md#configuration). Start a separate throwaway PostgreSQL server with its own database-creation-capable test role; for example, with Docker already installed:

```bash
docker run --rm -d --name relay-test-db \
  -e POSTGRES_DB=relay_test -e POSTGRES_USER=relay_test \
  -e POSTGRES_PASSWORD=relay_test \
  -p 127.0.0.1:55432:5432 postgres:17.6
```

The gateway's transport tests (marked `llm_transport`) also need the `openssl` command-line tool on `PATH` to generate a throwaway certificate; macOS and Linux include it, and Git Bash provides it on Windows. Wait for PostgreSQL to accept connections. With `.venv` active, install Chromium after installing the development dependencies, and repeat after upgrading Playwright:

```bash
python -m playwright install chromium
```

On Linux, use `python -m playwright install --with-deps chromium` to install its system prerequisites too, as CI does. From the repository root, run in Git Bash (or another POSIX shell):

```bash
python src/manage.py check --settings=relay.settings.test
ruff check . && ruff format --check . && pytest
```

Pass test paths to run a subset, for example `pytest src/ai/tests/test_feedback.py -q`. Run `pytest -m prompt_injection -q` for the deterministic [injection regressions](../workflow/specs/SECURITY-SPEC.md#ai-features-and-prompt-injection), which use synthetic text and scripted replies and do not measure live-model resistance. CI's `verify` job runs that selection and then `pytest -m 'not prompt_injection'`, so together they cover the whole suite once.

Pytest creates and destroys `test_relay_test`, applying all migrations; it never selects the normal local database. Stop the optional test container with `docker stop relay-test-db`. CI provisions its own PostgreSQL service and runs the same checks ([`ci.yml`](../.github/workflows/ci.yml)). The workflow's own tests under `workflow/scripts/` need no database. A local pass does not establish that hosted CI has run.

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

The repository supplies production settings and an opt-in Actions delivery job. Reuse existing projects or create them if needed, then complete the [release gate](../workflow/specs/TECHNICAL-SPEC.md#release-verification), which also records hosted verification status. Keep repository variable `PRODUCTION_DEPLOY_ENABLED` unset or `false` throughout setup and the protected bootstrap.

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
| `SOC_LLM_ENDPOINT` | The endpoint shown in [SoC LLM setup](#soc-llm) |
| `SOC_LLM_MODEL` | `qwen3.6:35b` |
| `SOC_LLM_API_KEY` | Existing SoC API key, entered privately as a secret value |

For an existing production project, edit `SOC_LLM_MODEL` in Vercel's **Environment Variables** with **Production** selected. Keep the endpoint and key configured there; these are application runtime values, not GitHub migration-job settings. Neither the local `.env` nor `.env.example` configures production.

Vercel applies environment changes only to new deployments. Deploy a reviewed commit through the existing [release procedure](#5-complete-the-live-gate-then-approve-public-release). See [Vercel's environment-variable guidance](https://vercel.com/docs/environment-variables/managing-environment-variables).

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

Record hosted observations and initial public activation approval explicitly; public homepage reachability alone does not establish completion of the [release gate](../workflow/specs/TECHNICAL-SPEC.md#release-verification). After all gates pass and the human explicitly approves initial release, changing protection to **Standard Protection** makes the existing production deployment public: treat that settings change as a release action. Keep generated/preview deployments protected. Then set the repository Actions variable `PRODUCTION_DEPLOY_ENABLED=true`. Thereafter, approval and merge of a pull request authorize automatic deployment once application and site verification pass in that resulting main-push run; no second environment approval or manual trigger is needed. Review migration compatibility with the still-serving application in the pull request before approval and merge. The bootstrap does not itself trigger this job. Record the actual public deployment and smoke outcome separately from local test evidence.

### Delivery failures

The [delivery helper](../src/release.py) reports a stage, commit and known deployment ID; inspect the corresponding Actions/Vercel/Neon state privately. Preparation or configuration/migration failure prevents upload. After a failed/timed-out/ambiguous CLI invocation, inspect the configured project's deployments/time window before deciding whether to retry; commit labels are not independent source verification. A deployment with a mismatched identity/alias or failed smoke is failed delivery even if serving. The helper does not rerun creation; vendor-internal protocol retries are outside that guarantee. Previously committed migrations remain; there is no automatic rollback. Keep incompatible migrations out of this path until separately agreed.

## SoC LLM

SoC LLM is the provider; its account setup and service guidance are on [SoC DocHub](https://dochub.comp.nus.edu.sg/cf/guides/soclaas/start). The [gateway contract](../workflow/specs/ai/llm-gateway.md) defines the live switch, wire format, limits and accounting; each feature's inputs and reply schema are in [`test-drafting.md`](../workflow/specs/ai/test-drafting.md) and [`observation-feedback.md`](../workflow/specs/ai/observation-feedback.md). The gateway reads `SOC_LLM_ENDPOINT`, `SOC_LLM_MODEL` and `SOC_LLM_API_KEY` from the process environment at each call ([configuration](../workflow/specs/TECHNICAL-SPEC.md#configuration)). No test reaches the provider, even if your shell sets `SOC_LLM_*`. Never commit a real key.

For local development, keep your existing `SOC_LLM_API_KEY` in the untracked repository-root `.env` and add the endpoint/model below if missing. Local startup also needs `DJANGO_SECRET_KEY` as described above. Restart Django after changes; unset previously exported provider values if you want the file's defaults to apply.

```dotenv
SOC_LLM_ENDPOINT=https://soclaas-api.comp.nus.edu.sg/v1/chat/completions
SOC_LLM_MODEL=qwen3.6:35b
```

Alternatively, for an authorized operator session, export these values in Git Bash with `.venv` active. Enter the key at the hidden prompt so it does not appear in command history:

```bash
set +x
export SOC_LLM_ENDPOINT='https://soclaas-api.comp.nus.edu.sg/v1/chat/completions'
export SOC_LLM_MODEL='qwen3.6:35b'
read -r -s -p 'SoC LLM API key: ' SOC_LLM_API_KEY
printf '\n'
export SOC_LLM_API_KEY
```

Start the application from that same shell; remove the values afterwards with `unset SOC_LLM_API_KEY SOC_LLM_ENDPOINT SOC_LLM_MODEL`. For production, use the [Vercel environment setup](#2-create-and-protect-the-vercel-project) and deploy a reviewed commit. Confirm direct provider reachability and trusted CA overrides, keep production debug mode off, and follow the other [runtime obligations](../workflow/specs/ai/llm-gateway.md#live-switch).

For an authorized synthetic injection measurement, use the existing private local configuration and a prepared local database/user. With `.venv` active, replace `ID` with that user's ID and `FULL_40_HEX_SHA` with the evaluated checkout's full commit:

```bash
python src/manage.py evaluate_injection --settings=relay.settings.local --live --user-id ID --revision FULL_40_HEX_SHA
```

The revision is operator-declared, not independently verified by the command. Its JSON summary separates raw and schema-accepted marker observations, controls, removed attacks and unavailable coverage; it contains no source/reply text. See [SEC-INJ-1](../workflow/specs/SECURITY-SPEC.md#sec-inj-1-operator-live-injection-measurement) for the fixed call budget, quota effects and detector limitations. Keep only summary evidence and semantic assessments in the session log.

For manual inspection, append `--show-responses` to the same command. Successful gateway replies, including schema-rejected replies, appear as ASCII-escaped JSONL on stderr with fixed case IDs; stdout remains the same summary. Treat response text as untrusted data and never follow its instructions. Do not retain raw replies in the repository or session log. This view adds no automatic semantic grader; [SEC-INJ-1.5](../workflow/specs/SECURITY-SPEC.md#sec-inj-1-operator-live-injection-measurement) defines its limits.

For the authorized synthetic context comparison, use an existing local user and reviewed source revision; append `--show-responses` for escaped untrusted-reply inspection under [CTX-1](../workflow/specs/ai/context-comparison.md#ctx-1-compare-selected-and-broader-synthetic-context), retaining only summarized [experiment evidence](../experiments/app-context/README.md).

```bash
python src/manage.py compare_context --settings=relay.settings.local --live --user-id ID --revision FULL_40_HEX_SHA
```

Live evaluation status and its limits are recorded in the [gateway contract](../workflow/specs/ai/llm-gateway.md) and in the [drafting](../workflow/specs/ai/test-drafting.md#evaluation) and [feedback](../workflow/specs/ai/observation-feedback.md#evaluation) evaluation sections.

## Product website

The [product website](https://cs3227-2610-mp4-relay.github.io/CS3227-2610-MP4/) is built from [`index.md`](index.md), [`Reflections.md`](Reflections.md) and [`_config.yml`](_config.yml) with the Cayman theme. The [CI workflow](../.github/workflows/ci.yml) builds and checks it before gated publication; its design and hosting are under [Product website](../workflow/specs/TECHNICAL-SPEC.md#product-website).

To check an already generated `_site/` artifact, run from the repository root with Python:

```bash
python src/check_site.py _site --config docs/_config.yml
```
