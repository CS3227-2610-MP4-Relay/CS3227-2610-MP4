# Slice 59: Settle the remaining sign-in limit residuals (#59)

Goal: record the human's decisions on the three residuals the ACC-3 security review left open ([security spec](../specs/SECURITY-SPEC.md#sign-in-and-access-control)), with no change to behaviour, criteria or controls.

Tier: Fast lane. Base: `9afbb51`, branch `59-sign-in-limit-residuals`, stacked on ACC-3's #52 (`4-limit-abuse`). Owner: zheng-jj. Budget: no `src/` change; actual 0.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27:

- **IPv6 grouping:** keep counting per `/64`. A `/56` or `/48` (often a whole campus) would put more legitimate users on one count, and [ACC-3](../specs/product/accounts.md#acc-3-limit-abuse-of-sign-in-and-demo-workspace-creation) requires peers in one lab to be able to share an address.
- **Per-username cap:** none. Generated passwords are about 95 bits, and a cap would let anyone who knows a username lock that account out.
- **Logging** of refusals and of requests counted under the `unknown` key: left to #5 (deployment). Recorded once, as a SECURITY-SPEC residual; the [release gate](../specs/TECHNICAL-SPEC.md#release-verification) already requires observing that no production request uses `unknown`, so it is unchanged. The ACC-3 plan's deferral note is frozen with that slice and left as is.

## Checkpoints

1. **Specs and plan** (`spec:`/`plan:`): `workflow/specs/SECURITY-SPEC.md` (ACC-3 residuals), this plan. Checks: `git diff --check`; `python workflow/scripts/check_scope.py builder --base 9afbb51`; read back. Fast lane: human diff review.

## Open issues

None.

## Checklist

- [x] Checkpoint 1: specs and plan.
