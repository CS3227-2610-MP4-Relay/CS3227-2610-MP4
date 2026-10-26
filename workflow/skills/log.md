# log

Summarises a working session in `logs/` so its author can check it and the team can reflect on it later. Use at the end of a session unless the human explicitly requests no log. Do not create a log or commit against that instruction.

**Input:** Session requests, the orchestrator's and every subagent's model/run metadata, agent triggers, supplied context, commands/results, decisions, changed files and observed usage.

1. Create `logs/<github-user>/<NNN>-<log-name>.md`, asking for the username only if not known from session context. NNN is the highest number in that folder plus one, padded to three digits. The name comes from a title of at most eight words in lowercase kebab case. Write one summary per session.
2. Use this structure:

   ```markdown
   # <Title>

   Slice: <local ID, #issue or none> · Tier: <tier or none> · Tool: <tool> · Orchestrator model: <model ID/type or unavailable> · Date: <YYYY-MM-DD>

   Tokens: <combined input, output and total; measurement cutoff>

   | Agent/source | Input | Cached input | Output | Reasoning output | Total | Recorded elapsed span |
   | --- | ---: | ---: | ---: | ---: | ---: | --- |
   | Orchestrator — <model/effort>, <hashed source ID> | <tokens> | <tokens> | <tokens> | <tokens> | <tokens> | <span> |
   | <Subagent — model/effort, hashed source ID> | <tokens> | <tokens> | <tokens> | <tokens> | <tokens> | <span> |

   <Brief run summary and any session-specific coverage exceptions.>

   ## Requests

   ## Agent runs

   ## Decisions and corrections

   ## Problems
   ```

3. Fill in the sections:
   - **Orchestrator model:** explicitly name the main/coordinating agent's model ID/type. Use observed run metadata or an explicit model selection, identifying the source briefly beside the model values; do not guess a model or assume subagents inherited it. Record effective model and reasoning effort for the coordinator and each subagent, distinguishing configured/requested settings from observed execution. Mark unobservable values `unavailable` with the reason. Record observed overrides, fallbacks, model changes or discrepancies under **Agent runs**; omit routine prose confirming metadata checks or their absence.
   - **Tokens and table:** keep the table immediately below `Tokens:`, above **Requests**, with exactly the columns and order shown. Include the orchestrator and every subagent; identify each model/effort and hashed source in its row. Report combined input, output and total in the summary without repeating every table value. Use `unavailable` for missing values and give a shared reason once. For shared totals, label the scope and reference it from affected rows instead of inventing per-run/model splits. Report tokens only; omit monetary cost fields.
   - **Run summary:** give the subagent count and session elapsed span. Add cache-write tokens, calls, retries and repair rounds when measured and attributable, identifying the affected agent. Do not repeat a list of uncollected operational metrics in every log. Keep necessary coverage notes to a short session-specific line (for example, a missing baseline or an excluded overlapping source); link to [token reporting](../README.md#token-reporting) for definitions and accounting rules rather than copying them into the log.
   - **Requests:** the human's requests and corrections, summarised accurately.
   - **Agent runs:** include the orchestrator/main agent and every subagent run, including unsuccessful runs. For each, record its identity/role, trigger, context supplied, role file version or hash where applicable, status, changes and actual checks; refer to its token-table row for model/effort and usage instead of repeating them. If no subagents ran, state that explicitly. For reviews, include exact candidate identity/range, findings returned and resolved, and what remained unverified. Record duplicate work or evidence reused and why it stayed valid.
   - **Decisions and corrections:** human decisions, unresolved questions, handoff decisions and next steps.
   - **Problems:** failures, blocked steps, scope violations, suspicious content, missing telemetry and repair loops.
4. Take a usage baseline before work and a final report using [the measurement procedure and accounting rules](../README.md#token-reporting). Associate hashed sources with observed model/run metadata; use separate measurement intervals for different runs or models in one session, or report the combined scope. Never copy raw transcripts, prompts, answers, secret values or transcript paths into the repository.
5. Summarise tasks rather than every turn. Reference available commits/paths and a candidate manifest for uncommitted work. Keep observations apart from assumptions; say when history is missing. Leave out secrets and personal data. Do not persist hidden reasoning.
6. Never write that a human verified the log. Present it for its author to check. Commit it only when authorized; the author can confirm the check in the PR.

**Done when:** The summary path is reported for its author to check, or the explicit instruction to omit a log was followed.
