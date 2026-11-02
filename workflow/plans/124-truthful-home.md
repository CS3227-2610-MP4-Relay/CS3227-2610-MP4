# 124: Truthful public home

Goal: describe the built testing workflow on the public home under [PLT-1.1](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification).

Tier: Standard (exact acceptance copy changes); integrated High review. One requirement changed; <=400 runtime lines, estimate 2–8. Why: the coming-soon statement is stale. Exact replacement copy lives only in PLT-1.1. Existing public actions/methods and signed-in redirect remain unchanged.

Checkpoints:
1. Specs/plan recorded with 123 before source edits.
2. `fix: Describe available workflows on home`: `src/relay/templates/home.html`, `src/relay/tests/test_pages.py` and existing public-home browser coverage in `src/e2e/test_presentation.py`. Red: assert replacement copy and absence of stale message. Green: public GET/HEAD, allowed actions/methods and role redirect regression checks, browser visible copy. Update any existing smoke-test fixture expectations for PLT-1.1 if needed; no deployment change.

Evidence: base `048eb5e3c388c38e1f4fdc97ab6cce6bd85dcb55`, private snapshot `relay-124-builder-home.json`. Before the template edit, updated landing-page and 320/1440 public-browser expectations failed for the missing built-workflow copy (3 failures). After editing one paragraph, `pytest src/relay/tests/test_pages.py src/accounts/tests/test_demo_views.py src/e2e/test_presentation.py::test_public_actions_are_compact_grouped_native_controls` passed 31 in 6.46s, retaining method/action/HEAD/redirect checks. Changed Python lint/format passed. Repository source/workflow-script scan found no other stale copy fixture expectations. Runtime diff: 2 lines. Public screenshots remain temporary outside the repository.

Review mapping: PLT-1.1 → `test_public_landing_page` in [page tests](../../src/relay/tests/test_pages.py), `test_public_actions_are_compact_grouped_native_controls` in [browser presentation tests](../../src/e2e/test_presentation.py), and `test_signed_in_user_is_sent_home_and_creates_nothing` in [demo tests](../../src/accounts/tests/test_demo_views.py). Existing page method tests retain PLT-1.2 coverage.

Next: User Guide copy aligned with built home; coordinator commits combined docs, runs full integrated checks, then independent review and delivery. Runtime 124: 2 lines. No open product decisions.
