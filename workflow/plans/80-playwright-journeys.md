# 80: Browser journeys

Goal: verify four existing Relay journeys through real Chromium forms in the existing CI verification job.

## Scope and decisions

- Human trigger: `/slice 80`, High tier; user prefers one build then independent verifier/security review chain per journey. No delegation by builder. Coordinator owns Git and delivery.
- Existing criteria only: ACC-1.1–1.5, RND-1.1, RND-2.1–2.2/2.6 and RND-3.1/3.3; no product criterion changes. Browser examples supplement, rather than replace, existing server tests and do not claim complete coverage of every clause.
- Architecture and artifact handling have their home in [Browser verification](../specs/TECHNICAL-SPEC.md#browser-verification); security implications in [CI and dependencies](../specs/SECURITY-SPEC.md#ci-and-dependencies).
- Authorized additions: development-only Playwright and its required pinned transitives, its Chromium download/Linux prerequisites, existing `verify` integration and synthetic failure diagnostics. No runtime dependency, service, credential, product behaviour or additional journey.
- Estimate: 250–400 test lines plus 120–180 configuration/spec/plan/guide lines, zero application behaviour lines; within the 400 non-test/non-migration source-line budget. Operating burden: developers install Chromium once per Playwright upgrade; CI downloads Chromium and prerequisites per run and stores failures for three days. Stop and report if this estimate or confirmed scope cannot be met.
- Prefer the Playwright library directly over adding a pytest browser plugin: one small local fixture controls per-test lifecycle, database ordering and failure retention. Keep helpers limited to repeated form actions, with assertions visible in journey tests.
- Pin the live-server CLI address to `127.0.0.1:0` in pytest configuration so inherited live-server environment values cannot change its bind address. Use only the fixed test settings and pytest's test database.

## Commit and review checkpoints

Each implementation checkpoint is built, checked, frozen and independently verified/security-reviewed before the coordinator commits it and supplies a fresh scope snapshot. Do not start the next journey early. Keep regression checks and related harness repairs with the checkpoint that needs them.

1. **Specs and plan** (`spec:` then `plan:`): this document, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`. Read changed sections back, check whitespace and builder scope; yield before implementation.
2. **Shared setup, in separate editing runs**: first dependency pins, `pytest.ini` and `src/e2e/conftest.py` (`test:`): verify package identities/transitives, install dependencies and Chromium, check collection, exercise one temporary browser smoke and controlled failure diagnostic without retaining an extra journey, and confirm settings/ORM lifecycle cleanup. Freeze, review and commit this harness before starting `.github/workflows/ci.yml` and focused existing CI/configuration regressions (`ci:`); verify the official artifact action commit. Then update `docs/DeveloperGuide.md` (`docs:`). Coordinator supplies a fresh snapshot after each commit; complete shared setup review before journey 1.
3. **Journey 1** (`test:`): `src/e2e/test_accounts.py`; parameterize coordinator/tester sign-in, own heading/username/workspace, sign-out notice, then direct protected revisit redirects to sign-in (ACC-1.1/1.3/1.5). Focused run plus independent review before journey 2.
4. **Journey 2** (`test:`): same test module; wrong password shows exact generic message and leaves visitor unauthenticated; each signed-in role directly visits the opposite home, sees 403/message without workspace data, and can return to its own home (ACC-1.2/1.4). Focused run plus independent review before journey 3.
5. **Journey 3** (`test:`): `src/e2e/test_rounds.py`; coordinator creates Draft round, adds criterion and linked case, reloads to verify title/steps/expected result/link, publishes a named build, sees success/Open/current build and frozen edit controls (RND-1.1/2.1/2.2/3.1). Focused run plus independent review before journey 4.
6. **Journey 4** (`test:`): same test module; independently submit otherwise-valid case with no selected criterion and otherwise-valid publish label on an empty Draft round. Assert exact refusal messages, preserved input and unchanged Draft/no case/no build after reload (RND-2.6/3.3). Focused run plus independent review.
7. **Integrated validation and delivery**: full `ruff check . && ruff format --check . && pytest`, Django system check, scope check, current guide/spec readback, final fixed-candidate reviews and configured CI result. Coordinator handles draft PR and records exact evidence; no merge or release.

## Research and verification

- Starting candidate: `a121d6e318686ff741e1c70ac6894aff79e31a2f`, clean `test/80-playwright-journeys`; coordinator supplied `%TEMP%/relay-80-builder-plan.json` scope snapshot.
- The existing `verify` job is in `.github/workflows/ci.yml`, uses Python 3.14.2 and throwaway PostgreSQL 17.6, and runs full pytest with read-only repository access. Test settings inherit Secure cookies. Existing account and round server tests already cover the selected criteria.
- [Microsoft's Playwright package](https://pypi.org/project/playwright/) resolves to `microsoft/playwright-python` and currently lists 1.64.1 (released 2026-10-22); verify that exact release's metadata/transitives and Python 3.14 compatibility during installation before pinning. No install performed in the planning checkpoint.
- [Official library usage](https://playwright.dev/python/docs/library) supports an explicit synchronous lifecycle; [official CI instructions](https://playwright.dev/python/docs/ci) cover browser/prerequisite installation. [pytest-django live server](https://pytest-django.readthedocs.io/en/latest/helpers.html#live-server) uses transactional access because requests run in a separate thread. [Django async safety](https://docs.djangoproject.com/en/6.1/topics/async/#async-safety) explains why ORM work must avoid a running event loop.
- These are tests of built behaviour: a passing first run is expected, so no artificial red application implementation phase. Assertions must detect wrong redirects/messages, leaked workspace text, missing persistence/links, incomplete publication and unintended writes on refusal. Record focused commands and observed outcomes at each checkpoint.
- Planning checkpoint: repository/code and primary-source inspection only; full application checks deferred to implementation. Session usage baseline stored outside the repository as `%TEMP%/relay-80-builder-usage.json`; no raw transcripts retained in the repository.

## Open items and next step

- Coordinator started an isolated temporary PostgreSQL 17 cluster at the fixed test address and reported `pytest src/relay/tests/test_database.py -q` passing (1 passed, 3.05s). Coordinator owns that cluster's lifecycle. Builder will verify browser visibility in checkpoint 2 without reading runtime secrets or repointing tests.
- Next: coordinator reviews/commits this specification checkpoint, then supplies the next baseline and authorizes shared harness checkpoint 2. No implementation is included here.
