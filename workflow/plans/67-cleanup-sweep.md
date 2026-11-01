# Slice 67: cleanup sweep

Goal: record #67's cleanup sweep and correct stale text.

## Sweep and slices

Requested by the human (zheng-jj) on 2026-11-01: "do that" (run #67, starting with a read-only sweep to scope small cleanup PRs), then "mark prs ready for review after u are done". Three read-only agents swept `main` at `045c33c`, one per area: `rounds` and `ai`; accounts, settings, release and workflow scripts; tests and guides. They found no authorization or workspace-isolation defect beyond the one listed below. Every checkable criterion has a marked test except PLT-2.6, and the User Guide matches the product.

Behaviour-preserving slices, each through the [slice workflow](../skills/slice.md):

| Slice | Tier | Scope |
| --- | --- | --- |
| Stale text (this plan) | Fast lane | Spec, guide, README and product-site status text; dead lint ignore; `src/.gitkeep` |
| Test helpers | Standard | Shared test helpers, one ordered snapshot, an e2e sign-in fixture, weak drafting tests |
| Accounts tidy | High | `_role_home`'s one caller, duplicated session lifetime, unused `LOGIN_URL`, settings readability, stale docstrings |
| Rounds tidy | High | A typed Closed conflict instead of a message comparison, one `available_rounds`, one cases-and-builds prefetch, `form_page` for every round form, stale docstrings |
| AI tidy | High | Redundant `never_cache`, the drafting form on `RecordForm`, shared strict JSON loading and gateway configuration, a smaller `draft_page`, stale docstrings |

Deferred until after release: splitting `workflow/scripts/resource_usage.py`'s `collect`.

Needing the human's decision, because each changes behaviour or a criterion:

- No `LOGGING` setting, so with `DEBUG` off Django's `django.request` and `django.security` records (500 tracebacks, the session-interrupted warnings the [technical spec](../specs/TECHNICAL-SPEC.md) says are logged, rejected hosts) go nowhere.
- The start page's "Testing workflows are coming soon." is no longer true, but PLT-1.1 fixes that text.
- `compose.yaml` is unused and pins PostgreSQL 18.6, while CI, the guide and production use 17.
- PLT-2.6, the hosted site's HTTPS check, has no marked test and is not `[manual]`.
- `close_round` does not turn `RoundNotOpen` into a 409 as `retest_round` does; the case cannot occur under the round lock.
- `delete_criterion` checks for links without a round filter; only a cross-round link stored directly could make it refuse a delete (raised in #25's closeout, PR #107).

## Stale-text slice

- Fast lane: cosmetic text only, with no behaviour, acceptance-criterion or security-control change. Base `045c33c` on `67-stale-docs`. Human diff review required.
- Items, each confirmed against the code:
  1. [`TECHNICAL-SPEC.md`](../specs/TECHNICAL-SPEC.md): opening status in the present tense, listing RND-4, RES-1 to RES-4 and PLT-3, with production pending its [release gate](../specs/TECHNICAL-SPEC.md#release-verification); the pre-ACC-1 "until then" sentence removed; `src/` and the accounts/rounds routes in the present tense; the AI drafting bullet says the gateway, not the view, closes the connection after reservation (`src/ai/gateway.py`). The observation-feedback paragraph is already accurate: its view closes the connection itself.
  2. [`SECURITY-SPEC.md`](../specs/SECURITY-SPEC.md) opening status names the built ACC, RND, RES, PLT, access-matrix and SEC-INJ-1 controls and links the product status lines; [`results.md`](../specs/product/results.md) status adds the built RES-4 so the two agree.
  3. [`DeveloperGuide.md`](../../docs/DeveloperGuide.md): link to the User Guide instead of listing features; drop the #103 deployment, slice-verification and live-measurement status notes while keeping the redeploy rule and pending evaluation links; SoC LLM is used.
  4. `pyproject.toml`: remove the ignore for the nonexistent `settings.py`; `pytest.ini` comment in the present tense.
  5. Delete the unreferenced `src/.gitkeep`.
- The coordinator updated `README.md` and `docs/index.md` (the product site) with the `maintain-docs` skill: both now describe tester results and the two AI features as built, with only public hosting pending, as [PLT-2.1](../specs/product/platform.md) requires.
- One checkpoint, committed by the coordinator as `spec:` (items 1–2), `docs:` (item 3 and the README and site), `chore:` (items 4–5) and `plan:` (this file).
- Checks: `git diff --check`; read-back of changed sections; link/anchor resolution; `ruff check .`; `ruff format --check .`; `pytest --collect-only -q`; builder scope check against `045c33c`.
