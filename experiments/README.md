# Experiments

This folder will hold experiment methods, reproducible inputs, observed results and analysis. No experiments have been run or results recorded in this scaffold.

## Planned comparisons

| Comparison | Quality checks | Resource evidence |
| --- | --- | --- |
| App context: broader versus selected relevant, authorized context on a small fixed set covering both roles | Requirement coverage and useful drafts; missing-detail detection; unnecessary questions and unsupported suggestions | Observable tokens, calls and latency |
| Development workflow: separate spec/test/plan/build/review stages versus the consolidated builder/verifier workflow on a few small tasks | The same acceptance/security checks; repair effort and remaining defects | Coordinator and delegated-agent usage, elapsed time, retries and repeated work |

Keep task/model settings comparable and define quality checks before seeing results. Replay development tasks from the same starting state in separate runs. Bypass result caching for the app-context comparison; evaluate cache reuse separately if it is implemented. Lower resource use counts as an improvement only when quality remains acceptable.

## Evidence layout

Use one `experiments/<short-name>/` folder per comparison, with a `README.md` describing the question, frozen method, inputs, settings, commands, results and limitations. Keep sanitized supporting evidence alongside it and link to relevant specs, commits and session summaries rather than copying them. Distinguish measured values, estimates and unavailable telemetry; report failures and small-sample limits. Never include secrets, private account state or raw personal data.

Development-control checks should use synthetic secrets and malicious repository instructions. Retain observed actions and outcomes, including whether agents attempted prohibited access or test weakening. Representative ordinary, cosmetic and security-sensitive tasks should show which agents and checks actually ran.
