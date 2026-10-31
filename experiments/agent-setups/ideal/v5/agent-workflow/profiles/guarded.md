# guarded profile

For smaller or cheaper models, such as Claude Haiku or DeepSeek Flash. It is also the default whenever `AGENT_PROFILE` is not set to `strong`. It keeps the [slice](../slice.md) and adds fixed steps, hard stops and evidence rules.

Smaller models, run without these rules, did the following, and each rule below prevents one of them:
- broke scope;
- rewrote the rules after the fact;
- wrote tests that could not fail;
- misreported numbers;
- chose their own reviewer model;
- left accepted risks out of their home.

## Hard stops

Stop if the change would do any of the following. Write the question and the smallest option in your report, and do no more work on that part.
- Touch a requirement, file area or issue not named in the request.
- Add a setting, dependency, service, credential, endpoint or file format nobody specified.
- Change `AGENTS.md`, anything in `agent-workflow/`, any agent or skill adapter, or a path `project.md` says never to edit.
- Exceed the size budget.

## Steps

Copy this checklist into your plan and tick each item as you finish it. Do the steps in order.

1. [ ] The working tree is clean or its edits are recorded, and a branch is created.
2. [ ] Requirements are changed for the request only, the plan is written, and both are committed.
   - The plan lists each decision the human gave and where it lives: the requirement, test, code, or the decisions-and-risks home in `project.md`.
3. [ ] New tests are written, and the focused test command is run **before** the implementation. Its failing count is copied into the plan.
4. [ ] The implementation is written, the same focused command passes, and it is committed with its tests.
   - Where a rule lists values (characters, states, roles, limits), every value has its own test case.
5. [ ] Self-check that the tests can fail:
   - comment out or bypass the new check, run the focused tests, and confirm at least one fails;
   - restore the code exactly and re-run them green;
   - record both results in the plan.
6. [ ] The user-facing docs are updated to match the behaviour, and committed.
7. [ ] The requirements and docs have been searched for each name the change touches, and every hit is listed in the plan as "updated" or "still true".
8. [ ] The test diff has been read line by line. No existing test had its input switched to one the new rule allows; where an old input is now refused, the test creates the data directly instead.
9. [ ] Every accepted risk or residual from the decisions is written in the decisions-and-risks home, not only in the plan.
10. [ ] The full verification command from `project.md` has been run, and its last line is copied into the plan.
11. [ ] An independent reviewer has been started as the slice says, its findings recorded, and the repairs made and re-reviewed, at most two rounds.
12. [ ] The report is written.

## Evidence rules

- Every number in the plan or report comes from a command you ran in this session, with the command copied beside it. That covers tests, lines changed, commits and models. If you did not measure something, write "not measured".
- One commit per finished step. Never rewrite, squash or reorder commits.
- If the same check fails three times in a row, stop and report the failure. Do not change tests or rules to make it pass.
- Do not claim a review happened unless a separate reviewer session produced it. Run reviewers on the model the slice says: `AGENT_REVIEW_MODEL`, or your own. Do not choose one yourself.
