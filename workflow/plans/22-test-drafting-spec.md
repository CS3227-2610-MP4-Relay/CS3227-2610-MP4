# Slice 22: AI test drafting — contract and implementation (#22)

Goal: propose and implement the test-drafting AI feature's contract, its pages as [RND-8](../specs/product/rounds.md#rnd-8-draft-test-cases-with-ai) and its [AI contract](../specs/ai/test-drafting.md), using the [gateway](../specs/ai/llm-gateway.md) (#6) and its fake provider.

Tier: High (AI feature), with a verifier and a security review. Base: `20f4ea7`, branch `22-test-drafting-spec`. Owner: zheng-jj. The contract was proposed before code, except the exact instruction wording ([history deviations](#history-deviations)); the implementation adds the `ai` app and its tests, and the gateway contract is in `ai/llm-gateway.md`. Live provider calls are switched off ([repair](#repair-after-independent-review-2026-10-29)).

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27: write the contract now with sensible defaults, each listed for the human and Whimsyturtle to confirm in the PR; gateway decisions (model, endpoint, quota, time, retries, caching, telemetry) stay in the gateway contract, and drafting states only what it needs from it.

### Coordinator defaults

Each is a **coordinator default, pending human and Whimsyturtle confirmation**. Checkpoint 1's D3 (hidden characters) and D7 (adoption) are now builder proposals B4 and B3.

- **D1 Home:** the pages and criteria are a new requirement, RND-8, in `product/rounds.md`, because drafting is a Draft-round coordinator action under the same rules; the model-facing contract stays in `ai/test-drafting.md`. Status: implemented with live provider calls switched off (human decision 1 below); the live provider check is an operator step.
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

Repair round 2 (on `440de48`), coordinator defaults under the same instruction, pending human and Whimsyturtle confirmation:

- **D20 In-flight caps and connections (S-R1):** gateway need 5 adds a deployment-wide in-flight cap beside the per-user one; an in-flight marker expires no sooner than the time bound and is released on every exit. Releasing the database connection before the call is a feature rule (contract Limits and TECHNICAL-SPEC), because the drafting view owns its connection. SECURITY-SPEC records, pending the human's confirmation, that demo workspaces can use up the deployment-wide allowance, making drafting unavailable to everyone while the manual workflow stays usable; its numbers wait for #6.
- **D21 Format characters outside the table (S-R2, V-N2):** cleaning also removes U+FFF9 to U+FFFB and U+13430 to U+1343F, and keeps the visibly drawn prepended marks (U+0600 to U+0605, U+06DD, U+070F, U+0890 to U+0891, U+08E2, U+110BD, U+110CD), because they render and carry meaning in Arabic, Syriac and Kaithi text. Checked: these are exactly the Cf characters outside Default_Ignorable_Code_Point in Unicode 16.0.0.
- **D22 Empty selection (S-R3):** criterion text is trimmed after cleaning; if every selected criterion is then empty, no call is made and the no-drafts message is shown.
- **D23 Wording (V-N1, V-N3, V-N4, V-N5):** cleaning applies to reply fields after parsing, never the raw reply; rule 5 and limits apply to reply fields, not pre-fill text; the pre-filled form holds exactly the cleaned text after re-cleaning turns posted CR LF into LF, with a CR LF test; RND-8.4 now names a call in flight and an over-limit request, tested by lowering the limit; the 200 status is "whatever the drafting outcome", since a storage failure still gets 503.

### Builder proposals

Not in the coordinator's brief; proposed by the builder in checkpoint 1, pending human and Whimsyturtle confirmation:

- **B1 Empty reply:** a valid reply with no drafts is accepted and shows "No test cases were suggested for these criteria. You can still add test cases yourself.", giving the model an honest answer for untestable criteria.
- **B2 Cap before call:** a round at 30 test cases gets the existing cap message before any gateway call, saving quota.
- **B3 Pre-fill route:** "Use this draft" POSTs to a pre-fill route. A GET with query parameters was rejected (a full draft can exceed common URL limits, and query strings reach access logs), as was storing drafts in the session (that saves them).
- **B4 Remove, not refuse:** hidden characters are removed from input and reply rather than refused, so pasted text still drafts and nothing hidden reaches the model or an adopted case. Manual round text still allows them (the #68 residual).

Builder choices in the 2026-10-29 repair, pending the same confirmation:

- **B5 Pre-fill bound (S7):** a "Use this draft" text field longer than twice its RND-2 limit is ignored, as if not posted, before cleaning; twice allows every line break to come back as CR LF.
- **B6 Remove `ai.Usage` (S7):** nothing records token metrics, and its seeded row showed a count of 0 where the contract requires "unavailable", so the model and row are removed by a migration; a slice that records metrics specifies its own table.
- **B7 Deadline mechanics (S1):** the deadline starts at reservation; name resolution runs in a helper thread that is abandoned at the deadline (superseded by the [#6 review repair](6-llm-gateway.md#review-repair-2026-10-29): aiohttp resolves names and the deadline is its total timeout); slots expire 35 seconds after reservation, the 30-second bound plus a 5-second release margin.
- **B8 Seeded slots in tests (repair D):** an autouse fixture in `src/ai/tests/conftest.py` recreates the two deployment slots for every database-backed AI test, because ACC-3's transactional tests and the browser tests' live server flush every table, seeded rows included. The gateway still refuses when they are missing, as the spec's fixed rows require; `serialized_rollback` was rejected because it collides with content types recreated after a flush.

## Checkpoints

1. **Specs and plan** (`spec:` `d65f7df`, `plan:` `13e8e75`): `workflow/specs/ai/test-drafting.md`, `workflow/specs/product/rounds.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`, this plan.
2. **Repair round 1** (`spec:` `83dbc7a`, `plan:` `440de48`): the same four spec files (findings V-M1 to V-M4, S-M1, S-M2, S-L1 to S-L6, V-L1 to V-L10 and the gateway checklist), then this plan.
3. **Repair round 2**, the last allowed (`spec:` then `plan:`, on `440de48`): the same four spec files (S-R1 to S-R3, V-N1 to V-N5), then this plan (V-N6 and the security follow-up). Checks: `git diff --check`; `python workflow/scripts/check_scope.py builder --base 440de48`; invisible-character scan of `workflow/`; read back.

## Size

Criteria: RND-8.1 to RND-8.9, nine, one above the guideline. It stays reviewable: the split separates independently changeable behaviours (selection scope, pre-fill handling) rather than adding scope, every criterion is one page flow of two views, and the inherited round rules are tested with existing helpers. The spec-time estimate was 300 to 380 lines under `src/` outside tests, with over 400 needing the human's budget decision. The built size, and the human's one-off budget increase, are under [human decisions](#human-decisions-2026-10-29-confirmed).

## Open issues

- **For #6 (Whimsyturtle) and the human:** confirm or change the gateway's [proposals](../specs/ai/llm-gateway.md), which answer drafting's nine [requirements on the gateway](../specs/ai/test-drafting.md#requirements-on-the-gateway); the time bound against the [release gate](../specs/TECHNICAL-SPEC.md#release-verification) (not edited here); who owns the live evaluation if #6 declines it; the provider's retention and training on submitted text.
- **For the human:** confirm D1, D2, D4 to D6, D8 to D23 and B1 to B7 (D3 and D7 became B4 and B3; B7's helper-thread resolution is superseded by the [#6 review repair](6-llm-gateway.md#review-repair-2026-10-29)), in particular the RND-8 home, the 1-to-5 and 0-to-5 counts, removal rather than refusal, the pre-fill route with its rule-5 exception, nine criteria, the reload residual and the deployment-wide allowance residual.
- **For the human:** confirm the repair size, 534 lines against decision 2's estimate of 100 to 200 ([round 2 evidence](#evidence-and-checks)).
- **Before turning live calls on:** the conditions of the [live switch](../specs/ai/llm-gateway.md#live-switch), then the operator's live evaluation.
  - The final security re-review of `8a27ea7` adds two items for that change.
  - First, bound the body read independently of the Python patch level: refuse a `Content-Length` above `RESPONSE_BYTES` and read in bounded chunks, because older 3.14 `http.client` builds pre-allocate the declared length. Superseded by the [#6 review repair](6-llm-gateway.md#review-repair-2026-10-29): aiohttp reads the body in chunks counted against the cap, and `http.client` is no longer used.
  - Second, make the off-for-now notice depend on `SOC_LLM_LIVE`, or test that it can't survive the switch.
  - Repair rounds were exhausted, so these are recorded here rather than fixed in this PR.
- **Access matrix:** resolved; #77 is merged into this branch (`6e7b844`) and the `ai:*` rows were added in [repair round 2](#repair-round-2-2026-10-29) (`46fae22`).

## Split (2026-10-29)

At the human's request, #78 was split by layer into two PRs. The first, from branch `6-llm-gateway`, holds every spec change, this plan, the [#6 plan](6-llm-gateway.md), log 018 and the gateway (`ai` app, models, migrations, gateway, fake provider, their tests and settings). #78 keeps RND-8's drafting pages, their tests, the `ai:*` access-matrix rows, the User Guide and log 019, and merges after it. The content is unchanged apart from consistency edits in the first PR: its status sentences say RND-8 is specified but not built and the Developer Guide describes only the gateway, which #78 updates when the pages land, and the AI tests' fixtures drop the rounds fixtures only the drafting tests use. The coordinator records each PR's size.

## Repair after independent review (2026-10-29)

On `5c354c3`. PR #78's implementation was produced by another model (DeepSeek) in a workflow experiment; independent reviews of `5c354c3` then found the issues below. Tier: High.

### Human decisions (2026-10-29), confirmed

1. **Live off.** Keep the drafting UI and the gateway code, but switch live provider calls off with a code-level setting, `SOC_LLM_LIVE = False`, in the shared settings, not an environment variable, so turning it on needs a reviewed change. While off, no network call happens, whatever `SOC_LLM_*` holds. It stays off until the real SoC LLM API, its retention and training terms and its limits are confirmed.
2. **Budget.** The PR's size is accepted as a one-off budget increase, plus these repairs. Measured on `5c354c3` against `b9a85da`: 869 added lines under `src/` outside tests, 767 without migrations; the drafting files (`drafting.py`, `views.py`, `forms.py`, `urls.py`, `draft.html`) add 411. The repairs are estimated at 100 to 200 more, mostly the transport.
3. **Proposals.** The gateway design (the wire format `{"model", "instructions", "data"}` to `{"text"}` or `{"refusal"}`, 20 calls per user per hour, 200 per deployment per hour, 2 in flight and the 30-second bound) stays a proposal pending confirmation by Whimsyturtle (#6) and the human, as do D1 to D23 and B1 to B7. The specs say so.

### History deviations

Recorded as facts; the rules they broke are unchanged.

- **Instruction wording after code.** D4, D11 and the contract require the exact instruction wording in the contract at the implementation's first checkpoint, reviewed before any code. It landed in repair `3caf1e8`, after the code commits `c6cb269` and `d9be48a`, following a High review finding on `89bebf9`.
- **Retrospective split.** Log 019 records that the first implementation branch exceeded the slice budget and was split into commits afterwards, instead of being committed checkpoint by checkpoint.
- **No builder agent.** Commits `550db7d` to `d234c9c` carry `Agent: builder`, but log 019 lists only the orchestrator and two review agents.
- **Third repair round without escalation.** This plan named repair round 2 the last allowed; review and repair continued through `3caf1e8`, `78ab9b7` and `d234c9c` without returning to the human.
- **Budget misreported.** This plan and the #6 plan reported 398 lines, within the 400-line budget; the measured sizes are in decision 2.
- **Status overclaimed.** The specs and this plan said the contract was settled before code, dropped its pending-confirmation line and presented the gateway's proposals as settled.

### Findings

From independent reviews of `5c354c3`; each is checked against the code in its checkpoint.

- **S1, Medium (B):** the 30-second bound covered only the body read. One deadline across every phase, name resolution included; slot expiry at the bound plus a margin (B7); release only of a slot still holding this call's expiry; a real local TLS server that trickles headers, with a throwaway certificate from the `openssl` CLI, replaces the mocked deadline test; no use of the private `response.fp.raw._sock`.
- **S3 (B):** an autouse fixture in `src/conftest.py` removes `SOC_LLM_*` and makes the transport's network step fail unless a test is marked `llm_transport` (registered in `pytest.ini`).
- **S4 (B):** `http.client.HTTPException` is `Failed("transport")`; the request body is encoded inside the `try`; `_transport` and `complete` mark the key, body, instructions and data sensitive; the drafting view adds `by_label`.
- **S5 (B):** a `DatabaseError` from reservation or release reaches the rounds 503 instead of the unavailable message.
- **S7, Info (B):** the envelope refuses repeated `text` keys and surrogates; `ai.Usage` is removed (B6); the pre-fill fields are bounded (B5).
- **V9 (C):** the missing or weak tests in the review brief: RND-8.1 covered-criteria mapping (fails if `by_label` is reversed); RND-8.2 adopt-and-submit equality; RND-8.7 and access (another workspace's round, signed-out, Beta Tester, missing CSRF token and foreign `Origin` on both routes, hostile reply rendering); RND-8.8 another workspace's and a missing criterion; the unauthorized-label and hidden-character samples; the cleaning table against the listed ranges; `InvalidReply.code` per malformed-reply guard; the tautology in `test_views.py` and the over-limit test that passes through not-configured; a non-vacuous logging test; a quota test with a failing call; the deployment in-flight cap and quota; a two-thread reservation race; the connection released during the call. Each new test is shown failing first, or a mutation shows it detects the defect.
- **V12 and V2/V3 (A):** one home per fact (gateway decisions in `ai/llm-gateway.md`, marked proposals; the `ai` tables, pruning and `SOC_LLM_*` settings in the technical spec; token metrics; drafting's needs in `ai/test-drafting.md` linking to the gateway); honest status lines; the instruction-wording rule kept and its deviation recorded above.
- **V-Low:** reuse `rounds.forms.has_visible_character` and the RND-2 limits in `drafting` (B); the `_sock` access goes with S1 (B); the security spec links to the gateway's quota instead of restating it (A); the Developer Guide links instead of restating gateway controls (D).
- **Docs (D):** the User Guide describes only what users can see with live off, the page and the unavailable message, in the product's exact words; the README qualifies AI drafting as switched off until the provider is confirmed.

Out of scope here: the `ai:*` access-matrix rows (added in [repair round 2](#repair-round-2-2026-10-29)) and correcting log 019 (coordinator).

### Repair checkpoints

The coordinator commits each unit after its focused checks.

- **A. Specs and plans** (`spec:`, then `plan:`): `workflow/specs/ai/llm-gateway.md`, `workflow/specs/ai/test-drafting.md`, `workflow/specs/product/rounds.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`; this plan and `6-llm-gateway.md`. Checks: `git diff --check`; `python workflow/scripts/check_scope.py builder --base 5c354c3`; read back.
- **B. Live switch and gateway repairs** (`fix:` units: live switch with the test fixture; transport deadline and conditional release; envelope, exception mapping and sensitive variables; storage errors; `Usage` removal; pre-fill bound and `drafting` reuse): `src/relay/settings/base.py`, `src/conftest.py`, `pytest.ini`, `src/ai/gateway.py`, `src/ai/views.py`, `src/ai/drafting.py`, `src/ai/models.py`, a new `src/ai/migrations/0004_*.py`, `src/ai/tests/`. Checks: red-first focused `pytest src/ai`, then `ruff check` and `ruff format --check`.
- **C. Tests** (`test:`): `src/ai/tests/`, `src/e2e/test_rounds.py` if a journey changes. Checks: failing-first or mutation evidence per test; focused `pytest src/ai`.
- **D. Guides** (`docs:`): `docs/UserGuide.md`, `docs/DeveloperGuide.md`, `README.md`. README is outside the builder's `writes` list, so the coordinator applies that edit. Checks: read back against the rendered pages.

### Repair round 1 evidence

From the round-1 builder handoffs (`1969298`..`712df3f`), not rerun here:

- **Red first (B):** the new and changed tests gave 20 failed and 1 error on the old code, and 26 passed after the repair.
- **Mutations (C):** 29 mutations, all caught. Reversing `by_label` passed all 161 old tests and fails the new ones.
- **Size:** by the [slice skill's metric](../skills/slice.md) for `5c354c3..712df3f`, 257 insertions plus 149 deletions = 406 lines (net about 108). Human decision 2 estimated the repairs at 100 to 200 lines; the net size is in that range, the insertions plus deletions are not.
- **Commit granularity:** `60b9574` bundled six independently reviewable units (live switch with its fixture; transport deadline and conditional release; envelope, exception mapping and sensitive variables; storage errors; `Usage` removal; pre-fill bound and `drafting` reuse) that checkpoint B planned as separate commits. History was not rewritten.

## Checklist

- [x] Checkpoint 1: specs and plan (`d65f7df`, `13e8e75`).
- [x] Repair round 1: specs and plan (`83dbc7a`, `440de48`).
- [x] Repair round 2: specs and plan (on `440de48`).
- [ ] Human and Whimsyturtle confirmation in the PR.
- [x] Implementation slice for RND-8, using the fake provider; live evaluation remains an operator step.
- [x] Repair A: specs and plans (`1969298`, `85143ac`).
- [x] Repair B: live switch and gateway repairs (`60b9574`).
- [x] Repair C: test repairs and additions (`15e0611`).
- [x] Repair D: guides and README, with a test-isolation fix and log correction (`8d2200a`, `a62f34d`, `dc77969`, `c170ff0`, `712df3f`).
- [x] Repair round 2 A: specs and plan (`ba9c43c`, `ce2d0dd`).
- [x] Repair round 2 B: notice, transport and reservation repairs with tests (`816a2c4`, `26982cc`, `9a13dff`).
- [x] Repair round 2 C: access-matrix rows (`46fae22`).
- [x] Repair round 2 D: guides and this plan's evidence (`5827cd9`, `da32d66`). The coordinator merged the updated #77 branch (`8a27ea7`). The final independent re-reviews of `8a27ea7` found nothing above Low; their two security Info items are recorded under open issues.

## Repair round 2 (2026-10-29)

On `6e7b844` (712df3f plus #77's access matrix merged, so #78 stacks on #77). Tier: High. The last repair round allowed; findings from independent re-reviews of `712df3f`, which found no High issue.

### Human decision (2026-10-29), confirmed

While live calls are off, the drafting page shows an off-for-now notice in place of "Only their text is sent to the AI service."; the page and its link stay. Builder's wording choice: "AI suggestions are switched off for now, so nothing is sent to the AI service." The change that turns live calls on replaces it ([live switch](../specs/ai/llm-gateway.md#live-switch)).

### Findings

- **Matrix (C):** `test_every_route_has_a_matrix_entry` fails without `ai:draft` and `ai:use-draft` rows. Add both with the matrix's conventions, a 200-render success expectation alongside the 302 one, a `BODY_ID_ROUTES` entry for `criteria`, and assert the off-for-now and unavailable outcome of a valid draft POST.
- **Ver N1, Medium (B):** `_exchange` reads until close, so a provider that keeps the connection open turns a complete reply into `Failed("timeout")`. Stop at `Content-Length` or the final chunk; `llm_transport` tests for both with the connection held open.
- **Sec Low 1 (B):** slot expiry is taken before `_reserve` waits for its locks. Take the reservation time after the `select_for_update` calls and start the monotonic deadline then.
- **Sec Low 2, Ver N2 (B):** the lookup thread catches only `OSError`; a `UnicodeError` from `getaddrinfo` escapes as `KeyError`. Catch `Exception` and treat a missing result as `Failed("transport")`.
- **Sec test gap (B):** a certificate trusted through `SSL_CERT_FILE` but issued for `DNS:synthetic.invalid`, served at 127.0.0.1, is `Failed("transport")`, and the test fails with `check_hostname` off.
- **Ver N3 (A):** the live-switch conditions say the transport ignores `HTTPS_PROXY`.
- **E2E marks (B):** the drafting journey in `src/e2e/test_rounds.py` exercises only the unavailable outcome, so it is marked RND-8.4, not RND-8.1 and RND-8.2, and checks the notice.
- **Ver N7 (A, D):** the test fixture's home is TECHNICAL-SPEC Configuration and the live switch's is `ai/llm-gateway.md`; the other copies link to them.
- **Ver N4, N5, N8 (A):** this plan's round-1 evidence, size, commit-granularity fact and Repair D tick, above.

### Checkpoints

- **A. Specs and plan** (`spec:`, then `plan:`): `workflow/specs/product/rounds.md`, `workflow/specs/ai/llm-gateway.md`, `workflow/specs/TECHNICAL-SPEC.md`, this plan. Checks: `git diff --check`; `python workflow/scripts/check_scope.py builder --base 6e7b844`; read back.
- **B. Code and tests** (`fix:` units: notice with its tests and e2e marks; transport completion; reservation time; lookup errors; `test:` hostname mismatch): `src/ai/templates/ai/draft.html`, `src/ai/gateway.py`, `src/ai/tests/`, `src/e2e/test_rounds.py`. Checks: red-first or mutation evidence per new test; focused `pytest src/ai`, the e2e drafting journey; `ruff check`, `ruff format --check`.
- **C. Matrix rows** (`test:`): `src/relay/tests/test_access_matrix.py`. Checks: the whole matrix.
- **D. Guides** (`docs:`, then `plan:`): `docs/UserGuide.md` (exact notice quote), `docs/DeveloperGuide.md` (links for N7), this plan's evidence. Checks: read back against the rendered page.

### Evidence and checks

From the builder's runs on each checkpoint; full verification is the coordinator's.

- **Notice (B):** on the old template, the GET and foreign-selection view tests and the e2e drafting journey failed; all pass after the change. The journey is now marked RND-8.4.
- **N1 (B):** a complete reply on a held-open connection (`Content-Length`, chunked, chunked with a trailer) failed as `Failed("timeout")` on the old code and passes. `_exchange` now lets `http.client` read through a deadline-and-cap reader instead of reading until close; a hand-written framing parser was tried first and dropped as larger. A new chunked over-cap test caught a regression in that change (`http.client` turns a `ValueError` on a chunk-size line into `IncompleteRead`), so the cap error is no longer a `ValueError`.
- **Low 1 (B):** with the slot locks held by another transaction for a second, expiry was before release plus 35 seconds on the old code; now it is not. Mutation: starting the deadline after `_reserve` returns fails the test.
- **Low 2 (B):** a 64-character label and a `RuntimeError` from `getaddrinfo` raised `KeyError` on the old code; both are now `Failed("transport")`.
- **Hostname (B):** passes as built; it fails with `check_hostname = False`.
- **Matrix (C):** `test_every_route_has_a_matrix_entry` failed without the `ai:*` rows; with them, the whole matrix passes (501). A successful drafting POST is the new `RENDERED` outcome (200, nothing changed), and the snapshot now covers `CallRecord` and `CallSlot`. Mutations caught: `use_draft` without its Draft check, a selection from every round, the notice removed, `use_draft` saving a case. `use-draft`'s `criteria` has no body-ID row: under RND-8.9 it shows no message, and `src/ai/tests/test_views.py` covers it.
- **Focused checks:** `pytest src/ai` 190 passed; `pytest src/relay/tests/test_access_matrix.py` 501 passed; the e2e drafting journey passed; `ruff check .` and `ruff format --check .` clean; `check_scope.py builder` clean at each checkpoint.
- **Size, pending the human's confirmation:** by the [slice skill's metric](../skills/slice.md), round 2 changes 128 lines of non-test `src/` (76 insertions plus 52 deletions, `6e7b844..46fae22`), so the repairs total 534 (406 plus 128). That exceeds human decision 2's estimate of 100 to 200 lines for the repairs; the human has not yet confirmed it.
