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

Creating a workspace does not sign you in. Each workspace is separate: its accounts never see another workspace's records. Resubmitting the page, which your browser asks about first, creates another new workspace rather than showing the same passwords again, and the browser's back button may still show the earlier page. While you are signed in, choosing **Create a demo workspace** takes you to your own home page and creates nothing.

If creation fails, the page says "Relay is temporarily unavailable. Try again later." and nothing is created.

## Sign in

1. Choose **Sign in** on the start page, or open `/sign-in/`.
2. Enter your **Username** and **Password**, then choose **Sign in**.

A Test Coordinator lands on **Coordinator home** and a Beta Tester on **Tester home**. Each home page shows `Username:` and `Workspace:` with your username and workspace name.

If the username or password is wrong, or a field is blank, the page shows "Username or password is incorrect." and does not say which field was wrong. You are not signed in; if you were already signed in, you stay signed in as before.

Opening a home page while signed out takes you to the sign-in page. Opening the other role's home page shows "You do not have access to this page."; you stay signed in.

## Sign out

Choose **Sign out** on your home page. The sign-in page shows "You have signed out."

You are also signed out 8 hours after signing in, whatever you do in between; opening a home page after that takes you to the sign-in page.

## Test rounds

Only a Test Coordinator can prepare, publish and close test rounds. A new round is in the **Draft** state; [publishing](#publish-a-round) it makes it **Open**, and [closing](#close-a-round) it makes it **Closed**. Beta Testers do not see rounds yet.

**Coordinator home** has a **Rounds** heading with a **New round** link. Below it, each round in your workspace is listed, newest first, as a link to its round page followed by its state, such as "(Draft)". With no rounds, it says "No rounds yet."

Whenever creating, publishing or closing a round, or saving or deleting anything in it, fails, the page says "Relay is temporarily unavailable. Try again later." and nothing changes.

### Create a round

1. On **Coordinator home**, choose **New round**.
2. Enter a **Title**, then choose **Create round**.

The round page opens. It shows the title as its heading, "State: Draft", an **Edit round** link, the round's [acceptance criteria and test cases](#acceptance-criteria-and-test-cases), a **Build label** field with a **Publish round** button, and a **Coordinator home** link.

### Change a round's title

1. On the round page, choose **Edit round**.
2. Change the **Title**, then choose **Save**.

The round page shows the new title.

### Titles and limits

A title has 1 to 120 characters; spaces or line breaks at either end are removed. An empty title, a title of only spaces or invisible characters, or a longer one gets "Enter 1 to 120 characters." A title containing a null character gets "Null characters are not allowed."

A workspace can have up to 20 rounds. Creating a 21st gets "This workspace has reached its limit of 20 rounds." Nothing deletes a round.

### Acceptance criteria and test cases

The round page has an **Acceptance criteria** heading, listing each criterion's text, and a **Test cases** heading, where each case shows its title, then **Steps**, **Expected result** and **Linked acceptance criteria** with that text. Both are listed in the order they were added. With none, they say "No acceptance criteria yet." and "No test cases yet."

You can add, edit and delete them only while the round is Draft.

To add or edit a criterion:

1. On the round page, choose **Add acceptance criterion**, or **Edit criterion** next to a criterion.
2. Enter the **Text**, then choose **Add acceptance criterion** or **Save**.

To add or edit a test case:

1. On the round page, choose **Add test case**, or **Edit test case** under a case.
2. Enter the **Title**, **Steps** and **Expected result**, tick one or more of the round's criteria under **Linked acceptance criteria**, then choose **Add test case** or **Save**.

Saving opens the round page. Each of these pages has a **Back to round** link.

To delete, choose **Delete test case** under a case or **Delete criterion** next to a criterion; there is no confirmation. Deleting a case keeps its criteria. A criterion that a case links to cannot be deleted: the round page shows "This criterion is linked to a test case. Unlink it first." under it, so edit those cases first.

### Criteria and test case limits

Criterion text has 1 to 500 characters; a case's title has 1 to 120, its steps 1 to 2000 and its expected result 1 to 1000. Spaces or line breaks at either end are removed, and a line break counts as one character. A field that is empty, holds only spaces or invisible characters, or is too long gets "Enter 1 to N characters." next to it, with N its maximum, such as "Enter 1 to 500 characters." for criterion text; a null character gets "Null characters are not allowed."

A case with no linked criterion gets "Link at least one acceptance criterion." If a criterion you ticked was deleted meanwhile, the form says "Choose criteria from this round."

A round can have up to 20 acceptance criteria and 30 test cases. Adding a 21st criterion gets "This round has reached its limit of 20 acceptance criteria." and a 31st case "This round has reached its limit of 30 test cases."

### Publish a round

While a round is Draft, its round page ends with a **Build label** field and a **Publish round** button. The build label names the version of the software under test, such as "1.4.0-beta".

1. On the round page, enter a **Build label**.
2. Choose **Publish round**.

The round page shows "Round published." and "State: Open". An Open round cannot return to Draft.

A build label has 1 to 100 characters; spaces or line breaks at either end are removed. An empty label, a label of only spaces or invisible characters, or a longer one gets "Enter 1 to 100 characters." next to the field, and a label containing a null character gets "Null characters are not allowed." A round with no test cases gets "Add at least one test case before publishing." After any of these messages the round stays Draft, with your label still in the field.

### An Open round

An Open round's page shows "State: Open" and the criteria and cases exactly as they were when it was published. Its title, criteria and cases can no longer be changed, so the page has no **Edit round** link, no add, edit or delete links and buttons, and no **Publish round** button. The only action left is to [close](#close-a-round) the round.

Under each case's linked criteria, **Current build** shows the label of the build the case is tested on. After the test cases, a **Builds** heading lists the round's builds, oldest first: each build's label, then **Covered test cases** with the titles of the cases it covers. A newly published round has one build, covering every case.

### Close a round

Closing ends testing on an Open round and makes it read-only. While a round is Open, its round page ends with "Closing makes this round read-only. It cannot be reopened." and a **Close round** button. A round can be closed at any time, even if some cases have not been tested.

1. On the Open round's page, choose **Close round**. There is no further confirmation.

The round page shows "Round closed." and "State: Closed". A Closed round cannot be reopened or returned to Draft.

A Closed round's page still shows its criteria, its cases with their linked criteria and **Current build**, and the **Builds** list. It has no links or buttons for changing the round, and no **Close round** button.
