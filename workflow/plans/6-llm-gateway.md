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
3. `test:` AI route coverage, criterion-marked tests and documentation.

## Size

The gateway adds one app, three migrations and its tests. Drafting is tracked by #22; its 398 non-test source lines are within the 400-line hard budget, above the earlier 300–380 estimate by 18 lines after review repairs.

## Built checkpoints

1. `spec:` the gateway contract, plan and the RND-8 implementation notice.
2. `feat:` `ai` app, seeded deployment locks, gateway/fake provider, RND-8 pages and tests.
3. `test:` AI route coverage, criterion-marked tests and documentation.

The implementation uses the standard-library HTTP client, so no dependency was added. On 2026-10-29 the focused AI suite passed 86 tests, the rounds/accounts suites passed 801 tests, and the full AI branch suite passed 1128 tests plus 220 subtests. The live provider check is still pending a verified endpoint, model and credential.
