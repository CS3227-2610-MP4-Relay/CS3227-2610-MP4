# Security spec

Threats to Relay and to how it is built, and the intended controls against them. This is a planning scaffold. Controls link to their acceptance criteria where these are specified; verification is added by the slices that implement them, and no deployed security is claimed here.

## Secrets and settings

Threat: leaked keys, credentials or debug details expose data and production access.

- Keep secrets and personal data out of code, logs, fixtures and experiment evidence. Agents must not read secret files; see [`AGENTS.md`](../../AGENTS.md).
- Use separate development/test and production credentials and databases. Disable production debug mode and validate production configuration before startup.
- Tests use fixed non-secret values and a fake LLM provider. CI validation receives no production secrets. Production database TLS, host validation and error-detail handling must be specified and tested before deployment.

## Sign-in and access control

Threat: a visitor or user accesses another role's operations, another workspace's records or another tester's private draft.

- Authorize every route and record lookup on the server before reading data or selecting AI context. Define role, workspace, ownership and state permissions for each operation.
- Use Django's authentication, password hashing and CSRF protections, including its `Origin` check. Sessions are server-side, get a new identifier at every sign-in, end at sign-out and expire at an absolute time; sign-in ignores redirect targets ([ACC-1](product/accounts.md#acc-1-sign-in-and-out-by-role)). Session and cookie settings are in the [accounts routes](TECHNICAL-SPEC.md#accounts-routes), and production settings under [Configuration](TECHNICAL-SPEC.md#configuration).
- Accounts come only from demo workspace creation, with generated passwords shown once on an uncached response and stored only as hashes ([ACC-2.1 to ACC-2.3](product/accounts.md#acc-2-create-an-isolated-demo-workspace)). Accounts have no staff or admin capability ([account model](TECHNICAL-SPEC.md#accounts-and-workspaces)).
- Check the role before any record lookup, and filter every lookup by the signed-in user's workspace before reading; another workspace's record is indistinguishable from a missing one ([ACC-2.4](product/accounts.md#acc-2-create-an-isolated-demo-workspace)).
- Share an authorization test matrix across manual and AI actions. Include forged identifiers, cross-workspace requests and denied state transitions.

Threat: repeated sign-in attempts guess passwords, or repeated demo creation exhausts shared storage.

- Count failed sign-ins and demo creations per client address, with an overall creation cap, atomically in the database; refuse when the count cannot be checked ([ACC-3](product/accounts.md#acc-3-limit-abuse-of-sign-in-and-demo-workspace-creation)). Store addresses only as keyed hashes, and never trust client-supplied forwarding headers. Production waits for the client-address [release gate](TECHNICAL-SPEC.md#release-verification).
- Residual gaps, accepted for now:
  - An attacker with many addresses can use up the overall cap and block demo creation for everyone.
  - Behind a proxy that hides client addresses, or for requests without a parseable address, clients share one count.
  - Fixed windows allow a burst across a window boundary.
  - Storage still grows without bound: unlimited successful sign-ins create session rows, and expired sessions are never deleted; rotating addresses or IPv6 prefixes creates limit-counter rows. Hashed addresses are kept indefinitely until the [retention decision](TECHNICAL-SPEC.md#data-model) is made.

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
- Keep production and Pages publication privileges in their controlled release jobs. Hosted environment restrictions remain operator work under [Release verification](TECHNICAL-SPEC.md#release-verification).
- Protect the default branch: changes arrive only by pull request with one approving review, new pushes dismiss earlier approvals, and the GitHub Actions `verify` check must pass; a status posted by another app or user does not satisfy it. The branch need not be up to date before merging. The rules apply to admins; force pushes and branch deletion are blocked. Emergency bypass is an admin temporarily turning the rule off in Settings.
- Residual branch-protection gaps: admins, including agent sessions using an admin's credentials, can disable the rule or use API paths around it; an approver may approve commits they pushed to someone else's pull request; because branches need not be up to date, an incompatible combination of merges is caught only by CI on the default branch afterwards; and a pull request's own workflow changes can alter `verify`, which only a reviewer reading those changes would catch.
- Enable secret scanning and push protection for supported provider patterns (non-provider patterns are off). A pusher can bypass a push-protection block by giving a reason, so this complements keeping secrets out of the repository rather than replacing it.
- Design migration compatibility, credential scope, checked-source delivery and unknown-outcome recovery before enabling deployment. No deployment implementation is included in this scaffold.
