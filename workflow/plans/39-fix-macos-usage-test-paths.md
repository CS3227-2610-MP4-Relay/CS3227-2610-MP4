# Fix the child-discovery usage test's path comparison on macOS (#39)

Goal: make `test_child_discovery_is_bounded_by_ancestry_and_project` pass wherever the temporary directory sits behind a symlink, without changing `resource_usage.py`.

Tier: Standard, because this is a test fix for usage telemetry, not a development security control. Base: `f69ca558f14c6a90004856a66af7b31fc79f07a3`.

Cause: on macOS, `tempfile` returns `/var/folders/...`, and `/var` is a symlink to `/private/var`. `discover_children` returns resolved paths (`resource_usage.py` lines 115 and 122). It needs them to deduplicate explicit parents against directory entries (line 123); `collect` resolves paths on its own (line 181). The test compared those resolved paths against the unresolved paths it had written, so it failed on macOS but passed on Linux CI.

Decisions: the code's behaviour is intended, so correct the test's expectation, not the code. Resolve only the three expected paths in this test. The set equality still rejects the unrelated session, the wrong-project session and any missing descendant. No spec or criterion covers this script, so no spec change is needed.

Ownership: `workflow/scripts/**` is outside the builder's write scope, so the coordinator edits the test and this plan, following the [agent-model-defaults](agent-model-defaults.md) precedent. The verifier reviews the fixed candidate.

Budget: one test assertion and this plan.

- [x] Record the failure before the fix (macOS, Python 3.14.7): `AssertionError` comparing `/private/var/...` with `/var/...`; it also fails on a clean export of `d1cbde4`.
- [x] Correct the expectation; run full verification, `python -m unittest discover -s workflow/scripts` and `git diff --check`.
- [x] Freeze the candidate; verifier review.
- [ ] Human merge decision.

Check evidence (macOS, Python 3.14.7): Ruff lint/format passed. pytest: 70 passed, 85 subtests passed; the failure from before the fix is gone. `python -m unittest discover -s workflow/scripts` ran 70 tests, OK. `git diff --check` is clean. The changed assertion still fails if `discover_children` adds the unrelated or wrong-project session, drops a descendant, or returns unresolved paths where they differ from resolved ones.

Outcome: the verifier found no blocking issues. `check_scope.py --unchanged` confirmed the candidate was stable, and the diff under `workflow/scripts/` is one line. After the review, the coordinator corrected the plan's cause wording (a Low finding) and updated the checklist; the test change is unchanged. Deferred: a portable symlinked-directory test, so that Linux CI also exercises the path-resolution case.
