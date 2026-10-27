# User Guide

Relay runs locally only; no public hosted app is available yet. Start the application using the [Developer Guide](DeveloperGuide.md#run-locally), then open <http://127.0.0.1:8000/>.

## Start page

The page is headed **Relay** and says:

> A beta-testing portal for small software teams.
>
> Testing workflows are coming soon.

Its only action is the **Sign in** link.

## Accounts

Each account has one role, **Test Coordinator** or **Beta Tester**, in one workspace. You cannot get an account through Relay yet: there is no registration, and demo workspaces are planned but not built. For local testing, a developer creates accounts as described in the [Developer Guide](DeveloperGuide.md#create-accounts-for-manual-testing).

## Sign in

1. Choose **Sign in** on the start page, or open `/sign-in/`.
2. Enter your **Username** and **Password**, then choose **Sign in**.

A Test Coordinator lands on **Coordinator home** and a Beta Tester on **Tester home**. Each home page shows `Username:` and `Workspace:` with your username and workspace name.

If the username or password is wrong, or a field is blank, the page shows "Username or password is incorrect." and does not say which field was wrong. You are not signed in; if you were already signed in, you stay signed in as before.

Opening a home page while signed out takes you to the sign-in page. Opening the other role's home page shows "You do not have access to this page."; you stay signed in.

## Sign out

Choose **Sign out** on your home page. The sign-in page shows "You have signed out."

You are also signed out 8 hours after signing in, whatever you do in between; opening a home page after that takes you to the sign-in page.
