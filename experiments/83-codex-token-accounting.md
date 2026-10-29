# Codex token accounting investigation (#83)

Date: 2026-10-29. Question: which reported fork, continuation, discovery and subtotal gaps can be reproduced in the existing collector, and what evidence would a repair need?

The investigation reproduces all four classes of limitation with synthetic inputs. It also confirms working cases: preserved fork timestamps, unchanged session identity and bounded descendant discovery, including a linked automatic approval source. No collector fix or historical-total correction is included.

## Method and evidence boundary

- Collector: base `471a4f77c28d255574efbd2be0928d271fd111dc`, [`resource_usage.py`](../workflow/scripts/resource_usage.py), SHA-256 `06757b37eacf9c56696fdbc3ee1bdff7704713a5825042b1d2e4ee63502050fd`; unchanged by this study.
- Harness: [`investigate_codex_usage.py`](../workflow/scripts/investigate_codex_usage.py), using the existing synthetic fixture constructors in [`test_resource_usage.py`](../workflow/scripts/test_resource_usage.py). Deterministic UTC times and invented session IDs/counters; temporary files are removed at exit. It accepts no real-session inputs and performs no network calls.
- Run from the repository root with the existing `.venv` active: `python workflow/scripts/investigate_codex_usage.py`. Exit zero means all 12 **current-behavior observations** matched; it does not mean accounting is correct. Assertions deliberately characterize defects and are outside automatic test discovery. A future collector repair must update or retire affected observations.
- Existing baseline command: `python -m unittest discover -s workflow/scripts -p test_resource_usage.py` → 34 passed in 1.143 seconds before the harness was written. These existing tests establish useful controls; they do not cover every new observation below.
- Scope/settings: standard-library, offline experiment on Windows, unchanged collector and fixture helpers. No provider model is called by the harness. Coordinator/agent usage is separate session evidence in the log, never the synthetic numbers below.

Historical starting evidence is in logs [001](../logs/Whimsyturtle/001-initialize-relay-scaffold-and-log-usage.md#problems), [006](../logs/Whimsyturtle/006-build-django-foundation-and-ci.md#decisions-and-corrections), [009](../logs/Whimsyturtle/009-prepare-checked-product-site-publication.md#problems) and [012](../logs/Whimsyturtle/012-prepare-vercel-and-neon-production-delivery.md#problems). Their observations are not newly replayed historical sessions. No previous total was recalculated.

The [official app-server documentation](https://learn.chatgpt.com/docs/app-server), retrieved 2026-10-29, distinguishes resuming an existing thread from forking stored history into a new thread ID, and describes `sessionId`/`forkedFromId` in its API. It does not establish a stable private-rollout counter provenance contract. Calling every changed-ID continuation a normal resume would overstate the evidence. This study infers collector limitations from explicit synthetic arrangements, not from undocumented client guarantees.

## Observations

Warnings below abbreviate exact codes printed by the harness: **copied** = `codex_copied_history_excluded`; **inherited** = `codex_inherited_or_missing_initial_history`; **baseline** = `added_session_has_no_task_start_baseline`; **unsupported** = `session_has_no_supported_usage`.

| Harness case | Reference under fixture assumptions | Observed result | Warnings |
| --- | --- | --- | --- |
| `rewritten_fork_overlap` | Unique total 248 | Aggregate 468 | None |
| `preserved_fork_timestamps` | Unique total 248 | Aggregate 248 | copied, inherited |
| `independent_equal_counters` | Two independent totals of 220 = 440 | Aggregate 440 | None |
| `same_identity_continuation` | Interval 55 | Aggregate 55 | None |
| `changed_identity_old_start` | Interval 55 known to fixture author | Aggregate unavailable | baseline, inherited |
| `original_baseline_source_omitted` | Original identity absent from final selection | `ValueError`: baseline sessions missing; include every original source | No report produced |
| `changed_identity_rewritten_history` | Interval 55 known to fixture author | Aggregate 165 | None |
| `bounded_descendant_discovery` | Parent, child, nested child, linked guardian | Exactly those four selected | Discovery emits no coverage warning |
| `explicit_other_directory_source` | Previous four plus explicit outside source | Exactly those five selected | Discovery emits no coverage warning |
| `older_approval_missing_baseline` | Old approval source was not baselined | Aggregate unavailable | baseline |
| `inactive_masks_measurable_subtotal` | One measurable session 110; idle source unknown | Aggregate unavailable; row subtotal 110, 1/2 available | None |
| `used_session_without_supported_usage` | One measurable session 110; used source unknown | Aggregate unavailable | unsupported |

### Fork attribution

The parent has cumulative input/output pairs `(100,10)` then `(200,20)`, totaling 220. Its child copies both events and adds `(25,3)`, reaching `(225,23)` or 248 cumulatively. Unique work across the pair is `220 + 28 = 248`.

When copied events precede the child's metadata creation time, `collect()` skips them and charges the first retained event's last usage, 28. When copied events are rewritten to creation time or later, that filter cannot identify them. The first copied event has equal cumulative and last counters, so the inherited-counter heuristic also does not fire. The child is charged 248 and the combined report becomes `220 + 248 = 468`, with no warning.

`collect()` deduplicates within hashed session identities, not across distinct parent/child streams; it does not use ancestry to subtract a shared prefix. The independent-equal-counters control shows why equal token values alone cannot safely identify duplicates. Copied timestamps, ancestry and counter similarity are evidence with different limits; none alone establishes ownership of every event.

### Baseline continuity

The baseline contains 110 tokens at second 5; subsequent cumulative usage is 165, so the fixture's new work is 55. Copies retaining the same identity merge and yield 55. A new identity with an old creation time is treated as unbaselined historical work and yields unavailable, even though its first-event heuristic retained 55. Omitting the original identity altogether rejects the report.

A different-ID stream with a new creation time and rewritten copied events can instead pass the post-baseline check and charge 165, without warning. This is another synthetic risk arrangement, not proof that normal Codex resume behaves that way. Existing `report()` matches hashed identities, not verified continuity or fork lineage; timestamps cannot repair that association by themselves.

### Source coverage

`discover_children()` scans only immediate `*.jsonl` files in one explicitly selected directory, filters candidate working directories and follows `parent_thread_id` or nested `source.subagent.thread_spawn.parent_thread_id`. The fixture confirms transitive selection and a guardian-shaped source with a top-level parent ID. An unlinked same-project source, a different-working-directory child and a previous-directory child are omitted. Explicitly selecting the outside source includes it; this does not automatically search other directories or establish a start baseline.

A read-only metadata check in this session also found a guardian with a parent ID, and current bounded discovery selected it. Automatic approval sessions are therefore not generically undiscoverable. Selecting the wrong coordinator, missing ancestry, day/worktree boundaries and late baseline capture remain separate coverage risks. The synthetic old-approval case emits the baseline warning; an entirely unselected source cannot contribute a warning. Warning-free selected sources do not establish whole-task coverage.

### Inactive sources and subtotals

An initialized metadata-only source remains `awaiting_usage=True`; its counters are unavailable and it has no unsupported-usage warning. `report()` requires every selected row's field to be available before summing that field. One such row therefore makes the aggregate unavailable although the other row measures 110.

The harness separately sums the available row for illustration; the collector has not gained a subtotal field. This is an **available selected-session subtotal**, not a whole-task total, and is not a guaranteed lower bound if overlap is unresolved. An assistant activity marker without supported counters instead produces the unsupported warning. Neither case justifies replacing unknown counters with zero or treating an initialized entry as a completed review. A real inactivity conclusion needs attributable metadata beyond absence of counters.

## Follow-up options, not approved implementation

The smallest viable outcome is this reproducible investigation plus continued explicit accounting caveats under [existing reporting policy](../workflow/README.md#token-reporting). It adds no runtime operating burden. Product requirements and telemetry controls remain unchanged.

| Possible follow-up | Estimated total diff, including tests/docs | Operating burden and decision |
| --- | --- | --- |
| Expose field-specific available subtotals, missing-source counts and explicit incomplete coverage while retaining unknown aggregates | 120–200 lines | No service/dependency; one output-schema compatibility decision. Recommended first, subject to confirmation. Does not solve overlap. |
| Retain explicit task/source baseline associations and bounded source inventory evidence across continuations | 180–320 lines | Operator-selected identities/locations and private manifest lifecycle; no new automatic filesystem scan. Needs confirmation of identity/privacy semantics before design. |
| Investigate reliable shared-history provenance before automatic fork subtraction | 150–300 lines for an additional study, implementation estimate unavailable | Sanitized client evidence or documented event lineage is needed. Equal counters/timestamps are insufficient; defer automatic deduplication. |

These are estimates and options, not acceptance criteria or assigned implementation tasks. Broader discovery, a persistent telemetry store, client integration, billing reconciliation and historical-log rewriting are deferred. No evidence here establishes billing errors, the frequency of these inputs in current clients, or that every earlier reported total is incorrect.

## Execution and next step

The harness completed all 12 observations with exit zero; focused Ruff lint/format passed after formatting the new helper. Exact integrated checks, candidate identities, independent reviews and hosted delivery are recorded in the [slice plan](../workflow/plans/83-token-accounting-investigation.md) and session log. A human can select a bounded repair option after reviewing this evidence; this investigation does not silently authorize it.
