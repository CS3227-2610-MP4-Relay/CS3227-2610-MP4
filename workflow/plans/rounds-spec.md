# Specify test rounds for the Test Coordinator (#9, #10, #11, #14, #16, #18)

Goal: specify how a Test Coordinator prepares, publishes, reviews, retests and closes a test round, plus the sample draft round in a new demo workspace, before any code exists.

Tier: High, because it sets role, workspace and state permissions. Base: `83a821f`, stacked on `accounts-spec` (repaired ACC merged at `fba8311`), whose ACC text is used as written and not edited. Spec only: no code, tests, dependencies or guide changes.

Decisions (human, zheng-jj): requirements live in [`rounds.md`](../specs/product/rounds.md) with prefix `RND`. The lifecycle is Draft → Open → Closed. Criteria and cases can be edited only in Draft; publishing freezes them and names the build under test; while Open, a retest names a new build for selected cases, and earlier results stay as history tied to their build; closing makes the round read-only. Results always stay tied to the build, criteria and cases they were recorded against. Only the workspace's Test Coordinator performs these actions, and Beta Testers never see Draft rounds. A new demo workspace contains a sample draft round, created inside ACC-2's transaction. Tester behaviour and the result format belong to RES (Whimsyturtle). The human raised the one-requirement budget for this spec-only PR; each requirement has at most 8 criteria and fits one later code slice.

Repair round 1 decisions (human, zheng-jj):

- An ID submitted in a form from another round or workspace gets that form's error (RND-2.7, RND-5.6); the 404 rule covers records named in the URL, and no route takes a build ID.
- A GET to a POST-only route gets 405, matching ACC; missing CSRF or a cross-origin `Origin` stays 403.
- RES-facing rules stay but are marked provisional, except what the human confirmed: no results in Draft, none new or changed once Closed, earlier results tied to their build.
- Storage worst case is a residual risk in the [security spec](../specs/SECURITY-SPEC.md#rounds-observations-and-history); capacity and retention are settled before the first persisting code slice; RES must cap results.

## Requirements and code-slice order

A criterion never depends on a later requirement's page or action. Earlier slices' tests may put a round into a state directly in test data.

| Requirement | Issue | Criteria | Code slice |
| --- | --- | --- | --- |
| RND-1 Prepare a test round | #9 | 7 | 1st, after ACC-1 and the persistence decisions |
| RND-2 Manage acceptance criteria and test cases | #10 | 8 | 2nd, after RND-1 |
| RND-3 Publish a round to Beta Testers | #11 | 6 | 3rd, after RND-2 |
| RND-6 Close a round | #18 | 5 | 4th, after RND-3 |
| RND-5 Request a retest | #16 | 8 | 5th, after RND-6 (RND-5.7 races a close) |
| RND-7 Sample draft round | — | 4 | 6th, after ACC-2 and RND-6 (RND-7.4 closes it) |
| RND-4 Review submitted results | #14 | 6 | Last, after RND-5 and the RES result record |

IDs keep the confirmed numbering; only the build order changes. Results-dependent clauses sit in RND-4: results on a Closed round (RND-4.1) and results left unchanged by a retest (RND-4.3). RND-7.5 was retired as a restatement of ACC-2.5.

Slice notes:

- RND-1 and RND-7: the shared round-creation code takes an explicit workspace argument, only ever `request.user.workspace` or the workspace ACC-2 has just created, never a value from request data.
- RND-7: the slice first updates the spec with the sample round's exact text, then writes code. It extends ACC-2.5's tests so a failed creation also leaves no sample round, criteria, cases or links.
- Every slice: its rules criterion runs the escaping and direction-isolation tests from the [rules for every round action](../specs/product/rounds.md#rules-for-every-round-action) for the user text its pages render, starting with RND-1.

## Proposed defaults (confirm in PR review)

- Fields: round title 1–120 characters; criterion text 1–500; case title 1–120, steps 1–2000, expected result 1–1000; build label 1–100. Text is trimmed; text with no visible character (only whitespace, control or format characters) counts as empty; Django's null-character validator stays.
- Caps, since storage is shared and nothing is cleaned up: 20 rounds per workspace (the sample round included), 20 criteria and 30 cases per round, 10 builds per round (the publish build included).
- Cases link to one or more criteria of the same round (many-to-many). A case always has at least one link, so a linked criterion cannot be deleted; deleting a case deletes its links explicitly. Unlinked criteria are allowed, including at publishing. Every foreign key uses `PROTECT`.
- Publishing needs at least one case (and so at least one criterion) and a build label.
- A retest selects cases by checkbox and names a new build. Labels are unique within a round, compared case-sensitively after NFC normalisation, stored normalised, with a database unique constraint on round and label. A retest request is stored as a build covering the selected cases; a case's current build is the newest build covering it. The success message counts distinct cases and uses "1 test case" for one.
- Closing has no precondition; the close button warns that the round cannot be reopened.
- No round deletion, reopening, published-case edits or versioning.
- Checking order: method (405); sign-in, role and CSRF/`Origin` before any record is read (redirect or 403); URL records by workspace, then round membership (404); state (409); validation, including form-submitted IDs. Django's CSRF middleware runs before the view, so a signed-out POST without a token may get 403 rather than a redirect; tests of the redirect send a valid token.
- Page titles and routes under `/coordinator/rounds/` are in the [rounds routes](../specs/TECHNICAL-SPEC.md#rounds-routes); messages, including success messages, are in the [criteria](../specs/product/rounds.md). Coordinator home lists rounds newest first, with no pagination given the cap. The round page shows each case's fields and links and, from publishing, each case's current build and the builds list. "Earlier builds" sits under each case on the results page, after its current-build results.
- Concurrency: every round write locks the round row and re-checks state, caps and label uniqueness; round creation locks the workspace row. Racing requests: exactly one succeeds, and the losers get the cap message, the duplicate-label message or 409. Concurrent Draft edits to one record: last saved wins.
- Storage failure: ACC's 503 page; the whole change rolls back. The sample round shares ACC-2's transaction, so ACC-2.5 covers its failure.
- All user-written text is escaped, keeps its line breaks and sits in an element with `dir="auto"`, which isolates its direction.

## Out of scope

AI test drafting (#22); tester pages and the result record (RES); editing or versioning published cases; reopening a closed round; deleting rounds; anything beyond the confirmed lifecycle; any User Guide change.

## Open cross-area items for Whimsyturtle (RES)

These are assumptions RND makes; RES confirms or changes them, and any change to RND text comes back through review. Items marked required must be specified before RES code.

- Outcome vocabulary: RND-4 uses Pass and Fail provisionally.
- What counts as a "submitted" result, and whether a tester can save unsubmitted drafts. RND-4 shows only submitted results.
- Result fields: RND-4.1 provisionally shows the tester's username, outcome, observation and submission time.
- Result reference (provisional): a result references one case and one build of the same round that covers it; its criteria are the case's frozen links.
- Round-level permissions: no results in Draft and none new or changed once Closed (confirmed); while Open, new results only against a case's current build (provisional).
- Required: result creation and changes lock the round row, then re-check the state, that the build is in the round and covers the case, and that it is the case's current build. Tests include a submit racing a close and a submit racing a retest.
- Required: for testers, a Draft round is the same 404 as a missing round.
- Required: coordinator-written text shown to testers follows the same rendering rule and tests as the [rules for every round action](../specs/product/rounds.md#rules-for-every-round-action).
- Required: caps on results per case, tester or round, for shared storage.
- Whether a tester may edit a submitted result while Open, and whether one tester may submit several results for one case and build. RND-4 lists every submitted result, newest first.
- What Beta Testers see of Open and Closed rounds, including a retest prompt and their earlier results.

## Open questions

- No ACC change is needed. RND adds the round list to the Coordinator home without changing ACC-1's content, and the sample round uses ACC-2's existing transaction and failure rule.
- Retention and capacity for rounds, builds and results are part of the [data-model decisions](../specs/TECHNICAL-SPEC.md#data-model) required before the first persisting slice.
- Whether coordinators need a way to tell testers where to get each build; a build label is free text for now.
- For the AI features (#22, #23): published case text cannot be removed and could carry prompt injection into testers' prompts. One case with its linked criteria brings up to about 13,000 characters of coordinator text.

## Checklist

- [x] Write RND-1 to RND-7, the round states and the shared action rules in `rounds.md`.
- [x] Add `### Rounds` and `### Rounds routes` to `TECHNICAL-SPEC.md`; update "Rounds, observations and history" in `SECURITY-SPEC.md`. `PRODUCT-SPEC.md` needs no change.
- [x] Repair round 1: apply the human decisions and review findings above.
- [x] Read changed sections back; check criterion counts and IDs.
- [x] Run full verification and `git diff --check`.
- [x] Repair round 2: restore the Draft-invisibility control, move the rendering rule into the shared rules, fix the capacity link and the RES wording.
- [ ] Verifier and security-reviewer review the fixed candidate.
- [ ] Human and Whimsyturtle review of the proposed defaults and cross-area items; merge decision.

Check evidence (builder, macOS, `.venv`, repair round 2): Ruff lint and format passed; pytest reported 70 passed, 85 subtests passed. `git diff --check` is clean, and `check_scope.py builder --base b928c86` reported all changes within scope. Criterion counts: RND-1 7, RND-2 8, RND-3 6, RND-4 6, RND-5 8, RND-6 5, RND-7 4; no duplicate IDs.
