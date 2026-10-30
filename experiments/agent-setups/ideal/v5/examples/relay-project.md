# Project settings for the agent workflow

The agent workflow is the same in every repository; this file holds what is particular to this one. These are Relay's values.

- **Full verification:** `source .venv/bin/activate && python src/manage.py check --settings=relay.settings.test && ruff check . && ruff format --check . && pytest -q -p no:cacheprovider` (needs the PostgreSQL test server from the Developer Guide).
- **Focused tests:** `source .venv/bin/activate && pytest -q -p no:cacheprovider src/<app>/tests/<file>.py`
- **Source and tests:** source in `src/`; tests in `src/**/tests/`.
- **Requirements home:**
  - `workflow/specs/product/*.md`, criteria identified as `RND-5.1`;
  - architecture and routes in `workflow/specs/TECHNICAL-SPEC.md`;
  - security controls in `workflow/specs/SECURITY-SPEC.md`.

  Mark each acceptance test with its criterion ID: `@pytest.mark.ac("RND-5.1")`.
- **User-facing docs:**
  - `docs/UserGuide.md`, in the exact words the product shows;
  - `docs/DeveloperGuide.md` for setup and design.
- **Plans home:** `workflow/plans/<issue>-<short-name>.md`.
- **Decisions-and-risks home:** `workflow/specs/SECURITY-SPEC.md`, for accepted residual risks; the human's other decisions go in the plan.
- **High-risk areas** (these get a security review): sign-in, sessions, role and workspace permissions, AI and LLM calls, dependencies, CI and deployment, and the development security controls.
- **Size budget:** 400 changed lines under `src/` outside tests and migrations per change.
- **Commits:** `<type>: <imperative summary> (#<issue>)`, with types as `AGENTS.md` lists; stage files by explicit path.
- **Never edit:** `.env` files, `logs/`, and the repository's own workflow files (`workflow/agents/`, `workflow/skills/`, `.claude/`, `.codex/`, `.agents/`).
