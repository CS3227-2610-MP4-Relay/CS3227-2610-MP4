# Shared LLM gateway

Planned shared boundary for Relay's SoC LLM calls. No provider transport, quota, cache or telemetry implementation exists yet.

## Responsibilities

Feature code must authorize the user and select relevant source records before invoking the gateway. The gateway will keep fixed developer instructions apart from source data, bound requests and replies, validate structured output and return a defined success/refusal/failure result. Checked output remains untrusted.

The [security spec](../SECURITY-SPEC.md#ai-features-and-prompt-injection) owns threats and controls; feature contracts own their exact inputs, instructions and accepted outputs.

## Contract to settle before implementation

- Verify the actual SoC endpoint, model availability and service limits; choose the model and resource budget explicitly.
- Define request format, instruction/source separation, maximum context and output sizes, allowed schemas, identifier checks and plain-text rendering.
- Specify authentication boundaries, quota accounting, bounded time/retries and failure ordering. Manual testing must remain usable during an AI outage.
- Record observable tokens, calls, latency and cache use where available; mark missing metrics as unavailable. Specify privacy and retention before persisting telemetry. Decide whether result reuse is needed; if adopted, specify access scope and source/version invalidation.
- Define fake-provider tests, a small authorized live-check procedure and injection/usefulness evaluation before claiming the boundary is verified.
