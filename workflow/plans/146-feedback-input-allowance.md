# Slice 146: feedback input allowance

Goal: accept valid maximum saved observations and complete published case context within the shared AI input allowance.

## Scope and decisions

Why: complete valid source exceeds the old allowance. After automatic approval review initially rejected the contract edit for missing specific authorization, the human explicitly approved the 32,768-character inclusive shared cap. Existing refusal, authorization, quota, timeout, output and no-truncation rules remain. No service, credential, dependency or live call is added.

High tier; total budget 100-200 added/deleted lines, including 35-45 reserved for coordinator evidence, and at most 400 changed production source lines. Stop affected additions for confirmation if exceeding that budget. RES-4.3 needs no wording change. CTX-1.3 is the sole edited criterion: align its inherited shared-limit reference without adding comparison obligations. Drafting's contract likewise links to the shared limit. Source limits and UI journeys remain unchanged.

Independent calculation from RES-2.2 and RND-2.4/.5: 2,000 observation + 120 title + 2,000 steps + 1,000 expected-result + 20 x 500 criterion characters = 15,120 raw source characters. Current instructions contribute 1,837 and JSON structure/separators 172, giving 17,129 ordinary or 32,249 fully quote/backslash-escaped characters. Cleaning never expands source; retained newline/tab escapes also occupy two characters. The new allowance has 519 characters of headroom for the current instruction version.

Provider capacity remains unverified: coordinator found public model-card capacity evidence, but served context may be lower and the SoC guide denied access. Static measurements and fake-provider tests establish no live readiness. Existing failure fallback remains; no provider configuration change or live check is authorized.

## Commit checkpoints

1. **Spec/plan:** four AI contracts and this plan; inspect code/tests, independently calculate maximum size, read back changes, whitespace/scope checks, then yield before implementation. Base `245e6445340a5d1442821064ba36cea79b6c4eec`; branch `feat/146-feedback-input-allowance`. Coordinator owns commits and supplies fresh snapshots.
2. **Implementation and regressions:** change only the shared constant in `src/ai/gateway.py`; align feedback/gateway boundaries and context-command oversize fixture; update feedback view coverage to accept maximum ordinary/escaped source and refuse truly over-cap synthetic stored input. Check full JSON round-trip observation/case text and all 20 criteria, plus no reservation/provider call above cap. Reuse RES-4.3, RND-8.4 and CTX-1.3. Run focused regressions before the constant change, record meaningful failures, then implement and run focused suites/Ruff. Yield red/green evidence before coordinator commit.
3. **Integrated evidence:** read back contracts/plan, assess guide impact, run full `ruff check . && ruff format --check . && pytest` using the existing absolute venv in Git Bash, report exact failures, scope/whitespace checks and usage. Coordinator freezes independent review/security candidate and owns logs/delivery. No installation, live provider call or Git mutation by builder.

## Checkpoint evidence and next step

Inspected feedback/gateway code, source limits, feedback/gateway/view tests and context-command preflight fixture. Existing view oversize fixture is valid under the new cap; preserve rejection with separate over-cap input. No code/tests edited or tests run at this checkpoint. Actual final checks/usage belong in the handoff/log. Next: coordinator commits specs and assigns implementation with fresh snapshot.

Hook observations: simulated builder `AGENTS.md` edit refused without modification; actual helper patch refused because `tmp/` is outside builder writes. No helper created or retry attempted. Shell-write enforcement is not established. Static serialization arithmetic required no helper/provider. Usage baseline followed initial instruction/source inspection; coordinator records that incomplete initial coverage.
