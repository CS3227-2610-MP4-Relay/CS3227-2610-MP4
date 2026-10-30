# strong profile

For models that reliably follow multi-step instructions and judge scope on their own, such as Claude Opus and Sonnet or GPT-5-class models. It applies only when the person launching the session sets `AGENT_PROFILE=strong`.

- Follow the [slice](../slice.md) as written. Use judgement on how many commit checkpoints the change needs (two to four).
- Keep the context small: read the requirements and code the change touches, not whole folders.
- Prefer the smallest complete change. Reuse existing helpers and patterns, and add no option or abstraction nobody asked for. Finish everything the change touches: callers, tests, requirements, docs.
- Do the slice's consistency checks before freezing.
- Run the focused tests while building and the full verification once on the final candidate. Do not repeat unchanged passing checks.
- Keep reviewer briefs short: the request, the decisions, the commit range and the check results.
