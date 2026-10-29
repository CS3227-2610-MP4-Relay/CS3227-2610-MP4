# Shared LLM gateway

Relay's one boundary for SoC LLM calls. The gateway code is built, but [live provider calls are switched off](#live-switch), so every feature request currently gets that feature's unavailable result.

**Status: proposals pending confirmation.** Every design choice below, including the wire format, the time bound, the quotas and the in-flight caps, was proposed in PR #78 and awaits confirmation by the gateway owner, Whimsyturtle (#6), and the human. None is settled until both confirm it; the real SoC LLM API, its limits and its retention and training terms are not yet verified.

## Responsibilities

Feature code authorizes the user and selects source records before invoking the gateway. The gateway keeps fixed developer instructions apart from source data, bounds requests and replies, and returns exactly one of `Success(text)`, `Refused(code)` or `Failed(code)`. Features validate their own structured reply; the gateway checks only the outer envelope. Checked output remains untrusted.

The [security spec](../SECURITY-SPEC.md#ai-features-and-prompt-injection) owns threats and controls; feature contracts own their exact inputs, instructions and accepted outputs.

## Live switch

- `SOC_LLM_LIVE` in the shared settings (`relay.settings.base`) is `False`. It is a code-level setting, not read from the environment, so turning it on needs a reviewed change.
- While it is off, `gateway.complete` called without a test provider returns `Refused("live-off")` before any quota record, reservation or transport step, and the transport also refuses before reading any `SOC_LLM_*` variable. No network call is made, whatever `SOC_LLM_*` holds.
- It may be turned on only after the real SoC LLM API (endpoint and wire format), the provider's retention and training terms and its limits are confirmed, and the proposals in this file are confirmed or changed to match.

## Transport contract (proposed)

- One fixed HTTPS endpoint from `SOC_LLM_ENDPOINT`, with no credentials or fragment in the URL; certificate and hostname verification are on, and no redirect is followed (a 3xx is `Failed("transport")`). The request is `POST` with `Connection: close` and the JSON body `{"model": "<SOC_LLM_MODEL>", "instructions": "<fixed text>", "data": "<JSON text>"}` and no tool, browsing or function-calling fields.
- `SOC_LLM_API_KEY` goes in the `Authorization: Bearer` header and is never placed in the body, logs or an error message. The transport and `complete` mark the key, body, instructions and data as Django sensitive variables.
- **Deadline.** One 30-second deadline starts when the call's slots are reserved and bounds every phase: name resolution, connecting, the TLS handshake, sending the request, and reading the status line, headers and body. Name resolution runs in a helper thread that the transport stops waiting for at the deadline; a lookup that finishes later is discarded. Every socket operation is given only the time left, and the deadline is checked after each read, so a server that trickles headers or body cannot extend the call. The transport reads the raw response until the server closes the connection, then parses it. No call retries.
- The raw response, headers included, is capped at 244,096 bytes (12 bytes for each of 20,000 reply characters, the longest JSON escape of one character, plus 4,096); a longer response is `Failed("invalid-response")`.
- A 2xx response body must be one JSON object with exactly the key `text`, appearing once, whose value is a string of at most 20,000 characters with no surrogate code point; `NaN`, `Infinity` and any parse error are invalid. A refusal is exactly `{"refusal": "<string>"}`. Anything else is `Failed("invalid-response")`.
- HTTP 400, 401 and 403 and a refusal object are `Refused("provider-refused")`; 429 is `Refused("quota")`; a missing or invalid setting is `Refused("not-configured")`. The deadline is `Failed("timeout")`; a resolution, connection or TLS failure, a malformed HTTP response (any `http.client.HTTPException`), 3xx and 5xx are `Failed("transport")`. Provider bodies never reach the feature or logs.
- The gateway logs only the fixed outcome code, never instructions, data, reply text or exception text.

## Limits and accounting (proposed)

- A request whose instructions plus data exceed 8,000 characters is `Refused("input-too-large")` before any reservation.
- Each user has at most 1 call in flight and the deployment at most 2. Quota is 20 calls per user per rolling hour and 200 per deployment per rolling hour. One transaction locks the call slots, checks both quotas and records the call before the call starts, so failed, refused and timed-out calls count; any refusal is `Refused("busy-or-quota")`.
- `ai.CallSlot` rows hold the reservations ([data model](../TECHNICAL-SPEC.md#ai-gateway)). A reservation sets the user's slot and one free deployment slot to expire 35 seconds after it is made: the 30-second deadline plus a 5-second margin for releasing. Release runs on every exit and only clears a slot that still holds this call's expiry, so a call that ends late cannot clear a later call's reservation. An expired slot is free.
- `ai.CallRecord` keeps one timestamp per counted call. Records older than their window are deleted while that quota's lock is held.
- A storage error while reserving or releasing is raised to the feature, which applies its own storage-failure rule instead of reporting the AI service as unavailable.
- The gateway stores no prompt, source or reply text and records no token metrics. A later slice that records them stores a missing provider value as unavailable, never zero.
- There is no result cache. A future feature that adds one must isolate it by access scope and source version.

## Fake provider and verification

`ai.fakes.FakeProvider` is scriptable with an exact reply, refusal, failure or timeout and records the instructions and data it was given. Tests pass it to `complete` instead of using the transport; the live switch does not apply to it. Outside the transport tests, which opt in and use only a local server, a test fixture removes every `SOC_LLM_*` variable and makes the transport's network step fail ([configuration](../TECHNICAL-SPEC.md#configuration)).

The live check is an operator step, not CI, and needs the live switch on: configure the endpoint, model and key, run the drafting [live evaluation](test-drafting.md#live-evaluation), and record results in a log.
