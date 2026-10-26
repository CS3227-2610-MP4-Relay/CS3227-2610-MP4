# Apply targeted workflow improvements

Goal: close the five reported gaps while keeping MP4's combined builder and focused review workflow.

Tier: High, because the specialist-review trigger changes a development security control. Base: `95f22ab6dd59c62e5037f4e7f8caf6fe80e57fde`. The coordinator owns workflow maintenance, including scripts outside the builder's write scope; one GPT-6.1 Sol verifier and one security-reviewer inspect the fixed candidate without conversation forks.

Why: prevent incomplete usage from looking like a zero delta, make development security review explicit, retain the storage-capacity design question, enforce the existing log format and credit reused MP3 material.

Decisions before implementation:

- Treat usage-bearing Codex token events with missing or unusable cumulative counters as incomplete; warn and keep affected measurements unavailable through task reports. Rate-limit-only notifications do not imply token usage. Do not reconstruct totals from a last-event count or claim a historical undercount.
- Require High-tier specialist review when changes affect development security controls (agent permissions, scope enforcement and hooks). Ordinary workflow prose or formatting does not trigger this by filename alone.
- Before persistence, decide accumulated-record retention, workspace lifetime, expired-session handling and exhausted-capacity behaviour without silently losing required history. Preserve the question only; no cleanup subsystem or fixed policy now.
- Validate the existing orchestrator-model field and immediate token table's columns, separator and nonempty rows using the current checker. Accept explicitly unavailable measurements; structural validation cannot establish telemetry truth or discover omitted agents.
- Acknowledge MP3's workflow/tooling baseline in the Developer Guide using the local source repository's identity.

Budget: estimated under 350 changed lines in implementation, tests and documentation, excluding this plan/log; no `src/` changes, product criteria, dependencies, services or new recurring agent roles. Two focused regression runs before repairs, then one integrated verification and the existing workflow unittest command. Security-control changes incur specialist review; unrelated slices keep their existing tiers.

- [x] Record focused regression failures, implement and rerun affected tests.
- [x] Read changed documentation back and run full verification, workflow unittests and saved-log validation.
- [x] Freeze candidate, obtain independent and security reviews, check scopes/immutability and report resources.

Evidence: before implementation, the cumulative-usage regression command failed in 11 subcases (missing measurements/warnings), and log-checker tests failed in 10 subcases (missing model/table structure accepted). Afterwards, all 33 collector tests and six log-checker tests passed. Full verification passed in MP4's existing Python 3.14.2 environment: Ruff 0.17.0 lint/format, pytest (68 passed, one Windows symlink privilege skip), workflow unittest discovery (69 run, same skip), saved-log validation (zero findings) and `git diff --check`. An initial lint attempt caught three overlong fixture lines; splitting literals fixed them without changing fixture content. Documentation was read back for lost rules, duplicate headings and unsupported implementation claims.

Mapping: telemetry tests cover unusable/missing cumulative counters, later valid events, partial measurable fields and rate-limit-only notifications; log tests cover absent/empty model metadata, absent/misplaced/malformed tables and explicit unavailable values. Manual diff inspection checks the specialist trigger's scope, the open persistence decisions and MP3 acknowledgement; no new product criteria are introduced.

Review repair round 1: the verifier found that a first partial cumulative event could replace unknown counters with last-event values through the inherited-history fallback. A new focused test failed with `10 is not None`; preserving missing fields in that fallback made it pass. Full verification then passed again (69 pytest passes, one unchanged skip; 70 unittests, same skip; Ruff lint/format and log checker clean). The first fixed candidate had no security findings; both reviewers' scope and immutability checks passed before repair.

Outcome: both reviewers inspected the repaired candidate and reported no remaining findings; their scope and candidate-immutability checks passed. The [session log](../../logs/Whimsyturtle/004-apply-targeted-workflow-improvements.md) records candidate hashes, review limits and measured usage. This delivery annotation and that log were added after review; implementation, specs and guides remain the reviewed versions. Next: human diff/log review; merge/release decisions remain human-owned. No commits or remote writes requested.
