# Workflow

How we build Relay with AI agents: spec-driven, in small slices, using a builder and an independent verifier, with a security specialist where risk needs it. This page is for people; the rules agents follow are in [`AGENTS.md`](../AGENTS.md).

One slice is a coherent behaviour small enough to review in one sitting. Use a local identifier until it has a GitHub issue. The [`slice`](skills/slice.md) skill keeps spec-first order, decides how much review the slice gets, and stops a slice that grows too large.

## Files

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Rules for every agent: instructions versus data, where each fact lives, Git, handoffs |
| `CLAUDE.md` | Makes Claude Code load `AGENTS.md` |
| `workflow/agents/` | Builder, verifier and security specialist, each with its write scope |
| `workflow/skills/` | The orchestrator's procedures |
| `workflow/specs/` | The specs, the only home of product behaviour |
| `workflow/plans/` | A compact plan and handoff per slice |
| `workflow/scripts/check_scope.py` | Checks changes against a role's write scope; also the pre-edit hook |
| `workflow/scripts/resource_usage.py` | Collects observable development usage; see its help for inputs and limitations |
| `workflow/scripts/check_logs.py` | Checks the structure of saved session summaries |
| `workflow/scripts/test_*.py` | Tests for workflow scripts, adapters and hook settings |
| `.claude/`, `.codex/`, `.agents/skills/` | Thin role/skill adapters, plus hook and command settings |
| `.github/` | Pull request and issue templates |
| `logs/` | Session summaries checked by their author; explicit requests to omit a log take precedence |

## Using it

| | Claude Code | Codex |
| --- | --- | --- |
| Run a slice | `/slice` and the request or slice identifier | `$slice` and the request or slice identifier |
| Run one role | "Use the builder agent to ..." | "Have builder ..." |
| Review roles | Read/Grep/Glob tools only | No-write instructions, hooks and post-run checks |
| Edits outside a role's scope | Hook in `.claude/settings.json` | Hook in `.codex/hooks.json`, once trusted in `/hooks` |

Both tools load `AGENTS.md`. Codex skill adapters use the [documented `.agents/skills/` layout](https://learn.chatgpt.com/docs/build-skills). Codex [custom agents inherit the parent's permissions](https://learn.chatgpt.com/docs/agent-configuration/subagents); role instructions do not create a separate sandbox. Do not treat a reviewer role as native write prevention in Codex. Project discovery and hooks also depend on client support and project trust. Test role/skill discovery and a prohibited edit in each installed client before relying on the hooks. Activate `.venv` before launching the client so hooks can find `python` on PATH: Git Bash for Claude Code and PowerShell for Codex on Windows. Report unavailable enforcement instead of claiming it worked.

## How scope is enforced

1. Claude's verifier and security-reviewer adapters expose read tools only. Codex's adapters instruct the roles not to write; their permissions are inherited. The verifier independently inspects source and test assertions, and requests actual check results from the coordinator when it cannot run commands.
2. The pre-edit hook runs `check_scope.py --hook` and blocks a known role's file edit outside its scope. Shell commands are not checked, missing or unknown role metadata is allowed, and ignored files are not covered by the Git check. This catches accidents; it is not a security boundary against a malicious agent.
3. Capture `check_scope.py --snapshot <manifest>` before each role and check `<role> --since <manifest>` afterwards. Existing dirty changes are not charged to the next role, but new changes, HEAD movement, staged entries and the assume-unchanged/skip-worktree flags are checked. The older `--base <commit>` mode checks changed paths/HEAD, not staging alone. Neither mode enforces read permissions or proves test quality.
4. Review a fixed candidate. Record the base, diff, untracked source files and actual check results; use a snapshot manifest outside the repository for uncommitted work. Recheck it after review. Snapshots exclude ignored files and secret `.env`/`.env.*` filenames case-insensitively (except `.env.example`), reject redirected parent directories/submodules, and do not identify the external environment. Record relevant environment/check inputs separately. Changes to reviewed inputs invalidate affected evidence.

After changing a role, skill, adapter or hook, run `python -m unittest discover -s workflow/scripts`. In each new clone or worktree, and in each tool you use, check once that the hook works: ask the builder to edit `AGENTS.md`, and it must be refused. Test prohibited access and attempts to weaken tests with synthetic secrets and harmless malicious-content fixtures; record observed actions, not just configured rules.

## Resource-aware coordination

The main session chooses the risk tier, scopes the request and coordinates work. The builder updates the spec before implementation, tests and documentation in one run. The verifier independently checks the final behaviour; a security-reviewer joins under the [slice review triggers](skills/slice.md). Cosmetic changes use targeted checks and human diff review. Reclassify when scope changes.

Pass relevant paths and excerpts, decisions, acceptance/security criteria, checks and open findings. Retrieve other context when needed rather than forwarding the conversation. Run focused checks during edits, then the [slice tier's required checks](skills/slice.md) on the final integrated candidate. Reuse passing evidence only while code, inputs and environment remain unchanged. Give concurrent builders separate worktrees, file ownership and test resources; review their integrated candidate afterwards.

Measure coordinator and delegated usage from the start, plus elapsed time, retries and repair rounds. Logs record quality and defects alongside resource use using the [log skill's format](skills/log.md). Experiments compare the same starting state, model settings and acceptance/security checks, including unsuccessful runs.

### Token reporting

For example, in Git Bash with `.venv` active, choose the session files explicitly and keep the numeric baseline outside the repository:

```bash
python workflow/scripts/resource_usage.py snapshot --codex /path/to/current-session.jsonl > /tmp/relay-usage-before.json
python workflow/scripts/resource_usage.py report --codex /path/to/current-session.jsonl --baseline /tmp/relay-usage-before.json --retries 0 --repair-rounds 0
```

Use `--claude` for Claude session files; repeat the selector for delegated sessions. The collector reads numeric/identity metadata from selected transcripts and emits no message text or raw paths; raw logs remain private. It does not claim coverage of unselected agents. See `report --help` for bounded Codex child discovery and explicit Claude subagent selection. Worktree/out-of-directory children need explicit paths. Keep numeric snapshots outside version control.

- **Totals:** input includes cache reads/writes; output includes reasoning tokens. Cached input and reasoning output are included subsets, not additions to the total. Missing or ambiguous counters are unavailable, never assumed zero. A Claude message, completed Codex export turn or usage-bearing Codex token event with incomplete counters makes affected session/report counters unavailable and emits a warning; same-message Claude fragments may supply the missing counters. Codex rate-limit-only notifications do not imply usage. Logs report tokens without monetary cost fields.
- **Counter decreases:** a falling Codex subset makes that subset unavailable without resetting monotonic input/output/total counters. A primary-counter decrease is treated as a reset only when all three primary counters are available and non-increasing; mixed or incomplete reset evidence makes session totals unavailable. Each case emits a warning; task reports preserve unavailable values.
- **Coverage:** a before/after report measures a task interval. Without a session-start baseline, a snapshot reports only the selected sources' recorded totals; it cannot establish an exact task delta. Record the cutoff and any material omission briefly in the log; work after that cutoff is excluded.
- **Overlapping sources:** count each session once. Forks can repeat inherited cumulative counters with rewritten timestamps, which the collector may not flag. Check parent/fork overlap before combining sources; exclude a duplicate parent when its usage is already included in the selected continuation. Do not add collector smoke-test totals or overlapping interval reports to conversation totals.
- **Timing and operational metrics:** elapsed spans include idle/waiting time and are not active-work durations; concurrent spans are not additive. Token snapshots are not API-call counts. Record calls, retries and repair rounds only from attributable evidence, and omit routine prose about metrics that were not collected. Retain session-specific gaps that affect interpretation.

## Issues and delivery

- A GitHub issue is optional during local planning. When used, it points to spec IDs rather than holding requirements, rules or dependencies.
- Report a bug against the criterion it breaks or identify a spec gap.
- Humans own merge and release decisions. Templates do not configure protection, create issues or deploy anything. Never claim those controls are active without checking them.
