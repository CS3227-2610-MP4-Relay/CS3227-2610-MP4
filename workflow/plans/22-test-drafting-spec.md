# Slice 22: Test-drafting contract (spec only) (#22)

Goal: settle the test-drafting AI feature's contract, its pages as [RND-8](../specs/product/rounds.md#rnd-8-draft-test-cases-with-ai) and its [AI contract](../specs/ai/test-drafting.md), so it can be built once the [gateway](../specs/ai/llm-gateway.md) (#6) exists.

Tier: High (AI feature contract), with a verifier and a security review. Base: `20f4ea7`, branch `22-test-drafting-spec`. Owner: zheng-jj. Specs only: no code, tests, dependency, prompt file or guide change; `ai/llm-gateway.md` is the gateway owner's (Whimsyturtle) and is not edited.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27: write the contract now with sensible defaults, each listed for the human and Whimsyturtle to confirm in the PR; gateway decisions (model, endpoint, quota, time, retries, caching, telemetry) stay in the gateway contract, and drafting states only what it needs from it.

Every choice below is a **coordinator default, pending human and Whimsyturtle confirmation**:

- **D1 Home:** the pages and criteria are a new requirement, RND-8, in `product/rounds.md`, because drafting is a Draft-round coordinator action under the same rules; the model-facing contract stays in `ai/test-drafting.md`. Status: specified, not implemented, blocked on #6.
- **D2 Source:** the coordinator selects 1 to 5 of the Draft round's own criteria; only their current text is sent, labelled `C1` to `C5` in creation order, as a JSON data part separate from the instructions. No tester data, cases, titles, other rounds or workspaces, database IDs or usernames.
- **D3 Hidden characters** (the #68 residual left to #22): input and reply text lose every Cf character except ZWNJ and ZWJ, every variation selector and every Cc character except line feed and tab; the five blank fillers become spaces. Stored text is unchanged, and manual round text still allows them. Removing rather than refusing keeps drafting usable on pasted text, and nothing hidden can reach the model or an adopted case.
- **D4 Fixed instructions:** six required points in the contract; the wording is a versioned constant written by the implementation slice.
- **D5 Schema:** one JSON object `{"drafts": [...]}` of 0 to 5 drafts with exactly `title`, `steps`, `expected_result` and `criteria`; RND-2 limits and rule 5 after cleaning; `criteria` 1 to 5 unrepeated sent labels; no repeated keys; reply at most 20,000 characters. Any failure rejects the whole reply. An empty list is valid, so the model has an honest answer for untestable criteria.
- **D6 Messages:** "Drafting is unavailable right now. You can still add test cases yourself." for every failure, refusal, quota or invalid reply; "No test cases were suggested for these criteria. You can still add test cases yourself." for a valid empty reply; selection messages "Select 1 to 5 acceptance criteria." and the existing "Choose criteria from this round."; the existing case-cap message before any call.
- **D7 Adoption:** drafts are never stored. "Use this draft" POSTs the draft to a pre-fill route that renders the normal "New test case" form with initial values; only its normal submission saves. A GET with query parameters was rejected: a full draft can exceed common URL limits, and query strings reach access logs. Storing drafts in the session was rejected as saving them.
- **D8 Routes:** `/coordinator/rounds/<round>/cases/draft/` (GET, POST) and `.../cases/draft/use/` (POST), Draft only, under every round rule; POST with CSRF so another site cannot spend quota or plant a form.
- **D9 Calls and locks:** one gateway call per drafting request, after the selection and the case cap; no feature-level retry; no lock or transaction held during the call; nothing stored or logged except the result category and the failed schema rule.
- **D10 Evaluation:** automated cases with a fake provider are listed in the contract; the live usefulness and injection check on a small synthetic set is proposed as part of the gateway's live-check procedure.

## Checkpoints

1. **Specs and plan** (`spec:`, then `plan:`): `workflow/specs/ai/test-drafting.md` (contract), `workflow/specs/product/rounds.md` (status line, intro, RND-8), `workflow/specs/TECHNICAL-SPEC.md` (AI drafting bullet, two planned routes, delivery order), `workflow/specs/SECURITY-SPEC.md` (#68 residual pointer, drafting bullet), this plan. Checks: `git diff --check`; `python workflow/scripts/check_scope.py builder --base 20f4ea7`; read back.

## Size

Criteria: RND-8.1 to RND-8.7, seven, within the guideline; RND-8.7 also inherits the shared rendering and ordering tests for two routes. Implementation estimate (next slice, not confirmed): about 250 to 350 lines under `src/` outside tests (forms, two views, cleaning and reply validation, instruction constant, templates), excluding the gateway client, which #6 owns. Over 400 would need the human's budget decision.

## Open issues

- **For #6 (Whimsyturtle):** the seven [requirements on the gateway](../specs/ai/test-drafting.md#requirements-on-the-gateway): separate instruction and data parts with no tools; success, refusal or failure within a total time suited to a page request (30 seconds proposed); input under 8,000 characters and a reply of at least 20,000; per-workspace or per-user quota reported as refusal; no text in logs and no provider error bodies; no result reuse for drafting; a scriptable fake provider and a live-check run of the drafting set.
- **For the human:** confirm D1 to D10, in particular the RND-8 home, the 1-to-5 and 0-to-5 counts, removing hidden characters instead of refusing them, and the extra pre-fill route.

## Checklist

- [x] Checkpoint 1: specs and plan (on `20f4ea7`).
- [ ] Human and Whimsyturtle confirmation in the PR.
- [ ] Implementation slice for RND-8, after #6 provides the gateway and its fake provider.
