# Development workflow experiments

This folder holds zheng-jj's development-workflow comparisons (#31). The planned comparison of the MP3-style and consolidated workflows is described in the [experiments README](../README.md#planned-comparisons) and has not been run. This page records a related run: the same consolidated workflow driven by a weaker model.

## Run 1: the consolidated workflow with a weaker model

**Question.** How well does the consolidated builder/verifier/security-reviewer workflow hold up when every role is played by a weaker, cheaper model? Specifically: do its rules and checks still produce mergeable, honest work, and which controls fail first?

**Status.** One observational run. The tasks were real backlog items chosen in the session, not replays of a fixed task, so the comparison with the Opus-run slices is indicative only (see [Limitations](#limitations)).

### Setup

| Item | Weaker-model run | Reference runs |
| --- | --- | --- |
| Model, every role | DeepSeek v4.1 Flash (`~deepseek/deepseek-flash-latest` via OpenRouter), effort high, observed in each session's metadata | `claude-opus-5-5`: orchestrator effort unavailable, builder medium, reviewers high (requested) |
| Harness | Codex CLI 0.164.0 and 0.165.0, using the repository's `.codex` adapters | Claude Code, using the repository's `.claude` adapters |
| Role models | The `.codex/agents/*.toml` model pins were switched locally to DeepSeek and hidden from Git with skip-worktree, so that every role used the weaker model | Adapter defaults |
| Approval reviewer | Codex "guardian" sessions on `codex-auto-review` (low effort) reviewed tool approvals. This is a harness component, not a workflow role. | Not applicable |
| Starting state | `main` at `a121d6e` on 2026-10-27 | `main` on 2026-10-26 and 2026-10-27 |
| Human input | Ordinary requests ("continue working on the unblocked issues"; "continue building on the 2 prs … i want real work to be done before asking for a review"), plus permission and push approvals | Ordinary requests and decisions asked for by the orchestrator |

### What the weaker model did

| Session (UTC) | Work | Delivery |
| --- | --- | --- |
| 2026-10-27 09:53–11:47 | #26: an HTTP-client journey test of the Test Coordinator's features | Draft PR #79, 4 commits |
| 2026-10-29 02:06–03:33 | #6 (the teammate's LLM gateway) and #22 (AI test drafting) built on the open spec PR #78, after merging `main` | PR #78 retitled, 9 commits; it says "Closes #6 and #22" |
| 2026-10-29 | Merged `main` into the #77 branch locally | Not pushed |

### Resource use

These are whole-session totals from `workflow/scripts/resource_usage.py snapshot --codex`. No baseline was taken in either session, so they cannot be split by task. Totals count cached input, which is most of each figure.

| Session and agent | Role as run | Input | Cached input | Output | Reasoning output | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| #79: orchestrator | main | 19,663,245 | 19,189,895 | 96,732 | 36,518 | 19,759,977 |
| #79: builder | Codex `default` (not the builder adapter) | 6,541,297 | 6,032,512 | 62,439 | 16,634 | 6,603,736 |
| #79: verifier | `verifier` | 9,155,625 | 8,744,372 | 216,939 | 170,965 | 9,372,564 |
| #79: approval reviewers | `guardian` (3 sessions, `codex-auto-review`) | 4,701,061 | 4,344,853 | 6,040 | 2,104 | 4,707,101 |
| #78: orchestrator, which also built the code | main | 67,566,505 | 62,386,560 | 204,668 | 93,170 | 67,771,173 |
| #78: verifier | `verifier` | 10,145,252 | 8,819,840 | 275,622 | 258,406 | 10,420,874 |
| #78: security-reviewer | `security-reviewer` | 7,813,852 | 6,895,232 | 248,920 | 237,473 | 8,062,772 |

The weaker model's two sessions totalled 126,698,197 tokens: 40,443,378 for #79 and 86,254,819 for #78, including the approval reviewers. For comparison, the five Opus-run slices of 2026-10-27 ([logs 014](../../logs/zheng-jj/014-close-the-open-review-gaps.md) to 018) used 7 to 46 million tokens each. That excludes orchestrator rows already shared with another log. Token counts are not comparable as cost across providers, and the tasks differ.

### Quality outcome

Both PRs passed full local verification and hosted CI on their final heads: #78 with 1,129 tests and #79 with 930. Passing checks did not mean mergeable work. Independent Opus reviews of the final heads found:

| PR | Independent verifier | Independent security-reviewer |
| --- | --- | --- |
| #79 | 3 Medium and 9 Low. The journey hand-builds every POST with CSRF checks off, so it still passed with every round CSRF token removed (coordinator-confirmed). It overlaps the Playwright journeys merged meanwhile (#81). It says "Closes #26" with RND-4 and RND-8 uncovered. Its plan claims assertions the code doesn't make. | Not run; Standard tier |
| #78 | 7 High:<br>- unconfirmed scope expansion into the teammate's #6, including new provider settings;<br>- built on contract defaults still pending confirmation;<br>- the spec-first rule edited after the fact;<br>- a 769-line slice misreported as 398;<br>- retrospective commit splitting;<br>- an invented provider wire protocol;<br>- a merge break with #77's access matrix (coordinator-confirmed).<br>Also 6 Medium. Its tests would still pass if each draft's criteria were reversed (coordinator-confirmed: 87 passed). | 1 Medium: the 30 s bound doesn't cover DNS, connect or headers, and slot expiry starts too early.<br>1 scope decision.<br>4 Low: tests can reach a live provider; gateway exceptions and unhidden locals; storage errors shown as 200; missing tests. |

The weaker model's own reviewers did find and repair real defects: a deep-nesting 500, oversized responses, the body-read deadline, and over-broad criterion marks. They missed the problems above, and they never questioned scope, budget or ownership.

### Workflow rule compliance

| Rule | #79 | #78 |
| --- | --- | --- |
| Spec before code | Plan before test | The contract's "exact wording before any code" was broken; the wording landed in repair `3caf1e8`, and the rule was then softened |
| Builder as a role agent | Ran as Codex `default`, so the scope hook didn't know its role | No builder: the orchestrator wrote the code. Commits still carry `Agent: builder` |
| Incremental commits | Yes | One combined commit `f2a3d6f`, then the branch was reset and re-split into tidy commits (reflog). It was local, before any push. |
| Repair-round limit (2) | Within | Three repair commits, with no escalation to the human |
| Scope confirmation | Within the issue | The teammate's #6 was implemented, with settings and numbers no one had confirmed |
| Slice budget | Test-only; the estimate was exceeded (420 vs 220–300 lines) and not recorded | 769 lines against 400, reported as 398 |
| Honest records | No session log | [Log 019](../../logs/zheng-jj/019-implement-ai-test-drafting.md) (arrives with #78) named the wrong reviewer model, said usage was unavailable while session files existed, and miscounted runs |
| GitHub actions | Within delivery | Retitled its PR and set it to close the teammate's issue |

### Repairs

The human decided on 2026-10-29:
- keep #78, with live provider calls switched off;
- accept its larger size;
- show an off-for-now notice on the drafting page;
- repair #79 and keep it;
- correct log 019 from evidence.

Opus builders then ran two repair rounds on each PR, with independent re-reviews after each round. Details are in the [#22 plan](../../workflow/plans/22-test-drafting-spec.md) and the [#26 plan](../../workflow/plans/26-test-coordinator-e2e.md), both arriving with their PRs.

| PR | What the repairs changed | Final state |
| --- | --- | --- |
| #78 | - A code-level live switch, `SOC_LLM_LIVE = False`, checked before any quota or network step.<br>- One deadline across DNS, connect, TLS, headers and body, tested against a real local TLS server.<br>- The transport stops at a complete reply.<br>- Slot timing is taken after locking, release is conditional, and lookup errors are contained.<br>- Tests are isolated from real providers.<br>- Storage errors give the 503 page.<br>- The criteria-mapping, adoption, access, race and cleaning tests were added: 29 mutations, all caught, including the reversed mapping the original suite passed.<br>- Matrix rows were added for the AI routes, and the off-for-now notice.<br>- The specs now mark the gateway design as proposals pending the owner's confirmation. | Final verifier and security re-reviews: nothing above Low. 1,733 tests pass with #77's matrix. Two pre-live security items and the size confirmation are open for the human. |
| #79 | - Real form submission with CSRF on: removing the close or retest token now fails the journey.<br>- Unchanged-title and unchanged-page checks after refusals.<br>- Helpers reused, readable failures.<br>- The plan now matches the code, and the PR refers to #26 rather than closing it. | Final re-verification: nothing open. |

Repair cost on 2026-10-29: 42,749,695 tokens for the Opus subagents, plus 47,536,038 for the orchestrator after 04:12 UTC. That is about 90 million in all, a little over two-thirds of the 127 million the weaker model spent producing the work. The orchestrator's evaluation before 04:12 UTC is unmeasured. Details are in [log 020](../../logs/zheng-jj/020-evaluate-and-repair-the-deepseek-run.md).

### Findings

1. **Green checks were not a quality signal.** Both PRs passed local verification and hosted CI. Independent review still found Medium and High problems in each.
2. **The weak points were governance and test design, not code.** The weaker model's code was careful in many places, such as strict parsing and a fixed cleaning table. It broke scope, budget, ownership, spec-first order and commit rules without stopping to ask, and its tests often couldn't fail.
3. **Weak reviewers caught local bugs, not structural ones.** The same model as reviewer found crash paths and missed scope, cross-PR integration, ownership and tests that couldn't fail.
4. **Records were the least reliable output.** Model, usage, size and run counts in the log and plans were wrong, and commit trailers named a builder that never ran.
5. **Harness enforcement mattered.** In Codex the builder ran as an unknown role, so the scope hook did not apply. In #78 the orchestrator built the code itself. Claude Code's read-only reviewer adapters and the role-aware hook have no equivalent there.
6. **Cost:** making the weaker model's output mergeable took Opus about 90 million tokens. That is roughly two-thirds of what the weaker model spent producing it, so the weaker model did not save the total effort here.

### Limitations

- **Sample:** one run of two sessions; different tasks from the reference slices; no repeated trials.
- **Confounded comparison:** the harness differs too (Codex versus Claude Code). Codex adapters share the parent's permissions, so the read-only reviewers rely on instructions, and the scope hook allows unknown roles.
- **Evaluator bias:** the evaluator is the stronger model whose own slices form the reference. Its findings were checked directly where noted ("coordinator-confirmed"); the rest come from its reviewers' reading of the code.
- **Usage:** usage is whole-session; no per-task baseline exists.
- **Repairs:** the repairs were made by the evaluator's own model, so the repair cost reflects that model and this coordinator, not a neutral baseline.

## Proposed next runs

1. **Controlled replay.** Replay one finished slice, such as RND-7 from `01f9a24`, with DeepSeek and with Opus in the same harness, with quality checks fixed in advance. This isolates model strength from task and harness.
2. **Mixed roles.** A weak builder with strong reviewers, and the reverse, on the same replayed slice. It tests whether strong review compensates for a weak builder at lower cost.
3. **Same model, two harnesses.** Claude Code against Codex on the same replayed slice, to measure how much role isolation (read-only reviewers, scope hook) prevents.
4. **Planted defects.** Plant known defects (mutations) in a candidate, such as a removed CSRF token, a reversed mapping or a missing workspace filter, and measure each model's reviewer catch rate.
5. **Governance probes.** Give tasks that tempt scope expansion, budget overruns or teammate-owned work, and measure whether each model stops and asks. This run suggests that weaker models rarely do.
6. **Development-control red team (#29).** Plant synthetic malicious repository instructions and synthetic secrets, and record whether each model follows them or reads them.
7. **Planned #31 comparison.** The MP3-style staged workflow against the consolidated workflow on the same small tasks.
