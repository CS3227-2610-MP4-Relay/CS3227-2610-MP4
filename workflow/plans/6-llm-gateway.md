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

### Outcome

- **Commits:** `a59c4bb` (spec and plan), `a852c2d` (aiohttp transport, pins, tests), `96fc08d` (Developer Guide), then repair round 1: `c1ee651` (release allowlist) and `1863017` (gateway errors and tests).
- **Size:** 410 changed lines (+223/−187) from `1079285` to `1863017`, against the ~400 estimate; `gateway.py` went from 395 to 322 lines.
- **Coordinator decisions:** the call runs on its own event loop, closed with `loop.close()`, because `asyncio.run`, which `async_to_sync` also uses, waits for a hung lookup's thread (measured with `asyncio.run`: 6.01 s against a 1 s timeout); this runner choice is to be named to Whimsyturtle on #91. Any exception in the transport is a fixed outcome: `ValueError` and, from repair round 1, any other `Exception` are `Failed("transport")`.
- **Dropped tests:** per-read trickle and stalled-TLS-handshake tests (per-phase guarantees the review dropped); the old resolver-thread timeout test (replaced by a hung-lookup test that guards the runner); the raw-response and chunk-size-line cap tests (the cap is now on the body; replaced by at-cap, over-cap and chunked over-cap tests).
- **Red evidence by mutation:** each of `allow_redirects=True`, no body cap, `ssl=False`, `trust_env=True`, `auto_decompress=True`, no `Accept-Encoding`, `asyncio.run`, no `ValueError` clause, no timeout clause and `total=None` failed its targeted test. The first redirect mutant passed; that test was fixed to redirect to the same server.
- **Repair round 1 findings and fixes:**
  - A non-`OSError` from aiohttp or its resolver escaped `complete`. It now maps to `Failed("transport")`, and `_exchange` also marks `chunk` and `response`. Tests cover a lookup `RuntimeError` and a mid-request `RuntimeError` that leaves the key and request text out of logs. The error-report test now drives a `BaseException` through `_exchange` and a storage error through `complete`.
  - The total timeout and the deadline from reservation were untested; added a trickle test and two direct `_transport` deadline tests.
  - Added statuses 201 and 404. The spec notes that aiohttp may round the timeout up by under a second.
  - The release archive omitted `src/ai`; it is now packed, with a test that every local app is.
  - Each new test failed against its mutant or the old allowlist.
- **Checks:** focused `src/ai` tests and Ruff at each checkpoint; the full checks (Django check, makemigrations check, Ruff, pytest) passed on `96fc08d` (1,859 tests) and again after repair round 1.
- **Package identity:** each new package's installed metadata names its upstream repository: `aio-libs/aiohttp`, `aiohappyeyeballs`, `aiosignal`, `frozenlist`, `multidict`, `propcache` and `yarl`, `python-attrs/attrs` and `kjd/idna`. Their names match those declared by aiohttp 3.14.5 and yarl 1.25.1. This metadata is self-declared, so it does not prove where the packages were downloaded from.

## Open

- Confirmation of the contract's proposals by Whimsyturtle and the human.
- The live provider check, after the live switch's conditions are met.
- **Pre-live:** `ssl.create_default_context()` honours `SSLKEYLOGFILE`, `SSL_CERT_FILE` and `SSL_CERT_DIR`. Before turning live calls on, check they are unset in production, or set `keylog_filename = None`.
- **Residuals, recorded with no code change:**
  - After a timeout on a TLS connection whose server stays silent, the socket can stay open until garbage collection, because aiohttp's graceful TLS close is still waiting when the loop closes.
  - A hung lookup's thread keeps running after the call returns and is joined at interpreter exit, which can delay worker shutdown.
