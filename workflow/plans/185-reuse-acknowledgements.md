# Reuse acknowledgements (#185)

Goal: make the Developer Guide's acknowledgements distinguish concrete reused/adapted material, carried-forward ideas and Relay-specific implementation.

## Scope and decisions

- Fast lane: documentation only; no product behaviour, criteria, security controls, dependencies or source changes. Builder owns this plan and `docs/DeveloperGuide.md`; coordinator owns Git, delivery and `logs/Whimsyturtle/063-...md`.
- Starting candidate: clean `a93430a3879e3a0af85eaa251b428a1d791d83e5` in the separate `tmp/worktrees/issue-185` worktree. No spec change is needed because no contract changes.
- Preserve existing third-party credits. Expand only the acknowledgement section with a compact file/component inventory; distinguish literal matching material from adapted workflow ideas. Credit MP2's one-home-per-fact approach as reported in [the reflection](../../reflections/Whimsyturtle.md#organising-context-so-instructions-remain-findable), without implying MP2 application code was copied.

## Provenance and limits

- Read local MP3 Git objects at `97ad99155307825a4b53925906e42f663647a70b` using a command-local `safe.directory` exception; no persistent configuration change. Remote provenance has not been independently fetched.
- Direct comparisons found identical `CLAUDE.md`, all 17 MP3 `.gitignore` lines present in Relay, and concrete shared nonblank lines in `pyproject.toml`, `AGENTS.md`, `workflow/scripts/check_scope.py`, `workflow/skills/slice.md` and the GitHub issue/PR templates. Shared-line counts are leads for attribution, not a copying percentage or exhaustive audit.
- MP3's script inventory contains `check_scope.py`, `check_logs.py` and their tests; `resource_usage.py` is absent. Inspect remaining relevant pairs before naming them as literal reuse. Relay's initialization history (`c75363a`, `1a1cf10`, `3b5236c`) and [initialization log](../../logs/Whimsyturtle/001-initialize-relay-scaffold-and-log-usage.md) distinguish the adapted scaffold from fresh application work and the new collector.
- [The gateway plan](6-soc-chat-completions.md) and [integration log](../../logs/Whimsyturtle/020-check-soc-llm-readiness.md) attribute the chat-completions mapping to MP3 while retaining Relay's transport/quota controls. Inspect the two gateway implementations before describing any literal code reuse; do not call the whole gateway copied.
- New-component examples should name Relay's `src/relay/`, `src/accounts/`, `src/rounds/` and AI feature code with bounded wording supported by their introduction history; avoid claiming every line is original or that this inventory is exhaustive.
- Native pre-edit enforcement was unavailable: no exposed role-aware guarded edit tool demonstrably invokes the hook, so no out-of-scope `AGENTS.md` mutation was attempted. Coordinator collects delegated usage; per-run attributable telemetry is unavailable here.

## Checkpoints and next actions

1. `plan: Record reuse acknowledgement scope (#185)` — this plan only. Read back and run `git diff --check` plus builder scope check, then yield before Developer Guide edits.
2. `docs: Detail reused and new Relay components (#185)` — after coordinator supplies a fresh checkpoint, finish bounded provenance checks and edit only Developer Guide acknowledgements; update this plan with actual evidence. Read back the changed section, check local link targets, `git diff --check`, builder scope and the final two-path diff. No application tests are needed for prose-only attribution.
3. Coordinator records log 063, freezes the candidate, requests human diff review (pending until actually given), and completes authorized draft-PR delivery and configured CI. Do not describe pending review as completed.

## Implementation evidence

- Coordinator committed the plan at `d01668928da9fc91f362fb49de6369a99e3c5f0e` before implementation and supplied a fresh scope snapshot. Builder changed only Developer Guide acknowledgements and this plan; no Git state changes.
- Further local baseline comparisons found shared nonblank exact lines in `check_logs.py` (52), its tests (23), scope-check tests (65), and the PR/log/docs skills (1/10/6). These are distinct matching lines, not a reuse percentage; common syntax alone does not establish provenance. Initialization history/log supplies the adaptation context.
- MP3's 224-line `llm_gateway.py` and Relay's 570-line gateway share only 15 distinct nonblank lines; inspected request construction shows the same chat-completions fields with different instruction/data handling and output limits. The guide credits wire-format adaptation rather than whole-gateway copying. MP3 `llm.py` exists at the cited commit (`git cat-file -e` passed).
- Relay introduction commits inspected: application foundation `c566577`, identity `dd91b7c`, gateway storage `c6cb269`, drafting `d9be48a`, feedback `a17d210`, collector `3b5236c`. The guide names components developed for Relay without claiming every line is original. MP2 credit is explicitly supported by the team reflection, not an MP2 code-copy audit.
- Targeted checks after the guide edit: PowerShell extraction checked all 21 local acknowledgement link destinations/anchors successfully; `git diff --check` and `python workflow/scripts/check_scope.py builder --base d01668928da9fc91f362fb49de6369a99e3c5f0e` passed. Changed section read back: one acknowledgement heading, complete table/paragraphs, existing third-party credits retained. No tests added or application suite run for this prose-only change.
- Next: coordinator checks the supplied scope snapshot, reviews the final diff, records log 063, and completes authorized delivery. Human diff review remains pending. Remote URL availability was not checked; cited MP3 provenance was checked through the local Git objects.

No contradictory source fact found. Literal reuse versus conceptual adaptation remains qualified wherever provenance establishes similarity without the copying mechanism.
