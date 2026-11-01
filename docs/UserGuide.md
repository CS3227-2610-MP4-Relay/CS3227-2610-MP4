# User Guide

Relay runs locally only; no public hosted app is available yet. Start the application using the [Developer Guide](DeveloperGuide.md#run-locally), then open <http://127.0.0.1:8000/>.

## Start page

The page is headed **Relay** and says:

> A beta-testing portal for small software teams.
>
> Testing workflows are coming soon.

It has two actions: the **Sign in** link and the **Create a demo workspace** button. If you are already signed in, opening the start page takes you to your own home page.

## Accounts

Each account has one role, **Test Coordinator** or **Beta Tester**, in one workspace. Accounts come only from demo workspaces: there is no registration, password reset or way to add accounts.

## Create a demo workspace

1. While signed out, choose **Create a demo workspace** on the start page.
2. The **Your demo workspace** page shows `Workspace:` with the new workspace's name, and a table with the **Role**, **Username** and **Password** of one Test Coordinator and two Beta Testers. It says "Save these passwords now. They will not be shown again."
3. Save the usernames and passwords, then choose **Sign in** to sign in with any of them.

Each new workspace starts with one round, **Sample round**, in the **Draft** state. It has 3 acceptance criteria and 4 test cases about an example to-do app, and each test case is linked to at least one criterion. Its Test Coordinator can [publish](#publish-a-round) it straight away by entering only a build label, or change it first like any Draft round. It counts toward the workspace's [limit of 20 rounds](#titles-and-limits).

Creating a workspace does not sign you in. Each workspace is separate: its accounts never see another workspace's records. Resubmitting the page, which your browser asks about first, creates another new workspace rather than showing the same passwords again, and the browser's back button may still show the earlier page. While you are signed in, choosing **Create a demo workspace** takes you to your own home page and creates nothing.

If creation fails, the page says "Relay is temporarily unavailable. Try again later." and nothing is created.

Each network address can create up to 10 workspaces an hour, and Relay up to 200 a day in total. After that, the page says "Too many demo workspaces have been created recently. Try again later." and nothing is created.

## Sign in

1. Choose **Sign in** on the start page, or open `/sign-in/`.
2. Enter your **Username** and **Password**, then choose **Sign in**.

A Test Coordinator lands on **Coordinator home** and a Beta Tester on **Tester home**. Each home page shows `Username:` and `Workspace:` with your username and workspace name.

If the username or password is wrong, or a field is blank, the page shows "Username or password is incorrect." and does not say which field was wrong. You are not signed in; if you were already signed in, you stay signed in as before.

After 30 failed sign-ins from one network address within 15 minutes, the sign-in page says "Too many sign-in attempts. Try again later." and does not sign anyone in from that address, even with the right password, until 15 minutes after the first of those failures. Successful sign-ins do not add to this count and do not reset it.

Opening a home page while signed out takes you to the sign-in page. Opening the other role's home page shows "You do not have access to this page."; you stay signed in.

## Sign out

Choose **Sign out** near the top of your home page, above the round list. The sign-in page shows "You have signed out."

You are also signed out 8 hours after signing in, whatever you do in between; opening a home page after that takes you to the sign-in page.

## Find your way around

Creation links such as **New round**, **Add test case** and **Record result** have a filled primary style. Edit and review links, and links to AI pages, have an outlined secondary style; **Delete criterion**, **Delete test case** and **Close round** have a red outline. **Save draft** and **Sign out** use the secondary style, while **Submit** is primary. Ordinary navigation links are underlined.

Round, result, history, editing and AI pages have **Coordinator home** or **Tester home** near the top, with **Back to round** or **Back to result** where applicable. Return links also remain at the bottom.

Round pages, coordinator results and **My results** have **Contents** links to their sections or records. On a wide desktop, these links appear in a sidebar. On a narrower screen, **Contents** starts collapsed above the details; choose it to show the links.

Choose a case title or saved-result heading to expand or collapse its details. The first record starts expanded and the others collapsed; several can stay open together. Following a record's **Contents** link opens its details and brings them into view. A direct link to that record does the same. Reloading restores the starting layout, unless the address links directly to a record. You can use Tab to focus a heading, then Enter or Space to toggle it.

## View available tests

1. Sign in as a **Beta Tester**. On **Tester home**, **Available tests** lists your workspace's Open and Closed rounds, newest first. Each title is a link followed by "(Open)" or "(Closed)". If there are none, it says "No tests available."
2. Choose a round title. The page shows "State: Open" or "State: Closed" and **Test cases**. Each case's summary shows its title and **Current build**; expand it for **Steps**, **Expected result** and **Linked acceptance criteria**.
3. Test the software outside Relay using those instructions and the named build. If the coordinator requests a retest, reload the page: only the selected cases change to the new **Current build**; other cases keep their previous build.
4. Choose **Tester home** to return to the list, or return there to **Sign out**.

Both Beta Testers in a workspace see the same rounds. Draft rounds stay hidden. An Open round has a **Record result** link inside each expanded case. A Closed round remains available as read-only reference; after the coordinator closes it, reload to see "State: Closed" and "(Closed)" in the list, with the result-entry links removed.

If reading tests fails, the page says "Relay is temporarily unavailable. Try again later." Opening a Draft, missing or another workspace's round shows "Page not found."

## Save and submit a result

1. In an Open round, expand the case you tested and choose **Record result**. The **Record result** page shows **Test case** and **Current build**.
2. Choose **Pass** or **Fail** under **Outcome** and enter your **Observation**. Fail requires an observation; Pass allows it to be empty.
3. Choose **Save draft** to keep working later. The page shows "Status: Draft" and your saved fields; they remain when you reload or sign in again. Each tester has a separate private draft for each case and build.
4. Choose **Submit** when ready. You may submit directly or after saving a draft. The page shows "Status: Submitted", your outcome and your observation as read-only text. An empty observation says "No observation." Submission is final; another attempt to save or submit it says "This result has already been submitted."
5. Choose **Back to round** to return to the case instructions.

Both buttons apply the same checks. A missing outcome says "Choose Pass or Fail." An empty or invisible-only Fail observation says "Enter an observation for Fail." Observations allow at most 2000 characters after surrounding spaces and line breaks are removed; a line break counts as one character. A longer observation says "Enter at most 2000 characters." A nonempty invisible-only Pass observation says "Enter an observation with a visible character." Null characters and hidden text-direction characters get the same messages as [round text fields](#criteria-and-test-case-limits). Invalid input leaves your previously saved result unchanged.

Results belong to the build shown when you opened the entry page. After the coordinator requests a retest, reload the round and check the selected case's **Current build**. Test the fix outside Relay on that build, then choose **Record result**: the new build starts with empty **Outcome** and **Observation** fields. Choose **Pass** or **Fail** and **Submit** a separate result; earlier submissions remain available in [My results](#review-my-results). Cases omitted from the retest keep their existing build and result entry. If the build changes before you save or submit, the page says "This build is no longer current. Reload the round to record a result." Return to the round, reload, and choose **Record result** for the new build.

You can view your submitted result through **Record result** while its build is current and the round is Open. Once the round closes, an entry page says "This action is not available while the round is Closed." and saves nothing. The round's instructions remain available. If storage fails, the page says "Relay is temporarily unavailable. Try again later." and no part of the result change is saved.

## Observation feedback

1. On **Record result**, choose **Save draft**, then **Observation feedback**. The link is available for your saved draft while its round is Open and its build is current.
2. Review **Saved observation**, **Test case**, **Steps**, **Expected result**, **Linked acceptance criteria** and **Current build**. The page says "AI receives your saved observation, this test case and its linked acceptance criteria. Suggestions may be wrong. Review them and edit your result yourself. Unsaved edits are not included."
3. Choose **Suggest missing details** to request questions. Any suggestions appear under **Questions to consider**, beside the original source. They do not change your outcome, observation or submission.
4. Choose **Back to result**, edit **Observation** yourself and choose **Save draft** or **Submit** when ready.

An empty reply says "No missing details were suggested. You can still edit your result yourself." If the source is too long, the page says "This observation and test case are too long for feedback. You can still edit your result yourself." If feedback is unavailable, it says "Feedback is unavailable right now. You can still edit your result yourself." You can still choose **Back to result** and continue manually.

Questions are not saved. Opening the feedback page again clears them; resubmitting its request asks for new feedback. If your saved source changes during a request, the page says "Your saved draft or test case changed. Reload before requesting feedback." A missing draft says "Save a draft before requesting feedback." Submission, a newer build or a closed round prevents feedback with the same messages described under [Save and submit a result](#save-and-submit-a-result).

## Review my results

1. Open an Open or Closed round from **Tester home**, then choose **My results**.
2. The **My results** page shows the **Round** and its state, followed by your saved drafts and submissions for current and earlier builds. Each summary shows **Test case** with the case title, the original **Build**, **Outcome** and "Status: Draft" or "Status: Submitted". Expand an entry for **Linked acceptance criteria**, **Observation** and, for submissions, **Submitted at** in UTC. An empty observation says "No observation."; with no saved results, the page says "No results yet."
3. Choose **Back to round** to return to the instructions.

Only your own results appear. This page is read-only, including drafts. Reload to see later saves or submissions; retesting and closure retain earlier results with their original build and case details.

## Test rounds

Only a Test Coordinator can prepare, publish, review, retest and close test rounds. A new round is in the **Draft** state; [publishing](#publish-a-round) it makes it **Open**, and [closing](#close-a-round) it makes it **Closed**. Beta Testers [view available tests](#view-available-tests) from their own home page.

**Coordinator home** has a **Rounds** heading with a **New round** link. Below it, each round in your workspace is listed, newest first, as a link to its round page followed by its state, such as "(Draft)". A new demo workspace starts with its [sample round](#create-a-demo-workspace), so its list is not empty; "No rounds yet." appears only for a workspace with no rounds.

Whenever creating, publishing, retesting or closing a round, or saving or deleting anything in it, fails, the page says "Relay is temporarily unavailable. Try again later." and nothing changes.

### Create a round

1. On **Coordinator home**, choose **New round**.
2. Enter a **Title**, then choose **Create round**.

The round page opens. It shows the title as its heading, "State: Draft", an **Edit round** link, the round's [acceptance criteria and test cases](#acceptance-criteria-and-test-cases), a **Build label** field with a **Publish round** button, and a **Coordinator home** link.

### Change a round's title

1. On the round page, choose **Edit round**.
2. Change the **Title**, then choose **Save**.

The round page shows the new title.

### Titles and limits

A title has 1 to 120 characters; spaces or line breaks at either end are removed. An empty title, a title of only spaces or invisible characters, or a longer one gets "Enter 1 to 120 characters." A title containing a null character gets "Null characters are not allowed." A title containing a hidden character that changes text direction gets "Hidden text-direction characters are not allowed." Letters of any language, accents and emoji are fine.

A workspace can have up to 20 rounds, including the sample round of a new demo workspace. Creating a 21st gets "This workspace has reached its limit of 20 rounds." Nothing deletes a round.

### Acceptance criteria and test cases

The round page has an **Acceptance criteria** heading, listing each criterion's text, and a **Test cases** heading, where you can expand each case to read **Steps**, **Expected result** and **Linked acceptance criteria** with that text. Both are listed in the order they were added. With none, they say "No acceptance criteria yet." and "No test cases yet."

You can add, edit and delete them only while the round is Draft.

To add or edit a criterion:

1. On the round page, choose **Add acceptance criterion**, or **Edit criterion** next to a criterion.
2. Enter the **Text**, then choose **Add acceptance criterion** or **Save**.

To add or edit a test case:

1. On the round page, choose **Add test case**, or expand a case and choose **Edit test case**.
2. Enter the **Title**, **Steps** and **Expected result**, tick one or more of the round's criteria under **Linked acceptance criteria**, then choose **Add test case** or **Save**.

Saving opens the round page. Each of these pages has a **Back to round** link.

To delete, expand a case and choose **Delete test case**, or choose **Delete criterion** next to a criterion; there is no confirmation. Deleting a case keeps its criteria. A criterion that a case links to cannot be deleted: the round page shows "This criterion is linked to a test case. Unlink it first." under it, so edit those cases first.

### Criteria and test case limits

Criterion text has 1 to 500 characters; a case's title has 1 to 120, its steps 1 to 2000 and its expected result 1 to 1000. Spaces or line breaks at either end are removed, and a line break counts as one character. A field that is empty, holds only spaces or invisible characters, or is too long gets "Enter 1 to N characters." next to it, with N its maximum, such as "Enter 1 to 500 characters." for criterion text; a null character gets "Null characters are not allowed." and a hidden character that changes text direction gets "Hidden text-direction characters are not allowed."

A case with no linked criterion gets "Link at least one acceptance criterion." If a criterion you ticked was deleted meanwhile, the form says "Choose criteria from this round."

A round can have up to 20 acceptance criteria and 30 test cases. Adding a 21st criterion gets "This round has reached its limit of 20 acceptance criteria." and a 31st case "This round has reached its limit of 30 test cases."

### Publish a round

While a round is Draft, its round page ends with a **Build label** field and a **Publish round** button. The build label names the version of the software under test, such as "1.4.0-beta".

1. On the round page, enter a **Build label**.
2. Choose **Publish round**.

The round page shows "Round published." and "State: Open". An Open round cannot return to Draft.

A build label has 1 to 100 characters; spaces or line breaks at either end are removed. An empty label, a label of only spaces or invisible characters, or a longer one gets "Enter 1 to 100 characters." next to the field, a label containing a null character gets "Null characters are not allowed.", and a label containing a hidden character that changes text direction gets "Hidden text-direction characters are not allowed." A round with no test cases gets "Add at least one test case before publishing." After any of these messages the round stays Draft, with your label still in the field.

### An Open round

An Open round's page shows "State: Open" and the criteria and cases exactly as they were when it was published. Its title, criteria and cases can no longer be changed, so the page has no **Edit round** link, no add, edit or delete links and buttons, and no **Publish round** button. You can still [review results](#review-results), [request a retest](#request-a-retest) or [close](#close-a-round) the round.

Each case's summary shows **Current build** with the label of the build the case is tested on. After the test cases, a **Builds** heading lists the round's builds, oldest first: each build's label, then **Covered test cases** with the titles of the cases it covers. A newly published round has one build, covering every case; each [retest](#request-a-retest) adds another.

### Request a retest

A retest asks for some of an Open round's cases to be tested again on a new build. Only an Open round can be retested: while a round is Open, its round page has a **Request a retest** link directly under the **Builds** heading.

1. On the Open round's page, choose **Request a retest**.
2. Under **Test cases to retest**, tick the cases to test again. No case is ticked at first.
3. Enter a **Build label** for the new build, then choose **Request retest**.

The round page shows, for example, "Retest requested for 2 test cases on build 1.4.1-beta.", or "Retest requested for 1 test case on build 1.4.1-beta." for one case. The cases you ticked now show the new build as their **Current build**, and the other cases keep theirs. The new build is added to the end of the **Builds** list with the cases it covers; earlier builds stay listed with theirs, and the round's criteria and cases do not change. A case can be retested again later on another build. The **Request a retest** page also has a **Back to round** link.

If something is wrong, the page shows again with your ticks and label kept:

- With no case ticked: "Select at least one test case." next to **Test cases to retest**.
- The build label follows the same rules as when publishing: "Enter 1 to 100 characters.", "Null characters are not allowed." or "Hidden text-direction characters are not allowed." next to **Build label**.
- A label already used for a build of this round, including the one named at publishing: "This build label is already used in this round." next to **Build label**. Upper and lower case count as different, but invisible formatting characters such as zero-width spaces are ignored, and the same accented letter typed in different ways counts as the same.
- A round can have up to 10 builds, counting the one named at publishing. Requesting an 11th gets "This round has reached its limit of 10 builds." next to **Build label**.
- A ticked case that is not in this round gets "Choose test cases from this round." next to **Test cases to retest**.

If the round was closed in the meantime, the page says "This action is not available while the round is Closed." and no build is added.

### Close a round

Closing ends testing on an Open round and makes it read-only. While a round is Open, its round page ends with "Closing makes this round read-only. It cannot be reopened." and a **Close round** button. A round can be closed at any time while it is Open, even if some cases have not been tested.

1. On the Open round's page, choose **Close round**. There is no further confirmation.

The round page shows "Round closed." and "State: Closed". A Closed round cannot be reopened or returned to Draft.

A Closed round's page still shows its criteria, its cases with their linked criteria and **Current build**, and the **Builds** list. It has no links or buttons for changing the round, no **Request a retest** link and no **Close round** button, but you can still [review results](#review-results).

### Review results

While a round is Open or Closed, its round page has a **Review results** link directly under its state. A Draft round has no results and no link.

1. On the round page, choose **Review results**.
2. The page is headed "Results: " followed by the round's title, then "State: Open" or "State: Closed". Each test case follows in the order it was added. Its summary shows the title, **Current build** and the testers and outcomes for that build, or "No results for this build yet." Expand it for **Linked acceptance criteria**, **Results for this build** and any **Earlier builds**.
3. Each submitted result shows "Tester:" with the Beta Tester's username, "Outcome: Pass" or "Outcome: Fail", "Observation:" with the observation, or "Observation: No observation." when it is empty, and "Submitted at:" with the time in UTC. The newest submission comes first. A case with no submitted result for its current build says "No results for this build yet."
4. Choose **Back to round** to return to the round page.

Only submitted results appear; a Beta Tester's saved draft stays private to them. After a [retest](#request-a-retest), a retested case's earlier results move under **Earlier builds**, newest build first, each starting with "Build:" and its build label, while its new build starts with "No results for this build yet." until someone submits. Results stay listed after the round is [closed](#close-a-round). The page is read-only: it cannot record, change or delete a result. Reload it to see results submitted since you opened it. If reading results fails, the page says "Relay is temporarily unavailable. Try again later."

### Draft test cases with AI

Use AI to draft suggestions from selected acceptance criteria, then review each one before adding it. You can also add test cases yourself with **Add test case**.

While a round is Draft, its page has a **Draft test cases with AI** link directly after **Add test case**. The drafting page says "Select 1 to 5 acceptance criteria. The selected criteria are sent to the SoC AI service to suggest test cases. Suggestions are not saved; review each one before adding it." It lists the round's criteria under **Acceptance criteria to draft from**, with a **Draft test cases** button, an **Add test case** link and a **Back to round** link.

Tick one to five criteria and choose **Draft test cases**. When suggestions are returned, **Suggested test cases** shows each title, **Steps**, **Expected result** and **Covers acceptance criteria**. Review these beside the criteria; nothing is saved by drafting.

Choose **Use this draft** to open **New test case** with the suggested fields and covered criteria filled in. The page says "Pre-filled from an AI draft. Review it before adding it." Edit the fields and links as needed, then choose **Add test case** to save under the normal [test case limits](#criteria-and-test-case-limits).

If the service is unavailable or its reply cannot be used, the page says "Drafting is unavailable right now. You can still add test cases yourself." If it returns no drafts, or every ticked criterion is blank once hidden characters are removed, it says "No test cases were suggested for these criteria. You can still add test cases yourself."

With no criterion ticked, or more than five, the page says "Select 1 to 5 acceptance criteria." A ticked criterion that is no longer in the round, for example because it was deleted meanwhile, gets "Choose criteria from this round." A round with 30 test cases says "This round has reached its limit of 30 test cases." In every case your ticks are kept, the round, its criteria and its cases stay unchanged, and **Add test case** still works.
