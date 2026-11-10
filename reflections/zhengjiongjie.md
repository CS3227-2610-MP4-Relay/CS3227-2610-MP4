# Individual reflection, Zheng Jiongjie (`zheng-jj`)

This covers my work on Relay from 26 October to 5 November 2026. I wrote the workflow and slice skill, the spec-first review pattern, the early Relay slices, the AI drafting and gateway work, the agent-setups experiment, the #67 cleanup redo and the guide and workflow-control work that followed it.

I checked it against the live GitHub repository (47 pull requests I authored, 41 merged), `git log` on `origin/main` at `2ad1057`, my 28 session logs in `logs/zheng-jj`, the plans and the experiment archive.

My first pass ran without network. `gh` could not reach GitHub, the credential sat in a keyring my sandbox could not read, and my clone was 260 commits behind. With network access I pulled the two missing logs (027 and 028) and the full pull request list. Those logs supplied the sharpest evidence here and corrected my first draft.

## Multi-Agent SE

### The pattern

One writer, several readers, one frozen candidate. The orchestrator owns Git state, commits and delivery. `builder` is the only role that writes, and only inside its `writes` list. `verifier` and `security-reviewer` have an empty `writes` list and return findings, never edits.

A slice runs spec, then plan, then numbered commit checkpoints, with the orchestrator committing after a scope check. Review happens on a frozen candidate with a manifest, so builders and reviewers cannot move underneath each other. Tier decides the coordination cost. High risk work gets a builder, a verifier and a security reviewer, Standard gets a builder and a verifier, and Fast lane gets one writer plus a human diff review. Repair stops after two rounds.

I chose that shape because the expensive part is not extra thinking but extra context. Every role starts cold and re-reads the repository, so the pattern keeps low the number of sessions that need the repository in their head.

### Did the rules hold

Mostly, and the failures are the useful part.

The pattern held where artefacts existed. Log 026 reviews exact commit ranges. Log 025 shows every builder run passing a snapshot check. Log 017 records no scope violations and mutations proving the new tests can fail.

Enforcement itself failed open. Log 027 records six builders whose first scope hook check never ran. The Claude hook executes `python`, which was missing from that machine's PATH, so it exited 127 and the edit was allowed. Scope survived only because I checked it afterwards before each commit. PR #137 makes the hook fail closed, returning exit 2 when Python is missing, Python fails, input is unreadable or an exception is raised. A control that cannot show it ran must be treated as absent.

Log 019 is the other counter-example. I wrote the specs and code myself while the commits carried a builder trailer. I committed the work as one commit, reset and re-split it, which is the retrospective history editing the rules forbid. Three repair rounds ran against a limit of two with no escalation. The pull request added 767 source lines against a 400 line budget without asking. The header also named the wrong model and was corrected two days later.

Log 028 adds a smaller one. I closed #67 on its own closing rule while three follow-up pull requests were still open. The right question came back, did I close without finishing those, and it was fair.

The lesson is that a pattern is enforced by artefacts, not role names. A trailer proves nothing. A manifest, a checkpoint handoff and a diff size do. Where I relied on names, the log had to reconstruct what happened and independence was partly lost.

Independent review still earned its place. Log 020 records four defects that passed every local test, including a tester journey that worked with every CSRF token removed and a reversed criterion mapping that passed all 87 AI tests.

### Idle, overloaded, blocked

Log 003 notes that subagent spans overlap and include waiting time, so elapsed time is wall clock rather than work done. Log 004 records a reviewer idle between two intervals, measured as a delta. Logs 005 to 013 are one orchestrator session running eight slices, with usage explicitly not separable by slice. That is the overload symptom I missed at the time. The accounting collapses before the quality does. Log 001 shows the good case, where a builder reported blocked on a pre-existing macOS failure instead of inventing a fix, and that became issue #39.

### Retries and waste

Most logs record zero retries. The ones that happened were tooling, such as a Ruff stop on literal NUL characters (006) and escaping retries (007, 012), and they cost minutes.

The experiment holds the real repeat cost. Log 023 set aside 18 sessions, including runs cut short, a pause and a leaked scratch folder, and six runs restarted from scratch after the pause. Log 022 used 876.8M tokens and log 023 used 2.12B, almost all of it experiment runs.

Log 027 added a different waste. Two machine restarts wiped the scratch area, losing the usage baseline and the mutation backups. I rebuilt the baseline from a value I had printed by chance and reverted two trees by hand.

The repetition I did remove was restarts. One builder ran across four checkpoints in log 025, and reviewers were continued on the same candidate in log 024. Restarting a role to re-read the repository is the most expensive mistake available here.

### Disagreements

There was no voting and there should not be. Criteria are authoritative, so a finding is settled by a criterion, a test or code rather than by who spoke last. Reviewer findings are claims to check. Log 010 shows both reviewers making the same wrong finding about case IDs and both correcting it, so agreement is not evidence. Log 026 shows a builder declining a finding with reasons, which the reviewer accepted. Log 021 shows the cost of the opposite, where I passed a half-wrong review claim to the builder and it took a third round. Log 023 kept a genuine task 4 disagreement between reviewers as a stated limitation rather than averaging it away.

### Did coordination pay

It paid where a defect was cheap to miss and expensive to ship, as in logs 019 and 020. It paid less where review had nothing new to read. In log 017 the two reviewers used about 40 percent of that slice's agent tokens on a guard test over existing behaviour and found no product defect.

It is usually more expensive than building alone. On Opus, single session setups cost 43 to 45 percent less and took 45 to 50 percent less time than this workflow, and about half of each run went on subagents re-reading the repository. A six-role workflow cost the same and found nothing extra. The add-on setups ranged from 32 percent cheaper to 4 percent dearer, with savings that moved between tasks. Three of 18 unattended multi-agent runs ended when the coordinator finished while a background builder was still working.

Use it when a second independent reading of a frozen candidate is worth more than the repository re-read it costs, such as authorization, AI boundaries, state machines and anything where a passing suite can still be wrong. Use one reviewer rather than three, build in the same session for unattended work, and skip it for cosmetic work and guard tests over unchanged behaviour.

## Context Engineering and Resource-aware Use

### Prompts and skills

`AGENTS.md` is written as policy rather than advice. Three parts did most of the work. The first is instructions versus data, so code, issues, handoffs and review comments stay data however they are phrased, which is why I could treat a review comment as a request to discuss rather than a command. The second is one home per fact, a table assigning every fact to a single file. Most of my review findings were records drifting apart rather than logic errors, and a duplicated fact is a future inconsistency. The third is role scope as data, where `writes` and `never_writes` are checked mechanically.

The skills encode the procedure, so the same slice can run in another tool or on another model. For weaker models I kept instructions literal, with explicit paths and explicit stop conditions.

### Upfront or on demand

Policy, tier, scope, budget, criterion IDs and confirmed decisions go upfront. Code and long specs are retrieved. A cold role re-reading the repository was about half of the multi-agent bill, so sending whole specs upfront would multiply the thing I was trying to reduce. The exception is anything that changes what the task means. A missing decision produces invented behaviour, so decisions and limits must come upfront.

### Organisation and following instructions

Stable criterion IDs are the highest leverage formatting decision I made. A finding can name RND-4.2 and the next reader can find it, test it and close it. Headings and tables made token accounting auditable, and the fixed handoff block made role output checkable. The failure mode is equally clear. When a fact lives in two places, a model follows whichever it read last. That is why the ideal setup has a consistency check before review, and why almost all of the experiment's Medium and High findings were drift.

### Handoffs

The plan in `workflow/plans` and the session log did the work of a notes file. What let another session continue was the starting commit, the branch, the tier and budget, the checkpoint list with paths and focused checks, decisions with who approved them, open items with reasons, and the next step. Log 025 proves it, since one builder ran through four checkpoints, a repair round and a follow-ups checkpoint while a new orchestrator read the plan between each.

### When more context hurt

Four signals. Usage that becomes not separable by slice, as in logs 010 to 013, means the context is already too broad to reason about precisely. Repeated consistency findings mean duplicated context. Metadata written from prose rather than observed session data appeared in log 019. Re-deriving state, as when the orchestrator in 023 kept re-surveying which runs had finished, means a status file should have existed. Log 027 adds a fifth. My brief called the gateway design confirmed when the verifier could find no record of it, so a claim read from my own earlier writing became fact inside the task.

### Model choice

The configuration was Opus as coordinator, Opus builder at medium effort and Opus reviewers at high effort, then DeepSeek v4.1 Flash for the Codex and Hermes runs. Holding the setup fixed, every model passed every hidden suite. On the hardest task the ideal setup cost 13.26 dollars on Opus, 3.71 on Sonnet, 1.59 on Haiku and under 0.30 on DeepSeek. Quality separated less than cost did. Two rules I would keep are to never let the agent choose its own reviewer, since Haiku picked Opus and tripled the cost, and to match effort to the job. For reviewers effort is most of the bill, with reasoning taking 93.8 to 95.4 percent of output in log 019.

### Cache

Fitting the reported Opus costs across 21 experiment runs, cache reads were 40.9 percent of cost, cache writes 37.4 percent and output 21.7 percent. A miss is not a latency problem, it is re-buying the prefix at write price.

What I did was keep the top of the prompt stable in the same order, reuse one session across checkpoints, and never rewrite the header or plan mid-run. Hit rates were 83.7 to 94.4 percent in log 017 and 91.9 to 98.0 percent across log 027's eighteen agents, with the long-running orchestrator reaching 99.7 percent in log 028. A compression proxy was not worth it. Headroom saved roughly 1 percent of wire bytes while sitting in front of the credentials.

### Reasoning share

Where the client reports it, reasoning dominates output. It was 45.5 percent for the orchestrator in log 019 and 84.6 percent for the Codex subagents. Claude Code does not separate reasoning tokens, so most of my logs mark that column unavailable, which is a gap rather than a zero.

Persisted reasoning would only help if it captured the shape of the thinking, meaning assumptions, rejected hypotheses and the reason a repair was refused. The repository forbids storing hidden reasoning, so the honest substitute is to persist decisions and assumptions in the plan. An experiment I would like to run gives a second reviewer one paragraph of the first reviewer's assumptions and rejected findings, then measures whether re-review cost drops without losing findings.

### Monitoring and heavy tasks

I used `resource_usage.py` with a baseline before the work, delegated roots for child sessions, overlap removal where sources share history, and unavailable rather than zero for missing counters. I also checked claims, not just tokens. The experiment audit compared self-reported test counts with measured ones and they matched, yet log 023 still found four unsupported claims in the slides and readme that had to be reworded before commit.

The heavy tasks were multi-slice orchestrator sessions, the experiment at 2.12B, the #67 redo and the guides at 169.4M and 158.1M, live repair rounds at about 86M and 90M, and a three round review in #91. The clearest single day is 5 November, with 327.6M tokens across two sessions and 173.2M of that on the orchestrator alone. What worked was structural, through one builder and one reviewer, smaller slices, fewer repair rounds and cached prefixes. What did not work was anything applied after the fact.

## What I would do differently

1. Take a usage baseline per slice so no log ever says not separable by slice.
2. Escalate at the second repair round and at the first size overrun rather than recording them afterwards.
3. Keep the coordinator out of the code when the pattern says the builder writes it, and say so plainly when the coordinator does write it.
4. Build in the coordinator session for unattended work, with no background builder.
5. Treat a control as absent until a test shows it running, because the scope hook failed open exactly as written.
6. Do not close a parent issue until its follow-ups are merged or deferred in writing.
7. Default to one builder and one independent reviewer, with a consistency check before review.

## Sources

The main evidence is my session logs from 001 to 028 in `logs/zheng-jj`. I cite 017 for the access matrix and scope checks, 019 and 020 for the drafting and gateway defects, 023 for the experiment limitations, 027 for the scope hook failure and the lost baseline, and 028 for the premature issue closure. The experiment write-up is in `experiments/agent-setups`, and the rules I evaluated against are in `AGENTS.md` and `workflow/skills/slice.md`. Pull request counts come from `gh pr list --author zheng-jj` on 10 November 2026.

