# Slice 60: Store the markup test payload escaped (#60)

Goal: the rounds tests keep their markup red-team payload once, escaped, in a shared test module, so no source file holds the raw payload or raw tag fragments, as [AGENTS.md](../../AGENTS.md#safety) requires.

Tier: Fast lane, tests only; behaviour, criteria and security controls unchanged. Base: `c6aee04`, branch `60-escape-markup-payload`, stacked on #58. Owner: zheng-jj. Budget: 0 changed lines under `src/` outside tests; about 60 changed test lines.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27, issue #60: store the payload once, escaped, decoded only in test code; make every module use it; make the detection assertions raw-free without weakening them; report other raw payloads under `src/` and fix only those in tests. No spec change: the rule already lives in AGENTS.md.

Builder's details within that scope:

- **Home:** `src/rounds/tests/conftest.py`, which the rounds tests already import helpers from (`from .conftest import ...`), as #11's plan deferred it.
- **Escaping:** Python `\x` escapes for the five markup characters (`<` `>` `"` `'` `&` as `\x3c` `\x3e` `\x22` `\x27` `\x26`), the same way the tests already write bidi characters as `\u` escapes. The interpreter decodes the escapes only when a test module is loaded. The letters between them, such as `onerror=alert(2)`, stay readable, and without the markup characters they are inert. A future grep for `onerror` still finds this one line, which is the shared payload.
- **Detection fragments:** `SCRIPT_TAG` (`\x3cscript\x3e`) and `IMG_TAG` (`\x3cimg`), also escaped, in `conftest.py`. One import-time `assert` checks that both are substrings of the decoded `MARKUP`, so the fragments stay tied to the payload. Each `"<script>" not in html` and `"<img" not in html` keeps its existing checks, only with the constants. A module that checked only `<script>` keeps checking only that.
- **Byte-for-byte proof:** a recorded check, run once from the scratchpad and not committed. It parses `MARKUP` from `test_close.py` at `c6aee04` with `ast`, imports the new constant and compares their UTF-8 bytes and SHA-256 digests.
- **Not weakened:** the same mutation is run on a temporary copy of `src/rounds/templatetags/rounds_text.py` before and after the change. `isolated_lines` passes each line through `mark_safe`, so it emits raw text. The pass/fail counts of the six affected modules must match, and the focused rendering tests must fail. The file is restored, checked with `cmp`, and every run uses an empty `PYTHONPYCACHEPREFIX`, which avoids the stale-bytecode problem seen in #58.

## Raw payload scan (checkpoint 1, recorded)

`grep -rnIl -iE "onerror|javascript:|<svg|<iframe|<script|alert\(" src/ --exclude-dir=__pycache__` matched only these:
- the six modules above, all in tests;
- `src/accounts/tests/test_workspaces.py`, `src/rounds/forms.py` and `src/rounds/tests/test_forms.py`, but only because "ValidationError" contains "onerror" (not payloads).

A Perl-regex grep for non-ASCII characters in `.py` and `.html` under `src/` found none, so no bidi, zero-width or other character is typed literally; every one is a `\u` escape or `chr()`. Markup in other test assertions, such as `<h2>`, `<legend>` and `<span dir="auto">`, is the product's own markup, not a payload, so it stays.

## Checkpoints

1. **Plan** (`plan:`): this file. Check: `git diff --check`; read back.
2. **Shared escaped payload** (`test:`): `src/rounds/tests/conftest.py` (`MARKUP`, `SCRIPT_TAG`, `IMG_TAG`, the import-time assert); `test_close.py`, `test_messages.py`, `test_publish.py`, `test_record_rendering.py`, `test_rendering.py` and `test_retest.py` import them and drop their own copies and literals. Evidence: the byte-for-byte check; the mutation before and after; afterwards, `grep -rnE "<script|<img|onerror" src/rounds/tests` matches only the escaped line. Checks: each affected module run alone with `pytest -q -p no:randomly <module>` against the test database on 127.0.0.1:55432; Ruff check and format on the changed files. Full verification is the coordinator's.

## Size estimate

`src/` outside tests: 0 lines. Tests: about 10 added in `conftest.py`, 6 constant lines removed and about 20 assertion and import lines changed.

## Open issues

- None. The escaped payload still spells `onerror` and `alert` in plain letters. On 2026-10-27 the orchestrator chose option (a): escape only the markup characters, rather than hex-encoding the whole string, so the line stays readable and inert.

## Checklist

- [x] Checkpoint 1: plan (`6d6dc52`).
- [x] Checkpoint 2: shared escaped payload (on `6d6dc52`). `conftest.py` holds `MARKUP`, `SCRIPT_TAG`, `IMG_TAG` and the import-time assert; the six modules import them, drop their copies and use the constants in every detection assertion (`test_messages.py` still checks only the script tag). Byte check: each module's `MARKUP` at `c6aee04` (parsed with `ast`) and the new constant are the same 61 UTF-8 bytes, SHA-256 `22e35a29…97f9`; both tag constants equal the old literals. Mutation (`isolated_lines` passes each line through `mark_safe`, on a temporary copy, empty `PYTHONPYCACHEPREFIX`, restored and checked with `cmp`), each module run alone, before and after the change: the same 11 tests failed in both runs (close 1, messages 1, publish 2, record_rendering 1, rendering 1, retest 5), and the pass counts matched. Green, each module alone with `pytest -q -p no:randomly`: 28, 9, 49, 7, 19 and 74 passed. `grep -rnE "<script|<img|onerror" src/rounds/tests` matches only the escaped `conftest.py` line. Ruff check and format clean.
