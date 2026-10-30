Deliver issue #16 in this repository, using the development workflow that this repository's AGENTS.md describes.

## Issue #16: Request a retest

**Spec:** new (RND)
**Owner:** zheng-jj
**Tier:** Standard

Done when the pull request that closes this issue is merged.

## Decisions the human has already made

No human is available during this run. Treat these as the human's answers:

1. **Scope:** RND-5 only, as specified in `workflow/specs/product/rounds.md`: the retest route and page, the form and a retest service. Retesting is only for Open rounds. Tester views and results (RES), results review (RND-4) and the sample round are not included.
2. **Page:** the retest form is its own page at the `/coordinator/rounds/<round>/retest/` route the technical spec lists, titled "Request a retest". An Open round's page has a "Request a retest" link directly under its "Builds" heading; a Draft or Closed round's page has none.
3. **Form fields:** `cases`, the round's test cases as checkboxes in creation order with the label "Test cases to retest", and `label`, the new build's label, validated exactly as the publish form's build label is.
4. **Checks:** the rules for every round action come first. Both fields are then validated independently. The write then runs under the round-row lock and checks, in this order: the round is still Open (otherwise 409), the build cap, the case IDs against the locked round, and label uniqueness. Only the first refusal is shown.
5. **Labels:** the comparison key stays as it is (format characters removed, then NFC, not NFKC), so compatibility look-alikes such as full-width letters count as distinct labels. Record this as an accepted residual.
6. **User text:** no label in exception messages or log records. The success message's label is rendered escaped and direction-isolated, like other user text.
7. The work is local only: no push, no pull request, no GitHub or web access. Commits on a local feature branch are allowed.
8. Do not write a session log or a usage report; the experiment records usage separately.

If the workflow calls for a human decision that these answers do not cover, choose the smallest option consistent with the issue and the spec, note the question and your choice in your final report, and continue without waiting.

## Environment

- The PostgreSQL test server is already running. Do not start, stop or remove Docker containers.
- Use the existing `.venv`. Do not install packages.

When the work is finished, end with a short report: what changed, the checks you ran and their results, and anything left open.
