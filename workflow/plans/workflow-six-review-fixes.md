# Repair six workflow review findings

Goal: verify and repair the six reported workflow, snapshot, telemetry, permission and setup defects.

Tier: High, because the confirmed changes touch development security controls. Base: `4f2b9e2b84a94c398fe0d2a99ff71a7750eceeeb`. No product criteria or application code changes.

Why: restore the existing fast-lane intent, secret-file exclusion, honest telemetry, installation checkpoints and pinned-interpreter setup. The human explicitly requested these repairs and GPT 6.1 Sol subagents as needed.

- [x] Make tier requirements consistent in AGENTS, role/skill instructions, workflow overview and PR template; fast lane retains targeted checks and human diff review.
- [x] Reproduce and fix case-insensitive environment-file exclusions with a read guard, and detect assume-unchanged/skip-worktree index flags.
- [x] Reproduce missing Claude-message/Codex-export-turn usage; report unavailable counters and warnings while preserving same-message streaming merges.
- [x] Retain both Python pip-install approval entries; restore Python 3.14 prerequisite and explicit Windows interpreter selection.
- [x] Run focused regressions, full verification, fixed-candidate verifier/security reviews, scope checks and a session usage/log report.

Ownership: coordinator edits workflow controls because the builder's allowed paths exclude them. Reviewers are read-only and receive the fixed candidate and evidence. Preserve the existing untracked reference documents. No dependencies, commits, pushes or hosted changes are authorized by this task.

Budget: no `src/` changes and no added requirements. Tests use synthetic data only. Live adapter incidence of missing usage remains unverified; this repair targets the demonstrated export formats.

Verification environment: after the initial checks used MP3's existing environment, the human created MP4's `.venv`. The coordinator reran verification with MP4's activation script and confirmed Python 3.14.2, Ruff 0.17.0, pytest 9.1.1 and pytest-django 4.14.0. Results and remaining limitations are recorded in the session log below.

Outcome: all six findings confirmed and repaired. Full checks passed; both independent reviews returned no actionable findings, and scope/candidate rechecks passed. Evidence and limitations are in the [session log](../../logs/Whimsyturtle/002-repair-six-workflow-review-findings.md). Next step: human diff review of the uncommitted changes.
