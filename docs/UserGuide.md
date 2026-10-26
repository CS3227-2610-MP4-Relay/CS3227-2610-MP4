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

Only a Test Coordinator can prepare test rounds. A round starts in the **Draft** state; later states are **Open** and **Closed**. Beta Testers do not see rounds yet.

**Coordinator home** has a **Rounds** heading with a **New round** link. Below it, each round in your workspace is listed, newest first, as a link to its round page followed by its state, such as "(Draft)". With no rounds, it says "No rounds yet."

### Create a round

1. On **Coordinator home**, choose **New round**.
2. Enter a **Title**, then choose **Create round**.

The round page opens. It shows the title as its heading, "State: Draft", an **Edit round** link and a **Coordinator home** link.

### Change a round's title

1. On the round page, choose **Edit round**.
2. Change the **Title**, then choose **Save**.

The round page shows the new title. You can change the title only while the round is Draft; otherwise the page says "This action is not available while the round is Open." (or "Closed.").

### Titles and limits

A title has 1 to 120 characters; spaces at either end are removed. An empty title, a title of only spaces or invisible characters, or a longer one gets "Enter 1 to 120 characters." A title containing a null character gets "Null characters are not allowed."

A workspace can have up to 20 rounds. Creating a 21st gets "This workspace has reached its limit of 20 rounds." Nothing deletes a round.

If saving fails, the page says "Relay is temporarily unavailable. Try again later." and nothing changes.
