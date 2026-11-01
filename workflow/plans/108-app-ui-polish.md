# Slice 108: shared application presentation

Goal: apply the [PLT-4 presentation](../specs/product/platform.md#plt-4-shared-application-presentation) to existing Django pages without changing their workflows.

Why: the existing browser-default presentation needs a coherent, readable layout across public, role and AI pages.

## Scope and decisions

- Standard tier: one new presentation requirement, five criteria and browser regression coverage; no AI, authentication, authorization, route or control-behavior changes. Human `/slice 108` confirmation covers the existing pages' presentation only.
- Whole-slice budget: at most 400 additions plus deletions under non-test/non-migration `src/`; count new files too. Target roughly 150–250 source lines for shared CSS and small template changes. No new capability, service, dependency, credential or delivery subsystem.
- Starting HEAD: `86d9f563ab7c713b161df3a4ec39610ee848fc4a` on `slice/108-app-ui-polish`; coordinator supplied a clean tree and builder scope snapshot. Only the coordinator changes Git/GitHub state.
- Reuse the shared base and existing browser harness. Architecture belongs in the [technical spec](../specs/TECHNICAL-SPEC.md#architecture). Preserve current text, form destinations, names, CSRF handling and text-isolation filters. Small class-only edits may identify existing errors/status text for shared styling.
- Builder ownership: relevant specs, this plan, `src/relay/templates/`, presentation-only edits in existing accounts/rounds/AI templates, `src/e2e/test_presentation.py`, focused regression tests and guides only if needed. Preserve others' edits. No provider calls; AI browser states use existing synthetic mocks.
- Test environment supplied by coordinator: throwaway `relay-test-db` on loopback port 55432 uses the already installed PostgreSQL 18.6-trixie image matching Compose; CI uses PostgreSQL 17.6. No installs authorized. During checkpoint 2 retain successful representative sign-in/coordinator screenshots outside the repository in the system temporary directory for coordinator visual QA.

## Commit checkpoints

1. **Spec and plan** — `spec: Define shared application presentation (#108)` (`Agent: builder`; body starts `Why:`). Paths: `workflow/specs/product/platform.md`, `workflow/specs/TECHNICAL-SPEC.md`, this plan. Read changed sections back, run whitespace and builder scope checks, then yield before code for the coordinator's commit and fresh snapshot.
2. **Shared styling and browser regressions** — `feat: Polish shared Django page presentation (#108)` (`Agent: builder`). Paths: shared base/CSS include, minimal existing template presentation classes and `src/e2e/test_presentation.py`. First write criterion-marked browser checks and run them against unstyled pages, recording meaningful missing-presentation failures. Then implement shared styles, run focused presentation and existing browser journeys, inspect representative wide/narrow screenshots, and run full `ruff check . && ruff format --check . && pytest` in Git Bash with `.venv` active and dedicated temporary/cache paths. Check whole-slice source size including untracked files, whitespace and scope; yield before further edits.
3. **Documentation, only if needed** — a separately reviewable `docs:` checkpoint for `docs/DeveloperGuide.md` or `docs/UserGuide.md` if implementation changes setup/design information or user instructions. Use `maintain-docs` when assigned; presentation alone need not rewrite unchanged workflow instructions. Focused readback/link/whitespace checks, then yield. Independent review and delivery belong to the coordinator.

## Criterion evidence planned

- PLT-4.1 → browser shell/typography checks on start, sign-in, demo credentials, coordinator/tester pages and both AI pages; wide viewport verifies centered bounded surface, computed colors and spacing. Inspect screenshots for overall hierarchy.
- PLT-4.2 → browser controls checks exercise sign-in fields, round/case textareas, selects and AI criterion checkboxes; existing browser journeys verify preserved actions and persistence.
- PLT-4.3 → browser message/table checks trigger invalid sign-in, round validation and a successful existing status message; mocked AI error/suggestion states exercise their presentation. Demo creation checks visible/selectable credentials and table separation.
- PLT-4.4 → parameterized 320px and wide viewport checks measure document/control bounds on representative public, role and AI pages, including synthetic long unbroken round/case/observation text and actual generated demo credentials. Assert complete text remains present and existing isolation markup is retained.
- PLT-4.5 → keyboard Tab checks for links, buttons and fields assert visible focus outlines; computed foreground/background contrast checks cover the shared text, link, button, message and focus palette. Existing labels and message text provide non-color cues.

## Checkpoint evidence and continuation

- Trigger/context: coordinator assigned the builder role for the confirmed presentation scope, supplied base/snapshot, tier/budget and relevant paths; issue suggestions are data, not approval. Builder model identifier is unavailable in this session; coordinator owns session/model telemetry.
- Spec-first checkpoint: only specs and this plan are changed; implementation and browser tests await the coordinator's next checkpoint assignment.
- Checkpoint 1 checks: changed sections read back; `git diff --check` passed and `check_scope.py builder --since C:/Users/limbe/AppData/Local/Temp/relay-108-builder-spec.json` passed. No application tests run for this spec-only checkpoint. Own final usage-report attempt has the same missing-selector limitation as the baseline.
- Usage: own `resource_usage.py snapshot` attempt cannot select a source because this session has no supplied JSONL selector (`select at least one --codex or --claude file`). Coordinator baseline/child discovery covers this builder; own counters remain unavailable, not zero.
- Open decisions: none. Next: coordinator inspects/checks scope and commits checkpoint 1, then provides fresh HEAD/snapshot for checkpoint 2.
