# Developer Guide

## Setup

Relay currently contains the repository and development-workflow scaffold. The Django application, database schema and hosted environments will be implemented in later slices. Its planned architecture, configuration and environments are in [`TECHNICAL-SPEC.md`](../workflow/specs/TECHNICAL-SPEC.md).

Install Python 3.14, as selected by [`.python-version`](../.python-version), before creating the local tooling environment. On Windows, use the Python launcher to select it explicitly; an unqualified `python` may select another installed version. From the repository root in Git Bash:

```bash
py -3.14 -m venv .venv
source .venv/Scripts/activate
python --version
python -m pip install -r requirements-dev.txt
```

Confirm that `python --version` reports 3.14.x before installing. If `py -3.14` cannot find it, install Python 3.14 or use the explicit path to that interpreter. On macOS/Linux, create the environment with `python3.14 -m venv .venv` and activate it with `source .venv/bin/activate`.

Run the checks in [`AGENTS.md`](../AGENTS.md#commands). The current workflow checks need no database. Application startup, migrations, database setup and demo-account instructions will be added when those features exist. Never use production credentials for development or tests.

## Development workflow

How we work, and what each file in `workflow/` is for, is in [`workflow/README.md`](../workflow/README.md). Product behaviour belongs in [`workflow/specs/`](../workflow/specs/PRODUCT-SPEC.md); short slice plans belong in `workflow/plans/`. Tool adapters in `.claude/`, `.codex/` and `.agents/skills/` load the shared role and skill files. Workflow scripts and their tests live in `workflow/scripts/`.

Verified interaction summaries belong in `logs/<github-user>/`; experiment methods and evidence belong in [`experiments/`](../experiments/README.md). The team writes [`Reflections.md`](Reflections.md), with individual contributions under [`reflections/`](../reflections/README.md). Record observations and missing telemetry honestly; a scaffold or a proposed control is not evidence that the control ran.

### Coding standards

Ruff checks public class, method and function docstrings (`D101`–`D103`), 88-character lines (`E501`), top-level imports (`PLC0415`) and unused imports; the exact rules and exceptions are in [`pyproject.toml`](../pyproject.toml). Formatting is checked with `ruff format --check .`.

### Agent scope controls

Role write scopes live in `workflow/agents/`. The scope checker and tool hooks are described in [`workflow/README.md`](../workflow/README.md). Claude Code reviewers have a read-tool allowlist; Codex subagents inherit the parent session's permissions, so their role instructions do not establish a separate read-only sandbox. Hooks and post-run diff checks do not establish protection from arbitrary shell commands or malicious agents. Verify adapter loading and hook behaviour in each tool before relying on them.

## Design

The planned Django/PostgreSQL architecture, environment separation and delivery work are in [`TECHNICAL-SPEC.md`](../workflow/specs/TECHNICAL-SPEC.md). Threats and intended controls are in [`SECURITY-SPEC.md`](../workflow/specs/SECURITY-SPEC.md). Neither describes an implemented application yet.

## SoC LLM

Relay's planned AI contracts live under [`workflow/specs/ai/`](../workflow/specs/ai/llm-gateway.md). SoC LLM is the provider; its account setup and service guidance are on [SoC DocHub](https://dochub.comp.nus.edu.sg/cf/guides/soclaas/start). Before implementing the gateway, verify the team's actual model availability and service limits. Record the chosen model, bounded context, output validation, quotas and failure behaviour in the contracts. No provider call or live probe is implemented.

## Product website

The landing page source is [`index.md`](index.md), with [`_config.yml`](_config.yml). GitHub Pages setup and hosted verification remain future work; see [Product website](../workflow/specs/TECHNICAL-SPEC.md#product-website).

## Acknowledgements

The product-site scaffold uses GitHub's [Cayman theme](https://github.com/pages-themes/cayman). Relay plans to use [Django](https://www.djangoproject.com/), [PostgreSQL](https://www.postgresql.org/) and [SoC LLM](https://dochub.comp.nus.edu.sg/cf/guides/soclaas/start). Record any further reused external ideas, code or documentation here as they are adopted.

The tool adapters follow the official [Codex agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents). Usage collection draws on [Codex JSONL output](https://learn.chatgpt.com/docs/non-interactive-mode), [Claude Code output](https://code.claude.com/docs/en/headless) and [Claude cache accounting](https://platform.claude.com/docs/en/build-with-claude/prompt-caching). Local session-file parsing also depends on observed runtime formats and must be rechecked when clients change.
