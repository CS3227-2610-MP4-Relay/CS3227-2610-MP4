# 33: Developer Guide

Goal: make `docs/DeveloperGuide.md` a current setup and design overview that links to the specs for each rule, and delete the unused `compose.yaml`, under [#33](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/issues/33).

Tier: Fast lane. Documentation plus one unused config file; no behaviour, acceptance criterion or security control changes. Targeted checks; the human reviews the diff. Base `26e77cc`.

Confirmed items:
1. **Design section.** Replace the ~960-word paragraph that restates TECHNICAL-SPEC service and route rules with a short overview: the apps and what each owns, the main modules, where the shared helpers live (workspace lookups, round lock, `results`, gateway) and how a request flows. Link to the TECHNICAL-SPEC and SECURITY-SPEC sections for the rules. Every named module, function and class must exist.
2. **Rest of the guide** (setup, environment variables, verification, CI, production deployment, development workflow, SoC LLM, product website, acknowledgements): fix stale or wrong text, replace facts that have another home with a link, and remove duplicated counts and status histories. Operator procedures keep their meaning; a procedure that looks wrong is listed in the handoff, not rewritten.
3. **Delete `compose.yaml`.** `git grep` finds no reference outside the [#67 sweep plan](67-cleanup-sweep.md); it pins PostgreSQL 18.6 while CI, the guide and the spec use 17.6.

Out of scope: `docs/UserGuide.md`, specs, code and `docs/Reflections.md` (other builders or the team own them).

Checkpoints:
1. `plan: Plan the Developer Guide rewrite (#33)`: this file.
2. `docs: Trim the Developer Guide to an overview (#33)`: `docs/DeveloperGuide.md` (items 1 and 2). Checks: every relative link and anchor on added lines resolves to a file or heading slug; every named module/function/class exists in `src/`; kept commands checked with `--help` or `manage.py help` where side-effect free; word count before and after. Result: 43 relative links on added lines, 0 bad; 45 named modules/classes/functions import; `manage.py check --settings=relay.settings.test`, `manage.py help evaluate_injection|compare_context`, `check_site.py --help` and `playwright show-trace --help` valid. Guide 4910 → 4042 words; Design 957 → 535. +45/−26.
3. `chore: Delete the unused compose file (#33)`: `compose.yaml` (item 3). Checks: `git grep -n compose` finds no remaining reference outside plans; `ruff check .`; `python /Users/zheng/Desktop/mp4/.r67/dblock.py pytest -q -p no:cacheprovider src/relay/tests/test_site.py src/relay/tests/test_ci.py`. Result: only the frozen #67 sweep plan mentions it; `ruff check .` all passed; 27 passed. −26.

Decisions: none beyond the confirmed list.

Open: links into `test-drafting.md`, TECHNICAL-SPEC and SECURITY-SPEC sections depend on their headings, which another builder is editing; re-check anchors after both merge.
