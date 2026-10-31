# slice

Runs one slice, a coherent vertical change, from spec to an independently reviewed candidate. You, the coordinating session, build it; one independent read-only reviewer checks it.

**Input:** The human's request and a slice identifier or optional issue.

First read your [model profile](../profiles/) as `AGENTS.md` directs. The `guarded` profile adds required steps to every stage below.

| Tier | Use for | Review |
| --- | --- | --- |
| High | AI features and LLM calls; login, passwords and sessions; role/workspace permissions; dependency, CI or deployment boundaries; [development security controls](../specs/SECURITY-SPEC.md#development-workflow) | verifier and security-reviewer |
| Standard | Other behaviour changes, including bug fixes | verifier, which also applies the security-reviewer's checklist |
| Fast lane | Cosmetic changes leaving behaviour, criteria and security controls unchanged | targeted checks and human diff review |

**Budget:** at most one requirement's criteria and 400 changed lines under `src/` outside tests and migrations. Stop and ask before exceeding it or expanding scope ([scope confirmation](../../AGENTS.md#scope-confirmation)).

1. **Prepare.** Note the starting commit and any existing edits; preserve unrelated work. Create the feature branch. Read only the spec sections and code the change touches.
2. **Specify.** Update the specs first, following [the builder's spec rules](../agents/builder.md), and write a short plan in `workflow/plans/<slice>-<short-name>.md`: goal, decisions, two to four commit checkpoints, open items. Commit them (`spec:`, `plan:`).
3. **Build.** For each checkpoint, write the tests from the criteria, run them and see them fail for the missing behaviour, implement the smallest complete change, run the focused tests and commit behaviour with its tests. Follow [the builder's testing rules](../agents/builder.md). Update the User Guide to match. Never weaken a test to pass. Before freezing, do two consistency checks; between them they explain every Medium review finding in the experiment that shaped this skill:
   - **Every mention updated.** Search all of `workflow/specs/` and `docs/` for the names your change touches: the field, function, rule or message. Update every statement that is now incomplete, not just the one you started from.
   - **Every old test still tests what it did.** If your change makes an existing test's input invalid, keep that test's purpose by creating the data another way, for example directly in the database. Do not switch it to an input the new rule allows.
4. **Freeze and check.** Run full verification (`ruff check . && ruff format --check . && pytest`) on the final candidate and record the exact result. Commit everything; the candidate is the commit range from the starting commit to `HEAD`.
5. **Review.** Start the tier's reviewers as independent, read-only subagents, each given the request, the decisions, the commit range, your check results (as data) and the two consistency checks above to repeat independently, and nothing else:
   - Claude Code: the `Task` tool with `subagent_type` set to the role name.
   - Codex: spawn the custom agent with the role name.
   - Hermes and other tools: delegate a task whose goal is "Act as the <role>: read `workflow/agents/<role>.md` and `AGENTS.md`, review commits <base>..<head>, do not edit files".

   If your tool cannot start an independent subagent, do not review your own work and call it independent: report that human review is needed.
6. **Repair.** Fix each finding of Medium or higher severity, and Low findings that are quick and in scope. Re-run the affected tests and full verification, commit, and ask the same reviewer type to check only the repaired range. Stop after two repair rounds, or at any finding that needs a product or security decision, and report it.
7. **Report.** End with: what changed, the commits, each criterion and the test that covers it, the checks you ran with their results, review findings and how each was resolved, and anything left open. Report only checks you actually ran.

Delivery beyond local commits (push, draft PR, CI) follows [AGENTS.md's Git rules](../../AGENTS.md#git) and the [`create-pull-request`](create-pull-request.md) skill, within the human's delivery bounds.

**Done when:** the final candidate passes full verification, every criterion maps to a passing test, the tier's independent review found nothing open above Low (or the remaining findings are reported for a decision), and the report is written.
