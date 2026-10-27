# Slice 22: Test-drafting contract (spec only) (#22)

Goal: settle the test-drafting AI feature's contract, its pages as [RND-8](../specs/product/rounds.md#rnd-8-draft-test-cases-with-ai) and its [AI contract](../specs/ai/test-drafting.md), so it can be built once the [gateway](../specs/ai/llm-gateway.md) (#6) exists.

Tier: High (AI feature contract), with a verifier and a security review. Base: `20f4ea7`, branch `22-test-drafting-spec`. Owner: zheng-jj. Specs only: no code, tests, dependency, prompt file or guide change; `ai/llm-gateway.md` is the gateway owner's (Whimsyturtle) and is not edited.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27: write the contract now with sensible defaults, each listed for the human and Whimsyturtle to confirm in the PR; gateway decisions (model, endpoint, quota, time, retries, caching, telemetry) stay in the gateway contract, and drafting states only what it needs from it.

### Coordinator defaults

Each is a **coordinator default, pending human and Whimsyturtle confirmation**. Checkpoint 1's D3 (hidden characters) and D7 (adoption) are now builder proposals B4 and B3.

- **D1 Home:** the pages and criteria are a new requirement, RND-8, in `product/rounds.md`, because drafting is a Draft-round coordinator action under the same rules; the model-facing contract stays in `ai/test-drafting.md`. Status: specified, not implemented, blocked on #6.
- **D2 Source:** the coordinator selects 1 to 5 of the Draft round's own criteria; only their current text is sent, labelled `C1` onwards in creation order, as a JSON data part separate from the instructions. No tester data, cases, titles, other rounds or workspaces, database IDs or usernames.
- **D4 Fixed instructions:** six required points in the contract (repair round 1: the exact wording and version name are added to the contract at the implementation slice's first checkpoint and reviewed before any code).
- **D5 Schema:** one JSON object `{"drafts": [...]}` of 0 to 5 drafts with exactly `title`, `steps`, `expected_result` and `criteria`; RND-2 limits and rule 5 after cleaning; `criteria` unrepeated sent labels; no repeated keys; reply at most 20,000 characters. Any failure rejects the whole reply.
- **D6 Messages:** "Drafting is unavailable right now. You can still add test cases yourself." for every failure, refusal, quota or invalid reply; selection messages "Select 1 to 5 acceptance criteria." and the existing "Choose criteria from this round.".
- **D8 Routes:** `/coordinator/rounds/<round>/cases/draft/` (GET, POST) and `.../cases/draft/use/` (POST), Draft only, under every round rule; POST with CSRF so another site cannot spend quota or plant a form.
- **D9 Calls and locks:** one gateway call per drafting request; no feature-level retry; no lock or transaction held during the call; nothing stored; logs carry only fixed codes.
- **D10 Evaluation:** automated cases with a fake provider are listed in the contract; the live usefulness and injection check on a small synthetic set is proposed as part of the gateway's live-check procedure.

Repair round 1 (on `13e8e75`), coordinator defaults under the human's "draft with defaults" instruction, pending human and Whimsyturtle confirmation:

- **D11 Instruction review (V-M1):** exact wording enters the contract before code, as in D4, so SECURITY-SPEC's "exact prompts ... belong in `ai/` before implementation" holds.
- **D12 Gateway quota and concurrency (V-M2, S-M1):** deployment-wide cap as well as per workspace or user; atomic reservation before the call, counting failures and timeouts; at most one drafting call in flight per user. Needs for #6, not settled here.
- **D13 Parser safety (S-M2):** any parse exception, `NaN`/`Infinity` and any surrogate code point make the reply invalid.
- **D14 Cleaning (S-L1, V-L7, V-L5):** the removal set is Default_Ignorable_Code_Point of Unicode 16.0.0 as a fixed table (checked against the local `DerivedCoreProperties-16.0.0.txt`), except ZWJ and ZWNJ, plus Cc except line feed and tab, plus Cs; the five blank fillers become spaces first; title line breaks become spaces. A criterion empty after cleaning is sent as an empty string under its label (builder's choice: it keeps labels in step with the selection and needs no extra message).
- **D15 Pre-fill (S-L2, V-M4):** the pre-fill view re-cleans posted text and checks only the URL round's criteria whose IDs equal a posted string, with no lookup on posted values; hidden fields are attribute-escaped only and round-trip exactly. It shows no rule-5 messages, recorded as an exception in RND-8.
- **D16 Encoding and size (S-L3, S-L4, V-L6):** the data part is built with a JSON encoder, `ensure_ascii=False`; worst case about 5,200 characters; the serialised request is measured before the call against 8,000, and an over-long request gets the unavailable message without a call. Labels match exactly.
- **D17 Error reports (S-L5):** criteria, instructions, data part and reply are sensitive variables, both POSTs use `sensitive_post_parameters`, and logs carry fixed codes only.
- **D18 Status and residual (S-L6, V-L1):** both drafting POSTs return 200 and do not redirect (exception noted in the rounds routes preamble). Reload resubmission spending another call is recorded as a residual in SECURITY-SPEC, pending confirmation.
- **D19 Criteria (V-L4):** RND-8.6 is split: selection of another round's or workspace's criterion becomes RND-8.8; pre-fill unchecking and re-cleaning are RND-8.9; the Draft-only round-page link joins RND-8.1. These IDs were never merged, so RND-8.6 is narrowed rather than retired.

### Builder proposals

Not in the coordinator's brief; proposed by the builder in checkpoint 1, pending human and Whimsyturtle confirmation:

- **B1 Empty reply:** a valid reply with no drafts is accepted and shows "No test cases were suggested for these criteria. You can still add test cases yourself.", giving the model an honest answer for untestable criteria.
- **B2 Cap before call:** a round at 30 test cases gets the existing cap message before any gateway call, saving quota.
- **B3 Pre-fill route:** "Use this draft" POSTs to a pre-fill route. A GET with query parameters was rejected (a full draft can exceed common URL limits, and query strings reach access logs), as was storing drafts in the session (that saves them).
- **B4 Remove, not refuse:** hidden characters are removed from input and reply rather than refused, so pasted text still drafts and nothing hidden reaches the model or an adopted case. Manual round text still allows them (the #68 residual).

## Checkpoints

1. **Specs and plan** (`spec:` `d65f7df`, `plan:` `13e8e75`): `workflow/specs/ai/test-drafting.md`, `workflow/specs/product/rounds.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`, this plan.
2. **Repair round 1** (`spec:` then `plan:`, on `13e8e75`): the same four spec files (findings V-M1 to V-M4, S-M1, S-M2, S-L1 to S-L6, V-L1 to V-L10 and the gateway checklist), then this plan. Checks: `git diff --check`; `python workflow/scripts/check_scope.py builder --base 13e8e75`; read back.

## Size

Criteria: RND-8.1 to RND-8.9, nine, one above the guideline. It stays reviewable: the split separates independently changeable behaviours (selection scope, pre-fill handling) rather than adding scope, every criterion is one page flow of two views, and the inherited round rules are tested with existing helpers. Implementation estimate (next slice, not confirmed): about 300 to 380 lines under `src/` outside tests (forms, two views, cleaning table, reply parser and validator, instruction constant, templates), excluding the gateway client, which #6 owns. Over 400 would need the human's budget decision; if the estimate grows, split the pre-fill route (RND-8.2, RND-8.9) into its own slice.

## Open issues

- **For #6 (Whimsyturtle):** the nine [requirements on the gateway](../specs/ai/test-drafting.md#requirements-on-the-gateway):
  - separate instruction and data parts, with no tool-calling parameters;
  - a total time bound (30 seconds proposed) that, with request overhead, stays below the platform function limit; the [release gate](../specs/TECHNICAL-SPEC.md#release-verification) only requires that limit to be at least 30 seconds, so the bound or the gate must change (not edited here);
  - input under 8,000 characters, a reply of at least 20,000 and a raw-response byte cap;
  - quota per workspace or user and deployment-wide, reserved atomically before the call, counting failures and timeouts;
  - at most one drafting call in flight per user;
  - a fixed endpoint with TLS verification and no redirects, transport-level timeouts, and a credential from the environment that is never logged;
  - no text in logs and no provider error bodies;
  - no result reuse for drafting;
  - a scriptable fake provider and a live-check run of the drafting set.

  Also: who validates structured output; who owns the live evaluation if #6 declines it; the provider's retention and training on submitted text.
- **For the human:** confirm D1 to D19 and B1 to B4, in particular the RND-8 home, the 1-to-5 and 0-to-5 counts, removal rather than refusal, the pre-fill route with its rule-5 exception, nine criteria, and the reload residual.

## Checklist

- [x] Checkpoint 1: specs and plan (`d65f7df`, `13e8e75`).
- [ ] Repair round 1: specs and plan (on `13e8e75`).
- [ ] Human and Whimsyturtle confirmation in the PR.
- [ ] Implementation slice for RND-8, after #6 provides the gateway and its fake provider.
