# Slice 68: Refuse hidden text-direction characters in round text (#68)

Goal: every round text form refuses text containing a Unicode bidi control character with "Hidden text-direction characters are not allowed.", while escaping, `dir="auto"` isolation and page-title stripping stay as defence in depth ([rule 5](../specs/product/rounds.md#rules-for-every-round-action)).

Tier: Standard, with a security review (validation of attacker-written input on round routes). Base: `3bda6e1`, branch `68-refuse-direction-controls`, stacked on #56 → #62 → #63 → #64. Owner: zheng-jj. Budget: at most 400 changed lines under `src/` outside tests; confirmed estimate 20 to 40 lines of `src/` plus tests and spec.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27: refuse only invisible text-direction controls, not all Unicode; letters of any script, accents, curly quotes and other Unicode stay allowed; rendering defences stay. Nothing else is in scope.

Coordinator's decision: the refused set is the Unicode `Bidi_Control` property, U+061C, U+200E, U+200F, U+202A to U+202E and U+2066 to U+2069 (12 characters). Not all of category Cf: U+200C and U+200D are needed in emoji sequences and scripts such as Persian; zero-width spaces stay as now (invisible for emptiness only).

Builder's details within that scope (checkpoint 1):

- **Message:** "Hidden text-direction characters are not allowed.", parallel to the null-character message.
- **Order:** the check runs in `RoundTextField.clean()` after Django's checks (required, length, null character) and the visible-character check, so only text passing them reaches it. Text of only bidi controls and spaces stays "Enter 1 to N characters." (the existing `"​ ‮ "` case in `test_views.py` is unchanged), and a too-long or null-containing value gets only its existing message.
- **Criteria:** none added or edited. The shared rule 5 carries the sentence; the field criteria RND-1.3, RND-2.4, RND-3.2 and RND-5.2 mark the tests, as the null-character tests are marked. Within the "at most one requirement" budget.
- **Form only:** services and models do not repeat the check (they do not repeat the null check either), so rendering still treats stored text as untrusted; TECHNICAL-SPEC says so.
- **Existing data:** a record stored before this change that holds a control is shown in its edit form as before; saving it unchanged is refused until the characters are removed. No migration or cleanup (out of scope).
- **Page-title filter unchanged:** it strips U+202A to U+202E and U+2066 to U+2069 but not U+061C, U+200E or U+200F, which do not open an embedding; noted, not changed.

## Checkpoints

1. **Specs and plan** (`spec:`/`plan:`): `workflow/specs/product/rounds.md` (rule 5 sentence; rendering paragraph says input refuses, rendering still isolates), `workflow/specs/SECURITY-SPEC.md` (rendering bullet), `workflow/specs/TECHNICAL-SPEC.md` (text fields), this plan. Check: `git diff --check`; read back.
2. **Refuse the controls** (`feat:`): `src/rounds/forms.py` (a module constant of the 12 characters and one check in `RoundTextField.clean()`); new `src/rounds/tests/test_direction_controls.py`. Red first, with the check absent:
   - each of the 12 characters, embedded in otherwise valid text, refused with the message next to its field, record unchanged (`everything()` or the field's value), spread pairwise over fields and routes: round title (create, retitle), criterion text (new, edit), case title, steps and expected result (new, edit), build label (publish, retest); every character on at least one field and every field and route with several characters;
   - accepted and saved exactly: ZWJ emoji sequence, ZWNJ in Persian, Hebrew, Arabic, accented Latin, CJK and curly quotes, spread pairwise over the same fields and routes;
   - order: bidi-only text gets "Enter 1 to N characters."; a too-long value with a control gets only the length message; a null plus a control gets only the null message;
   - the refused value shown again is escaped and inside the `dir="auto"` input (markup plus RLO in one value).
   Marks: RND-1.3, RND-2.4, RND-3.2, RND-5.2 by field. Expected red: every refusal case; the accepted, order and re-shown cases pass beforehand and detect over-broad refusal or a wrong order once the check exists.
   Existing tests that post a control through a form (expected in `test_publish.py`, `test_retest.py`, `test_messages.py`; confirmed by running the rounds tests with the check in place) are changed to store the text through the models or services and then render it, keeping every assertion. Each changed test and its reason is listed in the handoff and the checklist below. Checks: each affected module alone with `pytest -q -p no:randomly <module>` against the test database on 127.0.0.1:55432; Ruff on changed files. Full verification is the coordinator's.
3. **Guides** (`docs:`): `docs/UserGuide.md` lists validation messages for titles, criteria and cases, build labels and retests; add the new message to each in the product's words.

## Size estimate

`src/` outside tests: about 10 to 20 lines. Tests: about 150 new lines and about 30 changed. Specs: 4 changed lines.

## Open issues

- None.

## Checklist

- [ ] Checkpoint 1: specs and plan.
- [ ] Checkpoint 2: refuse the controls, with tests and existing-test adjustments.
- [ ] Checkpoint 3: guides.
