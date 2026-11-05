# #67 spec consistency

Goal: make the specs agree with each other and with the built code for the held items 3, 4, 5, 6 and 11 of the [cleanup sweep](67-cleanup-sweep.md), with no code, test or behaviour change.

Tier: High (the release gate and the wording of development security controls). Base: `26e77cc`. Branch: `67-spec-consistency`. Budget: 0 `src/` lines. Builder writes only `workflow/specs/**` and this plan.

## Decisions (orchestrator, under the human's instruction to decide the held items)

1. **Connection release.** The specs say what is built: `gateway.complete` releases the request's database connection after reserving and before the call (`src/ai/gateway.py`, pinned by `test_the_drafting_view_holds_no_connection_during_the_call`), and no view holds a lock or transaction during the call. The rule's home is [`llm-gateway.md`](../specs/ai/llm-gateway.md#limits-and-accounting-proposed); TECHNICAL-SPEC's AI drafting paragraph and `test-drafting.md` Limits link there. The feedback view's own extra close stays described where it is.
2. **Gateway contract status.** `llm-gateway.md` is the home; its rules are implemented, but confirmation of their design by #6 and the human is still pending ([plan 22, human decision 3](22-test-drafting-spec.md#human-decisions-2026-10-29-confirmed)); only the provider terms are confirmed. `test-drafting.md`'s requirements intro and TECHNICAL-SPEC's AI gateway table intro stop calling the gateway's answers proposals and link to it without implying confirmation.
3. **Function time limit.** `vercel.json` sets `maxDuration` 60; the gateway's bound is 30 s plus a 5 s release margin. The release gate requires a verified function time limit of at least 60 seconds, above both the limit timeouts plus a password hash and the AI bound plus margin. `test-drafting.md` need 2's open note closes.
4. **Case label order.** RND-3/RND-4 prose and RES-1.3 put "Current build" in the case summary, before the expanded "Linked acceptance criteria", as PLT-4.9 and the templates do. RND-3's round-page sentence (`rounds.md`, "after its linked criteria") has the same disagreement and is fixed with it; RND-3.1's test already pins the built order.
5. **`.env.example`.** TECHNICAL-SPEC describes it as non-secret local defaults and empty placeholders.
6. **Criterion marking.** CTX-1.6 and DWF-1.6 get `[manual]` with a reason, as PLT-1.14 does; CTX-1.6 points to the experiment report. SECURITY-SPEC states that the automated DWF-1 checks are `unittest` tests in `workflow/scripts/test_check_scope.py` naming the criterion in their docstrings. PLT-2.6 stays untagged, keeping log 009's choice that hosted checks can be automated; its open coverage gap is recorded only under Open items.

## Commit checkpoints

1. `plan:` this file.
2. `spec:` items 1–3: `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/ai/test-drafting.md`, `workflow/specs/ai/llm-gateway.md`. Checks: links/anchors resolve; `git diff -U0` criterion lines; `src/ai/tests/test_views.py` and `src/relay/tests/test_configuration.py` through the database lock.
3. `spec:` items 4–6: `workflow/specs/product/rounds.md`, `workflow/specs/product/results.md`, `workflow/specs/product/platform.md`, `workflow/specs/ai/context-comparison.md`, `workflow/specs/SECURITY-SPEC.md`, `workflow/specs/TECHNICAL-SPEC.md`. Checks: as above, plus the files marked with each changed criterion, then full verification (base: 2869 passed, 254 subtests).

## Open items

- PLT-2.6 has no automated test: its hosted evidence is in log 009, and automating the hosted check remains an open coverage gap (orchestrator decision: do not tag it `[manual]`).
- `test-drafting.md`'s opening says its own contract "awaits confirmation by the human and the gateway owner". That is the drafting contract, not the gateway's, so it is out of this slice.

## Progress

- Checkpoint 1: plan written (`7c35c03`). Orchestrator then kept PLT-2.6 untagged and confirmed the RND-3 sentence fix.
- Checkpoint 2 (items 1–3, `89b88a8`): `llm-gateway.md` Limits holds the connection-release rule; TECHNICAL-SPEC's AI drafting paragraph and `test-drafting.md` Limits link to it. The gateway table intro and `test-drafting.md`'s requirements intro no longer call the gateway's answers proposals. The release gate requires at least 60 seconds; need 2's open note is closed. No criterion line changed. Links resolved; dblock `src/ai/tests/` and `src/relay/tests/test_configuration.py` gave 733 passed.
- Checkpoint 3 (items 4–6, `6444fc6`): RND-3 and RND-4 prose and RES-1.3 put "Current build" in the case summary, linking PLT-4; TECHNICAL-SPEC describes `.env.example` as non-secret local defaults and empty placeholders; CTX-1.6 and DWF-1.6 are `[manual]` with reasons; the DWF-1 intro states the `unittest` docstring convention. DWF-1.6 also has one docstring-marked test (main and unknown roles unenforced), so its reason excepts that test. Changed criterion lines: DWF-1 (intro), DWF-1.6, CTX-1.6, RES-1.3.
  - Full verification on that candidate: `ruff check .` and `ruff format --check .` passed; dblock `pytest -q -p no:cacheprovider` gave 2869 passed, 254 subtests passed. Focused: rounds/tester/review/publish modules and their e2e modules 170 passed; `unittest discover -s workflow/scripts -p test_check_scope.py` 27 OK.
- Review of `6444fc6` (verifier and security reviewer). Accepted findings, repaired in round 1 (spec and plan only):
  - Verifier M1: the gateway design was not confirmed; `llm-gateway.md` now says its confirmation by #6 and the human is pending, and `test-drafting.md` no longer implies confirmation.
  - Security L1: the release gate states that an AI request's work outside the gateway deadline (reservation lock wait, reconnect, feedback re-read) is assumed to fit the remaining headroom and is not measured.
  - Verifier L1: RES-1.3's "case summary" links to PLT-4. Verifier L2: the PLT-2.6 note left `platform.md`; its home is this plan. Verifier N2: need 2 links to the gate's limit instead of repeating 60 seconds. Verifier N1: this record.
  - Verifier L3 accepted as is: the planned bundling of items into two `spec:` commits stays, with no history rewrite.
