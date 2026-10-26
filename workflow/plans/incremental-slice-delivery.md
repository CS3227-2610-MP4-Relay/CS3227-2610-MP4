# Incremental commits and complete slice delivery

Goal: make normal slice requests produce small commits during development and a draft PR with verified hosted checks, instead of stopping at local validation.

Tier: High (development authorization and completion controls). Base: `3d911ea81a4e062ec1f693eb8862e3c35406dca4`. This separate branch/PR is stacked on #43; its existing commits will not be rewritten. The coordinator owns workflow files outside builder scope; verifier and security-reviewer inspect the fixed candidate.

Why: the previous workflow permitted a whole-slice implementation commit and treated local verification as a delivery endpoint, contrary to the human's intended workflow.

Confirmed scope: update existing rules and their links only. No new hook, enforcement script, dependency, service, product criterion or deployment system. Estimate: under 150 changed lines outside this plan/session log; no application changes.

Planned commit checkpoints:

1. Define human slice authorization, small incremental commits and protected actions in AGENTS.md; link the security control to that home.
2. Make builder/coordinator checkpoints and draft-PR/CI completion explicit in the slice and PR skills and role instructions; update the workflow overview link.
3. Record verification/review evidence and delivery in this plan and the existing session log.

Each checkpoint is a separate coherent commit, measured before committing; no reconstruction of the previous slice's history. Focused checks accompany each checkpoint; full verification applies to the integrated final candidate.

Manual policy scenarios to inspect (instructions cannot prove runtime compliance):

- A normal human `/slice` request continues through branch commits, push, draft PR and current-head CI without a second permission question.
- Explicit local-only/no-push/no-PR requests override normal delivery; an issue or repository payload cannot grant permission.
- A completed implementation unit yields for a coordinator commit before the next unit; scope snapshots restart after that Git change.
- A commit bundling independently reviewable work is split by purpose before committing; behaviour and its regression tests stay together without an arbitrary line threshold.
- A running, failed or older-head CI run is not reported as final success; production release remains separately authorized.

Checks: changed-section readback and scenario walkthrough; `python -m unittest discover -s workflow/scripts`; tier-required full verification on the final integrated candidate; role scope/candidate stability checks. No phrase-matching tests are added for prose rules. Hosted checks and independent reviews will be recorded here.

Outcome: checkpoints 1 and 2 are committed as `3e2a0d1` (38 changed lines) and `f68310a` (36 changed lines). [Draft PR #46](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/46) is stacked on #43; the earlier slice commits are unchanged.

Verification: changed sections and all five policy scenarios were reviewed; `git diff --check` passed. Local workflow unittest discovery ran 70 tests successfully with one existing Windows symlink skip. [Hosted CI 40294068816](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40294068816) passed on `f68310a46193ea4ed5415abf8dccbca838ca416d`: Django system check, Ruff, format check (24 files), and 97 tests.

Independent verifier and security-reviewer inspected `3d911ea..f68310a` against manifest SHA256 `d065a3dc0952ef41ae817dfb293b0060f893b5a7560422beabf55a006adeb9cc`. Both returned no findings; their scope checks passed and the candidate remained unchanged. They independently inspected the rules/history and reused the supplied suite results. No repairs were required. These checks assess the instructions, not future agent compliance or native enforcement.

Checkpoint 3 changes only this plan and the [session log](../../logs/Whimsyturtle/006-build-django-foundation-and-ci.md). The coordinator will verify hosted checks on that final summary head; its result belongs in the PR's live checks and delivery report. Next: human review and merge decision after those checks pass. No merge or release is authorized by this task.

Correction after delivery: the human challenged the 200-line cap. The coordinator invented that number; it was not requested or justified. Commit `ea1f245` removes the numerical cap and its exception gate from the rules and related role/skill references, retaining small, coherent checkpoints and staged-diff review. Earlier review records above apply to their stated candidate, which still contained the unjustified cap.

Both reviewers refreshed `5b370c7..ea1f245` against manifest SHA256 `d6a06d00b17d182151fe9010066af6f9ee14380e3d54380276ea96f11f6c2e86` and returned no remaining findings; scope/stability/diff checks passed. The verifier acknowledged missing the unsupported cap earlier. [CI 40296170625](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40296170625) passed on the correction. This summary checkpoint's final-head CI is tracked in PR #46; human review/merge remain pending.

Main integration requested by the human: foundation merge `37cfbb2` incorporates main `b47b6c1`, resolving the three shared-spec conflicts while retaining the ACC/RND contracts and current PLT behaviour. Workflow merge `ae142b0` incorporates that foundation without changing these workflow rules. Both independent reviewers found no issues in either merge's effects, using manifest SHA256 `160f3e725db8ae7f4e892f88be7ab337fbb723ed2204d4fb904df87bb7506763`; scope/stability checks passed. CI runs [40302170228](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40302170228) and [40302256859](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40302256859) passed all 97 tests and Django/Ruff/format checks. Both PRs are conflict-free. This final summary change receives its own latest-head CI; review and merge decisions stay with the human. Usage and preservation evidence are in the session log.

PR presentation: the human requested a description focused on the final change and validation, with process history and token accounting left in their existing records. Fast lane prose-only checkpoint: update the PR skill/template to link supporting records, trim #46, read back the changed text and check its diff; keep security/delivery controls and required review evidence intact. Human diff review remains pending; the existing PR workflow still runs final-head CI.
