# strong profile

For models that reliably follow multi-step instructions and judge scope on their own, such as Claude Opus and Sonnet or GPT-5-class models. It applies only when the person launching the session sets `RELAY_PROFILE=strong`.

- Follow the [slice skill](../skills/slice.md) as written. Use judgement on how many commit checkpoints the change needs (two to four).
- Keep the context small: read the spec sections and code the change touches, not whole folders.
- Prefer the smallest complete change: reuse existing helpers and patterns, add no option or abstraction nobody asked for, and finish everything the change touches (callers, tests, specs, User Guide).
- Do the slice's two consistency checks before freezing: search the specs and docs for every name you touched, and make sure no existing test lost its purpose because its input became invalid.
- Run full verification once on the final candidate, and focused tests while building. Do not repeat unchanged passing checks.
- Keep reviewer briefs short: the request, the decisions, the commit range and the check results.
