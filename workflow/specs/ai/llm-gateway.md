# Shared LLM gateway

Relay's one boundary for SoC LLM calls. The transport is provider-independent; a deployment sets `SOC_LLM_ENDPOINT`, `SOC_LLM_MODEL` and `SOC_LLM_API_KEY`. Missing configuration is a refusal, never a local fallback.

## Responsibilities

Feature code authorizes the user and selects source records before invoking the gateway. The gateway keeps fixed developer instructions apart from source data, bounds requests and replies, and returns exactly one of `Success(text)`, `Refused(code)` or `Failed(code)`. Checked output remains untrusted.

The [security spec](../SECURITY-SPEC.md#ai-features-and-prompt-injection) owns threats and controls; feature contracts own their exact inputs, instructions and accepted outputs.

## Transport contract

- One fixed HTTPS endpoint from `SOC_LLM_ENDPOINT`; certificate verification is on and redirects are refused. The request is `POST` with the JSON body `{"model": "<SOC_LLM_MODEL>", "instructions": "<fixed text>", "data": "<JSON text>"}` and no tool, browsing or function-calling fields.
- `SOC_LLM_API_KEY` goes in the `Authorization: Bearer` header and is never placed in the body, logs or an error message.
- The transport uses one 30-second timeout for the whole request. No call retries. The feature sees one outcome within that bound.
- A successful HTTP response must be one JSON object with exactly the key `text`, a string of at most 20,000 characters. Anything else is `Failed("invalid-response")`.
- HTTP 400/401/403/429, a provider refusal object, or a missing credential are `Refused`; timeouts, connection failures, 5xx and malformed responses are `Failed`. Provider bodies never reach the feature or logs.
- The gateway logs only the fixed outcome code, never instructions, data, reply text or exception text.

## Limits and accounting

- A request whose serialized instructions plus data exceeds 8,000 characters is `Refused("input-too-large")` before any call.
- Each user has at most one call in flight and the deployment has at most two. A row lock on `ai.CallSlot` reserves a slot before the call and releases it on every exit.
- Quota is 20 calls per user per rolling hour and 200 per deployment per rolling hour, reserved atomically before the call. Failed, refused and timed-out calls count. `ai.CallRecord` keeps one timestamp per counted call; rows older than the window are removed while the quota lock is held.
- Reservation rows are `ai.CallSlot`: one row per user scope and two fixed deployment rows, holding an expiry timestamp. An expired slot is reusable; a live one refuses another call. `ai.Usage` rows are the per-user and deployment quota locks. Missing provider token metrics are recorded as unavailable, never zero. No prompt, source or reply text is stored.
- There is no result cache. A future feature that adds one must isolate it by access scope and source version.

## Fake provider and verification

`ai.fakes.FakeProvider` is scriptable with an exact reply, refusal, failure or timeout and records the instructions and data it was given. Tests inject it through the gateway rather than opening a network connection.

The live check is an operator step, not CI: configure the endpoint/model/key, run the drafting live evaluation in [test-drafting](test-drafting.md#live-evaluation), and record results in a log. The provider's retention and training terms must be confirmed before the check.
