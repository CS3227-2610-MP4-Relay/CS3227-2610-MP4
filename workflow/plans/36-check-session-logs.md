# Check every session log

Goal: Audit all saved session logs and correct evidenced mechanical documentation defects while preserving historical content and its evidence limits.

## Scope and decisions

- Trigger: human `/slice 36`; issue #36 identifies the audit. Fast lane: documentation only; no behaviour, acceptance criteria, security controls, dependencies or source changes. Product specs need no change for this internal audit.
- Audit every file under `logs/` against the existing [log standard](../skills/log.md), including numbering, local references and narrative integrity. Historical omissions or unverifiable claims remain explicit limitations; do not invent telemetry, author approval or independent review.
- Builder owns this plan only at the first checkpoint. The coordinator owns log/reference corrections through the log skill because `logs/` is outside builder scope. Preserve unrelated files and edits.
- Author approval and Fast lane human diff review remain pending until actually supplied. Merge and release remain human decisions.

## Commit checkpoints and checks

1. **Plan:** builder writes this plan before audit implementation; coordinator checks scope and commits the plan. Focused checks: read back the plan, inspect its diff and run the before/after builder scope check.
2. **Audit and mechanical corrections:** after a fresh coordinator snapshot, builder reads every saved log and records concrete findings here; coordinator applies evidenced log numbering/reference repairs. Check all logs with `workflow/scripts/check_logs.py`, validate affected local references, inspect diff integrity and compare exact historical payloads for renamed files. Record check commands/results and unresolved evidence limits. Keep independently reviewable repairs coherent; do not imply retrospective commit splitting was incremental work.
3. **Current session and delivery:** coordinator records this session using the log skill, preserving observed model/run metadata and available usage; reruns affected targeted checks on the final candidate, freezes it for human diff review, and delivers the authorized branch/draft PR with configured CI results. Human review remains pending if not received.

## Starting evidence and next step

- Coordinator supplied starting HEAD `ea02420df1b651f76c9abb546961989640a5d7a1`, branch `docs/36-check-session-logs` and a private before-run scope snapshot. Coordinator owns usage measurement and final reporting, including this builder run (configured `gpt-6.1-sol`, medium effort).
- Coordinator's pre-audit checker result is supplied evidence, not a builder rerun: 57 Whimsyturtle logs and 28 zheng-jj logs; duplicate Whimsyturtle numbers 039, 040, 041, 042, 044 and 046, with missing 043. Confirm these findings during the audit before selecting repairs.
- The required prohibited-edit assessment refuses an `AGENTS.md` mutation because it is outside builder writes. No mutation is attempted; this does not prove native hook enforcement.
- Next: yield this plan for the coordinator's checkpoint and fresh snapshot before reading/auditing the log corpus. No audit repairs have been made and no historical claims have been verified at this checkpoint.
