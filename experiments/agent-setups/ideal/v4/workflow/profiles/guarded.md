# guarded profile

For smaller or cheaper models, such as Claude Haiku or DeepSeek Flash, and the default whenever `RELAY_PROFILE` is not set to `strong`. It keeps the [slice skill](../skills/slice.md) and adds fixed steps, hard stops and evidence rules. Earlier runs with a smaller model broke scope, rewrote the rules after the fact, wrote tests that could not fail and misreported numbers; each rule below prevents one of those.

## Hard stops

Stop, write the question and the smallest option in your report, and do no more work on that part if the change would:
- touch a requirement, file area or issue not named in the request;
- add a setting, dependency, service, credential, endpoint or file format nobody specified;
- change `AGENTS.md`, `workflow/skills/`, `workflow/agents/`, `workflow/profiles/` or any adapter;
- exceed the slice budget.

## Steps

Copy this checklist into your plan file and tick each item as you finish it. Do the steps in order.

1. [ ] `git status` is clean or its edits are recorded; feature branch created.
2. [ ] Specs changed for the request only; plan written; committed as `spec:` then `plan:`. The plan lists each decision the human gave and where it lives: the spec section, residual, test or code that carries it.
3. [ ] New tests written; the focused test command run **before** the implementation, and its failing count copied into the plan.
4. [ ] Implementation written; the same focused command passes; committed as `feat:` or `fix:` with its tests. Where the rule lists values (characters, states, roles), every value has its own test case.
5. [ ] Self-check that the tests can fail: comment out or bypass the new check, run the focused tests, confirm at least one fails, restore the code exactly and re-run them green. Record both results in the plan.
6. [ ] User Guide updated to match the behaviour; committed as `docs:`.
7. [ ] Searched `workflow/specs/` and `docs/` for each name the change touches (`grep -rn "<name>" workflow/specs docs`); every hit listed in the plan as "updated" or "still true".
8. [ ] Read `git diff <start>..HEAD -- '*/tests/*'` line by line: no existing test had its input switched to something the new rule allows. Where an old input is now refused at the form, the test creates the data directly instead.
9. [ ] Full verification run: `ruff check . && ruff format --check . && pytest`. Its last line copied into the plan.
10. [ ] Independent reviewer started as the skill says; findings recorded; repairs made and re-reviewed (at most two rounds).
11. [ ] Report written.

## Evidence rules

- Every number in the plan or report (tests, lines changed, commits, models) comes from a command you ran in this session; copy the command with it. If you did not measure something, write "not measured".
- Size: `git diff --shortstat <start>..HEAD -- src ':(exclude)*/tests/*'`.
- One commit per finished step. Never rewrite, squash or reorder commits.
- If the same check fails three times in a row, stop and report the failure instead of changing tests or rules to make it pass.
- Do not claim a review happened unless a separate reviewer session produced it. Run reviewers on the model the slice skill says (`RELAY_REVIEW_MODEL`, or your own); do not choose one yourself.
