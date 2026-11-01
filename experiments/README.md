# Experiments

This folder holds experiment methods, reproducible inputs, observed results and analysis.

- [agent-setups](agent-setups/README.md) (zheng-jj, #31) runs the development-workflow comparison below on four tasks. It covers 14 workflow, model, methodology and add-on setups, then a portable setup tested in Claude Code, Codex and Hermes. Its evidence is in a zip archive, so agents searching the repository do not read it.
- [development-workflow](development-workflow/README.md) records one observational run of the consolidated workflow with a weaker model.
- The app-context comparison has not been run.

## Planned comparisons

| Comparison | Quality checks | Resource evidence |
| --- | --- | --- |
| App context: broader versus selected relevant, authorized context on a small fixed set covering both roles | Requirement coverage and useful drafts; missing-detail detection; unnecessary questions and unsupported suggestions | Observable tokens, calls and latency |
| Development workflow: separate spec/test/plan/build/review stages versus the consolidated builder/verifier workflow on a few small tasks | The same acceptance/security checks; repair effort and remaining defects | Coordinator and delegated-agent usage, elapsed time, retries and repeated work |

Keep task/model settings comparable and define quality checks before seeing results. Replay development tasks from the same starting state in separate runs. Bypass result caching for the app-context comparison; evaluate cache reuse separately if it is implemented. Lower resource use counts as an improvement only when quality remains acceptable.

## Evidence layout

Use one `experiments/<short-name>/` folder per comparison, with a `README.md` describing the question, frozen method, inputs, settings, commands, results and limitations. Keep sanitized supporting evidence alongside it and link to relevant specs, commits and session summaries rather than copying them. Distinguish measured values, estimates and unavailable telemetry; report failures and small-sample limits. Never include secrets, private account state or raw personal data.

Development-control checks should use synthetic secrets and malicious repository instructions. Retain observed actions and outcomes, including whether agents attempted prohibited access or test weakening. Representative ordinary, cosmetic and security-sensitive tasks should show which agents and checks actually ran.
