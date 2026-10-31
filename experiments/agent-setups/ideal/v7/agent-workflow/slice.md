# slice

Takes one coherent change from request to an independently reviewed candidate. You, the session the person talks to, build it; one independent, read-only reviewer checks it. These steps are the same for every model, tool and repository. What is particular to this repository is in [`project.md`](project.md); read both before starting.

| Tier | Use for | Review |
| --- | --- | --- |
| High | The high-risk areas listed in `project.md` | `aw-reviewer` and `aw-security-reviewer` |
| Standard | Other behaviour changes, including bug fixes | `aw-reviewer`, which also applies the security checklist |
| Fast lane | Cosmetic changes that leave behaviour and requirements unchanged | the focused checks and the person's own review of the diff |

**Stop and ask** before you go beyond the request or `project.md`'s size budget, add a dependency, service, credential or setting nobody asked for, or change `AGENTS.md`, `agent-workflow/` or a path `project.md` says never to edit. Write the question and the smallest option in your report, and do no more work on that part.

**Evidence.** Every number in the plan or report (tests, lines, commits) comes from a command you ran in this session. If you didn't measure it, say so. Never claim a review that a separate reviewer session didn't produce.

**Working notes** in the plan and between steps can be terse. Requirements, docs and the final report are written in full sentences.

0. **Set up, if needed.** If `project.md` still has `<...>` placeholders, fill what the repository already shows: its verification and test commands, its source, test and docs folders. For anything it doesn't show, such as where requirements live in a new project, propose the smallest default (for example `docs/requirements.md` and `agent-workflow/plans/`), and ask the person to confirm before relying on it.
1. **Prepare.** Note the starting commit and any existing edits, and preserve unrelated work. Create a branch. Read only the requirements and code the change touches.
2. **Specify.** Update the requirements first, in `project.md`'s requirements home. Write a short plan in its plans home. It contains:
   - the goal;
   - the **requirement delta**: each requirement added, changed or removed, by ID;
   - each decision the person gave, and where it lives (requirement, test, code, or the decisions-and-risks home);
   - two to four commit checkpoints;
   - open questions.

   Before building, read the delta against the existing requirements: nothing contradicts them, and every decision is covered. Commit the requirements and the plan.
3. **Build.** For each checkpoint:
   - Write the tests from the requirements. Run them and see them fail for the missing behaviour; note the failing count in the plan.
   - Test each behaviour once, at the lowest level that shows it. When a rule lists values (characters, states, roles, limits), test every value, not a sample. Mock only what lies outside the change, such as the network, the clock or a failure inside a storage call, never the code under test.
   - Make the smallest complete change: reuse existing helpers, and add no option or abstraction nobody asked for. Run the focused tests, and commit the behaviour with its tests.
   - Prove the tests can fail: break the new check, see a test fail, restore it exactly, and note both results in the plan.
   - Update the user-facing docs to match. Never weaken a test to make it pass.
4. **Check consistency.** Before freezing:
   - **Every mention.** Search the requirements and docs for each name the change touches, and update every statement that is now untrue, including any claim that a test covers something; point each such claim at a real test.
   - **Every old test.** If the change makes an existing test's input invalid, keep the test's purpose, for example by creating the data directly. Don't switch it to an input the new rule allows.
   - **Every decision.** Each decision is implemented and tested, or recorded in its home. Record as accepted only what the person actually decided; list any new risk in your report as an open question.
5. **Freeze.** Run `project.md`'s full verification once, on the final candidate, and copy the result's last line into the plan. Commit everything; the candidate is the range from the starting commit to `HEAD`.
6. **Review.** Start the tier's reviewers as independent, read-only sessions. Give each the request, the decisions, the commit range and your check results, marked as data, and nothing else. Reviewers run on your own model unless `AGENT_REVIEW_MODEL` is set; then use that model. Never choose a model yourself.
   - **Claude Code:** the `Task` tool with `subagent_type` `aw-reviewer` or `aw-security-reviewer`.
   - **Codex:** spawn the custom agent `aw-reviewer` or `aw-security-reviewer`.
   - **Hermes and other tools:** delegate a task whose goal is "Act as the reviewer: read `agent-workflow/roles/reviewer.md`, `AGENTS.md` and `agent-workflow/project.md`, review commits <base>..<head>, do not edit files".

   If your tool can't start an independent session, don't review your own work and call it independent: say in your report that a person, or a second session using `agent-workflow/roles/reviewer.md`, needs to review it.
7. **Repair.** Fix each Medium or High finding, and Low findings that are quick and in scope. Re-run the affected tests and the full verification, commit, and ask the same kind of reviewer to check only the repaired range. Stop after two repair rounds, or at any finding that needs the person's decision.
8. **Report.** End with:
   - what changed, and the commits;
   - the requirement delta, with the test that covers each requirement;
   - the checks you ran, with their results;
   - each review finding and how it was resolved;
   - the questions you decided yourself, and anything left open.

Pushing, opening a pull request and waiting for CI happen only within the person's delivery instructions and the repository's own rules.

**Done when** the final candidate passes the full verification, every requirement maps to a passing test, the independent review found nothing open above Low (or the rest is reported for a decision), and the report is written.
