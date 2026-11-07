# Slice 164: Explain the shared AI allowance

Goal: Explain the public deployment's shared AI allowance and the existing option for teams to host Relay with their own authorized provider account.

## Scope and decisions

- Fast lane documentation of existing behaviour: no changed acceptance criteria, application source, dependencies or security controls. Estimate: a few short guide paragraphs plus this compact plan and a session log.
- Existing requirements suffice: [gateway limits and accounting](../specs/ai/llm-gateway.md#limits-and-accounting), [live configuration](../specs/ai/llm-gateway.md#live-switch), [RND-8](../specs/product/rounds.md#rnd-8-draft-test-cases-with-ai) and [RES-4](../specs/product/results.md#res-4-suggest-missing-details-in-a-draft-observation). No spec change is needed.
- Explain that workspaces share the public deployment's allowance; other users can exhaust it while an individual's allowance remains. The deployment cap bounds Relay calls using the deployer's provider account, without guaranteeing availability or protection against the account's total provider-budget overrun.
- Link existing setup, hosting and provider-configuration instructions for teams using their own authorized account and credentials. Reusing the public deployer's account continues to share that account's provider allowance. Keep exact limits solely in the gateway contract.
- Preserve unrelated edits. Builder owns this plan and, after the coordinator checkpoint, `docs/DeveloperGuide.md` only. The coordinator owns Git state, delivery and the session log.

## Commit checkpoints and checks

1. `plan: Record shared AI allowance documentation scope (#164)` — this plan only; compare scope with the existing contract, read back and run the builder scope check.
2. `docs: Explain shared AI allowance and hosting tradeoff (#164)` — add the explanation under the Developer Guide's SoC LLM section, linking the gateway contract and existing setup/production runbook anchors. Read back the changed section, verify local link targets/anchors, run `git diff --check` and the builder scope check. No new regression tests or full application suite are needed for unchanged behaviour.
3. `log: Record shared AI allowance documentation session (#164)` — coordinator records actual checks, resources, review limits and delivery evidence, then updates the authorized draft PR and verifies its current hosted checks.

## Checkpoint and next step

- Starting candidate: `351a2ce8472f8cc067698c8e29103d4473379a6b`, supplied as a clean separate worktree; initial `git status --short` showed no changed paths (Git emitted a global-ignore permission warning).
- Source inspection confirms deployment-wide reservation/accounting and per-user quotas in `src/ai/gateway.py`; provider configuration is process-wide. The existing guide and runbook already contain the setup/production links needed. No conflicting requirement found.
- An AGENTS.md write is outside the builder's scope and is refused without attempting a mutation. This establishes role refusal only, not native-hook enforcement in this worktree.
- Open issues: none. Human diff review remains required for Fast lane; no human approval or independent review is inferred.
- Plan checkpoint committed by the coordinator at `01f88ca4dd974eed6a3e0b530a3b564e345e9c48`; guide work resumed against a fresh scope snapshot.
- Guide checkpoint: added two paragraphs under SoC LLM covering shared allowance, the operating tradeoff and existing hosting/configuration links. Read back the complete section with adjacent headings; no duplicated headings, orphaned fragments or lost text found. Verified all four added relative link destinations and their matching Markdown heading anchors.
- Targeted checks after the guide edit: `git diff --check` passed; `check_scope.py builder --since <relay-164-builder-docs.json>` passed. No acceptance criteria, source or tests changed, so no application tests were run.
- Next: coordinator checks and commits the guide/plan candidate, records session evidence, obtains the required human diff review and completes authorized draft-PR delivery with hosted checks on the current head. Human review remains pending.
- Builder telemetry is unavailable in this delegated session; the coordinator measures usage with `workflow/scripts/resource_usage.py`.
