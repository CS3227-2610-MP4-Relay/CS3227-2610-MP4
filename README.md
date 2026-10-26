# Relay

Relay is a beta-testing portal for small software teams: Test Coordinators prepare test rounds, and Beta Testers record observations and retest fixes. Each role will have an AI feature.

Relay has a local Django app with demo workspaces, sign-in by role, draft test rounds with acceptance criteria and test cases, and isolated PostgreSQL tests; publishing rounds, testing workflows and hosted environments remain planned. See the [Developer Guide](docs/DeveloperGuide.md) to run it.

- [User Guide](docs/UserGuide.md)
- [Developer Guide](docs/DeveloperGuide.md)
- [Reflections](docs/Reflections.md)

## How we build it

We use spec-driven development with a builder, an independent verifier and security review where needed. Start with [`workflow/README.md`](workflow/README.md); the rules agents follow are in [`AGENTS.md`](AGENTS.md).
