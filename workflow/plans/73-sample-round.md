# Slice 73: Sample draft round in a new demo workspace (#73)

Goal: every new demo workspace gets one Draft "Sample round" with 3 acceptance criteria and 4 linked test cases of fixed synthetic text, written inside the demo creation transaction ([RND-7](../specs/product/rounds.md#rnd-7-sample-draft-round-in-a-new-demo-workspace), [ACC-2.5](../specs/product/accounts.md#acc-2-create-an-isolated-demo-workspace)).

Tier: Standard, with a security review (it changes what `/demo/` writes inside its limited transaction). Base: `01f9a24`, branch `73-sample-round`. Owner: zheng-jj. Budget: RND-7.1 to RND-7.4 as specified (RND-7.5 stays retired); estimate about 70 lines of `src/` outside tests.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27: build RND-7 as already specified; nothing beyond the spec.

Builder's details within that scope (checkpoint 1):

- **Where:** new `src/rounds/sample.py` holds the fixed text as constants and `create_sample_round(workspace)`; `accounts.demo.create_demo_workspace` calls it inside its savepoint, after writing the accounts. No import cycle: `rounds.sample` imports `rounds.services` and `rounds.models`, which import only `accounts.models`.
- **Shared services:** `create_round` (workspace lock and round cap), then the new round row locked with `select_for_update` as `add_criterion` and `add_case` require, then 3 `add_criterion` and 4 `add_case` calls, so caps and same-round links are enforced. The rows are uncommitted, so no other transaction can wait on these locks; the limit locks are already held, as the [limited transactions](../specs/TECHNICAL-SPEC.md#accounts-and-workspaces) allow for writing during creation.
- **Text home:** the RND-7.1 criterion leaves the text unspecified ("fixed, synthetic"), so its one home is the `rounds.sample` constants, and TECHNICAL-SPEC points there. ASCII only, about a fictional to-do app; every case linked to at least one criterion, every criterion linked by at least one case. The User Guide quotes only the title and counts.
- **Specs changed:** status lines in `product/accounts.md` and `product/rounds.md`; TECHNICAL-SPEC opening, Creation (no "RND-7 adds"), Round creation ("later" removed) and the Sample round bullet; SECURITY-SPEC opening and the round-creation bullet. No criterion is added or changed.

## Checkpoints

1. **Specs and plan** (`spec:`/`plan:`): the four spec files above and this plan. Check: `git diff --check`; read back.
2. **Sample round** (`feat:`): `src/rounds/sample.py`, `src/accounts/demo.py` (call and docstring). New `src/rounds/tests/test_sample_round.py`:
   - RND-7.1: one round per new workspace, titled "Sample round", Draft, 3 criteria, 4 cases, each case linked, every field valid under the round forms' shared field (limits, visible text) and ASCII; identical text in two workspaces; the Coordinator home lists "Sample round (Draft)".
   - RND-7.2: publish with only a build label through the route ("Round published.", all 4 cases on that build); before that, retitle, edit a criterion and add a case through the routes like any Draft round.
   - RND-7.3: 19 more rounds created through `create_round`, the next one through the route gets the RND-1.4 message.
   - RND-7.4: two demo workspaces; editing, publishing and closing one's sample round leaves the other's round, criteria, cases, links and builds unchanged; the other coordinator gets 404 for it.
   ACC-2.5 additions: `test_demo_views.py` `FAILURES` gains a "sample case write" failure (a storage error on the third `add_case`); `counts()` also counts rounds, criteria, cases and links, so every nothing-left check covers the sample round; `test_demo.py` gains a sample-write failure outside a transaction. Expected red: every new test, the ACC-2.5 failure cases included, because without a sample round the patched `add_case` is never reached and creation succeeds. The widened `counts()` passes beforehand; it detects a sample row left behind once the sample exists. Existing tests: `counts()` literals `(1, 3)` and `(0, 0)` in `test_demo_views.py` widen to the new tuple; each change listed in the handoff. ACC-3 limit and concurrency modules run unchanged. Checks: each affected module alone against 127.0.0.1:55432; Ruff on changed files; non-ASCII scan of changed `.py` files.
3. **Guides** (`docs:`): `docs/UserGuide.md`, where the demo workspace is described: the "Sample round" in Draft with 3 acceptance criteria and 4 test cases, ready to publish or edit, and counting toward the 20-round limit. `docs/DeveloperGuide.md`: one sentence where it describes demo creation. Check: read back; `git diff --check`.

## Open issues

- None.

## Checklist

- [x] Checkpoint 1: specs and plan (on `01f9a24`).
- [x] Checkpoint 2: sample round (on `1513b70`). New `rounds/sample.py` (constants and `create_sample_round`, 90 lines); `accounts/demo.py` calls it inside its savepoint (+5/-2). New `test_sample_round.py`, 9 tests. Red before the code: 9 failed (7 `Round.DoesNotExist`, the RND-7.3 count 18 != 19, the coordinator home's empty list); `test_demo_views.py` sample-write failure and success count, and `test_demo.py` sample-write failure, failed. Green: all pass. Existing tests changed: `test_demo_views.py` `counts()` also counts rounds, criteria, cases and links, so its `(0, 0)` and `(1, 3)` literals became `NOTHING` and `ONE_WORKSPACE`. Mutations, restored and checked with `cmp`: sample call outside the savepoint fails the `test_demo.py` failure test; a criterion left unlinked fails the RND-7.1 structure test; a non-ASCII character fails the RND-7.1 text test. Each accounts, rounds and relay test module alone: passed. Ruff clean; no non-ASCII characters in changed `.py` files.
- [ ] Checkpoint 3: guides.
