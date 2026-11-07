# Developer Guide

This guide introduces Relay's design and engineering approach. Start with the [design views](#design), use [Setup](#setup) to get running, and follow the [runbook](Runbook.md) for detailed commands and operating procedures.

## Design

Relay uses a server-rendered Django application with PostgreSQL and a shared boundary for AI provider calls; the [architecture overview](../workflow/specs/TECHNICAL-SPEC.md#architecture-overview) shows how those parts interact.

### Reading the diagrams

The diagrams live with their canonical architecture and data-model definitions in the technical spec, so a design change has one place to update.

| View | What it helps you understand |
| --- | --- |
| [Architecture overview](../workflow/specs/TECHNICAL-SPEC.md#architecture-overview) | Application responsibilities, storage and the external provider boundary |
| [Domain class diagram](../workflow/specs/TECHNICAL-SPEC.md#domain-class-diagram) | Workspace ownership and the relationships between rounds, criteria, cases, builds and results |
| [Round state diagram](../workflow/specs/TECHNICAL-SPEC.md#round-state-diagram) | Publication, retesting and closing |
| [Drafting request sequence](../workflow/specs/TECHNICAL-SPEC.md#drafting-request-sequence) | Authorized context, provider work and the user's separate save action |

These are conceptual views of the existing implementation; field definitions, route contracts and exact guards remain in the linked spec sections.

### Application responsibilities

| Package | Responsibility | Design reference |
| --- | --- | --- |
| [`relay`](../src/relay/) | Project configuration, routing and shared presentation | [Architecture](../workflow/specs/TECHNICAL-SPEC.md#architecture) |
| [`accounts`](../src/accounts/) | Workspace and account identity, sign-in, demo creation, coordinator-added testers and tester password reset | [Accounts and workspaces](../workflow/specs/TECHNICAL-SPEC.md#accounts-and-workspaces) |
| [`rounds`](../src/rounds/) | Round preparation, build coverage, results and retained history | [Rounds](../workflow/specs/TECHNICAL-SPEC.md#rounds) |
| [`ai`](../src/ai/) | Feature-specific drafting/feedback and the shared provider gateway | [AI contracts](../workflow/specs/ai/llm-gateway.md) |

For orientation within an app, begin with its URL patterns and views, then follow the operation into its domain logic and models; function-level explanations belong in their docstrings.

### Reasoning about the boundaries

The following consequences of the design are useful when assessing a change; their detailed rules stay in the referenced contracts.

| Design choice | Engineering consequence | Authoritative detail |
| --- | --- | --- |
| Server-rendered pages in one Django project | A user journey crosses views, forms and templates within the same application, so browser checks complement service tests. | [Architecture](../workflow/specs/TECHNICAL-SPEC.md#architecture) |
| Workspace-scoped access | Record relationships alone do not establish permission; the signed-in user's workspace provides the context for lookups. | [Access control](../workflow/specs/SECURITY-SPEC.md#sign-in-and-access-control) |
| Transactions around state-dependent writes | Rechecking under the shared round lock keeps concurrent actions consistent, while lock contention remains a cost to consider. | [Round writes](../workflow/specs/TECHNICAL-SPEC.md#rounds) |
| Explicit build coverage and retained results | A case's current build can change while an earlier result keeps its original case/build context. | [Result history](../workflow/specs/TECHNICAL-SPEC.md#rounds) |
| Transient AI assistance | A provider reply is validated and presented for human use; choosing a draft and saving a case are separate actions. | [AI boundaries](../workflow/specs/SECURITY-SPEC.md#ai-features-and-prompt-injection) |

The [drafting sequence](../workflow/specs/TECHNICAL-SPEC.md#drafting-request-sequence) makes the transaction boundary visible: provider latency is outside the domain write transaction, while gateway quota and usage bookkeeping are separate storage operations.

### AI assistance

The [shared gateway](../workflow/specs/ai/llm-gateway.md) centralizes provider transport and operational limits, while the [drafting](../workflow/specs/ai/test-drafting.md) and [observation-feedback](../workflow/specs/ai/observation-feedback.md) contracts define each feature's authorized source and accepted reply.

Read those contracts' confirmation and evaluation qualifications before relying on a provider assumption or interpreting test results; deterministic boundary checks and live-model usefulness answer different questions.

## Engineering approach

### Development workflow

The [slice workflow](../workflow/skills/slice.md) takes a scoped request through specification, small implementation checkpoints, a fixed review candidate and delivery, with checks and independent review selected by risk tier.

The builder, verifier and security-reviewer responsibilities, their tool adapters, and the limits of scope enforcement are explained in the [workflow guide](../workflow/README.md); the authoritative permission and approval rules are in [AGENTS.md](../AGENTS.md) and the [security spec](../workflow/specs/SECURITY-SPEC.md#development-workflow).

A slice's [plan](../workflow/plans/) records decisions and next steps, while [session logs](../logs/) and [experiments](../experiments/README.md) hold measured evidence rather than product requirements.

### Testing strategy

| Evidence | Main question | Where to look |
| --- | --- | --- |
| Unit and service checks | Do validation, domain operations and failure paths satisfy their contracts? | Each app's `tests/` directory and criterion IDs in the [product specs](../workflow/specs/PRODUCT-SPEC.md) |
| PostgreSQL integration and concurrency checks | Do persistence, constraints and competing actions preserve the required state? | [Data model](../workflow/specs/TECHNICAL-SPEC.md#data-model) and [test environment](../workflow/specs/TECHNICAL-SPEC.md#environments) |
| Browser journeys | Can a user complete the flow through the rendered forms, messages and navigation? | [`src/e2e/`](../src/e2e/) and [browser verification](../workflow/specs/TECHNICAL-SPEC.md#browser-verification) |
| Scripted AI and injection regressions | Does the application enforce its boundaries for synthetic source and replies? | [AI verification limits](../workflow/specs/SECURITY-SPEC.md#ai-features-and-prompt-injection) |

The [verification procedure](Runbook.md#verify) supplies commands and diagnostic steps; the [CI workflow](../.github/workflows/ci.yml) defines the configured hosted checks.

### Coding standards and documentation

The [Ruff configuration](../pyproject.toml) defines executable style checks; [AGENTS.md](../AGENTS.md#one-home-per-fact) assigns each kind of documentation its maintained home.

When navigating a design change, use the guide for orientation, the specs for contracts and diagrams, and source/docstrings for implementation mechanics.

## Setup

Follow the [runbook's setup steps](Runbook.md#setup) to select the repository's Python version and create the development environment; runtime and dependency pins stay in [`.python-version`](../.python-version) and the root requirements files.

### Run locally

Use the [local startup procedure](Runbook.md#run-locally), which includes PostgreSQL, configuration, migrations and starting Django.

### Create accounts for manual testing

Follow [demo account creation](Runbook.md#create-accounts-for-manual-testing), then use the [User Guide](UserGuide.md) for the role journeys.

The coordinator can [add Beta Testers](UserGuide.md#add-a-beta-tester) and [reset their passwords](UserGuide.md#reset-a-beta-testers-password) in that workspace; these actions use the existing account model without a migration, with transaction, credential and session handling defined in [accounts and workspaces](../workflow/specs/TECHNICAL-SPEC.md#accounts-and-workspaces).

### Verify

Use the [verification procedure](Runbook.md#verify) for the isolated test database, browser prerequisites, checks and failure diagnostics.

## Production deployment

Use the [production runbook](Runbook.md#production-deployment) together with the authoritative [release gate](../workflow/specs/TECHNICAL-SPEC.md#release-verification) for operator steps and their approval boundaries.

Deployment smoke checks require the public runtime database readiness probe described in the [release verification contract](../workflow/specs/TECHNICAL-SPEC.md#release-verification).

## SoC LLM

The [SoC LLM runbook](Runbook.md#soc-llm) contains local configuration and operator evaluation commands; feature and gateway contracts are linked under [AI assistance](#ai-assistance).

## Product website

The [product-site architecture](../workflow/specs/TECHNICAL-SPEC.md#product-website) describes the static documentation site, and its [runbook section](Runbook.md#product-website) contains the build-artifact check.

## Acknowledgements

Relay's development workflow, tooling, repository conventions and SoC chat-completions wire mapping were adapted from the [MP3 Deskmate baseline](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/tree/97ad99155307825a4b53925906e42f663647a70b), then streamlined for MP4; the gateway retains MP4's networking and quota controls.

The product-site scaffold uses GitHub's [Cayman theme](https://github.com/pages-themes/cayman). Relay uses [Django](https://www.djangoproject.com/) and [PostgreSQL](https://www.postgresql.org/) and calls [SoC LLM](https://dochub.comp.nus.edu.sg/cf/guides/soclaas/start) through its [shared gateway](../workflow/specs/ai/llm-gateway.md). The LLM gateway sends its requests with the [aiohttp](https://github.com/aio-libs/aiohttp) client library. Local/CI container examples use the [official PostgreSQL image](https://hub.docker.com/_/postgres). Record any further reused external ideas, code or documentation here as they are adopted.

Static-site delivery uses GitHub's official [Jekyll build](https://github.com/actions/jekyll-build-pages), [artifact upload](https://github.com/actions/upload-pages-artifact) and [Pages deployment](https://github.com/actions/deploy-pages) actions.

Browser verification uses Microsoft's [Playwright Python library](https://github.com/microsoft/playwright-python) and GitHub's official [artifact upload action](https://github.com/actions/upload-artifact).

Production setup follows Vercel's [native Django deployment](https://vercel.com/docs/frameworks/full-stack/django), [CLI deploy](https://vercel.com/docs/cli/deploy), [deployment lookup](https://vercel.com/docs/rest-api/deployments/get-a-deployment-by-id-or-url), [alias API](https://vercel.com/docs/rest-api/aliases/get-an-alias) and [deployment protection](https://vercel.com/docs/deployment-protection) documentation, and Neon's [project](https://neon.com/docs/manage/projects) and [pooled/direct connection](https://neon.com/docs/connect/connection-pooling) guidance.

The tool adapters follow the official [Codex agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents). Usage collection draws on [Codex JSONL output](https://learn.chatgpt.com/docs/non-interactive-mode), [Claude Code output](https://code.claude.com/docs/en/headless) and [Claude cache accounting](https://platform.claude.com/docs/en/build-with-claude/prompt-caching). Local session-file parsing also depends on observed runtime formats and must be rechecked when clients change.

Diagrams use [Mermaid](https://mermaid.js.org/intro/) syntax, following [GitHub's diagram documentation](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams).
