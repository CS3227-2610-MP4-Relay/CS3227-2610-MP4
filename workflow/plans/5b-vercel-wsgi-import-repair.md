# 5b: Repair hosted WSGI package imports

Goal: initialize the existing Django application when the host loads WSGI by file path without adding `src` to Python's import path.

## Scope and reason

- Continuing authorized slice-5 deployment; High tier. Base `951c5998e88e790666bf9a33703c9e38751ca4af`, branch `fix/5-vercel-wsgi-import`, snapshot `%TEMP%/relay-wsgi-import-plan.json`. Builder `gpt-6.1-sol`, medium; no delegation, Git changes or hosted actions. Merged plans 5/5a remain frozen.
- Why: the reported deployment builds Ready but invocation fails importing `relay.settings.production` after WSGI is loaded through an importlib file specification. `manage.py` starts inside `src` and configuration probes inject `PYTHONPATH`; WSGI currently establishes neither package path.
- Existing PLT-1.4/1.8/1.12 cover startup/delivery; no new criterion, dependency, service, setting or release control. Add only stable file-relative package-path setup in `src/relay/wsgi.py`, preserving explicit settings selection and the local default. Target at most 150 total changed lines and fewer than 15 production source lines. Hosted retry/public activation remain outside this repair.

## Checkpoints

1. **Contract clarification and plan**: clarify existing WSGI startup architecture in the technical configuration; read back, check whitespace/scope and yield before implementation.
2. **WSGI repair and regression**: one coherent code/test commit. Add an executable `.py` subprocess probe under `src/relay/tests/` and criterion-marked configuration regression: clear inherited application/provider/database configuration and `PYTHONPATH`, run from an unrelated temporary directory, load the real WSGI file with `importlib.util.spec_from_file_location`, and exercise its WSGI application on an anonymous HTTPS start-page request. Use synthetic production values and forbid database connections; verify successful startup, configured settings selection and the expected response. Run red before the minimal WSGI change, then focused configuration tests and Ruff/format/scope checks; yield for commit.
3. **Integrated verification and delivery**: coordinator runs full checks, freezes the fixed candidate for independent verifier/security review, records usage/log evidence and delivers the draft PR with exact-head CI. Human merge and hosted actions remain separate; local startup success is not hosted verification.

## Evidence and next step

- At diagnosis, WSGI called `get_wsgi_application()` without adding its parent package root. Existing `settings_probe.py` is invoked with `PYTHONPATH=src`, masking direct-file hosted startup. The new isolated probe avoids pytest's module cache and path changes.
- Reported hosted traceback is diagnostic data; no production credentials, configuration files or database need inspection. No new diagnostic endpoint or production workaround is planned.
- Plan/contract committed `eea894d5c62f79292b60f8ac96244570a572bcab`; implementation snapshot `%TEMP%/relay-wsgi-import-implementation.json`. Red: `pytest src/relay/tests/test_configuration.py -q -k wsgi_file_import` reproduced `ModuleNotFoundError: No module named 'relay'` in both production and local-default partitions. Three WSGI source lines establish the file-relative package root; isolated file-import probes now verify selected settings, real start-page 200/content and zero database connection attempts.
- Green: focused configuration/release tests passed 116 in 81.32 seconds; global Ruff/format, whitespace and builder scope passed. Fixed `7de4119bd83ac92f9e3e54c4f44bafe89d871b45` independently passed verifier/security review with no findings; each ran both isolated startup cases. A real prepared archive also returned the expected production 200 without database IO; `-I -B` preserved its 53 files. Full local result: 1,036 passed, three previously documented Windows timeout-text failures, one skipped; Django/Ruff/format and all eight browser journeys passed. [Linux CI](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40801498535): 1,037 passed, three skipped; verify/site passed, publication skipped.
- [Draft PR 85](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/85) records final summary-head CI. Next: human review/merge, verified main CI and fresh protected upload; repaired hosted invocation remains unverified. No runtime setting, dependency or hosted state changed. Usage and review details: [session log](../../logs/Whimsyturtle/012-prepare-vercel-and-neon-production-delivery.md).
