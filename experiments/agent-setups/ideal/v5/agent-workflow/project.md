# Project settings for the agent workflow

The agent workflow is the same in every repository; this file holds what is particular to this one. Agents read it instead of guessing, so fill in every value.

- **Full verification:** `<the command that must pass before review, such as "make check" or "npm test && npm run lint">`
- **Focused tests:** `<how to run one test file or one test>`
- **Source and tests:** source in `<paths>`; tests in `<paths or patterns>`.
- **Requirements home:** `<where requirements or specs live, and how they are identified>`
- **User-facing docs:** `<docs that must match the behaviour>`
- **Plans home:** `<where a change's plan goes>` (default: `agent-workflow/plans/`).
- **Decisions-and-risks home:** `<the file where the human's decisions and accepted risks or residuals are recorded>`
- **High-risk areas** (these get a security review): `<such as sign-in, permissions, payments, external services, dependencies, CI and deployment>`
- **Size budget:** `<such as 400 changed lines of source outside tests per change>`
- **Commits:** `<message format>`; stage files by explicit path.
- **Never edit:** `<paths agents must not change, such as secrets or generated files>`
