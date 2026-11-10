# Reflection

I spent about two weeks building Relay, a beta testing portal, mostly by telling coding agents what to do and then checking what came back. My teammate did the tester side while I handled the coordinator side, the workflow we both worked under, and an experiment comparing different ways of setting agents up. This is what I took from it, including the parts where I got it wrong.

## The setup

One agent wrote code, and separate agents checked it without permission to edit anything. I split the checks by risk. Anything touching logins, permissions or AI input got two readers, one for correctness and one for security. Ordinary behaviour changes got one. Cosmetic work got none and a human read the diff. Reviewers saw a frozen copy of the change, so nobody was editing underneath them, and after two rounds of repairs the work stopped and went to a person with whatever was left open.

I built it that way for one reason. Every new agent starts with no memory of the repository and has to read itself back into the problem, and that reading is the expensive part, not the thinking. So I wanted as few sessions touching the repository as possible while still getting an independent opinion on the risky bits.

## The checks did not always run

Where something mechanical enforced the rules, they held. Where I trusted a label, they did not. We had a hook supposed to stop the builder touching files outside its area. It could not find Python on that machine, exited quietly with nothing, and let all six agents through on their first attempt. I only caught it because I was checking by hand each time before committing. The fix made it fail loudly instead of silently, which is obvious in hindsight and was not obvious before.

The other failure was mine. On the AI drafting feature I wrote the specs and the code myself, and let the commits say a builder had done it. I committed everything as one lump, reset it, and split it into tidier pieces so the history would look better than the work actually was. I also ran three repair rounds when the rule was two, and went to roughly twice the size limit I had set without asking anyone. Two days later I had to correct the header of my own summary from session data because it named the wrong model.

## Agents stalling, waiting and retrying

Most sessions had no retries. The ones that did were tooling, such as a linter refusing a literal null byte I had smuggled in through shell escaping. Fine, minutes lost.

The real waiting was structural. On the first night I ran eight slices through one orchestrator session, and afterwards I could not say what any single slice had cost, because there was one running total for the whole night. That is a sign I was holding too much at once, and I did not notice at the time.

The experiment produced the clearest failure of all. In three of eighteen unattended multi agent runs, the coordinator finished its turn while a background builder was still working, and the run simply ended there. Nothing errored. It just stopped, and if I had not been checking, silence would have looked like success.

## What the team cost and what it bought

Yes where a bug was cheap to miss, no where the review had nothing new to read. The strongest case was an AI drafting branch where my own tests were green while a user journey still worked with every security token stripped out, and a second bug had the mapping between drafts and acceptance criteria reversed but passed all eighty seven AI tests. I would have shipped both.

The price is real. In an experiment over fourteen setups and four tasks, on a strong model, doing everything in one session was 43 to 45 percent cheaper than a builder plus reviewers, and took less wall clock time. About half the money in team runs went on agents re-reading the repository. A six role workflow cost the same as mine and found nothing mine had missed. A guard test over behaviour that already existed burned around 40 percent of that slice's agent tokens for zero product findings.

So I would use the team where a green suite can still be wrong, meaning logins, permissions, AI input and state machines. I would not use it for small tidy-ups, and I would never use it where the roles mostly read the same files to agree with each other.

## Arguments between agents

There was no voting and there should not be. Acceptance criteria decide, so a finding gets settled by pointing at a criterion, a test or the code. Reviewer findings are claims, not orders. Twice both reviewers made the same wrong finding about case IDs and both had to walk it back, so agreement between two readers is not evidence. When a builder refused a low finding with a reason, the reviewer accepted it, which is the system working. When I passed a half wrong review claim straight to the builder without checking it, it cost an extra round to undo, which is the system failing on my side.

## Writing instructions for agents

I wrote the agent rules as policy rather than advice, so they could not be negotiated with. The parts that mattered most were telling an agent what to treat as data rather than instruction, since code comments, issue text and review comments are all written by someone else, and then keeping each fact in exactly one file. That last one sounds fussy, but nearly every review finding I got was not a logic error. It was a spec claiming a test existed when it did not, or a decision recorded in a plan but never in the spec. When the same fact lives in two places, the agent follows whichever one it read last.

For weaker models I kept the instructions blunt, with file paths and explicit stop conditions rather than nuances to interpret.

## Giving context up front or making the agent find it

Rules, scope, budget, the criterion identifiers and any decisions already made went up front. Code and long specs were left to be retrieved. Sending whole specs up front would have multiplied exactly the cost I was trying to cut, since the agent re-reads them anyway.

The exception is anything that changes what the task means. A missing decision does not make an agent ask, it makes it invent something. So decisions and limits always travelled with the brief.

## Notes for whoever comes next

My stand-in for a notes file was a short plan per feature plus the summary I wrote afterwards. What actually let another session pick up was boring detail. Where the branch started, what was in and out of scope, the list of checkpoints with the files each one touches, which decisions a person had approved, what was still open and why, and the next step. One builder session ran through four checkpoints, a repair round and a follow up because a fresh orchestrator could read the plan between each.

## When more context made things worse

A few signals showed up. My usage accounting quietly collapsing into one number for a whole night of work meant the context was already too broad for me to reason about precisely. Reviewers repeatedly finding records that had drifted out of sync meant facts were duplicated. Writing a summary from what I assumed rather than what the session actually reported bit me directly when the model name was wrong.

There was a worse version of that last one. I briefed a task by calling a design confirmed, and a reviewer went looking for the confirmation and found none. I had repeated my own earlier writing back to myself as if it were evidence.

## Cache and token use

Caching mattered more than I expected. When I fitted the reported costs across the experiment, cache reads were about 41 percent of spending, cache writes about 37 percent, and actual output only about 22 percent. A cache miss is not a delay, it is buying the same context again at the write price.

What worked was keeping the top of the prompt stable, meaning the rules, then the role, then the specs, read in the same order every time, and not rewriting the header or the plan in the middle of a task. Hit rates landed between about 90 and 98 percent once I did that. I also kept a session alive across checkpoints instead of restarting an agent to re-read everything, which was the single largest saving available.

I tried a compression proxy and would not bother again. It saved around one percent of bytes while sitting in front of the credentials.

## Which tasks ate the tokens

Long orchestrator sessions that spanned several features, the experiment itself, and features that needed repeated repair rounds. The experiment was by far the biggest, close to two billion tokens across four tasks and a hundred odd runs, though most of that was paid deliberately for a fair comparison.

The clearest single day was one where I moved 327 million tokens, and more than half of it was the orchestrator rather than the agents doing the work. That is the number that made me change how I split up features.

## Choosing models

Every model I tried passed every hidden test, including the cheap ones. On the hardest task the same setup cost about 13 dollars on a strong model and under 2 on a cheap one. That told me model choice matters far less than how the work is broken up and how much of the repository is reloaded each time. Effort settings did matter for reviewers, where almost all of the output was reasoning.

One thing I would never allow again is letting an agent pick its own reviewer. A cheap model chose an expensive one and tripled the cost.

## What I would do differently

Measure usage per feature rather than per day, so I never again have to say I cannot tell what something cost. Escalate at the second failed repair instead of quietly running a third. Keep myself out of the code when the process says a builder writes it, and if I do write it, say so plainly at the time. Build inside the orchestrator session for unattended work so nothing gets cut off. Treat a control as broken until I have watched it run, because the hook proved that. And not close an issue until its follow-ups are actually merged.

