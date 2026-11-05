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
- **What tracebacks may carry.** The 500 tracebacks Django now prints are the same kind the 503 routes already log "with its traceback only": exception and database error text, such as a constraint violation naming an existing username or workspace name, never a plain password or frame variables. Request warnings print the escaped path without the query string; `DisallowedHost` prints the rejected Host header escaped by `repr`.
- **Criterion.** No new product criterion: logging is production configuration under [PLT-1.8](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification), whose policy lives in TECHNICAL-SPEC Configuration, so the tests carry `PLT-1.8`.
- **Digest.** The multi-arch index digest of `postgres:17.6` from `docker buildx imagetools inspect postgres:17.6` on 2026-11-05: `sha256:00bc86618629af00d2937fdc5a5d63db3ff8450acf52f0636ec813c7f4902929`. The tag stays in the reference for readability; Docker resolves by digest. The Developer Guide's `docker run` examples keep the tag (another builder is editing that guide).

## Open

- None.

## Next

Checkpoint 3 after the orchestrator commits the plan and spec.
