# SoC chat completions integration (#6)

Adapt Relay's provider wire format using MP3 evidence and enable the gateway while retaining its controls and documenting pending review and live validation.

- **Tier:** High: LLM provider boundary. Starting HEAD: `5d3fd29e3ca3e072214ff4733b29a959c8e714ad`; branch `6-soc-chat-completions`.
- **Confirmed scope:** request/response adapter, code-level live enablement, existing TLS key-log/debug safety obligations, meaningful regression tests and developer setup documentation under the request to complete integration through a branch and draft PR. The human separately confirmed provider terms/defaults on 2026-10-31; independent and human review remain pending. No dependencies, probe route/token, services, networking redesign or UI implementation. Correct only RND-8's planned notice; preserve unrelated edits and the frozen `6-llm-gateway.md` plan.
- **Budget:** at most one requirement affected (existing RND-8 gateway-dependent behaviour); no new product criterion. At most 400 changed non-test/non-migration source lines; expected adapter below 120, whole diff roughly 300–600 lines including tests/spec/docs. Stop and report any expansion.
- **Why:** Relay's top-level `instructions`/`data` request and `text`/`refusal` response do not match the local MP3 chat-completions implementation. The [gateway contract](../specs/ai/llm-gateway.md#transport-contract-proposed) owns the replacement format and edge cases.

## Commit checkpoints

1. **Spec and plan:** update `workflow/specs/ai/llm-gateway.md`, the narrowly required `SECURITY-SPEC.md` cross-reference and `product/rounds.md` planned notice, and this new plan; read back changed sections, inspect diff/size and run builder scope check against the coordinator's snapshot. Yield before implementation. Coordinator commits this checkpoint and supplies a new HEAD/snapshot.
2. **Adapter and live enablement with tests:** change request serialization and envelope extraction in `src/ai/gateway.py`, clear each TLS context's key-log filename and explicitly disable the call loop's debug mode; set `SOC_LLM_LIVE=True` in `src/relay/settings/base.py` after adapter/safety tests pass. Update fixed test settings/fixtures only as needed to preserve network isolation and test the opt-out path, with tests in `src/ai/tests/test_gateway.py` and `src/ai/tests/test_transport.py`. First demonstrate focused failures against the old behaviour, then implement and run focused tests/Ruff and scope checks; retain red and green evidence in handoff. Use synthetic local transport replies, never the real provider. Mark affected acceptance tests with existing RND-8.4/8.5/8.6 IDs as appropriate. Yield for coordinator commit before documentation.
3. **Developer setup and integrated verification:** update `docs/DeveloperGuide.md` with the built format/setup and pending live prerequisites, linking to the contract. Update this plan's next step without duplicating requirements. Run full `ruff check . && ruff format --check . && pytest` with `.venv` active in Git Bash, plus Django system/migration checks where applicable and builder scope/size checks. Yield the final candidate for coordinator commit, independent verifier/security review and authorized draft PR delivery.

## Verification partitions

- Exact chat request, fixed system instructions versus unchanged user JSON (including instruction-like synthetic source), configured model, deterministic non-streaming flags, Bearer header outside body and no tools/retries.
- First assistant content with ordinary metadata, absent/assistant role, ignored later choices, empty content and 19,999/20,000/20,001 characters including non-BMP text; preserve byte-cap below/at/above tests.
- Independently invalid root/choices/first choice/message/content/role/tool fields; missing, null and wrong types; nested duplicate keys, nonfinite numbers, invalid UTF-8, parser recursion failure, lone surrogates and legacy envelopes.
- Message refusal, null/absent refusal, malformed refusal, content-filter refusal, truncated `length` replies and refusal mixed with content; fixed outcomes and absence of provider text in logs.
- Test the enabled shared default and explicit live-off override, unconfigured refusal before networking, TLS key-log suppression and disabled per-call debug despite debug environment settings. Retain existing transport, quotas and cleanup tests and test-environment network blocking. RND-8 UI and feature evaluation belong to separate work; no browser journey is added here.

## Decisions and open items

- The [gateway contract](../specs/ai/llm-gateway.md) owns MP3 evidence and the human's 2026-10-31 no-retention, no-training and default-limit confirmations. Live enablement is authorized within this PR, conditional on implemented/tested adapter and runtime safety controls. No live invocation occurs before operator environment configuration; smoke check and feature live evaluation remain pending, not executed or implied by local tests. Do not claim provider terms independently verified, production readiness or #6 complete.
- Do not copy MP3's 512-token output cap: local character/body/deadline bounds remain. Actual provider compatibility is part of pending manual validation.
- Trusted CA configuration and direct provider reachability remain documented operator obligations. Clear key logging and disable per-call debug as the existing controls require; no new safety subsystem. Preserve the existing hosting time-margin concern and report it without broadening this slice.
- **Next:** coordinator commits/pushes the CI test repair, then runs final full verification and CI on that committed candidate while independent reviewers inspect it. Human merge/release decisions and manual live validation remain pending.

## Checkpoint 2 evidence

- Spec-before-code: checkpoint 1 committed as `276fe9c`; implementation started only after the coordinator's fresh scope snapshot. Runtime now sends chat messages, reads the first assistant reply, suppresses TLS key logging/debug mode and enables the shared code-level switch; fixed test settings explicitly disable it.
- Red: chat subset against old code had 16 failures/37 passes; request-body assertions separately failed twice on old `instructions`/`data`. Shared-switch and debug tests failed as expected. Corrected TLS test creates the server before setting `SSLKEYLOGFILE`; temporarily removing client suppression then failed its key-line assertion, and restoring it passed.
- Green: Git Bash `.venv` Ruff check/format for `src/ai` and changed settings passed; `pytest src/ai -q -p no:cacheprovider --basetemp=C:/Users/limbe/AppData/Local/Temp/relay-issue6-green-checkpoint2 --tb=short` passed 158 tests. Full verification belongs to checkpoint 3, not this result.
- Test corrections: successful transport fixtures now use chat envelopes rather than the retired wire format. The existing sensitive-traceback test normalizes Windows paths and retains all secret-redaction assertions. Deep-nesting input increased from 2,000 to 20,000 levels because this parser accepts 2,000; invalid partitions otherwise passed before implementation because the old parser rejected all chat objects.
- Runtime source diff is 60 changed lines including shared/test settings, below the expected 120. No real provider calls, credentials, dependency changes or UI implementation were used; live smoke/evaluation remains pending.

## Checkpoint 3 evidence and open CI repair

- Developer setup now supplies the MP3 endpoint/model and hidden Git Bash key prompt, explains exported variables instead of dotenv loading, and separates local tests from pending live validation. Updated contract status and stale provider-status cross-reference; no runtime/test changes. New setup commands passed `bash -n`; local document paths and anchors were checked.
- Git Bash `.venv`: `ruff check .`, `ruff format --check .` (105 files), Django `check --settings=relay.settings.test` and `makemigrations --check --dry-run --settings=relay.settings.test` passed. Full `pytest -q -p no:cacheprovider --basetemp=C:/Users/limbe/AppData/Local/Temp/relay-issue6-full-checkpoint3 --tb=short` returned 3 failed, 1,960 passed, 1 skipped and 231 subtests passed in 297.80 seconds. The failures are unchanged account idle-timeout log assertions (`test_limit_views.py:564`, wrong-password/correct-password/demo idle variants), matching the coordinator's pre-change Windows baseline. Accounts remain untouched; full verification is not green.
- Coordinator-reported Linux CI at `b90351c` found the new fixed-20,000-depth metadata assertion invalid: the parser accepted it (1 failed, 1,960 passed, 3 skipped). No numeric nesting limit was confirmed. Proposed separate repair: say parser recursion failure explicitly and test `RecursionError` through the parser seam, retaining real malformed/duplicate/nonfinite/UTF-8 cases and the byte bound. Do not add an arbitrary nesting subsystem or merely increase the fixture depth. Code/tests were left unchanged in this checkpoint.

## CI repair round 1: spec checkpoint

- Correct the slice's inaccurate nesting assumption: reject parser recursion failure, with no independent numeric depth limit, under the existing response byte cap. Duplicate-key, UTF-8, nonfinite-number, content and body bounds remain intact. Specs precede the separately assigned test repair; runtime/tests are untouched here.

## CI repair round 1: test checkpoint

- Spec committed first as `82dd390`. Replaced only the platform-invalid depth fixture with a controlled parser `RecursionError` test, asserting the parser was called, the fixed failure outcome and no exception-text log leakage. Existing correct runtime passes it without changes; real malformed JSON and transport bounds remain tested.
- Mutation evidence: a temporary test-only rebind of the handler's `RecursionError` lookup to `KeyError` made the new test fail with uncaught `RecursionError`; removed the rebind before final checks. Ruff check/format passed; `pytest src/ai -q -p no:cacheprovider --basetemp=C:/Users/limbe/AppData/Local/Temp/relay-issue6-ci-focused --tb=short` passed 158 tests in 30.70 seconds. Coordinator owns final full verification/CI; runtime source remains unchanged at 60 changed lines.
