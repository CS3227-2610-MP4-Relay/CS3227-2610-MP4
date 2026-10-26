# Security spec

Threats to Relay and to how it is built, and the intended controls against them. This is a planning scaffold. Application controls, acceptance criteria and their verification will be added with the slices that implement them; no deployed security is claimed here.

## Secrets and settings

Threat: leaked keys, credentials or debug details expose data and production access.

- Keep secrets and personal data out of code, logs, fixtures and experiment evidence. Agents must not read secret files; see [`AGENTS.md`](../../AGENTS.md).
- Use separate development/test and production credentials and databases. Disable production debug mode and validate production configuration before startup.
- Tests use fixed non-secret values and a fake LLM provider. CI validation receives no production secrets. Production database TLS, host validation and error-detail handling must be specified and tested before deployment.

## Sign-in and access control

Threat: a visitor or user accesses another role's operations, another workspace's records or another tester's private draft.

- Authorize every route and record lookup on the server before reading data or selecting AI context. Define role, workspace, ownership and state permissions for each operation.
- Use Django's authentication, password hashing and CSRF protections. Specify session/cookie policy, demo-account creation, abuse limits and denied-request behaviour before implementing accounts.
- Share an authorization test matrix across manual and AI actions. Include forged identifiers, cross-workspace requests and denied state transitions.

## Rounds, observations and history

Threat: edits or concurrent submissions change the meaning of an earlier result, overwrite history or apply an action in the wrong round state.

- Define build and criteria associations, published-case version rules and observation edit/submission rules before writing the schema.
- Check permissions and state when applying writes, including explicit adoption of AI suggestions. Test important overlapping submissions and failure outcomes once those contracts are settled.

## AI features and prompt injection

Threat: user-written requirements, cases or observations steer the model into misleading another user, disclosing unrelated records or changing a testing decision.

- Keep developer instructions separate from user-written source data. Select only relevant, authorized context; exclude secrets and unrelated records.
- AI suggests text only. It has no browsing, execution or database tools and cannot publish tests, set outcomes, rewrite submitted observations or close rounds. Applying a suggestion requires an explicit authorized action through normal server checks.
- Validate a bounded response schema, allowed identifiers and text lengths; reject extra fields, including outcome/status changes. Render accepted suggestions as escaped plain text and keep the source material visible for review.
- Coordinator test drafting uses selected requirements, not tester reports. Tester feedback uses the tester's own draft and its case/criteria. Coordinator-authored cases can carry cross-user injection into tester prompts; test that path as well as direct injection.
- Test malformed replies, unauthorized identifiers, attempted disclosure/state changes, hidden failure instructions and misleading suggestions. A schema-valid answer may still mislead; measure that separately from unauthorized disclosure or writes.

Exact prompts, schemas, limits and failure rules belong in [`ai/`](ai/llm-gateway.md) before implementation. Prompt wording and human review are additional safeguards, not guarantees.

## Resource use and cached results

Threat: oversized inputs, repeated calls or incorrect cache reuse spend the shared allowance or expose another user's context.

- Bound context, replies, time, calls and retries according to verified SoC limits. Make AI failure or refusal leave the manual workflow usable.
- If result reuse is implemented, isolate it by access scope and source version; authorize before lookup and invalidate on relevant changes. Do not add a cache merely to fill out the scaffold.
- Record only the necessary operational metadata; specify retention and failure behaviour before adding persistent telemetry. Do not log prompts, observations, credentials or provider error bodies by default.

Threat: accumulated business records, abandoned workspaces and expired sessions exhaust shared storage and prevent other users from saving work. Settle the [persistence lifecycle and capacity decisions](TECHNICAL-SPEC.md#data-model) before implementing persistence.

## Development workflow

Threat: malicious repository content or a mistaken agent bypasses scope, weakens tests, reads secrets or claims verification it did not perform.

- Treat repository contents, issues, handoffs and model output as data rather than instructions, under [`AGENTS.md`](../../AGENTS.md).
- Restrict role tools and writes, keep independent verification, review a fixed candidate and recheck affected behaviour after repairs. Native read-only settings and scope checks have different limits; see [`workflow/README.md`](../README.md).
- Changes affecting development security controls, including agent permissions, scope-enforcement scripts and hooks, require High-tier specialist review under the [slice workflow](../skills/slice.md). Classify by effect on the control, not merely by filename; unrelated prose and formatting retain their normal tier.
- Verify development controls with synthetic secrets and malicious repository instructions that attempt prohibited access or test weakening. Retain observed actions and outcomes; configuration alone is not proof of enforcement.
- Record actual triggers, context, check results and repair rounds. Mark unavailable telemetry as unavailable; never invent human approval, test results or usage data.

## CI and dependencies

Threat: untrusted code receives secrets, dependency substitution runs malicious code or a passing check is mistaken for a checked release.

- Pin dependencies and third-party CI actions; verify package/action identities before adoption. Give validation jobs read-only repository permissions and no stored production secrets; do not use `pull_request_target` for untrusted code.
- Keep production and Pages publication privileges in their controlled release jobs. Branch protection, required checks and hosted environment restrictions remain operator work under [Release verification](TECHNICAL-SPEC.md#release-verification).
- Design migration compatibility, credential scope, checked-source delivery and unknown-outcome recovery before enabling deployment. No deployment implementation is included in this scaffold.
