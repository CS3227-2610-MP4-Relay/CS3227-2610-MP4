# Fix Codex token accounting (#83)

Goal: repair fork overlap, continuation baselines, bounded source discovery and unavailable-source reporting in the existing usage collector.

Tier: High, because accounting evidence affects development controls. Original base: `471a4f77c28d255574efbd2be0928d271fd111dc`; repair checkpoint base: `f5050f23b978a8381c35d3c4d2d562af39b753be`; branch: `chore/83-token-accounting-investigation`. Continue [draft PR #90](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/90). The human's `/slice 83` request authorizes normal slice delivery; merge and release remain human decisions.

Why: the human clarified that this work must fix the collector and must not be housed as an experiment. Replace the initial study artifacts with ordinary regression tests and collector repairs; retain prior observations only as historical context in the session log.

## Scope and decisions

- Authoritative accounting/privacy policy is in [Development workflow](../specs/SECURITY-SPEC.md#development-workflow). Operational usage belongs in [Token reporting](../README.md#token-reporting). No product requirement or application behavior changes, so no product criterion IDs are added.
- Repair `workflow/scripts/resource_usage.py` and its tests using the confirmed hashed turn/range provenance, conservative baseline continuity, bounded discovery and field-specific subtotal design. Keep backward compatibility for existing snapshots through optional fields and conservative legacy handling.
- Builder owns this plan and the concise telemetry policy in `workflow/specs/SECURITY-SPEC.md` only. Coordinator owns scripts/tests, workflow README, artifact cleanup and session log. Only the coordinator changes Git/GitHub state; preserve other edits.
- Remove `workflow/scripts/investigate_codex_usage.py` and `experiments/83-codex-token-accounting.md`, restoring the experiment index. Do not replace them with another report-only artifact. Convert useful reproductions into ordinary tests that assert correct or explicitly unavailable accounting.
- Budget: zero changed product requirements and zero changed `src/` lines. Revised overall estimate: roughly 1,000–1,500 changed lines, including deletion of the 287-line helper and 78-line report, repair implementation, tests, policy, plan and log. No service, dependency, credential, persistent telemetry store, billing reconciliation, raw transcript export or historical-total recalculation. Stop affected work for a specific decision if this scope or estimate is exceeded.
- Provenance establishes supported selected-source accounting, not undocumented client guarantees. Equal numeric counters, rewritten timestamps and related source metadata alone cannot prove shared work. Discovery metadata identifies candidates, not interchangeable usage identities.

## Commit checkpoints

1. `spec: Define conservative Codex accounting repairs (#83)` — this plan and telemetry policy only. Read changed sections back, run `git diff --check` and builder scope validation, then coordinator commits before implementation.
2. `fix: Account for shared Codex usage across continuations (#83)` — collector and focused regression tests together; remove the study helper/report and restore experiment index. Capture genuine focused failures before implementation, then passing fork/continuation and malformed-provenance tests. Preserve previously valid independent-counter and legacy-snapshot behavior.
3. `fix: Complete bounded usage discovery and partial reporting (#83)` — collector and focused tests together for repeated roots, nested directories, linked roots/guardians/descendants, bounded selection and per-field coverage/subtotals. Capture red then green evidence. Coordinator may perform this independent unit before checkpoint 2 if that simplifies implementation; commit each completed unit before starting the next.
4. `docs: Explain repaired usage reporting and its limits (#83)` — workflow README and repair log, with plan closeout by builder after a fresh commit/scope snapshot. Link policy rather than duplicating it. Record actual compatibility behavior, selection commands and output interpretation; remove stale experiment/fix-deferred language.
5. Run full verification, freeze the integrated candidate and obtain fresh independent verifier and security-reviewer reports. Repair only in-scope defects, with at most two review repair rounds; invalidate affected prior evidence. Coordinator completes summary log, pushes checkpoints, updates the draft PR and follows configured CI on the latest head. Human merge review remains pending until actually given.

## Verification partitions

These are regression partitions for the policy above, not new product criteria:

- Shared native turns/ranges across parent and fork: preserved and rewritten timestamps, repeated/copied events, partial overlap and baseline subtraction; independent turns with equal counters must remain distinct. Related streams lacking sufficient provenance must expose ambiguity instead of inflated totals.
- Continuations: unchanged identity, proven changed-identity replacement, baseline retained alongside replacement, genuinely omitted baseline, insufficient shared coverage and truncation. Include existing snapshots without new fields and malformed optional hashes/ranges with fixed errors that disclose no fixture payload.
- Discovery: one and repeated roots, nested date directories, parent and nested thread-spawn links, shared session-tree root/guardian/descendants, unrelated sources, project mismatch and explicit outside source selection. Test just below, at and above the combined 1,000-file boundary; no silent overflow or implicit wider search.
- Partial reporting: all measured, all unknown, metadata-only initialized and unsupported-usage activity, independently missing fields and ambiguous provenance. Check strict unknown aggregates alongside available per-field subtotals and counts; unknowns never become zero and warnings remain explicit. Counter subsets remain subsets rather than additions to totals.
- Use only synthetic fixture content and numeric/hash output checks. Existing privacy/error tests remain authoritative; no real transcript replay or message export is needed.

## Evidence and handoff

- Prior plan `b0c3a8467468ef6e4d8faf96198d6ac36f9ace06` and study `2cf99cb` characterized behavior, not a completed fix. Previous checks/reviews apply only to that earlier candidate. Historical observations and the human correction belong in `logs/Whimsyturtle/017-investigate-codex-token-accounting-gaps.md`; do not carry them forward as repair success evidence.
- Current assignment: spec/plan-only checkpoint against `f5050f2`, pre-run manifest `relay-83-fix-builder-plan.json` outside the repository. Builder adapter requests `gpt-6.1-sol`/medium; coordinator previously confirmed those settings from selective metadata. Coordinator owns baseline/final usage collection, cutoff and selected-source coverage; missing measurements remain unavailable.
- Focused command with `.venv` active: `python -m unittest discover -s workflow/scripts -p test_resource_usage.py`. Run focused Ruff lint/format and whitespace checks for each implementation unit; report actual red and green results.
- Required integrated command in activated Git Bash: `ruff check . && ruff format --check . && pytest`; an explicit temporary pytest base directory may be supplied. Record exact failures and skips. Prior local Windows failures or hosted passes do not establish the repaired candidate's result.
- Fixed-candidate review must inspect actual code/tests, compatibility and privacy boundaries, scope and diff. Capture a fresh candidate manifest; verify reviewer read-only scopes and unchanged candidate before delivery. No repair implementation, focused red/green, full verification or independent review of the repaired candidate has occurred at this spec checkpoint.

## Next step

Coordinator checks this builder checkpoint's scope, inspects and commits the spec/plan, then assigns the next implementation unit. Builder waits for a fresh commit/scope snapshot before further edits. Complete the repair in the existing PR; no report-only completion claim.
