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

Settings read exported environment variables, not `.env` files; [`.env.example`](../.env.example) lists local variable names. Debug defaults off; set `DJANGO_DEBUG=true` only for local debugging. Never use production credentials for development or tests. There is no production settings module or deployment workflow.

### Create accounts for manual testing

While signed out, choose **Create a demo workspace** on the start page. It creates a workspace in your local database with one Test Coordinator and two Beta Testers, and shows their generated passwords once; only the password hashes are stored. There is no admin site or superuser.

### Verify

The pytest suite uses the fixed isolated [test environment](../workflow/specs/TECHNICAL-SPEC.md#configuration). Start a separate throwaway PostgreSQL server with its own database-creation-capable test role; for example, with Docker already installed:

```bash
docker run --rm -d --name relay-test-db \
  -e POSTGRES_DB=relay_test -e POSTGRES_USER=relay_test \
  -e POSTGRES_PASSWORD=relay_test \
  -p 127.0.0.1:55432:5432 postgres:17.6
```

Wait for PostgreSQL to accept connections. From the repository root with `.venv` active, run in Git Bash (or another POSIX shell):

```bash
python src/manage.py check --settings=relay.settings.test
ruff check . && ruff format --check . && pytest
```

Pytest creates and destroys `test_relay_test`, applying all migrations; it never selects the normal local database. Test settings use a fast password hasher; other settings keep Django's default. Stop the optional test container with `docker stop relay-test-db`. CI provisions its own PostgreSQL service and runs the same checks. The workflow's own tests under `workflow/scripts/` still need no database. A local pass does not establish that hosted CI has run.

## Development workflow

How we work, and what each file in `workflow/` is for, is in [`workflow/README.md`](../workflow/README.md). Product behaviour belongs in [`workflow/specs/`](../workflow/specs/PRODUCT-SPEC.md); short slice plans belong in `workflow/plans/`. Tool adapters in `.claude/`, `.codex/` and `.agents/skills/` load the shared role and skill files. Workflow scripts and their tests live in `workflow/scripts/`.

Verified interaction summaries belong in `logs/<github-user>/`; experiment methods and evidence belong in [`experiments/`](../experiments/README.md). The team writes [`Reflections.md`](Reflections.md), with individual contributions under [`reflections/`](../reflections/README.md). Record observations and missing telemetry honestly; a scaffold or a proposed control is not evidence that the control ran.

### Coding standards

Ruff checks public class, method and function docstrings (`D101`–`D103`), 88-character lines (`E501`), top-level imports (`PLC0415`) and unused imports; the exact rules and exceptions are in [`pyproject.toml`](../pyproject.toml). Formatting is checked with `ruff format --check .`.

### Agent scope controls

Role write scopes live in `workflow/agents/`. The scope checker and tool hooks are described in [`workflow/README.md`](../workflow/README.md). Claude Code reviewers have a read-tool allowlist; Codex subagents inherit the parent session's permissions, so their role instructions do not establish a separate read-only sandbox. Hooks and post-run diff checks do not establish protection from arbitrary shell commands or malicious agents. Verify adapter loading and hook behaviour in each tool before relying on them.

## Design

The Django/PostgreSQL architecture, environment separation and planned delivery work are in [`TECHNICAL-SPEC.md`](../workflow/specs/TECHNICAL-SPEC.md). The `accounts` app (`src/accounts/`) holds the workspace and account models, sign-in, sign-out, the role home pages and demo workspace creation; its storage, routes and session rules are under [Accounts and workspaces](../workflow/specs/TECHNICAL-SPEC.md#accounts-and-workspaces) and [Accounts routes](../workflow/specs/TECHNICAL-SPEC.md#accounts-routes). `accounts/demo.py` generates the credentials and writes a demo workspace inside the `/demo/` view's single transaction, and `accounts/workspaces.py` holds `workspace_records`, the one helper every workspace record lookup goes through. The `rounds` app (`src/rounds/`) holds the round, acceptance criterion, test case and case–criterion link models and the coordinator's round pages, under [Rounds](../workflow/specs/TECHNICAL-SPEC.md#rounds) and [Rounds routes](../workflow/specs/TECHNICAL-SPEC.md#rounds-routes). `rounds/services.py` has `create_round(workspace, title)`, which locks the workspace row to enforce the 20-round cap and takes its workspace only from the caller, never from request data. Its criterion and case services (`add_criterion`, `add_case`, `save_case`, `delete_case`, `delete_criterion`) run inside the view's transaction after it locks the round row; they enforce the 20-criterion and 30-case caps, re-check that linked criteria belong to the round, delete a case's links before the case, and raise `Refused` with the user-facing message and the form field it belongs to. Links use the explicit `CaseCriterion` model so every foreign key stays `PROTECT`. `rounds/views.py` checks sign-in and role first through `coordinator_view(methods)`, reads rounds through `workspace_records`, then checks the round's state, and turns storage errors into the 503 page; `record_form` and `delete_record` serve all six criterion and case routes, with the record kind given in `rounds/urls.py`, and `round_form.html` renders every round form. The case form's criteria choices are the URL round's criteria only. In `rounds/templatetags/rounds_text.py`, the `isolated_lines` filter escapes each line of a title, criterion or case field into its own `dir="auto"` span, and the `title_isolate` filter removes bidi controls and line breaks and wraps a title in U+2068/U+2069 for the page `<title>`. Threats and controls are in [`SECURITY-SPEC.md`](../workflow/specs/SECURITY-SPEC.md).

## SoC LLM

Relay's planned AI contracts live under [`workflow/specs/ai/`](../workflow/specs/ai/llm-gateway.md). SoC LLM is the provider; its account setup and service guidance are on [SoC DocHub](https://dochub.comp.nus.edu.sg/cf/guides/soclaas/start). Before implementing the gateway, verify the team's actual model availability and service limits. Record the chosen model, bounded context, output validation, quotas and failure behaviour in the contracts. No provider call or live probe is implemented.

## Product website

The landing page source is [`index.md`](index.md), with [`_config.yml`](_config.yml). GitHub Pages setup and hosted verification remain future work; see [Product website](../workflow/specs/TECHNICAL-SPEC.md#product-website).

## Acknowledgements

Relay's development workflow, tooling and repository conventions were adapted from the [MP3 Deskmate baseline](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/tree/97ad99155307825a4b53925906e42f663647a70b), then streamlined for MP4.

The product-site scaffold uses GitHub's [Cayman theme](https://github.com/pages-themes/cayman). Relay uses [Django](https://www.djangoproject.com/) and [PostgreSQL](https://www.postgresql.org/) and plans to use [SoC LLM](https://dochub.comp.nus.edu.sg/cf/guides/soclaas/start). Local/CI container examples use the [official PostgreSQL image](https://hub.docker.com/_/postgres), whose [17.6 tag](https://hub.docker.com/layers/library/postgres/17.6/) was verified for this slice. Record any further reused external ideas, code or documentation here as they are adopted.

The tool adapters follow the official [Codex agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents). Usage collection draws on [Codex JSONL output](https://learn.chatgpt.com/docs/non-interactive-mode), [Claude Code output](https://code.claude.com/docs/en/headless) and [Claude cache accounting](https://platform.claude.com/docs/en/build-with-claude/prompt-caching). Local session-file parsing also depends on observed runtime formats and must be rechecked when clients change.
