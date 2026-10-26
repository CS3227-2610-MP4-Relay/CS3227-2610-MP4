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
- A 586-line implementation commit is split into coherent units before committing; a genuinely indivisible change needs a specific size exception.
- A running, failed or older-head CI run is not reported as final success; production release remains separately authorized.

Checks: changed-section readback and scenario walkthrough; `python -m unittest discover -s workflow/scripts`; tier-required full verification on the final integrated candidate; role scope/candidate stability checks. No phrase-matching tests are added for prose rules. Hosted checks and independent reviews will be recorded here.

Outcome: checkpoints 1 and 2 are committed as `3e2a0d1` (38 changed lines) and `f68310a` (36 changed lines). [Draft PR #46](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/46) is stacked on #43; the earlier slice commits are unchanged.

Verification: changed sections and all five policy scenarios were reviewed; `git diff --check` passed. Local workflow unittest discovery ran 70 tests successfully with one existing Windows symlink skip. [Hosted CI 40294068816](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40294068816) passed on `f68310a46193ea4ed5415abf8dccbca838ca416d`: Django system check, Ruff, format check (24 files), and 97 tests.

Independent verifier and security-reviewer inspected `3d911ea..f68310a` against manifest SHA256 `d065a3dc0952ef41ae817dfb293b0060f893b5a7560422beabf55a006adeb9cc`. Both returned no findings; their scope checks passed and the candidate remained unchanged. They independently inspected the rules/history and reused the supplied suite results. No repairs were required. These checks assess the instructions, not future agent compliance or native enforcement.

Checkpoint 3 changes only this plan and the [session log](../../logs/Whimsyturtle/006-build-django-foundation-and-ci.md). The coordinator will verify hosted checks on that final summary head; its result belongs in the PR's live checks and delivery report. Next: human review and merge decision after those checks pass. No merge or release is authorized by this task.
