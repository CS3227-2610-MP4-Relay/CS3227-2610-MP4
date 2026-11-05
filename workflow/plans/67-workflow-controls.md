# #67 workflow controls: a scope hook that fails closed

Goal: make the role-scope hook block instead of silently allowing edits when Python is missing or the hook fails, and check builder edits in other worktrees of this repository; report every missing session-log number.

Tier: High (development security controls: the scope hook, its adapters and the log checker). Base `26e77cc`. Implemented by the orchestrator, because the builder's write scope excludes `workflow/scripts/**`, `.claude/**` and `.codex/**`; reviewed by the verifier and security reviewer. The human told the orchestrator on 2026-11-05 to work on the held items in [the sweep plan](67-cleanup-sweep.md) and make its own decisions (items 1, 9 and 10).

## Findings

- **Hook fails open (sweep item 1).** `.claude/settings.json` ran `python ...check_scope.py --hook`. On a machine with only `python3` on `PATH` (macOS without a virtual environment) the shell exits 127, which Claude Code treats as non-blocking, so every edit went through. Observed on 2026-11-03: all six #67 builders' refusal checks on `AGENTS.md` succeeded. Codex's command had the same dependency. Unreadable hook input exited 1, also non-blocking, and any unexpected exception produced a traceback exit of 1.
- **Worktrees blocked (sweep item 1).** The hook took its repository root from the script's own checkout (`$CLAUDE_PROJECT_DIR`), so with a working interpreter it would refuse every edit in a sibling worktree, and would judge a worktree nested in the checkout by its path inside the checkout.
- **Role-file scope type (sweep item 9).** `writes: "src/**"` would be iterated character by character; `*` alone allows every top-level file. Latent: all role files use lists.
- **Log gap message (sweep item 10).** `check_logs.py` compared numbers with `range(1, len(numbers) + 1)`, so for logs 1, 2 and 5 it reported only 3, not 4. The exit status already failed.

## Changes

1. Both hook commands find `python`, else `python3`, exit 2 with a message when neither exists, and map any non-zero hook result to 2. The Windows Codex command was left unchanged at first; repair rounds 1 and 2 made it fail closed too (see Review).
2. `check_scope.py --hook` exits 2 for unreadable input and for any unexpected exception.
3. `worktree_relative()` resolves the target's existing folders (so a linked folder cannot hide where the edit lands), asks Git for that folder's worktree, requires the same common Git directory as this checkout, and returns the path relative to that worktree; scopes always come from this checkout's role files.
4. `load_scope()` rejects a `writes`/`never_writes` value that is not a list of strings; the hook already blocks on that error.
5. `check_logs.py` expects every number up to the highest one.
6. `workflow/README.md` "How scope is enforced" describes the new behaviour.

## Checks

- Tests added: `HookTest.test_invalid_json_is_not_success` (now exactly 2), `test_unexpected_errors_block`, `test_a_scope_that_is_not_a_list_blocks`; `SiblingWorktreeTest` (sibling, nested and other-repository paths; role files from this checkout; linked folders); `AdapterTest.test_hook_commands_block_when_python_is_missing_or_fails` (both commands, through `/bin/sh`, with no Python, only `python3`, unreadable input, a builder edit and the main session); `LogChecks.test_every_missing_number_is_reported`.
- Mutations, each restored afterwards, fail a named test: unreadable input exiting 1; catching only `ValueError`; dropping the list check; judging by this checkout's root only; skipping the folder resolution; the original `python`-only command; dropping the `python3` fallback; counting log numbers by `len`.
- System Python 3.9 (`/usr/bin/python3`, what the hook uses on this machine without a virtual environment) ran the hook against a real sibling worktree: `src/x.py` allowed (0), `AGENTS.md` blocked (2).
- `python -m unittest discover -s workflow/scripts`, Ruff and full verification: see Progress.

## Progress
- Implemented on `26e77cc`. `ruff check .` and `ruff format --check .` clean; `python -m unittest discover -s workflow/scripts` 113 tests OK; full `pytest` 2876 passed, 254 subtests (base 2869 plus the 7 new tests). Mutation results as listed under Checks.

## Review

- Verifier and security reviewer on `26e77cc..506aede`: no High.
  - Both found that the Windows Codex command (`python ...; exit $LASTEXITCODE`) still failed open: a missing `python` leaves `$LASTEXITCODE` unset, so it exits 0.
  - Security found that a link as the last path component, or `..` after a linked folder, was judged on the unresolved path.
  - The verifier found that no test pinned `|| exit 2`.
  - Lows: no Git timeout; inherited `GIT_*` settings could choose the repository; a planted `.git` file could choose the folder paths are judged from; missing tests for Git being absent and for `[1]`; the README did not say the main session is blocked too without Python.
- **Repair round 1:**
  - The Windows Codex command exits 0 only when `$LASTEXITCODE` is 0, else 2.
  - The hook judges both the path as written and `os.path.realpath(target)`.
  - Git runs without `GIT_*` settings and with a 10-second timeout; a timeout reaches the catch-all and blocks.
  - Only worktrees that `git worktree list` reports for this repository count.
  - New tests: a broken `python` and a project path with a space in the adapter test; Windows command form; a linked file, a dangling link and `link/../`; a planted `.git` file; `GIT_DIR` in the environment; no Git; `[1]` as a scope; a Git timeout.
  - The README states the Windows form and that the main session is blocked too.
- **Mutations rerun, each failing a named test:** unreadable input exiting 1; catching only `ValueError`; dropping the list check; judging by this checkout's root only; skipping the resolved-target check; skipping the worktree-list check; the `python`-only command; no `python3` fallback; no `|| exit 2`; the old Windows command; counting logs by `len`.
- **Covered only by overlap:**
  - Dropping the existing-folder resolution, or keeping `GIT_*` settings, no longer fails a test on its own. The resolved-target check and the worktree-list check block the same paths.
  - The folder resolution remains so that unresolved paths such as `/var` versus `/private/var` compare with Git's resolved worktree path.
- **Deviations recorded, not rewritten:**
  - Implementation came before the plan and unit commits. The three commits were made together after the focused checks.
  - The live check in each client is still to do. Hooks load when a session starts, so after this merges, a new Claude Code session should ask a builder to edit `AGENTS.md` from the main checkout and from a sibling worktree (refused) and `src/` in a sibling worktree (allowed). The same applies to Codex where it is used.
- **Deferred:**
  - Case-insensitive scope matching on macOS (`FLAGS` is case-sensitive outside Windows, so `src/.ENV` passes `**/.env`). Pre-existing; it needs its own slice.
  - A lone `000-*.md` log is no longer reported as a gap. Nit; logs start at 001.
- Repair round 1 on `506aede`: `ruff check .` and `ruff format --check .` clean; workflow unittest 118 OK; full `pytest` 2881 passed, 254 subtests.
- **Recheck of `506aede..5171ee1`:**
  - Both reviewers found every round-1 finding resolved except one: the Windows Codex command could still exit 0. The `git rev-parse` inside the command sets `$LASTEXITCODE` to 0 before a missing `python` fails to resolve.
  - New Low: each target could make up to six Git calls of 10 s each, which could outlast the client's hook limit.
- **Repair round 2:**
  - The Windows command exits 0 only when `$?` is true and `$LASTEXITCODE` is 0. A `pwsh` test, which runs where PowerShell is installed (as on CI's Ubuntu runner) and is skipped on this Mac, runs it with `git` but no `python` and expects 2.
  - All Git calls in one hook call share one 10-second deadline (`GIT_SECONDS`). A test records the timeouts and requires them to shrink.
  - Mutations failing a named test: per-call timeouts; dropping `$?`; the original Windows command; skipping the resolved-target check (rerun).
  - `ruff check .` and `ruff format --check .` are clean. Workflow unittest: 120 tests OK, 1 skipped (PowerShell). Full `pytest`: 2882 passed, 1 skipped, 254 subtests.
- **Accepted as is:** DWF-1.2's wording in SECURITY-SPEC still says "outside" without naming worktrees. The README, which SECURITY-SPEC links for the hook's mechanics, now defines it.
- **Usage:** reported in the session log rather than here, because the orchestrator implemented this slice in the same session as the others.
- **Repair round 2 rechecks:** both reviewers found M1 and the shared-deadline Low resolved in the code. The behavioural evidence for the Windows command is the `pwsh` test on CI.
- **Open nit, left after the last repair round:** the `pwsh` test links `git` with `symlink_to`. On a Windows machine with PowerShell 7 but no symlink rights it would error instead of skipping. CI and macOS are unaffected.
