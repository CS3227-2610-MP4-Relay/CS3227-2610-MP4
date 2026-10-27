# Relay

Relay is a beta-testing portal for small software teams: Test Coordinators prepare test rounds, and Beta Testers record observations and retest fixes. Each role will have an AI feature.

Relay has a local Django app with demo workspaces that start with a sample draft round, sign-in by role, abuse limits on sign-in and demo creation, test rounds with acceptance criteria and test cases that a coordinator can publish on a named build, retest on new builds and close, and isolated PostgreSQL tests; tester workflows and hosted environments remain planned. See the [Developer Guide](docs/DeveloperGuide.md) to run it.

- [User Guide](docs/UserGuide.md)
- [Developer Guide](docs/DeveloperGuide.md)
- [Reflections](docs/Reflections.md)

## How we build it

We use spec-driven development with a builder, an independent verifier and security review where needed. Start with [`workflow/README.md`](workflow/README.md); the rules agents follow are in [`AGENTS.md`](AGENTS.md).
