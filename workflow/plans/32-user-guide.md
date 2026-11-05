# 32: Bring the User Guide in line with the release

Goal: make [`docs/UserGuide.md`](../../docs/UserGuide.md) describe exactly what the app does at `26e77cc`, for coordinators and testers, in the product's exact words, under [#32](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/issues/32).

Tier: Fast lane. User Guide only; no behaviour, acceptance criterion or security control changes. Targeted checks; the human reviews the diff. Base `26e77cc`. Not edited: `docs/DeveloperGuide.md` (another builder), specs and code.

Baseline audit (2026-11-05, against `src/*/urls.py`, every template and the message constants in `rounds/`, `ai/` and `accounts/`):
- **Accuracy.** Every quoted string and bold label resolves in non-test `src/`. The 11 the script cannot match are composites or examples: "(Open)", "(Closed)", "(Draft)", "State: Open/Closed/Draft", "Outcome: Pass/Fail" and "Observation: No observation." (template text plus choice label), "Null characters are not allowed." (Django's built-in validator) and "1.4.0-beta" (example label). Limits match: titles 120, criterion 500, steps 2000, expected result 1000, build label 100, observation 2000; 20 rounds, 20 criteria, 30 cases, 10 builds; 1 to 5 criteria for drafting; 30 failed sign-ins per address per 15 minutes; 10 demo workspaces per address per hour and 200 per day; 8-hour session.
- **Coverage gaps.** No error-page summary: 403 (other role, failed form check), 404, 409 (every refusal renders the "Action not available" page with its message), 429 (demo limit page; the sign-in limit stays on the sign-in page) and 503 (including a sign-in storage failure, not yet mentioned). Coordinator refusals on the wrong state ("This action is not available while the round is Open." etc.) are only described for testers and retest. AI pages do not say that requests share a per-account quota (20 an hour, one at a time; 200 an hour and two at a time for Relay) or need the SoC LLM configured locally; both surface only as the unavailable messages.
- **Readability.** Tester sections come before the coordinator's, though a new workspace's only round is Draft and testers see nothing until it is published. Within rounds, AI drafting follows results review although it is a Draft-round step, and close precedes results review. "No results for this build yet." and the "No observation." rule are stated twice; "Relay is temporarily unavailable. Try again later." is repeated per section.

Checkpoints:
1. `plan: Plan the User Guide pass (#32)`: this file.
2. `docs: Correct and complete the User Guide (#32)`: `docs/UserGuide.md`. In-place fixes for the gaps and duplicates above, plus an "Error pages" section at the end; no section moves.
3. `docs: Order the User Guide by journey (#32)`: `docs/UserGuide.md`. Section moves only (reviewable with `git diff --color-moved`): coordinator rounds before tester sections; within rounds, create → title → criteria and cases → AI drafting → publish → Open round → review results → retest → close. Fold 2 and 3 into one commit only if the moves turn out trivial.

Focused checks for 2 and 3: the scratch script `.r67/32/check_quotes.py <worktree>` (quoted strings, bold, italic and code spans against non-test `src/` text; unmatched ones listed with a judgement); every relative link and in-page anchor resolves to a heading slug; `python .r67/dblock.py pytest -q -p no:cacheprovider src/relay/tests/test_site.py`; read changed sections back.

Decisions: AI quota and configuration get one sentence each with a link to the [gateway spec](../specs/ai/llm-gateway.md) and the Developer Guide rather than restating either. "Relay runs locally only" stays, since release is still held.

Open: the Developer Guide anchors `#run-locally` and `#soc-llm` may change in the parallel Developer Guide slice; recheck them before the final commit.
