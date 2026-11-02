# 124: Truthful public home

Goal: describe the built testing workflow on the public home under [PLT-1.1](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification).

Tier: Standard (exact acceptance copy changes); integrated High review. One requirement changed; <=400 runtime lines, estimate 2–8. Why: the coming-soon statement is stale. Exact replacement copy lives only in PLT-1.1. Existing public actions/methods and signed-in redirect remain unchanged.

Checkpoints:
1. Specs/plan recorded with 123 before source edits.
2. `fix: Describe available workflows on home`: `src/relay/templates/home.html`, `src/relay/tests/test_pages.py` and existing public-home browser coverage in `src/e2e/test_presentation.py`. Red: assert replacement copy and absence of stale message. Green: public GET/HEAD, allowed actions/methods and role redirect regression checks, browser visible copy. Update any existing smoke-test fixture expectations for PLT-1.1 if needed; no deployment change.

Next: wait for coordinator's assignment after 123; run focused tests then yield for commit. No open product decisions.
