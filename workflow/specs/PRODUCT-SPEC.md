# Product spec

Relay is a planned beta-testing portal for small software teams. It coordinates manual testing and records results; the software being tested runs outside Relay. How it will be built is in [`TECHNICAL-SPEC.md`](TECHNICAL-SPEC.md), and its threats and intended controls are in [`SECURITY-SPEC.md`](SECURITY-SPEC.md).

The repository currently contains a scaffold, with no application features implemented. The areas below record the agreed direction. Exact screens, fields, state rules and acceptance criteria must be settled before each implementation slice.

## Roles

- **Test Coordinator:** prepares and publishes test rounds, manages acceptance criteria and test cases, reviews results, requests retests and closes rounds. Its AI feature drafts a small set of acceptance tests from selected requirements for review.
- **Beta Tester:** views available tests, saves and submits outcomes with observations, reviews previous results and retests fixes. Its AI feature compares a draft observation with its case and criteria, identifies missing reproduction details and suggests clarifying questions without inventing facts.

Use role-based accounts and isolated demo workspaces so peers can try both sides. Define each action's role, workspace and ownership rules before implementation.

## Areas

| Prefix | Area | File |
| --- | --- | --- |
| `PLT` | Platform, shared infrastructure and delivery | [`product/platform.md`](product/platform.md) |
| `ACC` | Accounts, roles and demo workspaces | [`product/accounts.md`](product/accounts.md) |
| `RND` | Coordinator preparation, publication, review and closure | [`product/rounds.md`](product/rounds.md) |
| `RES` | Tester observations, outcomes, history and retests | [`product/results.md`](product/results.md) |

AI feature contracts live under [`ai/`](ai/): [test drafting](ai/test-drafting.md), [observation feedback](ai/observation-feedback.md) and the [shared gateway](ai/llm-gateway.md).

## Requirements

Each area's file will hold its requirements. A requirement's ID is its area's prefix and a number, such as `RND-1`; each acceptance criterion adds a second number, such as `RND-1.2`, and tests should identify the criteria they check. A criterion is met only when its marked tests pass; specifying it does not implement it.

The core loop is prepare → publish → test → review → retest as needed → close. Retesting may repeat. Preserve earlier results and the build and criteria they concern; settle edit/version rules for published cases and submitted observations before implementing them.

Out of initial scope: automated browser testing of external software, code execution, external integrations and a full bug-tracking system.
