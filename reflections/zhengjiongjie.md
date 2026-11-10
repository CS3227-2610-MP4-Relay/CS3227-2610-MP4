# Reflection

I spent about two weeks building Relay, a beta testing portal, mostly by telling coding agents what to do. My teammate and I settled on a routine where one agent writes the code and separate ones check it without being allowed to edit anything. I wrote most of that routine myself and then lived with it across roughly forty features. Most of what I learned came from the times it annoyed me.

The checking turned out to be worth more than I expected. I once had a whole test suite passing while a user journey still worked with every security token removed, and another bug had the mapping between drafts and acceptance criteria reversed but passed all eighty seven AI tests. That kind of mistake is invisible from the inside, which is why I stopped trusting an agent to judge its own work.

The cost is the other half of the story. I ran an experiment comparing fourteen ways of setting agents up, and on Opus, having one session do everything was 43 to 45 percent cheaper than a builder plus reviewers. About half the money in the team runs went on agents re-reading the repository because they started with no memory of it. A six role setup cost the same as mine and found nothing mine had missed. So I would keep the team for logins, permissions and anything involving AI input, where green tests can still be wrong, and skip it for small tidy-ups.

It also breaks in a boring way. In three of eighteen runs where I left it working unattended, the coordinator finished its turn while a background builder was mid edit, and the run just ended there. Silence looked like success until I checked.

The part I am least proud of is when I ignored my own process. On one slice I wrote the code myself and still let the commits say a builder did it. I committed everything as one lump, then reset it and split it into tidier pieces so the history would look better than the work was. I ran three rounds of repairs when the rule was two, and I went about twice over the size limit I had set without asking anyone. The log I wrote afterwards had to reconstruct all of this from session data because my own summary was wrong.

The rules were only as good as the things enforcing them, and at one point there was nothing. We had a hook meant to stop an agent editing files outside its area. It could not find Python on that machine, failed silently, and let every one of six agents through. I only caught it because I was checking by hand afterwards. The fix made it fail loudly instead of quietly, which sounds obvious but only after you have watched it not happen.

I also closed a large issue while three follow-up pull requests from it were still open, and got asked, reasonably, whether I had closed it without finishing the work. That stung because the answer was basically yes.

The other lesson is about what I send to an agent. Early on I gave every agent everything it might need and it got slower and vaguer. What worked was short and literal. A few file paths, the exact boundaries, and the decisions already made, with everything else left for the agent to find. An agent re-reading files is expensive, so I kept each session on one job and reused it rather than starting fresh. My cache hit rate sat around 90 to 98 percent once I stopped rewriting the top of the prompt mid task.

Every model I tried passed every hidden test, including cheap ones. On the hardest task the same setup cost about 13 dollars on Opus and under 2 on a cheap model. Model choice mattered far less than how the work was broken up and how much of the repository got reloaded each time.

If I did it again I would keep one builder and one reviewer, take usage measurements per slice instead of per day, escalate at the second failed repair instead of pushing to a third, and not close an issue until its follow-ups are merged.
