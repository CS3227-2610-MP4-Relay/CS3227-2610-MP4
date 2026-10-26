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
