# Slice 6: Shared SoC LLM gateway (#6)

Goal: one bounded, provider-independent gateway that feature code can call without knowing the provider. Tier: High, because it adds an external service boundary, credentials, quota and AI controls.

Built in PR #78 together with #22's drafting. Every gateway design choice in the [contract](../specs/ai/llm-gateway.md) is a proposal pending confirmation by the gateway owner, Whimsyturtle, and the human (human decision 3 of 2026-10-29 in the [#22 plan](22-test-drafting-spec.md#human-decisions-2026-10-29-confirmed)).

Split out of #78 into its own PR, landing before RND-8's pages: see [the split](22-test-drafting-spec.md#split-2026-10-29).

## Decisions

- **Live off (human, 2026-10-29, confirmed):** `SOC_LLM_LIVE = False` in the shared settings keeps every provider call off until the real SoC LLM API, its retention and training terms and its limits are confirmed ([live switch](../specs/ai/llm-gateway.md#live-switch)).
- **aiohttp for networking (human, 2026-10-29, confirmed after Whimsyturtle's review of #91):** the transport uses aiohttp 3.14.5 and the packages it needs, replacing the earlier proposal to use only the standard library ([review repair](#review-repair-2026-10-29)).
- **Proposals, pending confirmation:**
  - the provider endpoint, model and credential are deployment settings; the committed code has no invented provider or credential, and a missing setting is a refusal, so the manual product workflow stays available;
  - the gateway validates transport and the outer envelope; features validate their own structured payload, as RND-8 does;
  - call slots and quota are PostgreSQL rows locked inside one transaction, so concurrent requests cannot oversubscribe them;
  - live evaluation is operational and excluded from CI; fake-provider tests cover the boundary.

## Size

Accepted by the human on 2026-10-29 as a one-off budget increase; the measured size and the repair estimate are in [the #22 plan](22-test-drafting-spec.md#human-decisions-2026-10-29-confirmed). The earlier report of 398 lines within the 400-line budget was wrong ([history deviations](22-test-drafting-spec.md#history-deviations)).

## Built checkpoints

1. `spec:` `550db7d`, the gateway contract, plan and the RND-8 implementation notice.
2. `feat:` `c6cb269`, the `ai` app, seeded deployment rows, gateway and fake provider; `d9be48a` added RND-8's pages.
3. `docs:` `89bebf9`; repairs `3caf1e8`, `78ab9b7` and `d234c9c`.

These commits were split after the work was done, not checkpoint by checkpoint. The independent-review repair is planned in the [#22 plan](22-test-drafting-spec.md#repair-after-independent-review-2026-10-29); its gateway checkpoint (B) covers the live switch, the whole-call deadline, conditional release, envelope and exception hardening, storage errors and removing `ai.Usage`.

## Review repair (2026-10-29)

Whimsyturtle requested changes on #91: Relay should own its application rules and leave networking to an HTTP library, without hand-built DNS lookup or a per-phase deadline contract, accepting less control over DNS and TLS timing. The [transport contract](../specs/ai/llm-gateway.md#transport-contract-proposed) now has aiohttp make the request, with Relay's deadline as its total timeout.

Checkpoints, each committed after its focused checks:

1. `spec:` the transport contract, need 6's wording in [test drafting](../specs/ai/test-drafting.md#requirements-on-the-gateway), the hosting dependency sentence in the technical spec, and this plan.
2. `feat:` aiohttp and its requirements pinned in `requirements.txt`, the gateway transport rewritten on aiohttp, the network-blocking fixture moved to the new seam, and the transport tests adapted, with red evidence by mutation. Checks: `pytest -q -p no:cacheprovider src/ai`, Ruff.
3. `docs:` the Developer Guide's SoC LLM tests bullet and reused-code paragraph, if they changed.

Size estimate: about 400 changed lines in total, most of them removals (the hand-built networking and its tests), with the gateway about 100 lines shorter.

## Open

- Confirmation of the contract's proposals by Whimsyturtle and the human.
- The live provider check, after the live switch's conditions are met.
