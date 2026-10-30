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

- **Commits:** `a59c4bb` (spec and plan), `a852c2d` (aiohttp transport, pins, tests), `96fc08d` (Developer Guide), then repair round 1: `c1ee651` (release allowlist), `1863017` (gateway errors and tests) and `0e9d7f6` (plan); repair round 2: `33db58f` (spec) and `2158659` (plan); repair round 3: `668de0a` (test), `4168172` (spec) and `8262023` (plan).
- **Size:** 410 changed lines (+223/−187) from `1079285` to `1863017`, against the ~400 estimate; `gateway.py` went from 395 to 322 lines.
- **Coordinator decisions:** the call runs on its own event loop, closed with `loop.close()`, because `asyncio.run`, which `async_to_sync` also uses, waits for a hung lookup's thread (measured with `asyncio.run`: 6.01 s against a 1 s timeout); this runner choice is to be named to Whimsyturtle on #91. Any `Exception` in the transport is a fixed outcome (`ValueError` and, from repair round 1, any other `Exception` are `Failed("transport")`); a `BaseException` propagates after the slots are released.
- **Dropped tests:** per-read trickle and stalled-TLS-handshake tests (per-phase guarantees the review dropped); the old resolver-thread timeout test (replaced by a hung-lookup test that guards the runner); the raw-response and chunk-size-line cap tests (the cap is now on the body; replaced by at-cap, over-cap and chunked over-cap tests).
- **Red evidence by mutation:** each of `allow_redirects=True`, no body cap, `ssl=False`, `trust_env=True`, `auto_decompress=True`, no `Accept-Encoding`, `asyncio.run`, no `ValueError` clause, no timeout clause and `total=None` failed its targeted test. The first redirect mutant passed; that test was fixed to redirect to the same server.
- **Repair round 1 findings and fixes:**
  - A non-`OSError` from aiohttp or its resolver escaped `complete`. It now maps to `Failed("transport")`, and `_exchange` also marks `chunk` and `response`. Tests cover a lookup `RuntimeError` and a mid-request `RuntimeError` that leaves the key and request text out of logs. The error-report test now drives a `BaseException` through `_exchange` and a storage error through `complete`.
  - The total timeout and the deadline from reservation were untested; added a trickle test and two direct `_transport` deadline tests.
  - Added statuses 201 and 404. The spec notes that aiohttp may round the timeout up by under a second.
  - The release archive omitted `src/ai`; it is now packed, with a test that every local app is.
  - Each new test failed against its mutant or the old allowlist.
- **Checks:** focused `src/ai` tests and Ruff at each checkpoint; the full checks (Django check, makemigrations check, Ruff, pytest) passed on `96fc08d` (1,859 tests) after repair round 1 on `1863017` plus the plan (1,868 passed, 220 subtests), and again on `2158659` and `8262023` (1,868 passed, 220 subtests each, run by the coordinator).
- **Redundant clause:** the `ValueError` clause in `_transport` is now covered by the catch-all and is kept as documentation.
- **History deviation:** `1863017` carried two spec edits in a `fix:` commit rather than a separate `spec:` commit: the exception sentence and the timeout rounding clause. Their reason is this Outcome section; history was not rewritten.
- **Repair round 3 (approved by the human, 2026-10-30):** the error-report test now also checks that the slots are released when a `BaseException` escapes; the live-switch TLS bullet separates `SSLKEYLOGFILE` from the CA-store variables; the socket residual states both causes; and the decisions line distinguishes `Exception` from `BaseException`.
- **Package identity:** each new package's installed metadata names its upstream repository: `aio-libs/aiohttp`, `aiohappyeyeballs`, `aiosignal`, `frozenlist`, `multidict`, `propcache` and `yarl`, `python-attrs/attrs` and `kjd/idna`. Their names match those declared by aiohttp 3.14.5 and yarl 1.25.1. This metadata is self-declared, so it does not prove where the packages were downloaded from.

## Review repair (2026-10-30)

Whimsyturtle requested changes on #91: a timed-out request can leave background work and connections behind. This matches the two residuals previously recorded under [Open](#open) with no code change:

- After a timeout the socket stayed open until garbage collection. After TLS is established (a silent server or a trickle), `Connection.close()` starts asyncio's graceful TLS shutdown, which `loop.close()` abandons; with a garbage collection after each test and `-W error::ResourceWarning`, `test_a_server_that_never_answers_times_out` and the trickle test each reported an unclosed socket and `_SelectorSocketTransport`, and still passed. A discarded close callback during connect or the handshake was suspected but not shown: a scratch run against a listener that never answers the handshake reported no warning.
- A hung lookup's executor thread kept running after the call and was joined at interpreter exit, which can delay worker shutdown.

Goal: after any outcome the call leaves no open socket or transport and no thread that can delay interpreter exit, within the 30-second deadline and 5-second release margin and without a new dependency ([after the call](../specs/ai/llm-gateway.md#transport-contract-proposed)).

Approach: the call's loop subclasses `asyncio.EventLoop`, recording each transport `create_connection` returns, and its default executor runs each job in its own daemon thread. In `_run`'s `finally`, remaining tasks are cancelled and awaited for at most 1 second, the recorded transports are aborted, one loop pass runs their close callbacks, and the loop closes. A scratch run of this approach against `tls_server.py` showed no `ResourceWarning` for the silent and trickle cases and no non-daemon thread after a hung lookup.

Checkpoints, each committed after its focused checks:

1. `spec:` the "After the call" bullet in the transport contract and this section.
2. `fix:` `src/ai/gateway.py` (`_run`, the loop subclass and the daemon executor) with regression tests in `src/ai/tests/test_transport.py`, and `tls_server.py` if a helper is needed: no `ResourceWarning` and no client socket left open after a silent-server timeout, a trickle timeout, a success and an oversized body; no non-daemon thread after a hung lookup; a subprocess making one hung-lookup call exits promptly. Red evidence against the old `_run`. Checks: `pytest -q -p no:cacheprovider src/ai`, Ruff.
3. `plan:` the outcome, after the full checks.

Size estimate: about 180 changed lines: spec and plan about 30, `gateway.py` about 45, tests about 100.

### Outcome (2026-10-30)

- **Commits:** `0c243f6` (spec), `4cb6fda` (plan), `66f6a2e` (fix and tests), then this outcome.
- **Human decision (2026-10-30):** lookups use daemon threads; aiodns, which would make them cancellable, is not adopted.
- **Size:** 281 changed lines (+269/−12) against the ~180 estimate: spec and plan 24, `gateway.py` 70 (+67/−3), tests 187 (`test_transport.py` +143/−6, of which the 6 removals are `padded_reply` moved above its first use, and the new subprocess helper `hung_lookup.py`, 38). The overrun is in the tests: four outcome cases for open sockets instead of two, two `_run` task tests added beyond the plan, and the subprocess helper.
- **Tests:** `test_no_connection_is_left_open_after_the_call` (silent, trickle, success, oversized; no client socket to the server right after the call with automatic collection paused, and no `ResourceWarning` at a following `gc.collect()`; skipped where `/dev/fd` is missing), `test_a_hung_name_lookup_leaves_no_thread_that_delays_exit`, `test_a_process_with_a_hung_name_lookup_exits_promptly` (20-second hung lookup, exit in under 10 seconds), `test_the_call_cancels_its_leftover_tasks` and `test_a_task_ignoring_cancellation_delays_the_call_by_at_most_the_bound`.
- **Red evidence against the old `gateway.py`:** 6 failed, 3 passed. Silent and trickle left one open client socket; the hung lookup left a non-daemon thread; the subprocess took 20.5 seconds to exit; the leftover task was not cancelled. The cancellation-bound test failed only on the missing `CLEANUP_TIMEOUT`, so its evidence is the unbounded-wait mutant below. Success and oversized already passed: they guard against regressions.
- **Mutation evidence against the fix:** no `abort()` and no final loop pass each failed silent and trickle (and, with the socket count removed, the `ResourceWarning` assertion alone failed both); no daemon executor and `daemon=False` each failed the thread and subprocess tests; no `task.cancel()` failed the leftover-task test; `asyncio.wait` without a timeout failed the cancellation-bound test.
- **Checks:** focused `src/ai` tests (94 passed) and Ruff on `66f6a2e`'s candidate; full checks on `66f6a2e`: Django check (no issues), `makemigrations --check --dry-run` (no changes), Ruff check and format, `pytest -q -p no:cacheprovider` (1,900 passed, 231 subtests).
- **Known noise (fixed in repair round 1):** the cancellation-bound test left its task pending on purpose, so asyncio printed "Task was destroyed but it is pending!" to stderr.
- **Residual:** see [Open](#open).
- **Repair round 1 (verifier and security-reviewer on `a33d799`; size growth to about 340 lines approved by the human, 2026-10-30):**
  - Medium: a reply aiohttp cannot parse, on a held connection, left a socket open. aiohttp closes that TLS transport twice, and asyncio's second `close()` drops the transport's link to its TLS layer, so aborting it no longer reached the socket. `_CallLoop.create_connection` now also records the socket transport under a TLS transport, through asyncio's private `_ssl_protocol._transport` (no public route exists), and `_settle` aborts it. Recording and closing the `sock` argument instead, as suggested, closed the socket but still left an unclosed `_SelectorSocketTransport` warning at collection. aiohappyeyeballs closes its own socket if cancelled while connecting, and aiohttp passes that socket to `create_connection` with no wait in between, so the hand-off leaves no gap. New no-leak case: `unparsable` (`HELLO`, `Failed("transport")`).
  - Low: the no-leak test now always checks for `ResourceWarning` and skips only the socket count where `/dev/fd` is missing.
  - Low: the spec's "After the call" now gives the thread bound (20 per user and 200 per deployment per rolling hour, not bounded by the in-flight caps, accumulating only while the resolver fails to return), says transports are aborted and sockets still connecting or in the handshake are closed by cancellation, and says leftover-task reports are logged as a fixed code.
  - Low (security): `_CallLoop` has an exception handler that logs only `LLM gateway loop report: leftover-task`, and `_settle` retrieves the exceptions of tasks that finished during the wait. Tests: a failing, an early-failing and a stubborn leftover task log no key, exception or task text; a task that fails on cancellation logs no report. The stderr noise is gone.
  - Nit: `_settle` runs `loop.shutdown_asyncgens()` within the same 1-second bound as the task wait; a test checks a suspended async generator is closed.
  - **Red evidence against `a33d799`'s `gateway.py`:** `unparsable` (one open client socket), the async-generator test, the log-text test (the key and exception text in asyncio's report) and the cancellation-report test (asyncio's "Task exception was never retrieved") failed.
  - **Mutation evidence:** no recording of the socket transport failed `unparsable`; no exception handler failed the log-text test; no exception retrieval failed the cancellation-report test; no `shutdown_asyncgens()` failed the async-generator test; no `wait_for` bound failed the cancellation-bound test.
  - **Checks:** focused `src/ai` (98 passed) and Ruff; full checks: Django check (no issues), `makemigrations --check --dry-run` (no changes), Ruff check and format, `pytest -q -p no:cacheprovider` (1,904 passed, 231 subtests; the first run also reported "1 warning" whose text was not shown, and three reruns, one full, reported none).
  - **Size:** this round +135/−10 (`gateway.py` +37/−4, `test_transport.py` +86/−4, spec +1/−1, plan +11/−1); the whole 2026-10-30 repair from `ac2801d` is 418 changed lines (+406/−12): `gateway.py` 103, tests 269 (`test_transport.py` 231, `hung_lookup.py` 38), spec 1, plan 45. That is about 80 over the approved ~340, almost all in the four new tests; the human accepted the 418 lines as they are on 2026-10-30.

## Open

- Confirmation of the contract's proposals by Whimsyturtle and the human.
- The live provider check, after the live switch's conditions are met.
- **Pre-live:** the TLS environment variables condition in the [live switch](../specs/ai/llm-gateway.md#live-switch).
- **Residual:** a thread blocked in the operating system's resolver cannot be stopped. After the [2026-10-30 repair](#review-repair-2026-10-30) it no longer delays exit, but it keeps running until the resolver returns ([after the call](../specs/ai/llm-gateway.md#transport-contract-proposed)). Cancellable lookups would need aiodns, a new dependency the human declined on 2026-10-30.
