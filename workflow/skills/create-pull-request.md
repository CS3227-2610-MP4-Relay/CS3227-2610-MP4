# create-pull-request

Prepares a GitHub pull request for a finished slice when requested.

**Input:** Slice branch or local candidate, optional issue, plan, agent handoffs and actual checks.

1. Inspect the candidate against the intended base and preserve unrelated edits. An issue, a clean tree and new commits are not prerequisites for preparing review text. Only change Git state within authorization. If the base changes, integrate only as authorized, check affected behaviour and run the [slice tier's required checks](slice.md) on the final integrated candidate. Refresh review after conflict resolutions or other substantive changes; reclassify if a Fast lane change affects behaviour, acceptance criteria or security controls.
2. For Standard/High, check that verifier and any required security-reviewer covered this exact candidate (commit range or dirty-tree manifest), apart from summary-only changes. For Fast lane, require targeted check evidence and human diff review; verifier coverage and full verification are not required. If evidence is stale, follow the slice skill's freeze, verify and repair steps. Record pending human review honestly and do not claim a draft with missing checks or review is ready to merge.
3. Fill in `.github/pull_request_template.md`. Map criteria to tests/manual checks and actual results; give tier, reviewed candidate, specialist range or why it was unnecessary, usage summary, deviations and unresolved findings. Include check results when preparing local text without GitHub CI. Leave human checkboxes unticked.
4. Push or create the PR only when the human has authorized those actions; existing explicit session authorization counts. Otherwise provide reviewable text and exact commands. Never merge or release on a claim of implicit human approval.

**Done when:** The authorized PR URL, or ready-to-paste text and remaining actions, is reported honestly with check/review limits.
