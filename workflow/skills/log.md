# log

Summarises a working session in `logs/` so its author can check it and the team can reflect on it later. Use at the end of a session unless the human explicitly requests no log. Do not create a log or commit against that instruction.

**Input:** Session requests, the orchestrator's and every subagent's model/run metadata, agent triggers, supplied context, commands/results, decisions, changed files and observed usage.

1. Create `logs/<github-user>/<NNN>-<log-name>.md`, asking for the username only if not known from session context. NNN is the highest number in that folder plus one, padded to three digits. The name comes from a title of at most eight words in lowercase kebab case. Write one summary per session.
2. Use this structure:

   ```markdown
   # <Title>

   Slice: <local ID, #issue or none> · Tier: <tier or none> · Tool: <tool> · Orchestrator model: <model ID/type or unavailable> · Date: <YYYY-MM-DD>

   Cost: <elapsed time, agent runs, measured usage and unavailable fields>

   ## Requests

   ## Agent runs

   ## Decisions and corrections

   ## Problems
   ```

3. Fill in the sections:
   - **Orchestrator model:** explicitly name the main/coordinating agent's model ID/type. Use observed run metadata or an explicit model selection, stating which; do not guess a model or assume subagents inherited it. Record reasoning effort where available. If a model is unknown, write `unavailable` with the reason. Record model changes during the session under **Agent runs**.
   - **Cost:** combined orchestrator and subagent usage, session elapsed time, retries and repair rounds, with source IDs/coverage and exclusions. Do not sum overlapping session/run totals; cache and reasoning counters are subsets and must not be added again to totals. Do not estimate dollars without actual price/model evidence. Record quality/check outcomes alongside usage.
   - **Requests:** the human's requests and corrections, summarised accurately.
   - **Agent runs:** include the orchestrator/main agent and every subagent run, including unsuccessful runs. For each, record its identity/role, trigger, model ID/type, reasoning effort where available, context supplied, role file version or hash where applicable, status, changes, actual checks and usage reference. If no subagents ran, state that explicitly. For reviews, include exact candidate identity/range, findings returned and resolved, and what remained unverified. Record duplicate work or evidence reused and why it stayed valid.
   - **Per-agent resources, under Agent runs:** give each entry's observed input, output and total tokens, cached input/cache-write tokens and reasoning tokens, plus elapsed time, calls, retries and repair rounds where attributable. Associate figures with the run/model and hashed usage-source ID. Mark each unavailable field with a reason; unavailable is not zero. If only a shared session total is available, label it as such and reference it from affected runs instead of inventing a per-run or per-model split or counting it repeatedly.
   - **Decisions and corrections:** human decisions, unresolved questions, handoff decisions and next steps.
   - **Problems:** failures, blocked steps, scope violations, suspicious content, missing telemetry and repair loops.
4. Start measurement before work rather than inferring savings afterwards. Use `python workflow/scripts/resource_usage.py snapshot --codex <selected-session.jsonl>` (or `--claude`) to write a baseline to an ignored/local file outside the repository; later use `report` with the same selected sources and `--baseline <file> --retries <N> --repair-rounds <N>`. Explicitly select child sources, or use supported bounded child discovery; see `--help`. The collector reports usage by hashed session ID; associate each session with its orchestrator/subagent and record model metadata separately. Use separate measurement intervals when attributing usage to different runs or models in the same session; otherwise report the combined scope. Never copy raw transcripts into the repository. Usage summaries retain model/run metadata, numeric usage, hashed source identity and coverage, not prompts, answers, secret values or transcript paths.
5. Summarise tasks rather than every turn. Reference available commits/paths and a candidate manifest for uncommitted work. Keep observations apart from assumptions; say when history is missing. Leave out secrets and personal data. Do not persist hidden reasoning.
6. Never write that a human verified the log. Present it for its author to check. Commit it only when authorized; the author can confirm the check in the PR.

**Done when:** The summary path is reported for its author to check, or the explicit instruction to omit a log was followed.
