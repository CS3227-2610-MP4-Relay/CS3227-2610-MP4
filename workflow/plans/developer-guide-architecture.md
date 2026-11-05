# Developer Guide architecture pass

Goal: make the Developer Guide a stable introduction to Relay's design and engineering approach, with canonical diagrams and a linked operational runbook.

Tier: Fast lane (documentation only). Base: `e57316f0111ac2d04af594305a473fb0927a8ddc`. Branch: `docs/developer-guide-architecture`. The human authorized a new branch and draft PR without an issue, after accepting the proposed division between architectural explanation, specifications and operational procedures. No application behaviour, acceptance criterion, security control, dependency or hosting setting changes.

## Commit checkpoints

1. **Plan** — this file, before document edits; whitespace and scope readback.
2. **Canonical design views** — add an architecture overview, conceptual UML class diagram, round state diagram and AI-assisted request sequence to `workflow/specs/TECHNICAL-SPEC.md`. Check every relationship and boundary against current models, services and AI views/gateway; link existing contracts without adding requirements. Check syntax and relative links before committing; attempt rendered visual verification before delivery and report any unavailable check.
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
- Canonical views checked against current `accounts/models.py`, `rounds/models.py`, `rounds/services.py`, `rounds/views.py`, `rounds/results.py`, `ai/views.py`, `ai/feedback_views.py` and `ai/gateway.py`. All 127 relative file/anchor links in the technical spec resolve; whitespace check passed. Syntax was checked against the official Mermaid and GitHub diagram documentation.
- Rendered verification is currently unavailable: the browser host is absent and no local Mermaid installation/cache was found. Automatic approval review rejected exporting the draft diagrams to Mermaid Ink; no export occurred and no dependency was installed. Rendering remains a human browser-review step unless an existing local renderer becomes available.
- Canonical views committed as `cb5f834`; plan checkpoint is `c3c9478`.
- Guide/runbook checkpoint: guide reduced from 4,042 words / 330 lines to 1,125 words / 122 lines. The four operational sections (setup/verification, production, SoC LLM, website checks) are preserved verbatim in the runbook, including all 16 Bash/dotenv blocks. All Bash blocks pass `bash -n`; none of the operational commands were executed. Existing `#run-locally`, `#soc-llm` and `#production-deployment` guide anchors remain as signposts for incoming historical/User Guide links.
- Integrated documentation check: 281 relative file/anchor links across guide, runbook, technical spec, README and unchanged User Guide resolve; fences are balanced and whitespace checks pass. No source, requirement, security-control, CI-workflow, User Guide or Reflections changes. The runbook joins the existing guides in the site exclusion list.
- Focused checks in the existing `.venv`: Django system check with test settings passed; `pytest src/relay/tests/test_site.py src/relay/tests/test_ci.py -q` passed (27 tests); Ruff lint passed and format check passed (143 files). Safe help checks passed for both operator commands with test settings, site checker and Playwright trace viewer. No live provider or production operation was run.
- Guide/runbook checkpoint committed as `0c1fd183369d536d6a013b5b88aa1a44a8ad1df9`; the frozen clean candidate remained unchanged during final source/documentation self-checks. Branch pushed and [draft PR #139](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/139) opened through authenticated CLI after the connector returned 403. The [session log](../../logs/Whimsyturtle/038-restructure-developer-guide.md) records the measurement cutoff, evidence and rendering limitation.
- Next: commit/push summary evidence and follow configured CI on that final PR head; put its exact result in the PR validation section. Human diff review, rendered-diagram inspection and log approval remain pending. No merge or release is authorized.
