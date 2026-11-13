# Make session-log references unambiguous

Goal: Give every session log a unique identifier and make existing out-of-log references cite full filenames, because per-author numbering means each of 001–028 names two logs.

## Scope and decisions

- Trigger: human `/slice 186`; grader feedback quoted in issue #186 asks for unique identifiers in future records and full filenames in existing references. Standard tier: a workflow-rule change, with no development security control, CI, dependency, route or `src/` change. Spec: none (workflow records); no product criterion applies. Slice budget: 0 lines under `src/`.
- Human decisions confirmed this session:
  1. **Future rule:** keep per-author numbering. A log's identifier is `<github-user>/<NNN>` (for example `Whimsyturtle/062`); any reference to a log from outside that log links its full path. Small edit to [the log skill](../skills/log.md) only; no renames and no global numbering.
  2. **Merged plans:** reference-only corrections, turning each bare number into a link to the full filename with wording otherwise unchanged, following the [#36 precedent](36-check-session-logs.md#applied-corrections-and-delivery).
  3. **Logs:** repair only the one cross-folder reference, in [zheng-jj 028](../../logs/zheng-jj/028-finish-the-guides-and-the-deferred-cleanup.md) (last table row). Same-folder bare references inside logs stay as historical text.
  4. This session's log is `logs/Whimsyturtle/062-…` (human-chosen). 059–061 do not exist on this branch, so `check_logs.py` will report that gap; it is not run in CI.
- Out of scope: running `check_logs.py` in CI, a bare-reference lint, editing `AGENTS.md`, renaming logs.
- Ownership: builder writes this plan and the merged-plan corrections; the coordinator owns `workflow/skills/log.md`, `experiments/**`, `logs/**`, Git and the PR, which are outside builder scope, and also appends checkpoint and delivery notes to this plan.

## Reference mapping

Builder re-grepped the worktree at `a93430a` outside `logs/` for `log(s)`, `session(s)`, `log #`, `entry`, `next log`, `<author> NNN` and `<author>/NNN` followed by a three-digit number, excluding references already linked to a full log path. Targets were checked against folder contents and log headers.

| Location | Bare text | Target |
| --- | --- | --- |
| `experiments/agent-setups/README.md:21` | logs 022 and 023 | [`logs/zheng-jj/022-compare-agent-setups-and-tune-an-ideal-one.md`](../../logs/zheng-jj/022-compare-agent-setups-and-tune-an-ideal-one.md), [`logs/zheng-jj/023-extend-the-agent-setups-experiment-to-four-tasks.md`](../../logs/zheng-jj/023-extend-the-agent-setups-experiment-to-four-tasks.md) |
| `experiments/development-workflow/README.md:44` | `[logs 014](…) to 018` | [`logs/zheng-jj/018-specify-ai-test-drafting.md`](../../logs/zheng-jj/018-specify-ai-test-drafting.md) |
| `experiments/development-workflow/README.md:77` | correct log 019 | [`logs/zheng-jj/019-implement-ai-test-drafting.md`](../../logs/zheng-jj/019-implement-ai-test-drafting.md) |
| `workflow/plans/22-test-drafting-spec.md:83` | log 018; log 019 | [`logs/zheng-jj/018-specify-ai-test-drafting.md`](../../logs/zheng-jj/018-specify-ai-test-drafting.md); [`logs/zheng-jj/019-implement-ai-test-drafting.md`](../../logs/zheng-jj/019-implement-ai-test-drafting.md) |
| `workflow/plans/22-test-drafting-spec.md:100`, `:101`, `:120` | log 019 | [`logs/zheng-jj/019-implement-ai-test-drafting.md`](../../logs/zheng-jj/019-implement-ai-test-drafting.md) |
| `workflow/plans/36-check-session-logs.md:46` | next log is 058 | [`logs/Whimsyturtle/058-check-saved-session-logs.md`](../../logs/Whimsyturtle/058-check-saved-session-logs.md) (added to the coordinator's list; same plan links it at line 61) |
| `workflow/plans/67-spec-consistency.md:14`, `:24` | log 009 | [`logs/Whimsyturtle/009-prepare-checked-product-site-publication.md`](../../logs/Whimsyturtle/009-prepare-checked-product-site-publication.md) (records PLT-2.6 hosted evidence and the reclassification) |
| `workflow/plans/67-unit-test-helpers.md:13` | logs 036/037 | [`logs/Whimsyturtle/036-repair-ui-journeys.md`](../../logs/Whimsyturtle/036-repair-ui-journeys.md), [`logs/Whimsyturtle/037-fix-tester-results-and-feedback.md`](../../logs/Whimsyturtle/037-fix-tester-results-and-feedback.md) (both record `server closed the connection unexpectedly`) |
| `logs/zheng-jj/028-finish-the-guides-and-the-deferred-cleanup.md:105` | honouring log 009 | [`logs/Whimsyturtle/009-prepare-checked-product-site-publication.md`](../../logs/Whimsyturtle/009-prepare-checked-product-site-publication.md) |

- Confirmations: the zheng-jj headers, as confirmed by the coordinator, show [005](../../logs/zheng-jj/005-ask-before-agents-change-github-state.md) through [018](../../logs/zheng-jj/018-specify-ai-test-drafting.md) all dated 2026-10-27 with `claude-opus-5-5`, and [019](../../logs/zheng-jj/019-implement-ai-test-drafting.md) dated 2026-10-29 with DeepSeek. The README's "five" count is left as written because these corrections change references only; the coordinator will raise the wording with the human. Plan 22 is the zheng-jj #22 slice, so its 018/019 are zheng-jj's (table rows above); [Whimsyturtle 018](../../logs/Whimsyturtle/018-audit-historical-token-counts.md) and [Whimsyturtle 019](../../logs/Whimsyturtle/019-verify-tester-fix-retests.md) are unrelated to #22.
- Left unchanged by coordinator decision: author-named but unlinked references, because decision 2 covers bare numbers only. These are plan 36's text at `workflow/plans/36-check-session-logs.md:29` ("zheng-jj 006/017") and `:47` ("Whimsyturtle 047" to 050 line lists), the `src/accounts/tests/test_limit_views.py:535` comment `(logs/Whimsyturtle/036, 037)` (also under the 0-line `src/` budget), and author-named references inside logs. The coordinator will surface linking them to the human as an optional follow-up. The reflection and remaining matches already link full paths.

## Commit checkpoints and checks

1. **Plan** (builder): this file. Checks: read-back; builder scope check.
2. **Log-skill rule** (coordinator): `workflow/skills/log.md`. Checks: read-back of the changed section; link targets.
3. **Merged-plan corrections** (builder): `workflow/plans/22-test-drafting-spec.md`, `36-check-session-logs.md`, `67-spec-consistency.md`, `67-unit-test-helpers.md`. Checks: diff shows link markup only; every changed link target resolves locally; builder scope check.
4. **Experiments and cross-folder log** (coordinator): `experiments/agent-setups/README.md`, `experiments/development-workflow/README.md`, `logs/zheng-jj/028-finish-the-guides-and-the-deferred-cleanup.md`. Checks: as checkpoint 3.
5. **Session log and delivery** (coordinator): `logs/Whimsyturtle/062-…` and delivery notes here. Checks: re-run the grep above, showing no remaining bare out-of-log references; `workflow/scripts/check_logs.py`, expecting only the 059–061 gap finding; full verification `ruff check . && ruff format --check . && pytest` on the final candidate, using the shared PostgreSQL test server at 127.0.0.1:55432.

## Starting evidence and next step

- Coordinator supplied worktree `tmp/worktrees/issue-186`, branch `docs/186-unique-log-references`, HEAD `a93430a3879e3a0af85eaa251b428a1d791d83e5`, clean tree.
- Hook check: at the coordinator's request, as [the workflow README](../README.md#how-scope-is-enforced) requires in each new worktree ("ask the builder to edit `AGENTS.md`, and it must be refused"), a builder Edit appending a blank line to `AGENTS.md` was refused by the PreToolUse `check_scope.py --hook` ("builder may not write agents.md"); the file was not changed.
- Plan committed as `2a60dea`; log-skill rule committed as `d9ae866`. Coordinator decisions: include 36:46; leave the author-named references and the `src/` comment unchanged; leave the README's "five" count for the human as an observation.

## Checkpoint 3: merged-plan corrections

- From snapshot `d9ae8662ba83c81d93c3a2080640d5cfeff9f848`, builder wrapped the bare text in links at plan 22 lines 83 (018, 019), 100, 101 and 120; plan 36 line 46; plan 67-spec-consistency lines 14 and 24; and plan 67-unit-test-helpers line 13. Diff: 8 lines changed across four files, wording unchanged.
- Checks run: `git diff --word-diff=plain` showed only link markup added; `test -f` on all six resolved targets (the Whimsyturtle 009, 036, 037 and 058 and zheng-jj 018 and 019 targets in the table) passed; `python workflow/scripts/check_scope.py builder --base d9ae866` reported "All changes are within the builder scope." (exit 0).
- Next: coordinator commits checkpoint 3, then checkpoint 4.

## Checkpoint 4: experiments and cross-folder log

- Coordinator committed checkpoint 3 as `ae7652d` and checkpoint 4 as `183e6cc`. Checkpoint 4 links `experiments/agent-setups/README.md:21`, `experiments/development-workflow/README.md:44` and `:77`, and [`logs/zheng-jj/028-finish-the-guides-and-the-deferred-cleanup.md`](../../logs/zheng-jj/028-finish-the-guides-and-the-deferred-cleanup.md) line 105. Only the zheng-jj 028 link text gains the author ("Whimsyturtle log 009"), because that reference crosses folders.
- Checks run: word diff showed link markup only, apart from that qualifier. A temporary link validator, run on every changed file, resolved all new targets. It also found two broken anchors that predate this slice and are outside its scope (`experiments/development-workflow/README.md:3` `../README.md#planned-comparisons`; `67-spec-consistency.md:9` `#limits-and-accounting-proposed`). It also flagged this plan's table text `[logs 014](…)`, which the coordinator wrapped in code formatting.

## Repair round 1

- Verifier review of `a93430a..279f620` found 0 High and 0 Medium; the coordinator checked each finding. From snapshot `279f6204a43a9cfc7dbb4de291b949a65cad8053`, builder changed only this plan:
  - recorded that the coordinator requested the hook check, as the workflow README requires;
  - corrected the date note to zheng-jj 005–018, and recorded that the coordinator will raise the "five" wording;
  - followed the new rule here: every table Target cell and every cited log in prose now links its full path;
  - added the coordinator's notes to Ownership, and recorded the narrowing to bare numbers for author-named references;
  - corrected the plan-checkpoint claim that Whimsyturtle 019 is a token-accounting log; it verifies tester-fix retests (linked under Confirmations).
- Checks run: resolved every link in this plan, and all 15 file targets exist. The two anchors (`#how-scope-is-enforced`, `#applied-corrections-and-delivery`) match headings. The only unresolved match is the code-formatted `[logs 014](…)` quotation. `python workflow/scripts/check_scope.py builder --base 279f620` reported "All changes are within the builder scope." (exit 0).

## Verification and delivery

- The verifier re-reviewed `279f620..07aeb6e` and found nothing above Info. The `--unchanged` checks passed on both review candidates, and the plan's own links resolve.
- The final reviewed candidate `07aeb6e` passed ruff and the format check. The workflow-script tests (120 OK, 5 skipped) ran on `279f620`, which has the same code. A closing search found no bare log references outside `logs/`.
- A local full pytest run with the shared test database ended in 3,233 errors. Its first error was not captured, and other sessions were using that database at the time. A rerun with a private test database name passed everything except PLT-1.6's database-name assertion, which the override itself causes. That test then passed alone with the repository settings. The exact results are in the [session log](../../logs/Whimsyturtle/062-make-session-log-references-unambiguous.md#problems).
- [Draft PR #188](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/188): on `07aeb6e`, hosted `verify` and `site` passed, and `deploy` and `production` were skipped. With the session log added, `check_logs.py` reports only the expected 059–061 gap.
- Next: human review of the PR and the log. Optional follow-ups for the human are listed in the PR.
