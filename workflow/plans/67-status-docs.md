# 67: Status text, anchors and dead config

Goal: make the spec and guide status lines match what `src/` builds, fix two broken anchors and remove dead tool configuration, under [#67](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/issues/67).

Tier: Fast lane. These are status text, anchor and dead-config changes only. No acceptance criterion, behaviour or security control changes. Targeted checks; the human reviews the diff. Base `ebd890c`.

Confirmed items (sweep IDs; re-checked against the base on 2026-11-03):
- **D4** stale status lines: `PRODUCT-SPEC.md:3` ("planned"); `product/platform.md:59-61` "Planned work" (all built); `TECHNICAL-SPEC.md:3,7,12,87`; `SECURITY-SPEC.md:3`; `product/results.md:3` (omits RES-4); `ai/context-comparison.md:5` ("will hold"). Prefer one short sentence linking the area specs over feature lists.
- **D5** anchors: `TECHNICAL-SPEC.md:75` and `SECURITY-SPEC.md:72` → `ai/llm-gateway.md#limits-and-accounting-proposed` (heading "Limits and accounting (proposed)"). Fix the anchors only.
- **D3** `docs/DeveloperGuide.md:5` app summary and `:303` "plans to use SoC LLM".
- **A4/T10** `pyproject.toml` per-file ignores `**/*_test.py`, `**/tests.py` and `**/settings.py` match no file (settings is the `relay/settings/` package; `find` outside `.venv` finds none); remove them. `pytest.ini:1-3` comment to present tense.

Checkpoints:
1. `plan: Plan #67 status and docs cleanup (#67)`: this file.
2. `spec: Bring spec status lines up to date (#67)`: `workflow/specs/**` (D4, D5). Checks: every changed link/anchor resolves to a heading slug; `git diff -U0 ebd890c -- workflow/specs | grep '^[-+].*\*\*[A-Z]\+-[0-9]'` empty (no criterion line changed). Result: pending.
3. `docs: Correct Developer Guide app summary (#67)`: `docs/DeveloperGuide.md` (D3). Checks: as for 2. Result: pending.
4. `chore: Remove unmatched lint ignores (#67)`: `pyproject.toml`, `pytest.ini`. Checks: `ruff check .`, `ruff format --check .`, `pytest --collect-only -q | tail -1` (2857 at base). Result: pending.

Decisions: none beyond the confirmed list. Out of scope (held for the human): `test-drafting.md:85,89`; the `TECHNICAL-SPEC.md:75` words "proposals pending confirmation"; `TECHNICAL-SPEC.md:150`; the drafting "closes its database connection" wording; the RND-4/RES-1.3 vs PLT-4.9 label order; `DeveloperGuide.md:233`; `README.md`, `docs/index.md`; criterion marking.

Open: any further stale line found in these files is fixed if it is plain status text, otherwise listed in the handoff.
