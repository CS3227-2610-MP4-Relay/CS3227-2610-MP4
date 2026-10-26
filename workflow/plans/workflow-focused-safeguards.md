# Restore focused workflow safeguards

Goal: assess and apply the six requested safeguards without restoring MP3's separate spec/test/critic runs.

Tier: Standard workflow maintenance. Base: `f5b2383268e7ba4ccdabcd03206d4a3ea2e451f8`. The coordinator owns these workflow files, which are outside the builder's write scope; one read-only GPT-6.1 Sol verifier reviews the fixed candidate. No product criteria, authorization controls, dependencies or deployment changes.

Why: retain useful test/spec safeguards inside MP4's existing roles and prevent a subset counter decrease from inflating usage totals.

Decisions before implementation:

- Restore focused new-feature/regression failure evidence in the same builder run, with documented exceptions; no separate test writer or mandatory mutation suite.
- Prefer automated regression coverage, justify manual-only criteria and verify executed steps/results.
- Have the existing verifier challenge interpretations, cross-spec contradictions, missing cases and weakened security controls, limited to relevant specs.
- Restore below/at/above boundaries, isolated invalid inputs and pairwise coverage for interacting inputs; avoid redundant cases and exhaustive combinations.
- Record removed IDs in a `Retired:` line in their original spec file; no placeholder registers when no IDs have been retired.
- Preserve monotonic primary usage counters when only a subset falls; make the affected subset unavailable. Recognize a reset only when all primary counters are available and non-increasing, with at least one decrease. Mixed or incomplete primary-reset evidence makes session counters unavailable. Retain warnings and propagate unavailability into task reports.

Budget: focused role/skill wording, collector/tests and reporting documentation only; no `src/` changes or added requirements. Expected implementation and test diff below 200 lines, excluding this plan and the session log. No extra recurring agent runs or full-suite runs before implementation.

- [x] Update builder/verifier rules and the slice completion reference.
- [x] Demonstrate focused collector regressions before the fix, then repair and rerun them.
- [x] Run full verification and workflow unittests on the integrated candidate.
- [x] Freeze candidate, obtain independent verification, check scope/immutability and record usage.

Evidence: `python -m unittest discover -s workflow/scripts -p test_resource_usage.py -k decrease` failed in all seven subcases before the fix (including `275 != 165`), then passed both parameterized tests. `ruff check .`, `ruff format --check .`, `pytest` (63 passed, 1 skipped) and workflow unittest discovery (64 run, 1 skipped) passed in MP4's existing `.venv` with Python 3.14.2. The existing Windows symlink privilege skip remains. The original coherent-reset regression also passes.

Outcome: the independent GPT-6.1 Sol verifier found no defects in the fixed candidate; scope and immutability checks passed. Existing untracked reference documents and audit log were preserved during implementation. The human subsequently requested a local commit with the renamed [session log](../../logs/Whimsyturtle/003-restore-focused-workflow-safeguards.md), which records review and measurement evidence. Human diff/log review remains pending; no remote writes were requested.
