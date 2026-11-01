# Relay

Relay is a beta-testing portal for small software teams: Test Coordinators prepare test rounds, and Beta Testers record observations and retest fixes. Each role has an AI feature: coordinators can draft test cases, and testers can get feedback on a draft observation.

Relay is a local Django app. The [User Guide](docs/UserGuide.md) describes what is built, and the [Developer Guide](docs/DeveloperGuide.md) shows how to run it. The AI features' [live evaluation](docs/DeveloperGuide.md#soc-llm) and public hosting are still pending.

- [Product website](https://cs3227-2610-mp4-relay.github.io/CS3227-2610-MP4/)
- [User Guide](docs/UserGuide.md)
- [Developer Guide](docs/DeveloperGuide.md)
- [Production setup and pending release gates](docs/DeveloperGuide.md#production-deployment)
- [Reflections](docs/Reflections.md)

## How we build it

We use spec-driven development with a builder, an independent verifier and security review where needed. Start with [`workflow/README.md`](workflow/README.md); the rules agents follow are in [`AGENTS.md`](AGENTS.md).
