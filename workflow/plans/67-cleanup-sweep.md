# #67 cleanup sweep

Goal: split [#67](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/issues/67) into small behaviour-preserving cleanup slices on `main` at `ebd890c`, after the feature work in #115 and #118–#124, and hold every behaviour, spec or control change for the human.

The human asked on 2026-11-03 to redo #67 from scratch: the earlier sweep's PRs (#110–#114, #116) were closed unmerged and their branches deleted. Base verification at `ebd890c`: Ruff clean; `pytest` 2857 passed and 254 subtests.

## Sweep

Three read-only agents reviewed `ebd890c`: rounds and ai code; accounts, relay, settings, release, CI and workflow scripts; tests and docs. Their IDs (R, A, T, D) are used in the slice plans. They found no functional product defect.

## Slices

Each runs in its own worktree with its own plan and PR.

| Branch | Tier | Items | Plan |
| --- | --- | --- | --- |
| `67-status-docs` | Fast lane | Stale spec, guide, README and site status (D1–D4), two broken anchors (D5), lint ignores that match no file (A4, T10) | [67-status-docs](67-status-docs.md) |
| `67-unit-test-helpers` | Standard | One ordered domain snapshot that includes `Result` (T1, T3), shared test helpers (T4), a race harness that proves the second request waited on the lock (T2), driver-independent ACC-3.7 idle assertion (A13) | On its branch |
| `67-browser-test-helpers` | Standard | Shared browser sign-in and contexts with no cross-test imports (T5), no unasserted screenshots (T6), single-link locators (T7) | On its branch |
| `67-accounts-cleanup` | High | Plain coordinator home (A1), docstrings (A2), session lifetime from settings (A3), release smoke markers checked against rendered pages (A10) | On its branch |
| `67-rounds-cleanup` | High | One conflict page (R1), shared round-scoped queries (R2), docstrings (R6), view and template tidy (R7), role-derived home link (A11) | On its branch |
| `67-ai-cleanup` | High | Shared strict reply loader (R4), drafting view split and one encoder (R3), shared operator preflight (R5), docstrings and dead constant (R6) | On its branch |

## Held for the human

Each of these changes behaviour, a spec, a control or a dependency, or two homes disagree. The recommendation comes first.

1. **Scope hook fails open.** `.claude/settings.json` runs `python`, which is not on this machine's PATH, so the hook exits 127 and Claude Code lets the edit through. A working hook would also refuse every edit in a sibling worktree, because `check_scope.py` takes its root from its own checkout. Recommend a High-tier slice: fail closed when the interpreter is missing, and resolve the root from the edited path's worktree. Until then, `check_scope.py --since` runs before every commit.
2. **No production `LOGGING`.** With `DEBUG=False`, `django.request` 500 tracebacks, the `SessionInterrupted` warning (TECHNICAL-SPEC says it is logged) and DisallowedHost go nowhere, and gateway INFO is dropped. Recommend a minimal console `LOGGING` in production before release; alternatively defer it to the release gate.
3. **Spec and code disagree on drafting's connection release.** TECHNICAL-SPEC (RND-8) and `test-drafting.md` say the drafting view closes its database connection before calling the gateway; the code has `gateway.complete` close it. Recommend rewording the specs; alternatively add an explicit close to the view.
4. **Two AI specs disagree.** `test-drafting.md:85` calls the gateway rules "proposed … pending confirmation", while `llm-gateway.md` says they are implemented and confirmed. `test-drafting.md:89` says a 30 s function limit is too short, while the TECHNICAL-SPEC release gate still requires only "at least 30 seconds" (`vercel.json` sets 60). Pick one home for each.
5. **Case label order.** RND-4 and RES-1.3 list "Linked acceptance criteria" before "Current build"; PLT-4.9 and the templates put the current build first.
6. **Criteria with no marked test or `[manual]` tag:** CTX-1.6, DWF-1.1–1.6 (identified only in docstrings) and PLT-2.6 (hosted evidence in a log). Recommend tagging CTX-1.6, DWF-1.6 and PLT-2.6 `[manual]` with reasons and documenting the DWF docstring convention.
7. **`compose.yaml`** pins PostgreSQL 18.6 while CI, the guide and the spec use 17.6, and nothing references it. Recommend deleting it.
8. **CI PostgreSQL image** is pinned by tag only; actions are SHA-pinned. Recommend a digest pin (High tier, CI).
9. **`check_scope.py` role files:** `writes` accepts any JSON value, so a string would be read character by character. Latent; recommend list-of-strings validation (High tier, development control).
10. **`check_logs.py` gap message** counts to the number of logs rather than the highest number, so it can omit a missing number; the check still fails. One-line fix with a test.
11. **`.env.example`** sets `DJANGO_ALLOWED_HOSTS` and `DJANGO_DEBUG=true`, while TECHNICAL-SPEC says it holds only empty placeholders and throwaway database values.
12. **No `500.html`:** the 500 page is Django's plain page while other errors extend `base.html`.
13. **PLT-2.1 site test** checks links only; the "explains roles, distinguishes built from planned" parts are checked by human inspection.
14. **Developer Guide Design paragraph** (about 900 words) restates TECHNICAL-SPEC rules; recommend trimming it to an overview with links.

## Deferred

- `workflow/scripts/resource_usage.py` `collect()` (about 350 lines) could be split by platform; well tested and outside the app.
- The drafting view's copy of the 30-case limit message, until `rounds.services` exposes it as a constant.

## Final sanity check

After the cleanup PRs: merge every branch onto current `main` locally, run full verification (`ruff check . && ruff format --check . && pytest`) and `check --deploy` against production settings with throwaway values, and record the candidate, results and unresolved findings in the session log. [Release verification](../specs/TECHNICAL-SPEC.md#release-verification) beyond that needs hosted environments and the human's release approval; this issue does not authorize deployment.
