# Slice 6: Shared SoC LLM gateway (#6)

Goal: one bounded, provider-independent gateway that feature code can call without knowing the provider. Tier: High, because it adds an external service boundary, credentials, quota and AI controls.

Built in PR #78 together with #22's drafting. Every gateway design choice in the [contract](../specs/ai/llm-gateway.md) is a proposal pending confirmation by the gateway owner, Whimsyturtle, and the human (human decision 3 of 2026-10-29 in the [#22 plan](22-test-drafting-spec.md#human-decisions-2026-10-29-confirmed)).

## Decisions

- **Live off (human, 2026-10-29, confirmed):** `SOC_LLM_LIVE = False` in the shared settings keeps every provider call off until the real SoC LLM API, its retention and training terms and its limits are confirmed ([live switch](../specs/ai/llm-gateway.md#live-switch)).
- **Proposals, pending confirmation:**
  - the provider endpoint, model and credential are deployment settings; the committed code has no invented provider or credential, and a missing setting is a refusal, so the manual product workflow stays available;
  - the gateway validates transport and the outer envelope; features validate their own structured payload, as RND-8 does;
  - no dependency: the transport uses the standard library;
  - call slots and quota are PostgreSQL rows locked inside one transaction, so concurrent requests cannot oversubscribe them;
  - live evaluation is operational and excluded from CI; fake-provider tests cover the boundary.

## Size

Accepted by the human on 2026-10-29 as a one-off budget increase; the measured size and the repair estimate are in [the #22 plan](22-test-drafting-spec.md#human-decisions-2026-10-29-confirmed). The earlier report of 398 lines within the 400-line budget was wrong ([history deviations](22-test-drafting-spec.md#history-deviations)).

## Built checkpoints

1. `spec:` `550db7d`, the gateway contract, plan and the RND-8 implementation notice.
2. `feat:` `c6cb269`, the `ai` app, seeded deployment rows, gateway and fake provider; `d9be48a` added RND-8's pages.
3. `docs:` `89bebf9`; repairs `3caf1e8`, `78ab9b7` and `d234c9c`.

These commits were split after the work was done, not checkpoint by checkpoint. The independent-review repair is planned in the [#22 plan](22-test-drafting-spec.md#repair-after-independent-review-2026-10-29); its gateway checkpoint (B) covers the live switch, the whole-call deadline, conditional release, envelope and exception hardening, storage errors and removing `ai.Usage`.

## Open

- Confirmation of the contract's proposals by Whimsyturtle and the human.
- The live provider check, after the live switch's conditions are met.
