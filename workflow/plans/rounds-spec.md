# Specify test rounds for the Test Coordinator (#9, #10, #11, #14, #16, #18)

Goal: specify how a Test Coordinator prepares, publishes, reviews, retests and closes a test round, plus the sample draft round in a new demo workspace, before any code exists.

Tier: High, because it sets role, workspace and state permissions. Base: `83a821f`, stacked on `accounts-spec`, whose ACC text is used as written and not edited. Spec only: no code, tests, dependencies or guide changes.

Decisions (human, zheng-jj): requirements live in [`rounds.md`](../specs/product/rounds.md) with prefix `RND`. The lifecycle is Draft → Open → Closed. Criteria and cases can be edited only in Draft; publishing freezes them and names the build under test; while Open, a retest names a new build for selected cases, and earlier results stay as history tied to their build; closing makes the round read-only. Results always stay tied to the build, criteria and cases they were recorded against. Only the workspace's Test Coordinator performs these actions, and Beta Testers never see Draft rounds. A new demo workspace contains a sample draft round, created inside ACC-2's transaction. Tester behaviour and the result format belong to RES (Whimsyturtle). The human raised the one-requirement budget for this spec-only PR; each requirement has at most 8 criteria and fits one later code slice.

| Requirement | Issue | Criteria | Code slice |
| --- | --- | --- | --- |
| RND-1 Prepare a test round | #9 | 7 | After ACC-1 |
| RND-2 Manage acceptance criteria and test cases | #10 | 8 | After RND-1 |
| RND-3 Publish a round to Beta Testers | #11 | 6 | After RND-2 |
| RND-4 Review submitted results | #14 | 6 | After RND-3 and the RES result record |
| RND-5 Request a retest | #16 | 8 | After RND-3 |
| RND-6 Close a round | #18 | 5 | After RND-3 |
| RND-7 Sample draft round | — | 5 | After ACC-2 and RND-3 |

IDs follow the confirmed order, with no splits. RND-5 shows a retest's effect on the round page (each case's current build), so it does not wait for RND-4.

## Proposed defaults (confirm in PR review)

- Fields: round title 1–120 characters; criterion text 1–500; case title 1–120, steps 1–2000, expected result 1–1000; build label 1–100. All trimmed before checking; message "Enter 1 to <maximum> characters."
- Caps, since storage is shared and nothing is cleaned up: 20 rounds per workspace (the sample round included), 20 criteria and 30 cases per round, 10 builds per round (the publish build included).
- Cases link to one or more criteria of the same round (many-to-many). A case always has at least one link, so a linked criterion cannot be deleted. Unlinked criteria are allowed, including at publishing.
- Publishing needs at least one case (and so at least one criterion) and a build label.
- A retest selects cases by checkbox and names a new build whose label is unused in the round. A build covers the cases it names; a case's current build is the newest build covering it. A retest request is stored as that build, not as a separate record.
- Closing has no precondition; the close button warns "Closing makes this round read-only. It cannot be reopened."
- No round deletion, reopening, published-case edits or versioning.
- Routes under `/coordinator/rounds/`, page titles and success messages ("Round published.", "Retest requested for <count> test cases on build <label>.", "Round closed.") are in the [rounds routes](../specs/TECHNICAL-SPEC.md#rounds-routes). Coordinator home lists rounds newest first, with no pagination given the cap.
- Denied requests reuse ACC: signed out redirects, Beta Tester 403, other workspace or other round 404 "Page not found.", missing CSRF or cross-site `Origin` 403. A wrong-state request, including opening a Draft-only form, gets 409 "This action is not available while the round is <state>."
- Concurrency: every round write locks the round row and re-checks state, limits and label uniqueness; round creation locks the workspace row. An edit racing a publish is either included or refused with 409. Concurrent Draft edits to one record: last saved wins.
- Storage failure: ACC's 503 page; the whole change rolls back. The sample round shares ACC-2's transaction, so ACC-2.5 covers its failure.
- Sample round: "Sample round" with 3 criteria and 4 cases of fixed synthetic text, chosen in the RND-7 code slice.
- The results page escapes tester-written text and shows results for each case's current build, then "Earlier builds".

## Out of scope

AI test drafting (#22); tester pages and the result record (RES); editing or versioning published cases; reopening a closed round; deleting rounds; anything beyond the confirmed lifecycle; any User Guide change.

## Open cross-area items for Whimsyturtle (RES)

These are assumptions RND makes; RES confirms or changes them, and any change to RND text comes back through review.

- Outcome vocabulary: RND-4 uses Pass and Fail provisionally.
- What counts as a "submitted" result, and whether a tester can save unsubmitted drafts. RND-4 shows only submitted results.
- A result references one case and one build covering it; its criteria are the case's frozen links. RES specifies the result's fields, including the observation shown in RND-4.1.
- Round-level permissions RES should enforce and test: no results in Draft and Draft rounds invisible to testers; while Open, new results only against a case's current build; while Closed, no new or changed results.
- Whether a tester may edit a submitted result while the round is Open, and whether one tester may submit several results for one case and build. RND-4 lists every submitted result, newest first.
- What Beta Testers see of Open and Closed rounds, including a retest prompt and their earlier results.
- Whether limits on results per case or per tester are needed for shared storage.

## Open questions

- No ACC change is needed. RND adds the round list to the Coordinator home without changing ACC-1's content, and the sample round uses ACC-2's existing transaction and failure rule.
- Retention of rounds, builds and results stays with the open [data-model decisions](../specs/TECHNICAL-SPEC.md#data-model).
- Whether coordinators need a way to tell testers where to get each build; a build label is free text for now.

## Checklist

- [x] Write RND-1 to RND-7, the round states and the shared action rules in `rounds.md`.
- [x] Add `### Rounds` and `### Rounds routes` to `TECHNICAL-SPEC.md`; update "Rounds, observations and history" in `SECURITY-SPEC.md`. `PRODUCT-SPEC.md` needs no change.
- [x] Read changed sections back; check criterion counts and IDs.
- [x] Run full verification and `git diff --check`.
- [ ] Verifier and security-reviewer review the fixed candidate.
- [ ] Human and Whimsyturtle review of the proposed defaults and cross-area items; merge decision.
