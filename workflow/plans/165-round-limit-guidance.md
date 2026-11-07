# Round-limit guidance

Goal: help readers of the User Guide continue after reaching the round limit by linking to the existing demo-workspace instructions (#165).

- Tier: Fast lane; documentation only, with no changed behaviour, acceptance criteria or security controls. Use `maintain-docs`; no delegated roles are needed.
- Base: `351a2ce8472f8cc067698c8e29103d4473379a6b`; branch `docs/165-round-limit-guidance` in the separate `tmp/worktrees/issue-165` worktree. Preserve the original checkout's edits.
- Existing requirements: [RND-1.4](../specs/product/rounds.md#rnd-1-prepare-a-test-round) and [ACC-2](../specs/product/accounts.md#acc-2-create-an-isolated-demo-workspace). No spec change is needed.
- Budget: one sentence and one internal link in `docs/UserGuide.md`, plus this plan and the session log; zero source lines or criteria changed.

## Checkpoints

1. `docs:` add the recommendation beside the limit and this plan. Check the changed section and link against the specs, existing account views and round service; run `git diff --check`.
2. `log:` record actual checks, usage and delivery evidence. Validate the new log's structure.
3. Push the branch, create a draft PR and inspect CI on its latest head. Human diff review remains pending until given; merge and release remain human decisions.

## Verification and next step

Plan recorded before the documentation edit. Existing code enforces the workspace round limit, signs users out, and creates a new demo workspace only while signed out. The linked guide section already explains account isolation and creation limits.

- `git diff --check`: passed after the edit.
- Manual source and document comparison: the recommendation matches RND-1.4, ACC-2.1 and ACC-2.6, `src/rounds/services.py`, `src/accounts/views.py` and `src/accounts/demo.py`. The internal link targets the existing unique `Create a demo workspace` heading. The changed section reads cleanly, without duplicate headings or orphaned text.
- No behavioural tests were added or run for this prose-only change; full application and site checks will run in the configured PR CI.
- Human diff review remains pending. The session log records measurement and delivery evidence; the draft PR reports latest-head CI results.
