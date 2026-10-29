# Slice 6: Shared SoC LLM gateway (#6)

Goal: one bounded, provider-independent gateway that feature code can call without knowing the provider. Tier: High, because it adds an external service boundary, credentials, quota and AI controls.

## Decisions

- The provider endpoint, model and retention terms remain deployment settings; the committed code has no invented provider or credential. A missing setting is a refusal, so the manual product workflow stays available.
- The gateway validates transport and the outer `{"text": ...}` envelope. Features validate their own structured payload, as RND-8 requires.
- No dependency is added: the adapter uses the standard library's `urllib`.
- Call slots and quota are PostgreSQL rows locked inside one transaction, so concurrent requests cannot oversubscribe them.
- Live evaluation is operational and excluded from CI; fake-provider tests cover the boundary. The feature live check remains for the operator.

## Checkpoints

1. `spec:` gateway contract, technical/security links and this plan.
2. `feat:` `ai` app with models, gateway, fake provider and tests; migrations.
3. `test:` drafting wiring, route-matrix rows and documentation.

## Size

The gateway adds one app, one migration and its tests. Drafting is tracked by #22 and must stay within its confirmed 300–380 non-test-line estimate.

## Built checkpoints

1. `spec:` the gateway contract, plan and the RND-8 implementation notice.
2. `feat:` `ai` app, seeded deployment locks, gateway/fake provider, RND-8 pages and tests.
3. `test:` access-matrix rows and documentation.

The implementation uses the standard-library HTTP client, so no dependency was added. On 2026-10-29 the focused AI suite passed 68 tests, the rounds/accounts suites passed 801 tests, and the full AI branch suite passed 1106 tests plus 220 subtests. The live provider check is still pending a verified endpoint, model and credential.
