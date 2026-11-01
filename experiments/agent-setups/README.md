# Agent setups

Owner: zheng-jj · Issue: #31 · Run on 2026-10-30 to 2026-11-01

This experiment compared 14 coding-agent setups on four Relay tasks of rising difficulty, at equal settings. The setups covered workflows, model mixes, methodology plugins and token-saving add-ons, and the experiment then tuned one portable setup for any tool, model and repository.

**Results:**
- **Quality:** every counted run passed its hidden tests and full verification, so quality did not separate the setups.
- **Cost:** on Opus, building in one session cost 43–65% less than the multi-agent MP4 workflow. Most of MP4's extra cost went on subagents re-reading the repository.
- **Recommended setup:** ideal v7: one session builds, and one independent reviewer checks.

## The archive

Everything else is in [`agent-setups.zip`](agent-setups.zip), kept compressed so that agents searching this repository do not read it as instructions or requirements. It holds:
- the full write-up and method;
- the slides (`presentation.html`);
- the harness and hidden suites;
- per-run results and planted-bug specs;
- the setup packages v1 to v8.

The experiment paths in logs 022 and 023 (`harness/`, `results/`, `ideal/`) are inside the archive's `agent-setups/` folder.

Unzip it outside the repository:

```bash
unzip experiments/agent-setups/agent-setups.zip -d /tmp/relay-experiment
```

Then open `/tmp/relay-experiment/agent-setups/README.md` or `presentation.html`.
