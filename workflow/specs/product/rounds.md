# Test rounds

Planning area `RND`. The criteria below are specified but not implemented yet. See the [roles](../PRODUCT-SPEC.md#roles) and [accounts](accounts.md); data, routes, limits and page titles are in the [technical spec](../TECHNICAL-SPEC.md#rounds-routes), and controls in the [security spec](../SECURITY-SPEC.md#rounds-observations-and-history).

A test round is a workspace's set of acceptance criteria and test cases, tested against named builds of the software under test. Only the workspace's Test Coordinator performs the actions below. What Beta Testers see and record, including the result format, belongs to [test results](results.md). The [test-drafting AI feature](../ai/test-drafting.md) is not part of these requirements.

Each criterion is labelled happy, boundary, failure, adversarial or ambiguous.

## Round states

A round moves Draft → Open → Closed and never back. Nothing deletes a round.

| State | The coordinator can | Results ([RES](results.md)) |
| --- | --- | --- |
| Draft | Edit the title, criteria and cases; publish | None. Beta Testers cannot see the round |
| Open | Review results, request retests, close | New results are recorded for a case against its current build |
| Closed | View the round and review results | No new or changed results |

A build is a label naming a version of the software under test. Publishing creates the round's first build, which covers every case; each retest creates a build covering the selected cases. A case's current build is the newest build covering it. Criteria, cases and their links are frozen from publication, so a result stays tied to its build, its case and that case's criteria.

## Rules for every round action

These apply to every page and action in this file. A refused request changes nothing.

- A signed-out visitor is redirected to the sign-in page, and a Beta Tester gets the 403 page from [ACC-1.4](accounts.md#acc-1-sign-in-and-out-by-role).
- A round, criterion, case or build that does not exist, belongs to another workspace or is not in the round named by the request gets the 404 "Page not found." page from [ACC-2.4](accounts.md#acc-2-create-an-isolated-demo-workspace).
- A change request by GET, without a valid CSRF token, or whose `Origin` header names another site, is refused with 403.
- An action that the round's current state does not allow, including opening its form, gets a 409 page saying "This action is not available while the round is <state>.", naming Draft, Open or Closed.
- Invalid input shows the form again with the message next to the field. Text fields are trimmed before their length is checked.
- If storage fails, the request gets the 503 page from [ACC-2.5](accounts.md#acc-2-create-an-isolated-demo-workspace) and no part of the change remains.

## RND-1 Prepare a test round

The Coordinator home lists the workspace's rounds, newest first, each with its title and state, and has a "New round" link.

- **RND-1.1** (happy) Creating a round with a title opens its round page, which shows the title, the state "Draft" and no criteria or cases. The round appears on the Coordinator home.
- **RND-1.2** (happy) While the round is Draft, the coordinator can change its title, and the round page and Coordinator home show the new title.
- **RND-1.3** (boundary) A title of 120 characters is saved. An empty, whitespace-only or 121-character title gets "Enter 1 to 120 characters."
- **RND-1.4** (boundary) A workspace's 20th round is created; creating a 21st gets "This workspace has reached its limit of 20 rounds."
- **RND-1.5** (adversarial) With one round left before the limit, 5 simultaneous creation requests create at most 1 round.
- **RND-1.6** (adversarial) No page or response for a Beta Tester shows a Draft round's title, criteria or cases.
- **RND-1.7** (adversarial) Creating, viewing and retitling a round follow the [rules for every round action](#rules-for-every-round-action), including 409 for retitling an Open or Closed round.

## RND-2 Manage acceptance criteria and test cases

While the round is Draft, its page lists its acceptance criteria and test cases in creation order. Each case shows its linked criteria.

- **RND-2.1** (happy) Adding an acceptance criterion with its text shows it on the round page.
- **RND-2.2** (happy) Adding a test case with a title, steps, an expected result and one or more of the round's criteria shows it on the round page with those criteria.
- **RND-2.3** (happy) The coordinator can edit or delete any criterion or case. Deleting a case removes its links and leaves its criteria.
- **RND-2.4** (boundary) Criterion text is 1 to 500 characters; a case's title is 1 to 120, its steps 1 to 2000 and its expected result 1 to 1000. Each field at its maximum is saved; each field empty or one character over gets "Enter 1 to <maximum> characters." for that field, with the other fields valid.
- **RND-2.5** (boundary) A round's 20th criterion and 30th case are saved; a 21st criterion gets "This round has reached its limit of 20 acceptance criteria." and a 31st case gets "This round has reached its limit of 30 test cases."
- **RND-2.6** (failure) Saving a case with no linked criterion gets "Link at least one acceptance criterion." Deleting a criterion that any case links to gets "This criterion is linked to a test case. Unlink it first."
- **RND-2.7** (adversarial) A case linking a criterion of another round or workspace, or one that does not exist, gets "Choose criteria from this round."
- **RND-2.8** (adversarial) Managing criteria and cases follows the [rules for every round action](#rules-for-every-round-action), including 409 for any change to an Open or Closed round's criteria or cases.

## RND-3 Publish a round to Beta Testers

Publishing opens the round for testing on a named build. What Beta Testers then see belongs to [RES](results.md).

- **RND-3.1** (happy) Publishing a Draft round with a build label shows "Round published." The round page shows the state "Open", the build label as every case's current build, and the criteria and cases without edit or delete controls.
- **RND-3.2** (boundary) A build label of 100 characters is accepted. An empty or 101-character label gets "Enter 1 to 100 characters." and the round stays Draft.
- **RND-3.3** (failure) Publishing a round with no test cases gets "Add at least one test case before publishing." and the round stays Draft.
- **RND-3.4** (ambiguous) The published criteria, cases and links are exactly those saved before publishing, and no later request changes them.
- **RND-3.5** (adversarial) An edit racing a publish is either saved before publishing and included in the published round, or refused with 409. Of two simultaneous publish requests, exactly one succeeds and creates one build; the other gets 409.
- **RND-3.6** (adversarial) Publishing follows the [rules for every round action](#rules-for-every-round-action), including 409 for an Open or Closed round.

## RND-4 Review submitted results

For an Open or Closed round, the coordinator opens its results page. Which results count as submitted, and their outcome and observation, are defined in [RES](results.md); until then the outcome is provisionally Pass or Fail.

- **RND-4.1** (happy) The results page lists each case with its linked criteria and current build, then each submitted result for that build with the tester's username, outcome, observation and submission time, newest first.
- **RND-4.2** (boundary) A case with no submitted result for its current build shows "No results for this build yet.", even if it has results for earlier builds.
- **RND-4.3** (ambiguous) A result recorded against an earlier build is listed under "Earlier builds" with its build label, never as a result for the current build.
- **RND-4.4** (ambiguous) Results that are not submitted never appear, and the page offers no way to change or delete a result.
- **RND-4.5** (adversarial) Tester-written text, such as an observation containing HTML or script, is shown as escaped plain text.
- **RND-4.6** (adversarial) The results page follows the [rules for every round action](#rules-for-every-round-action), including 409 for a Draft round.

## RND-5 Request a retest

While the round is Open, the coordinator can ask for selected cases to be tested again on a new build. Testers then record new results against that build ([RES](results.md)).

- **RND-5.1** (happy) Selecting one or more cases and entering a new build label shows "Retest requested for <count> test cases on build <label>." The selected cases' current build becomes the new build; other cases keep theirs.
- **RND-5.2** (boundary) Selecting no case gets "Select at least one test case." A build label of 100 characters is accepted; an empty or 101-character label gets "Enter 1 to 100 characters."
- **RND-5.3** (failure) A label already used for a build in this round gets "This build label is already used in this round."
- **RND-5.4** (boundary) A round's 10th build, counting the build named at publishing, is created; an 11th gets "This round has reached its limit of 10 builds."
- **RND-5.5** (ambiguous) A case can be retested more than once. Earlier builds, results and the round's criteria and cases stay unchanged, and earlier results stay tied to their build.
- **RND-5.6** (adversarial) Selecting a case of another round or workspace, or one that does not exist, gets "Choose test cases from this round."
- **RND-5.7** (adversarial) Of two simultaneous retest requests with the same label, at most one succeeds. A retest racing a close either completes before the close or gets 409.
- **RND-5.8** (adversarial) Requesting a retest follows the [rules for every round action](#rules-for-every-round-action), including 409 for a Draft or Closed round.

## RND-6 Close a round

Closing ends testing and makes the round read-only. A closed round cannot be reopened.

- **RND-6.1** (happy) Closing an Open round shows "Round closed." Its round page shows the state "Closed", and its criteria, cases, builds and results stay visible on the round and results pages.
- **RND-6.2** (ambiguous) Closing needs no precondition: a round with untested cases or no results can be closed. The close button is shown with "Closing makes this round read-only. It cannot be reopened."
- **RND-6.3** (boundary) Every change to a Closed round, including retitling, editing criteria or cases, publishing, requesting a retest and closing again, gets 409.
- **RND-6.4** (adversarial) Of two simultaneous close requests, exactly one succeeds; the other gets 409.
- **RND-6.5** (adversarial) Closing follows the [rules for every round action](#rules-for-every-round-action), including 409 for a Draft round.

## RND-7 Sample draft round in a new demo workspace

[ACC-2](accounts.md#acc-2-create-an-isolated-demo-workspace) creates a sample round with each new demo workspace, so peers can publish and test straight away.

- **RND-7.1** (happy) A new demo workspace has exactly one round, "Sample round", in Draft, with 3 acceptance criteria and 4 test cases, each case linked to at least one criterion. Its text is fixed, synthetic and within the RND-2 field limits.
- **RND-7.2** (happy) The coordinator can publish the sample round straight away by entering only a build label, or edit it first like any Draft round.
- **RND-7.3** (boundary) The sample round counts toward the round limit: 19 more rounds can be created, and the next gets the RND-1.4 message.
- **RND-7.4** (adversarial) Each workspace's sample round is its own: editing, publishing or closing it changes no other workspace's sample round.
- **RND-7.5** (failure) If the sample round cannot be written, [ACC-2.5](accounts.md#acc-2-create-an-isolated-demo-workspace) applies: no part of the workspace remains.
