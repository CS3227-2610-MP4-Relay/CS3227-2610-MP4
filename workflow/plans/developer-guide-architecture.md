# Developer Guide architecture pass

Goal: make the Developer Guide a stable introduction to Relay's design and engineering approach, with canonical diagrams and a linked operational runbook.

Tier: Fast lane (documentation only). Base: `e57316f0111ac2d04af594305a473fb0927a8ddc`. Branch: `docs/developer-guide-architecture`. The human authorized a new branch and draft PR without an issue, after accepting the proposed division between architectural explanation, specifications and operational procedures. No application behaviour, acceptance criterion, security control, dependency or hosting setting changes.

## Commit checkpoints

1. **Plan** — this file, before document edits; whitespace and scope readback.
2. **Canonical design views** — add an architecture overview, conceptual UML class diagram, round state diagram and AI-assisted request sequence to `workflow/specs/TECHNICAL-SPEC.md`. Check every relationship and boundary against current models, services and AI views/gateway; link existing contracts without adding requirements. Check diagram rendering and relative links before committing.
3. **Guide and procedures** — rewrite `docs/DeveloperGuide.md` around design decisions, engineering practice and a short setup entry point; relocate existing setup/verification, production and live-evaluation procedures to `docs/Runbook.md`. Preserve command bodies and operational safeguards. Update direct incoming links in `README.md`, `.env.example` and the technical spec; exclude the runbook from the product site in `docs/_config.yml`. Check relocation parity, Bash syntax, links/anchors, source references and site configuration; read changed sections back for missing rules and fragments. Do not change the User Guide, Reflections, runtime code or frozen plans.
4. **Evidence and delivery** — record final targeted checks and resource usage in this plan and one session log; inspect staged diffs for each checkpoint, push the branch and create/update its draft PR using the repository template. Follow the latest PR head's configured CI through completion. Human diff review and log approval remain pending.

## Decisions and limits

- Architecture, domain relationships and request boundaries have one canonical home in the technical spec; the guide links to those diagrams instead of copying them or maintaining generated images.
- Diagrams explain stable responsibilities, associations and transitions, omitting field inventories, quotas and internal helper sequences. The sequence illustrates drafting; it distinguishes gateway bookkeeping from saving a case and includes refusal/invalid-reply outcomes.
- Keep useful operational information, external credits and existing safety/approval boundaries. Remove implementation narration whose maintained home is already code or a spec. No new tooling/dependency or live provider/production operation.
- Build from current `origin/main`, which already includes the earlier guide cleanup; the initial advice was based on the older local main. Existing merged plans stay frozen.
- Fast lane uses the `maintain-docs` route with coordinator edits and targeted checks. No delegated agents are required; self-checks are not independent review. Human diff review remains an explicit draft-PR step.

## Evidence and next step

- Starting working tree was clean; fetched `origin/main` and created the requested branch at the base above. Local main was left unchanged.
- Usage baseline captured before implementation; final measurement and session-specific coverage limits belong in the session log.
- Next: add and verify the canonical design views, then commit that checkpoint before restructuring the guide.
