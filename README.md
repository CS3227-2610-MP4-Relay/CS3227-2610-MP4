# Relay

Relay is a beta-testing portal for small software teams: Test Coordinators prepare, publish and review test rounds, and Beta Testers record results and observations and retest fixes. Coordinators can draft test cases with AI, and testers can ask AI to suggest missing details in an observation.

Relay runs locally as a Django app with isolated PostgreSQL tests; public application hosting remains planned. The [User Guide](docs/UserGuide.md) describes what is built, and the [Developer Guide](docs/DeveloperGuide.md) explains how to run it.

- [Product website](https://cs3227-2610-mp4-relay.github.io/CS3227-2610-MP4/)
- [User Guide](docs/UserGuide.md)
- [Developer Guide](docs/DeveloperGuide.md)
- [Production setup and pending release gates](docs/DeveloperGuide.md#production-deployment)
- [Reflections](docs/Reflections.md)

## How we build it

We use spec-driven development with a builder, an independent verifier and security review where needed. Start with [`workflow/README.md`](workflow/README.md); the rules agents follow are in [`AGENTS.md`](AGENTS.md).
