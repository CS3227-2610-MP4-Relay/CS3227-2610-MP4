# Relay MP4: speaker notes

Notes for [Relay-MP4.html](Relay-MP4.html), about 30 minutes in total. The time beside each slide is a budget, not a script length to hit exactly.

| Slides | Speaker | Focus | Time |
| --- | --- | --- | --- |
| 1–4 | zheng-jj | Product and the Test Coordinator role | 6 min |
| 5–8 | Whimsyturtle | Beta Tester role; multi-agent workflow, SWE and CI/CD | 6 min |
| 9–19 | zheng-jj | Agent-setup and Hermes experiments | 9 min |
| 20–31 | Whimsyturtle | App-context experiments and conclusion | 9 min |

Slides 11, 12, 22, 23 and 24 show full prompts and sample output. They are there in case we are asked; say one or two sentences and move on.

---

## zheng-jj · slides 1–4 · 6 min

### 1 · Relay (0:50)
Hi, we are zheng-jj and Whimsyturtle, and this is Relay: a beta-testing portal for small software teams. It connects the person who prepares the tests with the people who try a build and report what happened.

The colour bar at the bottom of each slide shows who is speaking. Blue is me, purple is Whimsyturtle. I will introduce the product and the Test Coordinator role. Whimsyturtle covers the Beta Tester role and how we built Relay with agents. Then each of us presents one experiment: mine on agent setups, Whimsyturtle's on the context we give the app's AI.

One question runs through all four parts: how do we get useful work from AI without paying for more than we need?

### 2 · One testing loop, two roles, one AI feature each (1:35)
Picture a small team with a new build, a few acceptance criteria and some people willing to test. Relay turns that into one loop.

The Test Coordinator, in blue, prepares a round: acceptance criteria, and test cases linked to them. Publishing names the build and opens the round. The Beta Tester, in purple, runs each case against the software, which runs outside Relay, and records Pass or Fail with an observation. The coordinator reviews the results. If something failed and a fix arrives, the coordinator requests a retest on the new build, which is the dashed arrow, and the loop repeats. When the round is done, closing makes it read-only.

Each role gets exactly one AI feature, placed where the writing is tedious. The coordinator can ask AI to draft test cases from selected criteria. The tester can ask AI which details are missing from an observation.

In both cases the AI only suggests. It has no tools. A person reviews the suggestion and takes a separate action to save anything, and if the AI service is down, the manual path still works. In lecture terms, that is human oversight with an approval gate on every change of state.

Underneath it is Django and PostgreSQL, with every LLM call going through one gateway to the SoC LLM. Next, the coordinator's side in the real app.

### 3 · Test Coordinator: prepare a round, then publish it (1:35)
This is the real round page, shown in full. The page continues in the right-hand column. I built the coordinator side.

A new round starts in Draft, box one. In Draft I add acceptance criteria, box two, and test cases. Each test case has steps, an expected result, and links to the criteria it checks, box three. So every case traces back to a requirement. That is the traceability check from our testing lectures, built into the data model.

Box four is the entry to the AI feature, which is the next slide.

Box five is publishing. I type a build label and the round becomes Open. From that moment the criteria and cases are frozen, so a test means the same thing for every tester while results come in.

After that I review results per case and per build. If a case failed, I request a retest and name the new build. The old result keeps its old build, so a Fail on one build and a Pass on the next are two separate records. Closing the round makes everything read-only.

The design point is that publish, retest and close are explicit states that the server checks, not something the team has to remember.

### 4 · AI drafts test cases; the coordinator decides (2:00)
Here is the AI drafting page, again shown in full.

Box one is the notice: the selected criteria are sent to the SoC AI service, and suggestions are not saved. In box two I tick one to five criteria. I never type free text to the model; the input is only criteria that already belong to this round. Box three sends the request.

Box four is one suggested test case: a title, numbered steps, an expected result, and the criteria it claims to cover, so I can check it against the source. Box five, Use this draft, opens the normal new-test-case form with the fields filled in. I still have to review it and press Add test case myself. So nothing the model returns reaches the round without two human actions.

The four lines on the left show what protects this. On the way in, the criteria are written by users, so the system prompt treats them as data, not instructions. That is our defence against prompt injection. The call goes through the shared gateway, with quotas and a deadline. On the way out, the reply must be one JSON object with a fixed shape, and a strict parser rejects anything else, so the model cannot smuggle in a change of state. And saving stays with me.

If the AI is unavailable, the page says so and I add cases by hand.

That is the coordinator's side. Whimsyturtle now takes the same round from the tester's side.

---

## Whimsyturtle · slides 5–8 · 6 min

### 5 · Beta Tester: record what happened on this build (1:20)
Thanks. I built the Beta Tester side.

A tester opens a published round, reads a case, tries the software, and comes to this page to record what happened. Box one is the build the result belongs to. Box two is the outcome, Pass or Fail, and box three is the observation; a Fail needs one. Box four lets the tester save a private draft first and submit when ready. Once submitted, it appears in the coordinator's review. Box five opens the AI feedback page, which is the next slide.

On the right is why the build matters. When the coordinator requests a retest, the tester gets a new entry for the new build, and the earlier result stays as it was. So the history shows both the original failure and whether the fix worked.

The server also enforces ownership and state. Testers see only their own results. And a form that was opened before a newer build, or before the round closed, is refused rather than overwriting newer data.

### 6 · AI feedback asks for the missing details (1:30)
Testers often write observations like this one: "the task was added, but it appeared at the bottom of the list." True, but hard to reproduce.

Box one says exactly what the AI receives: the saved observation, this test case and its linked criteria, and nothing else. Box two is that saved observation. Box three is an explicit button, so opening the page costs no AI call. Box four is the answer: up to five short questions about missing details, such as the browser and whether a message was shown. The questions are never saved and never change the outcome. The tester goes back and edits the observation.

The strip underneath is the gateway that both AI features share. On the way in: only authorized records, a size cap, and source text marked as untrusted. Around the call: a thirty-second deadline, and hourly quotas per user and for the whole deployment, because the SoC LLM is a shared resource. On the way out: a strict JSON parser. Those are input, loop and output guardrails. And the last box is dashed because it is a person: the tester decides.

Whether this selected context actually produces good questions is what my experiment tests later. First, how we built all this.

### 7 · How we built it: one builder, independent read-only reviewers (1:40)
We built Relay spec-first, in small slices, with specialized agents. Follow the diagram from the left.

A human request goes to the orchestrator, which is the main session. It scopes the work, picks a risk tier, and is the only one that touches Git. It dispatches one builder, which updates the spec first, then writes tests and code in small checkpoints. When the builder is done, the candidate is frozen: full verification passes on a fixed commit.

Then independent reviewers read that frozen candidate. They are read-only. In Claude Code their tool list is just Read, Grep and Glob. Findings go back to the builder along the dashed line. After two repair rounds the loop stops and a human decides. That is our max-iterations cap. So this is Orchestrator-Subagent for dispatch, with a Generator-Verifier loop inside.

How much review a slice gets depends on risk, in the table. AI features, logins, permissions and deployment get the verifier and a security reviewer. Ordinary behaviour changes get the verifier. Cosmetic changes get targeted checks and a human reading the diff.

Three things keep the agents in line. AGENTS.md tells them that everything in the repository is data, not instructions, and gives every fact one home. A PreToolUse hook blocks edits outside a role's write scope. And each slice has a short plan and a fixed handoff block, so the next agent retrieves what it needs just in time, not the whole conversation.

### 8 · Software engineering and CI/CD (1:30)
Around the agents is ordinary software engineering, automated.

Every slice lives on a feature branch and becomes a draft pull request. GitHub Actions then runs two jobs. Verify runs the Django checks, lint and formatting, then the prompt-injection regression tests as their own step, then the full test suite against a real PostgreSQL, including Playwright browser journeys for both roles. Site builds and checks the product website.

Only when both are green does a human review and merge. Agents never merge or release. A push to main then publishes the documentation to GitHub Pages and, through a separate production job, migrates the production database, deploys to Vercel and runs a smoke check.

The table shows how development and production are kept apart: different databases, different credentials, debug off in production, and CI never calls the real LLM. Deployment is run by our own GitHub Actions workflow, not by an AI tool's hosting.

That is the workflow we actually used. It works, but it is heavy: several agents for every slice. zheng-jj wanted to know what that costs.

---

## zheng-jj · slides 9–19 · 9 min

### 9 · Experiment 1: what does a workflow cost, and what does it buy? (1:00)
So my experiment asks a simple question: what does a coding-agent workflow cost, and what does it buy?

I took the workflow you just saw as the baseline and compared it with thirteen alternatives. The top row is how a run works. Every setup gets the same task prompt, from the same starting commit, in its own clone with its own test database and no web access. The human's decisions are written into the prompt, so no run waits for a person.

The bottom row is the lecture's recipe for evaluating a workflow, and what we did for each step. The important one is step three: five graders of three kinds. A hidden test suite the agent never sees, the project's full verification, five planted bugs that the run's own tests must catch, a blind review of the diff, and an audit of the transcript. In total, 135 counted runs.

### 10 · Four real tasks, fourteen setups (0:50)
The tasks are four real issues from our backlog, in rising difficulty. Task one is small: refuse hidden text-direction characters in twelve inputs. Task four is the hardest: limits on sign-in that must hold under simultaneous requests. I added tasks three and four because the first two were too easy to separate the setups.

The fourteen setups fall into five families. Different workflows, from our multi-agent baseline down to a single session. Different models, from Opus down to DeepSeek. Three methodology toolkits, including spec-kit and OpenSpec. Three token-saving add-ons. And an ideal setup that I tuned from the results.

Comparisons are always made on the same model. The next two slides are the exact prompt and one scored result, for reference.

### 11 · Setup: the full task prompt (0:25)
This is the complete task-one prompt, word for word. I will not read it. Three things matter. It points the agent at the repository's own workflow, so the setup is the only thing that changes between runs. It gives the human's decisions up front, including exactly which characters to refuse. And it fixes the boundaries: local only, no push, no web.

### 12 · Sample output: one Hermes run, as scored (0:30)
And this is a complete scored result for one run: DeepSeek in Hermes, on that prompt. On the left is every field we record. It cost thirteen cents, took about ten minutes, passed all 132 hidden tests and full verification, and wrote the spec before the code.

On the right are the five bugs we planted in the line it wrote. Its own tests caught all five. Every run in the experiment has a record like this.

### 13 · Result 1: every setup passed (1:00)
First result: the tests did not separate the setups. All 135 runs passed the hidden suite and full verification, and 133 caught all five planted bugs. If I had stopped at green checks, I would have concluded that every setup is equally good.

The blind reviews say otherwise: 58 findings of Medium or above, five of them High. The table on the right sorts them. Most are not logic bugs. They are records drifting apart: an earlier requirement quietly dropped or rewritten, a spec claiming more than the code does, or an old test weakened so that it still passes. Only seven were wrong behaviour, all in places the hidden tests did not look.

This is why the lecture asks for several kinds of graders. The deterministic ones hit a ceiling, and the review found what they could not. And because the test results were level, the real differences are in cost.

### 14 · Result 2: building in one session cost about half (1:05)
Second result: cost on Opus, compared with our multi-agent baseline in the first row. Green is cheaper or faster, red is dearer or slower.

Look at the rows that build in one session: solo, superpowers, spec-kit, OpenSpec. They cost 43 to 65 percent less and finish in about half the time, with the same quality scores.

Now the rows that add things. MP3's six roles cost the same as the baseline and found nothing extra. The add-ons looked good on task one, but follow them across to task four: two of them cost more than the baseline. Their savings do not hold.

The last row is the ideal setup I built from these findings: about a quarter cheaper on average. On the hardest task it costs the same, because review and repair rounds are charged at Opus prices.

So the pattern is: fewer hand-offs, lower cost. The next slide shows why.

### 15 · Why: the money goes on hand-offs (1:05)
Each bar is where an average Opus run's money goes. In the multi-agent baseline, more than half goes on subagent context, the orange part.

The reason is prompt caching, in the row below. A session that keeps running reads its context from the cache cheaply. But every subagent starts with an empty context. It reads AGENTS.md, its role, the specs and the code again, and writes all of it to a fresh cache. And a cache write costs about twenty times a cache read. Our baseline started nine to twelve subagents per task.

A solo session reads the repository once and keeps its cache warm, so most of its spend is the main session doing the work. The ideal setup sits in between: one building session, plus a reviewer. The reviewer is worth its fresh context, because it brings an independent opinion.

This is the lecture's trade-off for specialized agents, made concrete: the coordination cost is mostly re-reading.

### 16 · Hermes: the same workflow in a third tool (0:45)
A setup is only useful if it survives outside the tool it was tuned in. So I packaged the ideal setup as one folder of plain Markdown: the workflow steps, one file of project facts, and the reviewer roles. Each tool gets a thin adapter that just points at that folder.

Then I ran it in a third tool, Hermes, with a cheap open model, DeepSeek v4.1 Flash. The box shows the launch command as it was run: the same prompt file, reasoning high, and only the tools it needs.

One limit, stated plainly: the read-only reviewer is enforced by the tool only in Claude Code. In Codex and Hermes it is an instruction.

### 17 · Hermes results (1:05)
Here are the Hermes results. The top table is the same model in the same tool, with two setups.

On task one, the ideal setup cost 13 cents against 33, and took ten minutes against 68, with identical quality. On task four the trade-off flips. The ideal setup cost a little more and took longer, but its tests caught all five planted bugs where the baseline caught three, and it drew one Medium finding where the baseline drew two. So on the hard task, in Hermes, the ideal setup bought quality, not savings. Task three has no baseline run because the API key reached its spending limit.

The bottom table holds the setup fixed and changes the model, on the hardest task. Every model passed the hidden suite: thirteen dollars on Opus, under four on Sonnet, and about thirty cents on DeepSeek. Model choice moved the cost by more than forty times. It did not move the test results.

### 18 · The setup we recommend (0:45)
This is the setup I recommend, version seven. One session does everything in blue. It specifies first and builds test-first. Then comes a consistency check, which exists because most review findings were records drifting apart. Then it freezes the candidate, and one independent, read-only reviewer checks it, with at most two repair rounds. It is a Generator-Verifier loop with a single generator.

I also tested a version eight with four more rules. The table shows task three: it cost more on every model, and the reviews found no less. So I did not adopt it. A rule costs context on every run, so it has to earn its place.

### 19 · What I take from experiment 1 (0:30)
To sum up my part. Keep one building session, exactly one independent reviewer, a consistency check, and try the cheaper model first. Drop, or measure first, builder subagents, extra roles and add-ons, and never let a model choose its own reviewer.

This is one Django project and four tasks, so treat it as a strong hint. Whimsyturtle asked the same question inside the product: does giving the AI more context help?

---

## Whimsyturtle · slides 20–31 · 9 min

### 20 · Experiment 2: does extra context help the app's AI? (1:00)
My experiment moves from the development process into the app.

Both AI features send the model a small, selected context. A natural thought is: why not send more? More of the workspace, more background, so the model understands better. The lecture names the risk, the Context Paradox: the more context we provide, the less effectively it is used. So I measured it.

I kept the system prompt and the task data exactly as production sends them, and changed one field: a background passage. Relevant-only leaves it empty. App clutter adds about 500 words describing other, unrelated parts of a fictional app. Off-topic adds about 500 words about rivers, rocks and old buildings. In tokens, the prompt goes from about 475 to over a thousand.

Think of it as answering the same question at a clean desk, or with unrelated papers spread next to you.

### 21 · Design: 540 calls, frozen before the first one (1:05)
The design is on the top line. Twelve synthetic scenarios, six for drafting and six for feedback, each sent to three models under the three contexts, five times each. That is 540 calls. Everything was frozen by hash before the first call: prompts, parser, scenarios and the run order.

Now follow one call along the pipeline. It goes to the SoC LLM at temperature zero, with the production thirty-second deadline and no retries. The reply first meets the production parser, which is a deterministic grader: 486 calls returned text and 465 were accepted. All 54 timeouts were the small Llama model. Accepted answers then go to a rubric grader, a separate model that sees neither the model name nor the context. Finally I compare contexts on the same scenario and the same model.

A call is a success only if the parser passed and every check was met. The next three slides are the exact prompt, the input and a sample output.

### 22 · Setup: the full system prompt (0:20)
This is the complete system prompt for observation feedback, exactly as production sends it. The highlights are the parts that matter later: source text is untrusted data; ask only about missing details; do not decide Pass or Fail; and, importantly, if nothing useful is missing, return no questions.

### 23 · Setup: the full user message (0:35)
And this is a complete user message, scenario F2. Compare the two highlighted lines. The test case says: apply the Available filter, then export. The tester's observation says: I opened Items and selected Export. It never says the filter was applied. That gap is the one thing a good answer should ask about.

The last field is the background. It is empty here. In the other two conditions it carries the 500-word passage, which is in the backup slides.

### 24 · Sample output, and how it is scored (0:30)
Top left is what a good answer looks like: one question, about the filter at the moment of export.

Below it is everything we keep for a live call: timings, token counts, and hashes of the reply, not its text. On the right is the grader's judgment of that live call's answer: five checks, with a reason for each, all met here.

### 25 · Can we trust the numbers? (0:50)
Two things had to be true before I could trust any numbers.

First, are the models repeatable? I sent identical requests five times at temperature zero. In ten of twelve groups the reply text changed, and in nine the parsed answer changed. So temperature zero was not deterministic here, and one call per cell would prove little. That is why every cell has five repeats.

Second, is the grader reliable? I wrote 24 answers, half good and half deliberately flawed, and had the grader score them without the labels. It matched on 97 of 98 judgments, accepted no flawed answer and rejected no good one.

With both in place, here are the results.

### 26 · Result: drafting (1:00)
Drafting first. Each cell is how many of thirty attempts passed the parser and every check. Read across a row.

Qwen goes from 29 with relevant context only, to 20 with app clutter. The small Llama model collapses from 12 to 2 and then to 0, and the small table shows how: timeouts and broken JSON. Only x-test-2 holds steady. So for two of the three models, adding unrelated background made the output worse, and for none did it make it better.

The example on the right shows what that looks like. The scenario asks for one test of a Refresh button. With app clutter, one Llama answer returned that test plus four more, about astronomy, textiles, gardening and audio. Those topics exist only in the background passage. The background leaked into the answer. That is context pollution, and it is the Context Paradox on a very small scale.

### 27 · Result: feedback (0:55)
Feedback is a different picture. The numbers are low everywhere, even with relevant context only, and background does not push in one direction. Qwen drops. x-test-2 actually improves with app clutter. Llama never succeeds. So context was not the main problem here.

The main problem is in the small table. Two scenarios are complete reports: the tester already wrote everything needed, and the right answer is an empty list. Not one accepted answer did that. Zero out of 43, on both. Every model asked unnecessary questions, in perfectly valid JSON.

In the lecture's terms this is a negative control, and our no-change accuracy is zero. For the product it means a tester with a good report still gets questions, and that teaches people to ignore the feature. The parser cannot see this. Only the rubric did.

### 28 · Resource cost (0:50)
What did the extra context cost? The background adds about 580 input tokens to every call, which more than doubles the prompt.

Red cells are worse than relevant-only, green are better. Input tokens go up in every row. Success goes down or stays flat in five rows of six. And latency moves in both directions, so response time will not warn you about the waste.

In the lecture's words that is tokenmaxxing: more tokens spent, no outcome gained. And because the SoC LLM is shared and rate-limited, those tokens come out of everyone's allowance. So Relay keeps sending only the selected context, and now we have a measurement behind that choice.

### 29 · Next: fix the prompt, then measure again (0:40)
The experiment also tells us what to fix next, and it is the prompt, not the amount of context. Three small clarifications. Say explicitly that an empty list is the right answer for a complete report. Say that case steps are what the tester was asked to do, not what they did. And say that background adds no requirements.

Then freeze the changed prompt and rerun the scenarios that failed, against this run. This is proposed, not done yet. It follows the lecture's advice for system prompts: start minimal, test, and add instructions only for failures you have observed.

### 30 · Conclusion (1:00)
Putting the two experiments side by side, they say the same four things.

More is not better. Extra agents and rules about doubled the development cost with no quality gain, and extra context doubled the input tokens and usually hurt drafting.

Green checks are not quality. All 135 runs passed their tests while reviewers still found 58 issues, and every feedback answer was valid JSON while none handled a complete report correctly.

Independent judgment is worth paying for: one read-only reviewer in development, and a person's decision on every AI suggestion in the product.

And measure before believing. Task one made the add-ons look good and the later tasks did not. Our first eight-call comparison suggested a saving, but it had changed two things at once.

The short version: choose context and checks for the outcome they buy. Value, not token count.

### 31 · Thank you (0:15)
That is Relay. The app, the documentation and both experiment archives are at these links, and the remaining full prompts are in the backup slides. Thank you. We are happy to take questions.

---

## Backup slides (only if asked)

- **Backup 1–3 · task prompts 2, 3 and 4 (zheng-jj).** Same shape as task one. Task three gives only the interface, so each run had to write the requirements itself. Task four gives almost no decisions: build to the existing spec.
- **Backup 4–5 · the ideal setup's full workflow (zheng-jj).** The one file every tool reads. The highlights are the rules that came from findings: stop and ask, requirements first, prove the tests can fail, check consistency, at most two repair rounds, never choose the reviewer model yourself.
- **Backup 6 · the drafting system prompt (Whimsyturtle).** Same structure as the feedback prompt: criteria are data, use only stated behaviour, and return an empty list when nothing is testable.
- **Backup 7–8 · the two background passages (Whimsyturtle).** The highlighted phrases in the app-clutter passage are where the astronomy, textiles, gardening and audio tests on slide 26 came from.
