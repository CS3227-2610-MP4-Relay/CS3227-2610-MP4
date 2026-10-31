# Slice 28: live injection evaluation

Goal: measure exact marker following by SoC LLM under the existing drafting and feedback contracts, using [SEC-INJ-1](../specs/SECURITY-SPEC.md#sec-inj-1-operator-live-injection-measurement).

Why: fake-provider injection regressions establish application boundaries but provide no observation of instruction following by the configured live model.

## Scope and decisions

- High tier; branch `slice/28-live-injection-evaluation` starts at `2ccbe9d45cc2f69affda0faeedb46151de2180a3` on PR #100's `slice/24-prompt-injection-ci` branch. Normal slice delivery is authorized; only the coordinator changes Git/GitHub state.
- Human explicitly approved the narrow payload-decoding exception and use of the existing local configuration loader without exposing secrets. The coordinator owns the corresponding `AGENTS.md` change and session log; the builder preserves both. No direct secret/dotenv inspection.
- One internal evaluation requirement, zero product requirements; no dependency, service, credential, production prompt, UI journey, CI network exception or defense subsystem added. Existing broad feature-quality evaluations remain pending. Exact measurement semantics and limits live only in SEC-INJ-1.
- Estimated whole-slice diff: 450–650 changed lines including documentation/logs; at most 320 non-test source lines. Aim near 500 builder lines to leave evidence room. Stop affected work if confirmed scope/estimate needs expansion.
- Proposed implementation homes: `src/ai/evaluation.py` for corpus/encoding/scoring, `src/ai/management/commands/evaluate_injection.py` for operator execution, and `src/ai/tests/test_evaluation.py` for offline regressions. Reuse current gateway and feature helpers; no provider shortcut or stored source/reply artifacts.
- Operating burden: existing local configuration/database and an existing local user; one pass consumes at most 12 calls of their existing shared quota. Sequential deadlines permit roughly six minutes of provider waiting plus local overhead. Quota/configuration/transport failures limit coverage and never justify retries or quota bypasses. Only the coordinator runs the live command after offline checks and review; synthetic inputs only.
- Coordinator will use the normal local loader with process database overrides for the throwaway loopback cluster at `127.0.0.1:55432`, migrate it and seed a synthetic operator outside application code. The command accepts that existing user's ID; no user creation, database configuration or recovery feature is added.

## Commit checkpoints

1. **Specs and plan** — `spec: Define bounded live injection measurement (#28)` (`Agent: builder`, body starts `Why:`). Paths: `workflow/specs/SECURITY-SPEC.md`, this plan. Read changed sections back, run `git diff --check` and builder scope check against supplied snapshot. Yield before implementation.
2. **Corpus and scoring** — `test: Measure injection markers with feature validators (#28)`. Paths: `src/ai/evaluation.py`, `src/ai/tests/test_evaluation.py`. Add criterion-marked offline tests first and record meaningful missing-behavior failures, then implement fixed cases and distinct raw/accepted scoring. Cover controls, cleaning removal, field framing, malformed/schema-rejected replies, marker absent/present and unavailable results. Run focused pytest/Ruff; yield before commit.
3. **Operator command** — `feat: Add explicit live injection evaluation command (#28)`. Paths: `src/ai/management/**`, evaluation module/tests as needed. Test preflight and command execution with fake gateway calls before implementing. Verify absent flag/invalid configuration/user make zero calls, exact sequential corpus/no retries, unchanged domain records and summary without text leakage. Run focused pytest/Ruff; yield before commit.
4. **Guide and integrated evidence** — `docs: Explain operator injection measurement (#28)`. Paths: `docs/DeveloperGuide.md`, this plan; coordinator owns session log. Apply maintain-docs when assigned; link to SEC-INJ-1 and document the actual command. Read edited sections back, run Django check and full `ruff check . && ruff format --check . && pytest` in Git Bash with `.venv` active. Report every failure; coordinator freezes the candidate for independent review, then runs the approved live command and records summary evidence and hosted validation. Any repair returns through focused checks/review before delivery.

All pytest execution uses fixed test settings and the existing loopback PostgreSQL; no live test or new browser journey is introduced. Builder does not delegate or mutate Git and waits for a fresh coordinator snapshot between checkpoints.

## Evidence and next step

Coordinator supplied inherited injection baseline: `pytest -m prompt_injection -q` passed 95 tests, 2438 deselected, in 4.28s. This is offline evidence, not a live-model result. No implementation or live evaluation has run for this slice.

Next: coordinator reviews/commits the specification checkpoint and supplies a new snapshot before assigning corpus/scoring. Live configuration availability and actual provider outcomes remain unverified. Record actual checks, revisions, review limits and summarized measurements here or in the coordinator's session log as they occur; never claim pending checks passed.
