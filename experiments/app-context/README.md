# App-context comparison

We compared selected relevant context with broader role-visible synthetic context under [CTX-1](../../workflow/specs/ai/context-comparison.md). Method/rubric froze in `d802b54`, exact [inputs](../../src/ai/context_comparison.py) in `103a5ff`, before the 2026-11-02 live pass. Evaluated revision: `a9f701c65c7cf10af97749f573419626efdfc4bc`; corpus `context-1`; configured model `qwen3.6:35b`; instructions `drafting-2` / `observation-feedback-3`. The gateway requested temperature 0; effective provider sampling and seed settings were unavailable.

Execution used the existing local configuration loader and gateway, a disposable loopback database and synthetic operator, with alternating arm order and no retries. Command: `python src/manage.py compare_context --settings=relay.settings.local --live --show-responses --user-id ID --revision a9f701c65c7cf10af97749f573419626efdfc4bc`. All eight gateway invocations returned successful, schema-accepted replies; all numeric measurements were available. Raw replies were viewed transiently and not retained. Command milliseconds include gateway accounting overhead, rather than provider-only inference time.

| Fixed scenario/arm | Accepted items | Prompt/completion/total tokens | Command ms | Provisional rubric assessment |
| --- | ---: | --- | ---: | --- |
| drafting-boundary-selected | 1 | 463 / 171 / 634 | 2563 | All checks met: all four boundaries, observable results, followable steps and supported scope. |
| drafting-boundary-broader | 1 | 512 / 128 / 640 | 1727 | Coverage unmet: omitted the 1-character boundary. Steps/results and supported scope met. |
| drafting-state-broader | 1 | 494 / 77 / 571 | 1433 | All checks met: edit/cancel, restored saved name, unchanged item, executable steps and supported scope. |
| drafting-state-selected | 1 | 445 / 78 / 523 | 1134 | All checks met: edit/cancel, restored saved name, unchanged item, executable steps and supported scope. |
| feedback-incomplete-selected | 5 | 427 / 105 / 532 | 1443 | Unexpected-row evidence met; active-filter and reproduction-action checks unmet. No secrets/outcome decisions or unrelated background questions. |
| feedback-incomplete-broader | 4 | 477 / 86 / 563 | 1220 | Unexpected-row evidence met; active-filter and reproduction-action checks unmet. No secrets/outcome decisions or unrelated background questions. |
| feedback-complete-broader | 4 | 511 / 110 / 621 | 1732 | Empty-question check unmet: redundant filter/status questions and unsupported column-name assumptions. No secrets/outcome decisions. |
| feedback-complete-selected | 5 | 461 / 119 / 580 | 1583 | Empty-question check unmet: redundant filter/status questions and unsupported column-name assumptions. No secrets/outcome decisions. |

Per-arm totals each cover 4/4 available measurements: selected 1,796 prompt + 473 completion = 2,269 reported total tokens, 6,723 command ms; broader 1,994 + 401 = 2,395, 6,112 ms. Selected used 9.9% fewer prompt tokens and 5.3% fewer reported total tokens, but took longer overall. Only the state pair met every rubric check in both arms; selected used fewer tokens and less measured time within that pair. Other pairs do not establish an improvement preserving all required quality checks. Eight deployment-scope accounting rows were inspected once; workspace/user/domain counts were unchanged.

Assessments are the unblinded coordinator model's provisional qualitative judgments (`gpt-6.1-sol`, xhigh); human review remains pending. This four-pair single pass changes context and JSON shape together, has no repetition or seed control, and supports no statistical/general quality, causal latency, injection-resistance or production-readiness claim. Feedback weaknesses occurred in both arms; schema validity did not establish usefulness. Broader evaluation remains separate.
