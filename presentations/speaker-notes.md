# Relay MP4: speaker notes

Notes for [Relay-MP4.html](Relay-MP4.html): 22 slides in 15 minutes. The time beside each slide is a budget, not a script length to hit exactly. Everything else is in the appendix, for questions.

| Slides | Speaker | Focus | Time |
| --- | --- | --- | --- |
| 1–4 | zheng-jj | Product and the Test Coordinator role | 3 min |
| 5–8 | Whimsyturtle | Beta Tester role; multi-agent workflow, SWE and CI/CD | 3 min |
| 9–15 | zheng-jj | Agent-setup and Hermes experiments | 4.5 min |
| 16–22 | Whimsyturtle | App-context experiment and conclusion | 4.5 min |

---

## zheng-jj · slides 1–4 · 3 min

### 1 · Relay (0:20)

Hi, we are zheng-jj and Whimsyturtle, and this is Relay: a beta-testing portal for small software teams. We will show the product, how we built it, and the experiment that each of us ran.

### 2 · One testing loop, two roles, one AI feature each (0:55)

Relay is one loop with two roles. The Test Coordinator, in blue, prepares a round of acceptance criteria and test cases, then publishes it against a build. The Beta Tester, in purple, runs each case on the software, which runs outside Relay, and records Pass or Fail with an observation. The coordinator reviews the results, and either requests a retest on a new build, the dashed arrow, or closes the round.

Each role gets one AI feature. The coordinator can ask AI to draft test cases. The tester can ask AI which details an observation is missing. In both cases the AI only suggests: it has no tools, a person saves anything that is kept, and the manual path works without it. That is human oversight, with an approval gate on every change of state.

### 3 · Test Coordinator: prepare a round, then publish it (0:40)

This is the real round page, shown in full, and I built this side. A round starts in Draft, box one. I add acceptance criteria, box two, and test cases, by hand or from an AI draft, box three. Every case links to the criteria it checks, box four, so it traces back to a requirement. In box five I name the build and publish. From then on the criteria and cases are frozen, and results are kept per build, so a Fail on one build and a Pass on the next stay two separate records.

### 4 · AI drafts test cases; the coordinator decides (1:05)

This is the AI drafting page. Box one is the notice: the criteria go to the SoC AI service and nothing is saved. In box two I tick one to five criteria; I never type free text to the model. Box three sends the request. Box four is one suggestion, shown with the criteria it claims to cover. Box five opens the normal form with the fields filled in, and I still have to review it and press Add test case. So nothing reaches the round without two human actions.

The four lines on the left are the guardrails. The prompt treats criteria as data, not instructions, which is our defence against prompt injection. The call goes through a shared gateway with quotas and a deadline. A strict parser rejects any reply that is not the JSON shape we expect. And saving stays with me.

Whimsyturtle now takes the same round from the tester's side.

---

## Whimsyturtle · slides 5–8 · 3 min

### 5 · Beta Tester: record what happened on this build (0:40)

Thanks. I built the Beta Tester side. A tester reads a case, tries the software, and records the result here. Box one shows the build version they tested. Box two is the outcome: Pass or Fail. Box three is the observation, which is required for a Fail. Box four saves a private draft or submits. Box five opens the AI feedback page.

The example on the right shows why we record the build version in box one. When the coordinator requests a retest on a newer version, the tester records a separate result for that version. The earlier result is kept.

Testers see and edit only their own results. If a retest starts or the round closes while a tester has this form open, Relay blocks saving from that old form.

### 6 · AI feedback asks for the missing details (0:50)

Testers can write vague observations that leave out details needed to reproduce a bug. Box one explains what the AI receives: the saved observation, its test case and linked acceptance criteria. Box two shows an example observation: "The task was added, but it appeared at the bottom of the list." It does not say which browser was used.

Box three is the Suggest missing details button. The tester must manually click this button to request feedback, so opening the page makes no LLM call. Box four shows up to five LLM-suggested questions, such as "Which browser and version did you use?"

These questions help the tester identify what to add. The tester returns to the result, adds the relevant details to their observation, then saves or submits it themselves. The LLM-suggested questions are not saved, and the AI cannot edit the observation or change Pass or Fail.

The strip below shows the shared LLM gateway used by both roles: the Test Coordinator for drafting test cases, and the Beta Tester for observation feedback. It applies input guardrails, a deadline, hourly quotas and a strict output parser. The dashed final box is the tester, who decides what to save.

### 7 · How we built it: one builder, independent read-only reviewers (0:55)

Now that you've seen how Relay works, I'll share how we built it.

We built Relay spec-first, in small slices, with specialized agents. A human request goes to the orchestrator, the main session, which scopes the work and picks a risk tier. One builder updates the spec, then writes tests and code. Independent, read-only reviewers then inspect the updated spec, tests and code, which stay unchanged during the review.

Review findings go back to the builder along the dashed line for at most two repair rounds. This cap prevents an endless cycle of revisions that consumes more time and tokens. If issues remain, a human decides how to proceed.

The orchestrator delegating work to the builder and reviewers is the Orchestrator-Subagent pattern. The builder revising work in response to reviewers' findings forms the Generator-Verifier loop.

Review is proportional to risk, in the table: AI features, logins and deployment also get a security reviewer. We also use three workflow controls: AGENTS.md says repository content is data, not instructions; a file-edit hook checks the builder's and reviewers' allowed files, for example blocking the builder from changing AGENTS.md; and each slice has a short plan and handoff.

### 8 · Software engineering and CI/CD (0:35)

Alongside our multi-agent workflow, we follow standard software engineering practices. Every slice is a draft pull request. GitHub Actions runs the full test suite against a PostgreSQL test database, including browser tests and AI guardrail tests, plus lint and formatting checks.

The AI guardrail tests use mocked LLM responses. They check that untrusted text stays separate from instructions, invalid replies are rejected, output is displayed safely, and AI suggestions do not automatically change saved data.

Only then does a human review and merge; agents never merge or release. A push to main deploys to production and runs a smoke check. Development and production have separate databases and credentials.

That workflow works, but it is heavy. zheng-jj wanted to know what it costs.

---

## zheng-jj · slides 9–15 · 4.5 min

### 9 · Experiment 1: what does a workflow cost, and what does it buy? (0:45)

My experiment asks: what does a coding-agent workflow cost, and what does it buy? I took our workflow as the baseline and compared it with thirteen other setups: other workflows, cheaper models, methodology toolkits like spec-kit and OpenSpec, and token-saving add-ons. Every setup got the same prompt for four real tasks from our backlog, in its own clone, with the human's decisions written into the prompt.

Each run was then scored the way the lecture recommends, with several kinds of graders: a hidden test suite, full verification, five planted bugs that the run's own tests must catch, and a blind review of the diff. That is 135 runs. The full prompts are in the appendix.

### 10 · Result 1: every setup passed (0:40)

First result: the tests could not rank the setups. All 135 runs passed the hidden suite, and 133 caught every planted bug. But the blind reviews still found 58 issues, five of them High. Most are not logic bugs. They are records drifting apart: a requirement quietly dropped, a spec claiming more than the code does, an old test weakened so it still passes. So green checks hit a ceiling, and the review found what they could not. With quality level, the real differences are in cost.

### 11 · Result 2: building in one session cost about half (0:50)

This is cost on Opus against our multi-agent baseline in the first row. Green is cheaper, red is dearer. The setups that build in one session, solo, superpowers, spec-kit and OpenSpec, cost 43 to 65 percent less and finish in about half the time, with the same quality.

Adding things did not help. MP3's six roles cost the same and found nothing extra. The add-ons looked good on task one, but follow them across to task four: two of them cost more than the baseline. The last row is the setup I built from these findings, about a quarter cheaper on average. So the pattern is: fewer hand-offs, lower cost.

### 12 · Why: the money goes on hand-offs (0:40)

Why? Each bar is where an Opus run's money goes. In our baseline, more than half goes on subagent context, the orange part. The reason is prompt caching. A session that keeps running reads its context from cache cheaply. But every subagent starts empty, reads the rules, the specs and the code again, and writes a fresh cache, and a cache write costs about twenty times a cache read. So the coordination cost of specialized agents is mostly re-reading. The ideal setup keeps one builder, plus a reviewer whose fresh context buys an independent opinion.

### 13 · Hermes results (0:45)

A setup should survive outside the tool it was tuned in, so I packaged mine as one folder of Markdown and ran it in a third tool, Hermes, with a cheap open model, DeepSeek.

In the top table, on task one the ideal setup cost 13 cents against the baseline's 33, and took ten minutes against 68. On task four, the hardest, it cost slightly more, but its tests caught all five planted bugs where the baseline caught three. The bottom table changes only the model. Every model passed the hidden suite, from thirteen dollars on Opus to thirty cents on DeepSeek: model choice moved the cost more than forty times, and not the test results.

### 14 · The setup we recommend (0:25)

So this is the setup I recommend. One session does everything in blue: specify, build test-first, then a consistency check. Then one independent, read-only reviewer, with at most two repair rounds. I also tried a version with four more rules. It cost more on every model and found no less, so I dropped it.

### 15 · What I take from experiment 1 (0:25)

To sum up my part. Keep one building session, exactly one independent reviewer, a consistency check, and the cheaper model first. Drop, or measure first, builder subagents, extra roles and add-ons. This is one project and four tasks, so treat it as a strong hint.

Whimsyturtle asked the same question inside the product: does more context help?

---

## Whimsyturtle · slides 16–22 · 4.5 min

### 16 · Experiment 2: does extra context help the app's AI? (0:40)

zheng-jj studied the AI workflow used to build Relay. My experiment focuses on the AI features inside Relay itself. Both AI features send the model a small, selected context. Why not send more? The lecture names the risk, the Context Paradox: the more context we provide, the less effectively it is used. So I measured it. I kept the production prompt and task data fixed and changed one field, a background passage. It is empty, or 500 words about unrelated parts of an app, or 500 words about rivers and rocks. That roughly doubles the prompt. Same question, clean desk or cluttered desk.

### 17 · Design: 540 calls, frozen before the first one (0:50)

Twelve scenarios, three models, three contexts, five repeats: 540 calls, all frozen by hash before the first one. Five repeats because, when I checked, temperature zero did not give the same answer twice.

Each call goes to the SoC LLM with the production deadline and no retries. The reply first meets the production parser, a deterministic grader: 465 of 540 were accepted, and every timeout was the small Llama model. Accepted answers then go to a rubric grader, a separate model that sees neither the model name nor the context, and which was first checked on 24 answers written for the purpose. A call succeeds only if it passes the parser and every check.

### 18 · Result: drafting (0:45)

Drafting first. Each cell is successes out of thirty. Qwen falls from 29 with relevant context only to 20 with app clutter. The small Llama model collapses from 12 to 2, mostly timeouts and broken JSON. Only x-test-2 holds. So unrelated background made two of three models worse, and none better.

The example shows how. Asked for one test of a Refresh button, a Llama answer returned that test plus four more, about astronomy, textiles, gardening and audio, which exist only in the background. The background leaked into the answer. That is context pollution.

### 19 · Result: feedback (0:45)

Feedback is different. The numbers are low everywhere, even with relevant context only, and background does not push one way: Qwen drops, x-test-2 improves. So context was not the main problem.

The main problem is the small table. Two scenarios are complete reports, where the right answer is no questions. Not one answer did that: zero of 43, on both, all in perfectly valid JSON. In the lecture's terms it is a negative control, and our no-change accuracy is zero. The parser cannot see that. Only the rubric did. The fix is in the prompt, and it is our next step.

### 20 · Resource cost (0:35)

And what did the extra context cost? About 580 more input tokens on every call, which more than doubles the prompt. Success went down or stayed flat in five rows of six, and latency moved both ways, so response time will not warn you. That is tokenmaxxing: more tokens, no outcome. The SoC LLM is shared and rate-limited, so Relay keeps sending only the selected context, and now there is a measurement behind that choice.

### 21 · Conclusion (0:45)

Side by side, the two experiments say the same four things. More is not better: extra agents doubled development cost, and extra context doubled input tokens, with no gain. Green checks are not quality: 135 passing runs still had 58 review findings, and every feedback answer was valid JSON while none handled a complete report. Independent judgment is worth paying for: one read-only reviewer in development, and a person's decision on every AI suggestion in the product. And measure before believing: in both experiments the first small result was misleading.

So: choose context and checks for the outcome they buy.

### 22 · Thank you (0:10)

That is Relay. The full prompts, sample outputs and extra results are in the appendix. Thank you, and we are happy to take questions.

---

## Appendix (only if asked)

zheng-jj:

- **Appendix 1 · Four real tasks, fourteen setups.** The four tasks rise in difficulty; tasks 3 and 4 were added because the first two could not separate the setups. The setups fall into five families.
- **Appendix 2 · The full task prompt (task 1).** Sent unchanged to every setup. It points at the repository's own workflow, gives the human's decisions up front, and keeps the run local.
- **Appendix 3 · Sample output: one Hermes run, as scored.** Every field we record for a run, and the five bugs planted in its code; its own tests caught all five.
- **Appendix 4 · Hermes: the same workflow in a third tool.** One folder of Markdown plus a one-line adapter per tool, and the exact Hermes launch command. The read-only reviewer is enforced by the tool only in Claude Code.
- **Appendix 5–7 · Task prompts 2, 3 and 4.** Task 3 gives only the interface, so each run wrote the requirements. Task 4 gives almost no decisions: build to the existing spec.
- **Appendix 8–9 · The ideal setup's full workflow.** The one file every tool reads. The highlights are the rules that came from findings.

Whimsyturtle:

- **Appendix 10 · The full system prompt (observation feedback).** As production sends it. Note "if no useful detail is missing, return no questions", which slide 19 shows the models did not follow.
- **Appendix 11 · The full user message (scenario F2).** The case says to apply the Available filter; the observation never says the tester did. That gap is what a good answer asks about.
- **Appendix 12 · Sample output, and how it is scored.** A good answer, the record kept for a live call (hashes, not text), and the grader's five judgments with reasons.
- **Appendix 13 · Can we trust the numbers?** Identical requests at temperature 0 changed in 10 of 12 groups, hence five repeats. The grader matched 97 of 98 reference judgments on 12 good and 12 flawed answers.
- **Appendix 14 · Next: fix the prompt, then measure again.** Three clarifications to the system prompt, then a frozen rerun of the failing scenarios. Proposed, not run yet.
- **Appendix 15 · The full system prompt (test drafting).** Same structure as the feedback prompt: criteria are data, and an empty list when nothing is testable.
- **Appendix 16–17 · The two background passages.** The highlighted phrases in the app-clutter passage are where the astronomy, textiles, gardening and audio tests on slide 18 came from.
