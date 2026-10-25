# Observation feedback

Planned AI feature for the Beta Tester; no prompt, schema or implementation exists yet. Its manual workflow belongs in [test results](../product/results.md).

## Inputs and authorship

After role/workspace/ownership authorization, use the tester's own draft observation and its case/criteria. The observation and coordinator-authored case text are untrusted source material, kept separate from developer instructions. Exclude other testers' observations and unrelated records.

## Output and review

Identify missing reproduction details and suggest specific clarifying questions without inventing facts. Suggestions cannot set Pass/Fail, rewrite a submitted observation or change round state. Keep the original draft and source case visible for review.

## Contract to settle before implementation

Define source selection and version handling, fixed instructions, exact bounded schema, allowed IDs, input/output limits, model, quota/time/retry rules and user-visible failure/refusal messages. Evaluate missing-detail detection, unnecessary questions on complete observations, unsupported advice and direct/cross-user injection. Shared transport and resource rules belong in the [gateway](llm-gateway.md).
