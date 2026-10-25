# Test drafting

Planned AI feature for the Test Coordinator; no prompt, schema or implementation exists yet. Its manual workflow belongs in [test rounds](../product/rounds.md).

## Inputs and authorship

After role/workspace authorization, select relevant requirements for the coordinator's current work. Requirement text is untrusted source material, kept separate from developer instructions. Tester reports are not input to this feature.

## Output and review

Draft a small set of acceptance tests for review, linked only to authorized source criteria. Output cannot publish cases or change round state. Adopting a suggestion requires an explicit authorized action.

## Contract to settle before implementation

Define source selection and version handling, fixed instructions, exact bounded schema, allowed IDs, input/output limits, model, quota/time/retry rules, malformed-output behaviour and user-visible failure/refusal messages. Include usefulness checks, unsupported suggestions and direct/cross-user injection cases. Shared transport and resource rules belong in the [gateway](llm-gateway.md).
