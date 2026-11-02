# 123: Shared UI repairs

Goal: repair shared action styling, return navigation, Contents hierarchy, history typography and AI pending feedback under [PLT-4](../specs/product/platform.md#plt-4-shared-application-presentation).

Tier: Standard; integrated delivery is High because subsequent 125/126 touch AI and user-scoped reads. Starting HEAD: `0ce51aeb3e0f660d745382d79fa2baf1e2f93941`; coordinator snapshot: private `relay-123-builder-plan.json`. Coordinator observed builder model `gpt-6.1-sol`, medium effort; coordinator collects combined session usage. No dependencies, services or persistence changes. Limit: one requirement changed, <=400 runtime source lines (insertions + deletions); estimate 130–220.

Why: existing UI obscures navigation, hierarchy and slow AI requests. Existing PLT-4.2 covers demo styling; .6/.7 clarify history hierarchy and edit return navigation. New .10/.11/.12 separately define public return navigation, Contents nesting and transient pending behaviour.

Checkpoints:
1. `spec: Define UI journey repairs`: specs and compact plans for 123–126; yield before source/tests. Each later slice amends only its own product requirement.
2. `fix: Repair shared actions and reading navigation`: accounts templates, rounds edit view/Contents/history templates, shared CSS; regressions in `src/e2e/test_presentation.py`, `test_navigation.py` and `src/rounds/tests/test_views.py`. Red first: missing demo treatment/home link/edit return, flat lists and history hierarchy. Green: focused server/browser journeys, narrow and desktop, initial and invalid edit input, existing escaping/disclosures retained. Covers PLT-4.2/.4/.6/.7/.8/.10/.11.
3. `fix: Show pending AI form submissions`: base/shared script include and AI drafting/feedback templates; browser tests in `src/e2e/test_drafting.py` and `test_feedback.py` with gated fake gateway responses. Red first: no pending feedback or duplicate-submit guard. Green: immediate status/disabled button, repeated submit suppression (one fake call), history restoration, native invalid input, JavaScript-disabled normal forms and existing failures. Covers PLT-4.12; existing RND-8/RES-4 controls unchanged.

Audit: edit-round GET and invalid POST omit round context; other normal criterion/case/publish/retest/result/AI pages already supply return destinations. New round has only Coordinator home. Existing conflict/error actions remain unchanged. Contents nesting applies to both round roles; results/history retain applicable structure. History keeps exact Test case/Build/Status/Outcome and detail labels while placing the label above the title.

Next: coordinator commits spec checkpoint and assigns checkpoint 2 with fresh snapshot. PostgreSQL and Chromium available; no DB tests run during planning. Run full integrated lint/format/pytest after all implementation units, then independent verifier/security review. Guides updated only after behaviour is built.
