# Test rounds

Planning area `RND`. RND-1, RND-2, RND-3, RND-5, RND-6 and RND-7 are implemented; RND-4 and RND-8 are specified but not implemented yet, and RND-8 is blocked on the [shared LLM gateway](../ai/llm-gateway.md) (#6). See the [roles](../PRODUCT-SPEC.md#roles) and [accounts](accounts.md); data, routes and page titles are in the [technical spec](../TECHNICAL-SPEC.md#rounds), and controls in the [security spec](../SECURITY-SPEC.md#rounds-observations-and-history).

A test round is a workspace's set of acceptance criteria and test cases, tested against named builds of the software under test. Only the workspace's Test Coordinator performs the actions below. What Beta Testers see and record, including the result format, belongs to [test results](results.md). RND-8 holds the pages of the [test-drafting AI feature](../ai/test-drafting.md); that contract holds what is sent to the model, the reply it accepts and its evaluation.

Each criterion is labelled happy, boundary, failure, adversarial or ambiguous.

## Round states

A round moves Draft → Open → Closed and never back. Nothing deletes a round.

| State | The coordinator can | Results ([RES](results.md)) |
| --- | --- | --- |
| Draft | Edit the title, criteria and cases; publish | None. On tester pages, a Draft round is the same 404 as a missing round |
| Open | Review results, request retests, close | Provisional: new results for a case are recorded against its current build |
| Closed | View the round and review results | No new or changed results |

A build is a label naming a version of the software under test. Publishing creates the round's first build, which covers every case; each retest creates a build covering the selected cases. A case's current build is the newest build covering it. Criteria, cases and their links are frozen from publication, and earlier results stay tied to their build. The Results column is enforced by [RES](results.md); rules marked provisional hold until `results.md` specifies them.

## Rules for every round action

These apply to every page and action in this file, checked in this order. A refused request changes nothing.

1. A request with a method that can change data (anything but GET, HEAD, OPTIONS or TRACE) without a valid CSRF token, or whose `Origin` header names another origin, gets the 403 page of [ACC-1.4](accounts.md#acc-1-sign-in-and-out-by-role) first. Otherwise, a method the route does not accept, such as a GET to a POST-only route, gets 405.
2. A signed-out visitor is redirected to the sign-in page, and a Beta Tester gets the 403 page of ACC-1.4. No record is read before these checks.
3. A round, criterion or case named in the URL that does not exist, belongs to another workspace, or is not in the round the URL names gets the 404 page of [ACC-2.4](accounts.md#acc-2-create-an-isolated-demo-workspace). A 404 always comes before a 409, so another workspace's round state is never revealed.
4. An action that the round's state does not allow, including opening its form, gets a 409 page saying "This action is not available while the round is <state>.", naming Draft, Open or Closed.
5. Invalid input shows the form again with the message next to the field; an ID submitted in a form is checked here, as in ACC-2.4. Text is trimmed before its length is checked; text with no visible character (only whitespace, control or format characters such as zero-width spaces) counts as empty, and text with a null character gets "Null characters are not allowed." Text containing a text-direction control, one of the 9 invisible characters U+202A to U+202E (embeddings, overrides and their pop) and U+2066 to U+2069 (isolates), gets "Hidden text-direction characters are not allowed."; this check runs only once the text passes the other checks, so text that is also empty, too long or has a null character gets only those messages. Text that passes these checks is accepted whatever script or symbols it uses, including accents, curly quotes, emoji, the direction marks U+200E, U+200F and U+061C, and the zero-width joiner and non-joiner (U+200D and U+200C).

If storage fails, the request gets the 503 page of [ACC-2.5](accounts.md#acc-2-create-an-isolated-demo-workspace) and no part of the change remains. The one exception is saving the session at the end of a request, which stores a success message or drops one just shown: if that fails, the request gets a "Bad Request (400)" page instead, a change already saved remains and its message is lost ([rounds routes](../TECHNICAL-SPEC.md#rounds-routes)).

All user-written text is shown as escaped plain text. In page content it keeps its line breaks, and each of its lines sits inside its own element with `dir="auto"` that wraps only that user text, such as the build label inside a success message rather than the whole message, so its text direction is isolated from the page; site CSS does not reset `unicode-bidi`. In a page `<title>`, text-direction controls (rule 5) are removed from the user part, which is then wrapped in U+2068 FIRST STRONG ISOLATE and U+2069 POP DIRECTIONAL ISOLATE, so they cannot reorder the browser-tab title. Although rule 5 refuses text-direction controls in submitted text, rendering still escapes and isolates all user text, including a refused value shown again in its field and text stored by other means. Each requirement's rules criterion tests this for the user text its pages render: markup in element content and in attribute values, text used in the page title (checking its isolate characters, including a stray U+2069 followed by U+202E) or in a success message, line breaks, and text-direction controls or zero-width characters, which cannot reorder or hide surrounding page text.

## RND-1 Prepare a test round

The Coordinator home lists the workspace's rounds, newest first, each with its title and state, and has a "New round" link.

Under a "Rounds" heading, the Coordinator home shows each round as a link to its round page followed by its state in brackets, such as "(Draft)", or "No rounds yet." when there are none. The "New round" page has a "Title" field and a "Create round" button; the "Edit round" page has the same field holding the current title and a "Save" button. Creating or retitling a round opens its round page, with no success message. The round page shows the title as its heading, "State: <state>" and, while Draft, an "Edit round" link. The new-round, edit-round and round pages each link to "Coordinator home". Every message in RND-1, including the RND-1.4 limit, appears next to the "Title" field.

- **RND-1.1** (happy) Creating a round with a title opens its round page, which shows the title, the state "Draft" and no criteria or cases. The round appears on the Coordinator home.
- **RND-1.2** (happy) While the round is Draft, the coordinator can change its title, and the round page and Coordinator home show the new title.
- **RND-1.3** (boundary) A title of 120 characters is saved. An empty, invisible-only or 121-character title gets "Enter 1 to 120 characters."
- **RND-1.4** (boundary) A workspace's 20th round is created; creating a 21st gets "This workspace has reached its limit of 20 rounds."
- **RND-1.5** (adversarial) With one round left before the limit, exactly one of 5 simultaneous creation requests creates a round; the others get the RND-1.4 message.
- **RND-1.6** (adversarial) A Beta Tester gets the same 403 for an existing round's ID as for a missing one, and the Tester home shows no Draft round.
- **RND-1.7** (adversarial) Creating, viewing and retitling a round follow the [rules for every round action](#rules-for-every-round-action). Tests include another workspace's round in a wrong state getting 404, not 409, retitling an Open or Closed round getting 409, and the rendering tests for round titles on the round page, the Coordinator home and the page title.

## RND-2 Manage acceptance criteria and test cases

While the round is Draft, its page lists its acceptance criteria and test cases in creation order. Each case shows its title, steps, expected result and linked criteria.

After its state and "Edit round" link, the round page has an "Acceptance criteria" heading, listing each criterion's text, or "No acceptance criteria yet." when there are none, then a "Test cases" heading. Under it, each case shows its title as a subheading, then the labels "Steps", "Expected result" and "Linked acceptance criteria", each followed by that text, the linked criteria listed by their text in creation order; with no cases it shows "No test cases yet." These sections appear in every state; the controls below appear only while Draft. They are an "Add acceptance criterion" link under the first heading and an "Add test case" link under the second, an "Edit criterion" link and a "Delete criterion" button for each criterion, and an "Edit test case" link and a "Delete test case" button for each case. Deleting asks for no confirmation.

The "New acceptance criterion" page has a "Text" field and an "Add acceptance criterion" button. The "New test case" page has "Title", "Steps" and "Expected result" fields, then "Linked acceptance criteria" with a checkbox for each of the round's criteria, labelled with its text, in creation order, or "No acceptance criteria yet." when there are none, and an "Add test case" button. The "Edit acceptance criterion" and "Edit test case" pages have the same fields holding the current text and links, and a "Save" button. Each of these four pages links to "Back to round", the round page. Saving or deleting opens the round page, with no success message. Each message appears next to its field: the RND-2.4 messages next to the field they name, the RND-2.5 limits next to "Text" or "Title", and the RND-2.6 and RND-2.7 case messages next to "Linked acceptance criteria". A refused deletion shows the round page with the RND-2.6 message under that criterion.

- **RND-2.1** (happy) Adding an acceptance criterion with its text shows it on the round page.
- **RND-2.2** (happy) Adding a test case with a title, steps, an expected result and one or more of the round's criteria shows it on the round page with those criteria.
- **RND-2.3** (happy) The coordinator can edit any criterion or case, delete any case, and delete a criterion that no case links to. Deleting a case deletes its links and keeps its criteria.
- **RND-2.4** (boundary) Criterion text is 1 to 500 characters; a case's title is 1 to 120, its steps 1 to 2000 and its expected result 1 to 1000. Each field at its maximum is saved; each field empty or one character over gets "Enter 1 to <maximum> characters." for that field, with the other fields valid.
- **RND-2.5** (boundary) A round's 20th criterion and 30th case are saved; a 21st criterion gets "This round has reached its limit of 20 acceptance criteria." and a 31st case gets "This round has reached its limit of 30 test cases."
- **RND-2.6** (failure) Saving a case with no linked criterion gets "Link at least one acceptance criterion." Deleting a criterion that any case links to gets "This criterion is linked to a test case. Unlink it first."
- **RND-2.7** (adversarial) A case form submitting a criterion of another round or workspace, or one that does not exist, gets "Choose criteria from this round."
- **RND-2.8** (adversarial) Managing criteria and cases follows the [rules for every round action](#rules-for-every-round-action). Tests include a criterion or case ID of an Open round, used under a Draft round's URL in the same workspace, getting 404 and leaving that record unchanged, any change to an Open or Closed round's criteria or cases getting 409, and the rendering tests for criterion and case text.

## RND-3 Publish a round to Beta Testers

Publishing opens the round for testing on a named build. From then on, the round page shows each case's current build and lists the round's builds, oldest first, each with its label and the cases it covers. What Beta Testers then see belongs to [RES](results.md).

While the round is Draft, the round page ends, after the "Test cases" section and before the "Coordinator home" link, with a "Build label" field and a "Publish round" button. Publishing opens the round page, which shows "Round published." once, directly under its heading. A refused publish shows the round page again with the entered label kept in the field and the RND-3.2 or RND-3.3 message next to the "Build label" field; the label is checked first, so an invalid label on a round with no test cases gets only the RND-3.2 message. From publishing, each case shows, after its linked criteria, the label "Current build" followed by its current build's label. After the "Test cases" section, a "Builds" heading lists the round's builds, oldest first, each with its label as a subheading, then the label "Covered test cases" followed by the titles of the cases it covers, in creation order. An Open round's page has no "Edit round" link, no RND-2 controls and no publish form. A build label never appears in a page title.

- **RND-3.1** (happy) Publishing a Draft round with a build label shows "Round published." The round page shows the state "Open", that build as every case's current build, and the criteria and cases without edit or delete controls.
- **RND-3.2** (boundary) A build label of 100 characters is accepted. An empty, invisible-only or 101-character label gets "Enter 1 to 100 characters." and the round stays Draft.
- **RND-3.3** (failure) Publishing a round with no test cases gets "Add at least one test case before publishing." and the round stays Draft.
- **RND-3.4** (ambiguous) The published round's criteria, cases and links are exactly those saved before publishing.
- **RND-3.5** (adversarial) An edit racing a publish is either saved before publishing and included in the published round, or refused with 409. Of two simultaneous publish requests, exactly one succeeds and creates one build; the other gets 409.
- **RND-3.6** (adversarial) Publishing follows the [rules for every round action](#rules-for-every-round-action), including 405 for a GET, 409 for an Open or Closed round, and the rendering tests for build labels on the round page.

## RND-4 Review submitted results

For an Open or Closed round, the coordinator opens its results page. Which results count as submitted, and the result's fields, are defined in [RES](results.md); the fields below, and the outcome vocabulary Pass or Fail, are provisional until then.

- **RND-4.1** (happy) The results page lists each case with its linked criteria and current build, then each submitted result for that build with the tester's username, outcome, observation and submission time, newest first. A Closed round's results stay listed.
- **RND-4.2** (boundary) A case with no submitted result for its current build shows "No results for this build yet.", even if it has results for earlier builds.
- **RND-4.3** (ambiguous) After a case's current-build results, an "Earlier builds" list shows its results for earlier builds, each with its build label, never as results for the current build. A retest leaves those results unchanged.
- **RND-4.4** (ambiguous) Results that are not submitted never appear, and the page offers no way to change or delete a result.
- **RND-4.5** (adversarial) The results page renders all its user-written text, including tester-written observations and the round title in its page title, under the [rendering rule](#rules-for-every-round-action), with the rule's tests.
- **RND-4.6** (adversarial) The results page follows the [rules for every round action](#rules-for-every-round-action), including 409 for a Draft round.

## RND-5 Request a retest

While the round is Open, the coordinator can ask for selected cases to be tested again on a new build. Provisionally, testers then record new results against that build ([RES](results.md)).

While the round is Open, the round page has a "Request a retest" link directly under the "Builds" heading, before the first build; a Draft or Closed round's page has no such link. The "Request a retest" page has a "Test cases to retest" group with a checkbox for each of the round's cases, labelled with its title, in creation order, none selected; then a "Build label" field, a "Request retest" button and a "Back to round" link. Requesting opens the round page, which shows the RND-5.1 message once, directly under its heading, where only the label is user text. Invalid input shows the page again with the selected cases still selected and the entered label kept. Its checks run in this order after rules 1 to 4: both fields are checked, each on its own, so an invalid selection and an invalid label both get their message; then, once both are valid, the round's state is checked again (rule 4), followed by the build limit (RND-5.4), the selected cases again (RND-5.6) and the label's uniqueness (RND-5.3), in that order, against the round as it is at that moment; only the first refusal shows. The RND-5.2 selection message and the RND-5.6 message appear next to "Test cases to retest"; the RND-5.2 label message and the RND-5.3 and RND-5.4 messages appear next to "Build label".

- **RND-5.1** (happy) Selecting cases and entering a new build label shows "Retest requested for <count> test cases on build <label>.", or "1 test case" for one, counting distinct cases. The selected cases' current build becomes the new build; other cases keep theirs.
- **RND-5.2** (boundary) Selecting no case gets "Select at least one test case." A build label of 100 characters is accepted; an empty, invisible-only or 101-character label gets "Enter 1 to 100 characters."
- **RND-5.3** (failure) A label already used for a build in this round gets "This build label is already used in this round." Labels are compared case-sensitively after removing format characters (category Cf, such as U+200B) and then applying Unicode NFC normalisation.
- **RND-5.4** (boundary) A round's 10th build, counting the build named at publishing, is created; an 11th gets "This round has reached its limit of 10 builds."
- **RND-5.5** (ambiguous) A case can be retested more than once. Earlier builds stay listed with the cases they cover, and the round's criteria and cases stay unchanged.
- **RND-5.6** (adversarial) Submitting a case of another round or workspace, or one that does not exist, gets "Choose test cases from this round."
- **RND-5.7** (adversarial) Of two simultaneous retest requests with the same label, exactly one succeeds; the other gets the RND-5.3 message. A retest racing a close either completes before the close, or gets 409 after it.
- **RND-5.8** (adversarial) Requesting a retest follows the [rules for every round action](#rules-for-every-round-action), including 409 for a Draft or Closed round and the rendering tests for a build label in the success message.

## RND-6 Close a round

Closing ends testing and makes the round read-only. A closed round cannot be reopened.

While the round is Open, the round page ends, after the "Builds" section and before the "Coordinator home" link, with the paragraph "Closing makes this round read-only. It cannot be reopened." directly followed by a "Close round" button. Closing asks for no further confirmation and opens the round page, which shows "Round closed." once, directly under its heading. A Closed round's page shows the same title, "State: Closed", criteria, cases with their linked criteria and current build, and "Builds" section as an Open round's page, and has no "Edit round" link, no RND-2 controls, no publish form, no warning and no "Close round" button. The closing time is recorded but not shown.

- **RND-6.1** (happy) Closing an Open round shows "Round closed." Its round page shows the state "Closed", and its criteria, cases and builds stay visible there.
- **RND-6.2** (ambiguous) Closing needs no precondition: a round with untested cases can be closed. The close button is shown with "Closing makes this round read-only. It cannot be reopened."
- **RND-6.3** (boundary) Closing a Closed round gets 409, and no page or route returns a round to Open or Draft.
- **RND-6.4** (adversarial) Of two simultaneous close requests, exactly one succeeds; the other gets 409.
- **RND-6.5** (adversarial) Closing follows the [rules for every round action](#rules-for-every-round-action), including 405 for a GET and 409 for a Draft round.

## RND-7 Sample draft round in a new demo workspace

[ACC-2](accounts.md#acc-2-create-an-isolated-demo-workspace) creates a sample round with each new demo workspace, so peers can publish and test straight away. If it cannot be written, ACC-2.5 applies.

- **RND-7.1** (happy) A new demo workspace has exactly one round, "Sample round", in Draft, with 3 acceptance criteria and 4 test cases, each case linked to at least one criterion. Its text is fixed, synthetic and within the RND-2 field limits.
- **RND-7.2** (happy) The coordinator can publish the sample round straight away by entering only a build label, or edit it first like any Draft round.
- **RND-7.3** (boundary) The sample round counts toward the RND-1.4 limit, so 19 more rounds can be created.
- **RND-7.4** (adversarial) Each workspace's sample round is its own: editing, publishing or closing it changes no other workspace's sample round.

## RND-8 Draft test cases with AI

While the round is Draft, the coordinator can ask the AI service for a few draft test cases from selected acceptance criteria, review them beside those criteria, and start a normal new test case from one. Drafts are never saved. What is sent to the model, the reply it accepts and its limits are in the [test-drafting contract](../ai/test-drafting.md).

While Draft, the round page has a "Draft test cases with AI" link directly after the "Add test case" link; an Open or Closed round's page has none. The "Draft test cases with AI" page shows the paragraph "Select 1 to 5 acceptance criteria. Only their text is sent to the AI service. Suggestions are not saved; review each one before adding it.", then an "Acceptance criteria to draft from" group with a checkbox for each of the round's criteria, labelled with its text, in creation order, none selected, or "No acceptance criteria yet." when there are none; then a "Draft test cases" button, an "Add test case" link to the "New test case" page and a "Back to round" link. Drafting does not redirect: it shows the same page again, with status 200 whatever the drafting outcome (a storage failure still gets the 503 page), the selection kept, followed by a "Suggested test cases" heading. Under it, each draft shows its title as a subheading, then the labels "Steps", "Expected result" and "Covers acceptance criteria", each followed by that text, the covered criteria listed by their text in creation order, and a "Use this draft" button; or it shows an RND-8.4 message instead of drafts. Drafting's checks run in this order after rules 1 to 4: the selection, where a criterion not in this round gets the RND-8.8 message whatever the count, a repeated one counts once, and otherwise the count is checked (RND-8.3); then the case cap (RND-8.3); then, unless the [contract](../ai/test-drafting.md#limits) stops it first, one call to the AI service. Each RND-8.3 and RND-8.8 message appears next to "Acceptance criteria to draft from"; the RND-8.4 messages appear under the "Suggested test cases" heading.

"Use this draft" does not redirect either: it shows the "New test case" page of RND-2, with status 200, the paragraph "Pre-filled from an AI draft. Review it before adding it.", its fields holding the draft's title, steps and expected result and its covered criteria checked. As an exception to rule 5, it shows no message: it [cleans](../ai/test-drafting.md#cleaning) the posted text again and shows it, and checks only those of the round's criteria whose IDs were posted. Submitting it is the normal RND-2 add.

- **RND-8.1** (happy) While the round is Draft, its page links to "Draft test cases with AI". Selecting criteria and pressing "Draft test cases" shows the suggested test cases, each beside the criteria it covers, all of them among the selected ones. The round's criteria, cases and links are unchanged.
- **RND-8.2** (happy) "Use this draft" opens the pre-filled "New test case" page, and nothing is saved until the coordinator presses "Add test case", which saves the case, as edited, under every RND-2 rule.
- **RND-8.3** (boundary) Selecting 5 criteria drafts from exactly those 5. Selecting none or 6 gets "Select 1 to 5 acceptance criteria." A round with 30 test cases gets "This round has reached its limit of 30 test cases." Neither refusal contacts the AI service.
- **RND-8.4** (failure) When the AI service is unavailable, refuses, times out, has no quota left or already has a call in flight, the request is over the contract's input limit, or the service sends a reply the [contract](../ai/test-drafting.md#reply-schema) rejects, the page shows "Drafting is unavailable right now. You can still add test cases yourself." and no draft. A valid reply with no drafts, or a selection whose criteria are all empty once the contract cleans them, shows "No test cases were suggested for these criteria. You can still add test cases yourself." Either way the selection is kept, nothing is saved and the "Add test case" link still works.
- **RND-8.5** (adversarial) A reply with an extra field, a missing or wrongly typed field, too many drafts, text outside the RND-2 limits, a criterion label that was not sent, or that cannot be parsed safely is rejected whole, with the RND-8.4 unavailable message, even if some of its drafts are valid.
- **RND-8.6** (adversarial) Only the selected criteria's cleaned text is sent, and the drafts shown are cleaned, as the [contract](../ai/test-drafting.md#inputs-and-authorship) defines. Criterion text that tries to make the AI reveal other data, publish, close or change the round cannot change anything.
- **RND-8.7** (adversarial) Both drafting pages follow the [rules for every round action](#rules-for-every-round-action), including 409 for an Open or Closed round, 403 for a POST from another origin, so another site can neither start drafting nor pre-fill the form, and the rendering tests for criterion text and draft text in page content. In the "Use this draft" form, draft text is only attribute-escaped, and the pre-filled form holds exactly the cleaned draft text once the browser's CR LF line breaks are turned back into LF.
- **RND-8.8** (adversarial) A selection naming a criterion of another round or workspace, or one that does not exist, gets "Choose criteria from this round." and does not contact the AI service.
- **RND-8.9** (adversarial) On the pre-filled page, a posted criterion ID that is not an integer, is too large, belongs to another round or workspace, or does not exist checks no box and gives the same page as if it were not posted, and posted text containing hidden characters is shown cleaned.

Retired: RND-7.5 (covered by ACC-2.5).
