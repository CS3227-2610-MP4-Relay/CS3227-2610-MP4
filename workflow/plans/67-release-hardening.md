# #67 release hardening

Goal: before the release in [#37](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/issues/37), give production a minimal console log and pin CI's PostgreSQL image by digest, items 2 and 8 held in the [cleanup sweep](67-cleanup-sweep.md#held-for-the-human).

Tier High (production configuration and CI). Base `26e77cc`; branch `67-release-hardening`. The human confirmed both items and left the decisions to the orchestrator. No new dependency, service, handler type or criterion.

## Checkpoints

1. `plan:` this file.
2. `spec:` production logging in [TECHNICAL-SPEC Configuration](../specs/TECHNICAL-SPEC.md#configuration) and its control in [SECURITY-SPEC Secrets and settings](../specs/SECURITY-SPEC.md#secrets-and-settings).
3. `fix:` `LOGGING` in `src/relay/settings/production.py`, with tests in `src/relay/tests/test_configuration.py` and the probe `src/relay/tests/settings_probe.py`. Focused: `pytest src/relay/tests/test_configuration.py`; red first against unchanged settings.
4. `ci:` `.github/workflows/ci.yml` service image `postgres:17.6@sha256:<index digest>`; `src/relay/tests/test_ci.py` requires the digest form. Focused: `pytest src/relay/tests/test_ci.py`; red first against the tag-only workflow.
5. Final full verification, and `check --deploy --fail-level WARNING` on production settings with throwaway values through `env -i`.

## Decisions

- **Production only.** Local and test settings keep Django's defaults; tests capture logs themselves.
- **One handler.** A console `StreamHandler` on stderr, format `%(asctime)s %(levelname)s %(name)s %(message)s`, at WARNING, on the root logger and on `django`. `django` does not propagate, so each record prints once. `disable_existing_loggers` is false, so module loggers created before configuration still log. No mail handler, file or service.
- **Gateway INFO stays out.** [llm-gateway.md](../specs/ai/llm-gateway.md#transport-contract-proposed) says the gateway logs only the fixed outcome code but not whether that line reaches production; SECURITY-SPEC says to record only necessary operational metadata. So production keeps WARNING for every logger, and the per-call `ai.gateway` INFO outcome is dropped; its WARNING loop reports still print.
- **What logs may carry.** Stated once, in [SECURITY-SPEC Secrets and settings](../specs/SECURITY-SPEC.md#secrets-and-settings): escaped `Host`, CSRF `Origin`/`Referer` values and 4xx tracebacks, plus two residual gaps not yet accepted by the human: tracebacks whose PostgreSQL DETAIL can print coordinator-written text, and unlimited log volume.
- **Refusals stay unlogged** (repair round 1, orchestrator's decision keeping the human's #59 rule). A `CallbackFilter` on the console handler drops records whose `status_code` is 429, so Django's "Too Many Requests" warning for sign-in and `/demo/` refusals never prints.
- **Criterion.** No new product criterion: logging is production configuration under [PLT-1.8](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification), whose policy lives in TECHNICAL-SPEC Configuration, so the tests carry `PLT-1.8`.
- **Digest.** The multi-arch index digest of `postgres:17.6` from `docker buildx imagetools inspect postgres:17.6` on 2026-11-05: `sha256:00bc86618629af00d2937fdc5a5d63db3ff8450acf52f0636ec813c7f4902929`. The tag stays in the reference for readability; Docker resolves by digest. The Developer Guide's `docker run` examples keep the tag (another builder is editing that guide).

## Progress

- Plan `9715f3b`, spec `5f6b583`.
- Checkpoint 3: red first, 2 failed (`LOGGING` absent; no formatted 500 line). Green 61 passed in `test_configuration.py`. Mutations, each restored: removing the `django` entry fails the config test; `django` propagating (record printed twice), `disable_existing_loggers` true (early logger silenced) and INFO levels each fail both tests.
- Checkpoint 4: red first, `test_ci_runs_isolated_application_verification` failed on the tag-only image; green 3 passed; one changed digest character fails it again. `docker buildx imagetools inspect` resolves the pinned reference to the same index, with `linux/amd64` in it.
- `check --deploy --fail-level WARNING` on production settings with throwaway values through `env -i`: "no issues (2 silenced)".
- Review of `7456e18`: no High findings; verifier and security reviewer both raised M1, the printed 429 refusal records.
- Repair round 1: spec rewording first (snapshot `.r67/harden/repair1-spec-before-code.diff`). The probe also logs a 429 through `log_response`; the stream test now asserts "Too Many Requests" is absent (red: 1 failed), and the local-settings test asserts no `LOGGING`. Green 61 passed after the filter. Mutations, each restored: handler without the filter fails both tests; a callback keeping every record fails the stream test. `check --deploy`: "no issues (2 silenced)".

- Review of `fd91733`: the verifier resolved everything; the security reviewer raised a new Low, that SECURITY-SPEC called a failing row's coordinator-written text an accepted exposure. Repair round 2 (docs only, orchestrator's option b): the bullet now names that text as a residual gap not yet accepted by the human, and says tester observations stay out because `rounds.tester.tester_view` logs storage failures as a fixed line without a traceback.

## Open

- Human acceptance of the failing-row residual in [SECURITY-SPEC Secrets and settings](../specs/SECURITY-SPEC.md#secrets-and-settings) is not recorded.

## Next

Re-review of the repaired candidate; ask the human about the failing-row residual.
- Repair round 2 rechecks: the security reviewer found its Low resolved and no new findings; the verifier had already resolved everything at `fd91733`.
