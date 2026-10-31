Deliver issue #68 in this repository, using the development workflow that this repository's AGENTS.md describes.

## Issue #68: Refuse hidden text-direction characters in round text

**Spec:** RND rules for every round action (rule 5) and the rendering rule
**Owner:** zheng-jj
**Tier:** Standard

Raised in review of #51; the human chose on 2026-10-27 to refuse invisible text-direction control characters in round text at input rather than block all non-ASCII text.

Done when the pull request that closes this issue is merged.

## Decisions the human has already made

No human is available during this run. Treat these as the human's answers:

1. Refuse only the text-direction embedding, override and isolate characters: U+202A to U+202E and U+2066 to U+2069. Allow the direction marks LRM (U+200E), RLM (U+200F) and ALM (U+061C).
2. Other invisible characters, such as zero-width spaces and joiners, are not refused in this slice. Record them as a residual, to be handled with the AI input rules (#22).
3. Look-alike labels that the allowed direction marks can still produce are accepted as a residual.
4. The work is local only: no push, no pull request, no GitHub or web access. Commits on a local feature branch are allowed.
5. Do not write a session log or a usage report; the experiment records usage separately.

If the workflow calls for a human decision that these answers do not cover, choose the smallest option consistent with the issue, note the question and your choice in your final report, and continue without waiting.

## Environment

- The PostgreSQL test server is already running. Do not start, stop or remove Docker containers.
- Use the existing `.venv`. Do not install packages.

When the work is finished, end with a short report: what changed, the checks you ran and their results, and anything left open.
