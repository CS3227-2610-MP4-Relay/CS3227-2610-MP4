# Make criterion count a slice guideline

Goal: keep slices reviewable without encouraging unrelated acceptance obligations to share an ID merely to fit a count.

Tier: Standard, because this changes workflow behaviour but not development security controls. Base: `ea1c7da1ebe48482b66c600782f0aee6189d8a8c`. The human authorized the guideline change, feature branch, commits, pushes and draft PR on 2026-10-26.

Why: the [investigation](../../logs/Whimsyturtle/007-investigate-the-eight-criterion-slice-budget.md) found mixed obligations and count-preserving expansion, without establishing that the cap caused defects or that eight is an empirically validated threshold.

Scope and decisions:

- Make eight added or changed criteria a guideline for a slice, not a hard cap or a requirement's lifetime limit.
- Keep coherent input and boundary variants together; give independently changeable behaviours distinct IDs, without combining obligations just to fit the count.
- Above eight, assess scope and implementation/verification burden and record why the slice remains reviewable or split it. Criterion count alone does not require a budget exception.
- Preserve the one-requirement and 400 changed non-test/migration source-line budgets, human confirmation of scope expansion and remaining budget exceptions, and existing review/delivery controls.
- Keep the rule in `workflow/skills/slice.md`. Do not renumber existing criteria, revise frozen plans, add tests that merely repeat prose, or add dependencies/services.

Estimated change: under 20 changed skill lines plus this compact plan and the existing session log. No application changes. The coordinator owns workflow maintenance because `workflow/skills/` is outside the builder's write scope; an independent verifier reviews the fixed candidate.

Commit checkpoints:

1. `plan:` record the confirmed scope and checks in this file; inspect the staged diff.
2. `chore:` revise the size paragraph and criterion-grouping guidance in `workflow/skills/slice.md`; read it back, run workflow unittests and full verification, then commit the coherent rule change.
3. `log:` record final review/check evidence here and in the session log; push and verify configured CI on the latest draft-PR head.

Verification:

- Manual scenarios: nine clear criteria can remain one reviewable slice; eight compound IDs do not establish manageable scope; variants of one behaviour can share an ID; two requirements or over 400 source lines still need the existing budget exception; unconfirmed scope expansion still stops.
- Run `python -m unittest discover -s workflow/scripts`, the Standard-tier `ruff check . && ruff format --check . && pytest`, the saved-log checker and whitespace checks. Use the existing fixed test environment and installed PostgreSQL with an isolated temporary cluster if needed.
- Freeze the candidate and obtain an independent verifier report; check its read-only scope and candidate immutability. No security specialist is triggered unless review identifies a development-security-control effect.
- Use the repository PR template, leave human review boxes unticked, and wait for configured CI at the final head. Merge and release remain human decisions.

Outcome: the skill change is committed as `1af26b3`, after plan checkpoint `9e93c2e`. Manual inspection passed all five scenarios above. Django system checks, Ruff lint and formatting passed; pytest reported 96 passed and one Windows symlink-privilege skip. Workflow unittest discovery ran 70 tests with the same skip, and the saved-log checker reported zero findings. The installed PostgreSQL 17 test cluster was isolated, then stopped and removed.

The independent verifier reviewed `ea1c7da..1af26b3` with no findings, confirmed Standard tier and found no security-specialist trigger. Scope and candidate-immutability checks passed; the [session log](../../logs/Whimsyturtle/007-investigate-the-eight-criterion-slice-budget.md) holds the exact manifest and role metadata. Only summary updates follow that review.

[Draft PR #47](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/47) is open. Its required `verify` check passed on `1af26b3`; delivery must also confirm it on the final summary commit. The PR records that final-head result. Human log review and merge decisions remain pending.
