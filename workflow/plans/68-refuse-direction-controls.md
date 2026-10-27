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

- [x] Checkpoint 1: specs and plan (`e6160c4`, `81c2e12`).
- [x] Checkpoint 2: refuse the controls (on `81c2e12`). `forms.py` adds `DIRECTION_CONTROLS`, `DIRECTION_MESSAGE` and one check after visibility (src +9/-1). New `test_direction_controls.py`, 62 tests: 24 refusals (each control on two field routes, three positions), 14 acceptances, 8 order cases, 5 re-shown-value cases and one pairwise-coverage check. Red before the check: 29 failed (24 refusals saved with 302; 5 re-shown cases found no message), 33 passed. Green: 62 passed. Mutations on temporary edits with an empty `PYTHONPYCACHEPREFIX`, restored and checked with `cmp`: removing the check fails the same 29; refusing all of Cf fails the 7 ZWJ and ZWNJ acceptances; checking before visibility fails the 3 only-controls cases. Existing tests changed, assertions kept: `test_publish.py::test_bidi_and_zero_width_characters_stay_inside_their_element` publishes through `services.publish`; `test_retest.py::test_bidi_and_zero_width_characters_stay_inside_the_label_element` and `test_messages.py::test_an_unread_retest_label_is_isolated_and_escaped_on_the_sign_in_page` use the new `conftest.stored_retest`, which calls `services.request_retest` and stores the retest message in the session as the view does. Each posted a bidi label through a form that now refuses it. All three fail with `isolated_lines` losing `dir="auto"` or escaping. Every rounds test module alone: passed. Ruff check and format clean.
- [x] Checkpoint 3: guides (on `60ab3e2`). `docs/UserGuide.md` adds "Hidden text-direction characters are not allowed." beside each null-character message: round titles, criteria and case fields, publishing and retest build labels (4 lines). The Developer Guide does not describe round text validation, so it is unchanged.
