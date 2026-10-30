Deliver issue #13 in this repository, using the development workflow that this repository's AGENTS.md describes.

## Issue #13: Save and submit an outcome with observations

**Spec:** new (RES)
**Owner:** zheng-jj
**Tier:** Standard

Done when the pull request that closes this issue is merged.

## What the team has decided

No human is available during this run. These are the only decisions given. The specs' "Planned work" notes list what else must be settled before results are built.

1. **Scope:** RES-2 only. A Beta Tester records their own result for a test case's current build while its round is Open: an outcome, Pass or Fail, and an observation. They can save a draft, which they can replace, or submit a final result, which they cannot change. There is no result history page, coordinator review page or AI feedback.
2. **Route:** `/tester/rounds/<round>/cases/<case>/builds/<build>/result/`, with integer IDs, accepting GET and POST. On an Open round's tester page, each case has a "Record result" link to this page for the case's current build.
3. **The form:**
   - a field `outcome`, with the values `pass` and `fail`;
   - a field `observation`;
   - two submit buttons named `action`: `save`, labelled "Save draft", and `submit`, labelled "Submit".

   After a save or a submission, redirect back to the same page.
4. **What the page shows:**
   - once a draft is saved, "Status: Draft", with the saved values in the form;
   - once submitted, "Status: Submitted", with the outcome and observation as read-only text and no form.
5. **Rules:** an observation is optional for Pass and required for Fail, and at most 2,000 characters long. Invalid input shows the form again with status 200 and changes nothing.
6. **Privacy:** each tester has one private result per case and build, and sees and changes only their own.
7. **Refusals:**
   - a signed-out visitor is sent to sign-in;
   - a Test Coordinator gets 403;
   - a missing, Draft or other workspace's round, a case outside the round, or a build that doesn't cover the case gets 404;
   - a Closed round gets 409;
   - a build that is no longer the case's current build gets 409;
   - any POST after the result is submitted gets 409.
8. The work is local only: no push, no pull request, no GitHub or web access. Commits on a local feature branch are allowed.
9. Do not write a session log or a usage report; the experiment records usage separately.

Decide anything else the workflow needs a human for yourself. That includes concurrency, failure handling, the wording of messages and how retests affect saved results. Choose the smallest option consistent with the issue and the specs, record the question and your choice in your final report, and continue without waiting.

## Environment

- The PostgreSQL test server is already running. Do not start, stop or remove Docker containers.
- Use the existing `.venv`. Do not install packages. Browser tests use the Chromium that Playwright already has.

When the work is finished, end with a short report: what changed, the checks you ran and their results, and anything left open.
