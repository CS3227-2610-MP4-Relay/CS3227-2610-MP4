# #67 workflow controls: a scope hook that fails closed

Goal: make the role-scope hook block instead of silently allowing edits when Python is missing or the hook fails, and check builder edits in other worktrees of this repository; report every missing session-log number.

Tier: High (development security controls: the scope hook, its adapters and the log checker). Base `26e77cc`. Implemented by the orchestrator, because the builder's write scope excludes `workflow/scripts/**`, `.claude/**` and `.codex/**`; reviewed by the verifier and security reviewer. The human told the orchestrator on 2026-11-05 to work on the held items in [the sweep plan](67-cleanup-sweep.md) and make its own decisions (items 1, 9 and 10).

## Findings

- **Hook fails open (sweep item 1).** `.claude/settings.json` ran `python ...check_scope.py --hook`. On a machine with only `python3` on `PATH` (macOS without a virtual environment) the shell exits 127, which Claude Code treats as non-blocking, so every edit went through. Observed on 2026-11-03: all six #67 builders' refusal checks on `AGENTS.md` succeeded. Codex's command had the same dependency. Unreadable hook input exited 1, also non-blocking, and any unexpected exception produced a traceback exit of 1.
- **Worktrees blocked (sweep item 1).** The hook took its repository root from the script's own checkout (`$CLAUDE_PROJECT_DIR`), so with a working interpreter it would refuse every edit in a sibling worktree, and would judge a worktree nested in the checkout by its path inside the checkout.
- **Role-file scope type (sweep item 9).** `writes: "src/**"` would be iterated character by character; `*` alone allows every top-level file. Latent: all role files use lists.
- **Log gap message (sweep item 10).** `check_logs.py` compared numbers with `range(1, len(numbers) + 1)`, so for logs 1, 2 and 5 it reported only 3, not 4. The exit status already failed.

## Changes

1. Both hook commands find `python`, else `python3`, exit 2 with a message when neither exists, and map any non-zero hook result to 2. The Windows Codex command is unchanged.
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
