# Protect the default branch and require checks before merge (#8)

Goal: require a reviewed pull request with a passing `verify` check before changes reach the default branch, and enable secret scanning with push protection.

Tier: High, because this changes a development security control at the CI/merge boundary. Base: `d1cbde40b5400919eaec1ce1283f69f95e2246bc`.

Decisions before implementation (human, zheng-jj): use classic branch protection on the default branch, currently `main`. Require a pull request with one approving review and stale-review dismissal; no code-owner review or last-push approval. Require the `verify` status check from GitHub Actions without requiring the branch to be up to date, matching MP3 practice. Enforce for admins; emergency bypass is an admin temporarily disabling the rule in Settings. Block force pushes and deletion. Enable secret scanning and push protection. The control's home is [SECURITY-SPEC CI and dependencies](../specs/SECURITY-SPEC.md#ci-and-dependencies). No product criteria apply: this is a repository control, not product behaviour.

Out of scope: hosted environment restrictions (none exist yet; they stay future work), merge-method settings, rulesets, CODEOWNERS, GitHub Pages, the default-branch rename (#7) and any script or automated check of hosted settings.

Ownership: builder updates the two specs and this plan. The coordinator applies the hosted settings, runs the manual checks below and records results. Under the High tier, the verifier and security-reviewer each review the fixed candidate and re-review the range changed by repairs. No code, tests, dependencies or guide changes are needed.

Budget: three security-spec bullets, two technical-spec lines and this plan; about 9 changed spec lines and a plan of about 52 lines. The growth beyond the original estimate of about 40 lines came from review repairs and recorded evidence.

- [x] Update the security control and the operator-prerequisite bullet; read changed sections back.
- [x] Run full verification and `git diff --check` on the spec candidate.
- [x] Coordinator applies branch protection, secret scanning and push protection.
- [x] Coordinator runs the manual verification below and records actual output.
- [x] Round 0: verifier and security-reviewer review the candidate.
- [x] Round 1: verifier and security-reviewer re-review the repaired range.
- [ ] Round 2: verifier and security-reviewer re-review the repaired range.
- [ ] Human merge decision.

Manual verification (cannot be automated here: the settings are hosted on GitHub, outside pytest and CI, and reading them needs an authenticated admin API call):

1. `gh api repos/CS3227-2610-MP4-Relay/CS3227-2610-MP4/branches/main/protection` shows one required approving review, stale-review dismissal on, code-owner review and last-push approval off, `bypass_pull_request_allowances` and `dismissal_restrictions` empty or null; required check `verify` bound to GitHub Actions (`app_id` 15368) with strict (up to date) off; `enforce_admins` on; force pushes and deletions disallowed; and required signatures, linear history, conversation resolution, block creations, lock branch, fork syncing and push restrictions off or null.
2. `gh api repos/CS3227-2610-MP4-Relay/CS3227-2610-MP4 --jq .security_and_analysis` shows `secret_scanning` and `secret_scanning_push_protection` enabled.
3. After this slice's PR is opened, `gh pr view <n> --json mergeStateStatus,reviewDecision` reports `reviewDecision: REVIEW_REQUIRED` and `mergeStateStatus: BLOCKED`, with the PR's `verify` run concluding SUCCESS. Re-query if GitHub reports `UNKNOWN`.
4. With the human's approval, the coordinator pushes one empty commit, built on the current `main` without moving any local branch, directly to `main`, and expects GitHub to reject it as a protected branch. This tests that the rules bind admins. If it were accepted, only an empty commit would land; record that outcome and stop.

Open items and verification limits:

- Agent sessions using an admin's credentials can change or bypass these settings; gating this is issue #40, not part of #8.
- `test_child_discovery_is_bounded_by_ancestry_and_project` fails on macOS (`/var` versus `/private/var`); tracked in issue #39, not part of #8.
- Open question, not decided: push protection is configured but not exercised with a synthetic secret, although the [security spec](../specs/SECURITY-SPEC.md#development-workflow) calls for synthetic-secret tests of development controls; whether to accept that gap or test it.
- Open question, not decided: whether an emergency bypass must be recorded and the rule re-checked afterwards.
- Issue #7 must keep these protections, including `ci.yml`'s `push: branches: main` trigger, on any renamed default branch.
- Configuration readback and the checks above are not proof that every path is enforced.

Check evidence: on macOS with Python 3.14.7, Ruff lint/format passed and pytest reported 69 passed and 1 failed. The failure, `test_child_discovery_is_bounded_by_ancestry_and_project`, also fails on a clean export of the base: `/var` and `/private/var` resolve differently on macOS. CI passed on the base. `git diff --check` is clean, and the builder's scope check passed. Before applying the settings at 2026-10-26T07:10Z, the coordinator read the builder's spec diff and ran the builder scope check; no file timestamps were recorded.

Readback for step 1, from the protection endpoint projected with `--jq`:

```json
{"allow_deletions":false,"allow_force_pushes":false,"allow_fork_syncing":false,"block_creations":false,"checks":[{"app_id":15368,"context":"verify"}],"enforce_admins":true,"lock_branch":false,"required_conversation_resolution":false,"required_linear_history":false,"required_signatures":false,"restrictions":null,"reviews":{"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"require_last_push_approval":false,"required_approving_review_count":1},"strict":false}
```

`.required_pull_request_reviews` showed `bypass_pull_request_allowances` and `dismissal_restrictions` as `null`. The organisation has no installed GitHub Apps. For step 2, `secret_scanning` and `secret_scanning_push_protection` are `enabled`; non-provider patterns, validity checks and Dependabot security updates are `disabled`. `branches/main` reports `protected: true`.

Step 3, on [PR #41](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/41) at head `b02e843`: `mergeStateStatus: BLOCKED` and `reviewDecision: REVIEW_REQUIRED`, while `verify` [concluded SUCCESS](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40285610616/job/121448429746). That Linux CI run at head `b02e843` passed full verification. At head `a7f92c7`, `verify` also [concluded SUCCESS](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40285727936/job/121448799036) (run 40285727936), with PR #41 still `BLOCKED` and `REVIEW_REQUIRED`.

Step 4, at 2026-10-26T07:24:56Z, with the human's approval, the coordinator agent, authenticated as admin zheng-jj, pushed probe commit `35ce6b1` (empty, parent `d1cbde4`, built with `git commit-tree`) to `refs/heads/main`. GitHub rejected it with `GH006: Protected branch update failed`, listing "Changes must be made through a pull request" and "Required status check "verify" is expected". `origin/main` stayed at `d1cbde4`. An earlier attempt failed locally before contacting GitHub, because zsh read `$C:r` in the refspec as a modifier.
