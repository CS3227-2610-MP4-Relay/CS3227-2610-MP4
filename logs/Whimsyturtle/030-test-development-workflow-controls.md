# Test development workflow controls

Slice: #29 · Tier: High · Tool: Codex · Orchestrator model: gpt-6.1-sol / xhigh (observed turn metadata) · Date: 2026-11-01

Tokens: 4,754,001 input, 26,915 output, 4,780,916 total; selected-source interval ending 2026-11-01 22:37:05 SGT.

| Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Orchestrator — gpt-6.1-sol/xhigh, `codex:f167e58ba411bd9a3137f5ca` | 3,108,551 | 3,049,856 | 17,794 | 6,051 | 3,126,345 | 15m04s measured interval |
| Approval reviewer — codex-auto-review/low, `codex:b4626566c0263d1724fbfe82` | 673,224 | 615,680 | 1,721 | 601 | 674,945 | 14m35s recorded span |
| Builder — gpt-6.1-sol/medium, `codex:a927dc118e65959442eb1e3d` | 244,100 | 181,632 | 2,852 | 194 | 246,952 | 2m02s recorded span |
| Verifier — gpt-6.1-sol/high, `codex:9f0122e2d6886d5117590621` | 478,025 | 425,088 | 2,451 | 725 | 480,476 | 2m19s recorded span |
| Security reviewer — gpt-6.1-sol/high, `codex:149f8dfb6fbee9a9f0728c99` | 250,101 | 204,928 | 2,097 | 671 | 252,198 | 1m40s recorded span |

Three delegated role sessions plus the automatic approval reviewer; observed settings matched the role adapters. Coordinator selected the current session and related sources in the explicit session-day/project boundary with `resource_usage.py`. Five measured sources, no collector warnings, zero cache-write tokens and zero review repair rounds. The baseline followed initial discovery (22:22:01 SGT); earlier work and work after the cutoff are excluded. Role-local usage was unavailable because source selectors were not supplied; the combined report covers them. Spans include waiting and overlap; see [accounting definitions](../../workflow/README.md#token-reporting).

## Requests

Run `/slice 29`: test existing development-workflow controls against malicious content. The issue was authored by a repository MEMBER and had no comments. No additional capability or enforcement system was requested.

## Agent runs

- **Coordinator:** prepared clean `main` at `505b95d`, created `slice/29-workflow-control-tests`, chose High tier and tracked usage. Supplied scoped controls, paths, budget, commit checkpoints and private scope snapshots. Reviewed/staged each checkpoint before committing: spec/plan `9536f79`, tests `ae2921e`. Implemented workflow tests itself because those paths are outside builder writes. No dependencies, hosted settings or app code changed. Disposable PostgreSQL used the installed 18.6 image, loopback 55432 and fixed synthetic test credentials; no dotenv read or image download. Full `ruff check . && ruff format --check . && pytest` passed: 131 files formatted, 2,755 passed, one existing symlink skip in 585.85s. Workflow unittest passed: 105 passed, one existing skip in 33.369s. Log structure and diff whitespace checks passed.
- **Builder:** triggered for spec/plan only, using `workflow/agents/builder.md` at base `505b95d` (SHA256 prefix `7c1721cdc888`). Context: request/title data, High tier, DWF obligations/limits, unchanged scope implementation/tests, expected diff and ownership. Updated security verification IDs and plan. Readback, `git diff --check` and post-run builder scope passed. Assessed the proposed prohibited `AGENTS.md` edit and refused without a mutation attempt; no claim of native hook execution. Its attempted usage commands lacked selectors and failed; coordinator accounting supplies measured usage.
- **Verifier:** triggered for independent review of fixed `505b95d..ae2921e`, using `workflow/agents/verifier.md` at the same base (hash prefix `dc3d558e9db4`). Context: criteria, exact diff/candidate manifest, commit order, builder handoff, supplied focused/workflow checks and pending full/hosted status. Independently inspected code, assertion strength, helper collection, scope, size and reporting. Independently ran candidate comparison and whitespace check; no findings, no edits and no repairs. Full/hosted checks were pending at its cutoff, not independently rerun.
- **Security reviewer:** triggered by development-security scope, using `workflow/agents/security-reviewer.md` at the same base (hash prefix `3e7ee3da2a29`). Same fixed candidate and relevant controls/adapters supplied as data. Independently inspected malicious fixtures and implementation, ran focused tests (27 run, 26 passed, one existing symlink skip), role scope and candidate/whitespace checks; no findings or repairs. No real provider or secret access. Wider check results were supplied evidence.
- **Approval reviewer:** automatically triggered by escalated shell operations. Observed `codex-auto-review`/low metadata; no repository edits. It is an automated execution review, not human approval routing.

Review manifest SHA256: `38461ba71d5eaafdd119776909f79f729b2e40f693ce7d9c73c8c380ac6af563`. Post-run verifier/security scope checks passed; fixed candidate stayed unchanged. The reviewed diff has 201 changed lines and no `src/` changes. Required-check evidence is reused only for unchanged code/inputs; later changes are summary records.

## Decisions and corrections

- Formalize existing security obligations as DWF-1.1–DWF-1.6; preserve the hook implementation and disclosed gaps. No browser coverage added because no UI journey changed.
- Payloads stay base64-escaped in source and decode only in tests. The synthetic guard is a `.py` helper outside normal discovery; its asserted failing-to-passing mutation demonstrates that path scope and green tests cannot judge assertion quality. Fixed-candidate comparison catches the edit.
- Tests mark verification IDs in docstrings; the plan maps them to assertions. Existing controls passed new coverage before any enforcement change, so no missing-behaviour failure was manufactured.
- Keep subprocess decisions, snapshot observations and the one requested role refusal distinct from native hook dispatch, trust, permissions, prompt routing or broad malicious-instruction resistance. Current effective reviewer is `auto_review`; the project file does not change the active session.
- [Draft PR #115](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/115) is the delivery record. Required `verify` (GitHub Actions app 15368) and `site` passed on `ae2921e` in [run 41316668403](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/41316668403); deployment jobs correctly skipped on the PR. Check its final summary head and record that result in the PR/delivery response; leave human log review, merge and release decisions pending.

## Problems

- Sandbox restrictions initially blocked Git ref writes, network reads and Docker access. Authorized operations succeeded through reviewed escalation. The connector returned 403 for PR creation; authenticated CLI fallback created the draft. No automatic-approval rejection remained unresolved.
- Initial focused Ruff found three implicit-string-concatenation and two missing explicit subprocess `check` issues; corrected before the test commit. Focused tests then passed (26 passed, one existing skip); workflow unittest passed (105 passed, one existing skip). No implementation repair round was needed.
- Native client trust/hook dispatch, read prevention, human prompt routing, arbitrary malicious-instruction resistance, Unicode and cross-user attacks were not verified. Missing/unknown metadata, shell writes, ignored files and allowed assertion weakening remain stated control limits.
- Untrusted content seen: encoded fixture claims of maintainer authority, role delimiter spoofing and requests to weaken assertions or falsify verification. These remained test data; no such instruction was followed. No raw transcript, malicious prompt or real secret is retained here.
