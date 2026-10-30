# slice

Takes one coherent change from requirement to an independently reviewed candidate. You, the session the human talks to, build it; one independent, read-only reviewer checks it. This file is the same in every repository: this repository's commands, folders and homes are in [`project.md`](project.md). Read both before starting.

First read your [profile](profiles/), as `AGENTS.md` directs. The `guarded` profile adds required steps to every stage below.

| Tier | Use for | Review |
| --- | --- | --- |
| High | The high-risk areas listed in `project.md` | `aw-reviewer` and `aw-security-reviewer` |
| Standard | Other behaviour changes, including bug fixes | `aw-reviewer`, which also applies the security checklist |
| Fast lane | Cosmetic changes that leave behaviour and requirements unchanged | the focused checks and the human's own review of the diff |

**Budget:** stay within `project.md`'s size budget and the request. Stop and ask before exceeding either, or before adding a dependency, service, credential or setting nobody asked for.

1. **Prepare.** Note the starting commit and any existing edits, and preserve unrelated work. Create a branch. Read only the requirements and code the change touches.
2. **Specify.** Update the requirements first, in `project.md`'s requirements home. Write a short plan in its plans home: the goal, the decisions given, two to four commit checkpoints and open items. Commit them.
3. **Build.** For each checkpoint:
   - Write the tests from the requirements, run them and see them fail for the missing behaviour. Test the real code path: mock only what lies outside the change, such as the network, the clock or a failure inside a storage call, never the unit under test.
   - Make the smallest complete change, run the focused tests, and commit the behaviour with its tests.
   - When a rule lists values (characters, states, roles, limits), test each value on its own, not a sample.
   - Update the user-facing docs to match. Never weaken a test to make it pass.
4. **Check consistency.** Before freezing, check three things. Between them they explain every Medium or High review finding in the experiment that produced this workflow:
   - **Every mention updated.** Search the requirements and docs for every name the change touches (field, function, rule, message), and update each statement that is now incomplete. A statement that tests cover something must point to a test that does.
   - **Every old test still tests what it did.** If the change makes an existing test's input invalid, keep the test's purpose, for example by creating the data directly. Do not switch it to an input the new rule allows.
   - **Every decision has a home.** Each decision the human gave is either implemented, with a test, or recorded in its home. Accepted risks and residuals go in `project.md`'s decisions-and-risks home, not only in the plan. Record as accepted only what the human actually decided. A new risk you find is not accepted: list it in your report as an open question for the human.
5. **Freeze.** Run `project.md`'s full verification on the final candidate and record the exact result. Commit everything; the candidate is the range from the starting commit to `HEAD`.
6. **Review.** Start the tier's reviewers as independent, read-only subagents. Give each one the request, the decisions, the commit range and your check results, marked as data, and nothing else. Reviewers run on your own model unless `AGENT_REVIEW_MODEL` names another; then start them on that model. Never choose a model yourself, because that changes the cost without the human knowing.
   - **Claude Code:** the `Task` tool with `subagent_type` `aw-reviewer` or `aw-security-reviewer`.
   - **Codex:** spawn the custom agent `aw-reviewer` or `aw-security-reviewer`.
   - **Hermes and other tools:** delegate a task whose goal is "Act as the reviewer: read `agent-workflow/roles/reviewer.md`, `AGENTS.md` and `agent-workflow/project.md`, review commits <base>..<head>, do not edit files".

   If your tool cannot start an independent subagent, do not review your own work and call it independent. Report that human review is needed.
7. **Repair.** Fix each Medium or High finding, and Low findings that are quick and in scope. Re-run the affected tests and the full verification, commit, and ask the same reviewer type to check only the repaired range. Stop after two repair rounds, or at any finding that needs a human decision, and report it.
8. **Report.** End with:
   - your profile;
   - what changed, and the commits;
   - each requirement and the test that covers it;
   - the checks you ran, with their results;
   - each review finding and how it was resolved;
   - anything left open.

   Report only checks you actually ran.

Pushing, opening a pull request and waiting for CI happen only within the human's delivery instructions and the repository's own rules.

**Done when:**
- the final candidate passes the full verification;
- every requirement maps to a passing test;
- the independent review found nothing open above Low, or the remaining findings are reported for a decision;
- the report is written.
